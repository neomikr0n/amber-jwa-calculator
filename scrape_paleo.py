#!/usr/bin/env python3
"""
Downloads the complete dinodex from paleo.gg for Jurassic World Alive.

paleo.gg is Next.js: it serves all the data inside <script id="__NEXT_DATA__">.
No browser is needed. A normal request is enough.

Usage:
    python3 scrape_paleo.py --version 3.24            # uses the cache, only downloads what is missing
    python3 scrape_paleo.py --version 3.24 --refetch  # downloads everything again

`--version` is mandatory and it is THE ONE THING to change when the game
updates. It is written into the dataset as `meta.version_juego`, and the whole
project reads it from there (`rutas.version()`): the page title, the header
badge, the language strings and the exported data all take it from the same
value. Nothing else in the repository carries a version, and no file name does.

Output:
    cache/dinodex.html          index
    cache/<uuid>.html           raw card of each creature
    data/jwa.json               normalized dataset
"""

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from rutas import DATOS

RAIZ = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(RAIZ, "cache")
CARPETA_DATOS = os.path.join(RAIZ, "data")
BASE = "https://www.paleo.gg/games/jurassic-world-alive/dinodex"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
RETARDO = 0.25       # seconds between requests, out of politeness
REINTENTOS = 3


def version_valida(texto):
    """`3.24`, not `3,24`, not `v3.24`, not `3.24.1`.

    The value ends up in the page title and in the stored dataset, so a typo
    here is a typo the user reads. Better to reject it than to write it.
    """
    if not re.fullmatch(r"\d+\.\d+", texto):
        raise argparse.ArgumentTypeError("has to look like 3.24, not %r" % texto)
    return texto


def argumentos():
    p = argparse.ArgumentParser(
        description="Downloads the complete dinodex from paleo.gg for "
                    "Jurassic World Alive.")
    p.add_argument("--version", required=True, metavar="X.Y", type=version_valida,
                   help="the game version this download belongs to, e.g. 3.24. "
                        "It is the only thing an update has to change.")
    p.add_argument("--refetch", action="store_true",
                   help="download everything again instead of reusing the cache")
    return p.parse_args()


def version_guardada():
    """The version already in the dataset, or None if there is no dataset."""
    if not os.path.exists(DATOS):
        return None
    try:
        with open(DATOS, encoding="utf-8") as f:
            return json.load(f)["meta"]["version_juego"]
    except (OSError, ValueError, KeyError):
        return None


def bajar(url, destino, refetch=False):
    """Downloads url to destino. If it already exists and refetch is not asked for, it does not touch the network."""
    if os.path.exists(destino) and not refetch and os.path.getsize(destino) > 5000:
        with open(destino, encoding="utf-8") as f:
            return f.read()
    ultimo = None
    for intento in range(REINTENTOS):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode("utf-8", "replace")
            with open(destino, "w", encoding="utf-8") as f:
                f.write(html)
            time.sleep(RETARDO)
            return html
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            ultimo = e
            time.sleep(1.5 * (intento + 1))
    raise RuntimeError(f"could not download {url}: {ultimo}")


def next_data(html):
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("no __NEXT_DATA__ (paleo.gg has changed the HTML)")
    return json.loads(m.group(1))


# The six stats come in English from paleo.gg and are renamed to the SAME keys
# `stats` already uses. Keeping two keyings for the same six numbers is how the
# app ends up with two orders that disagree.
STAT_KEYS = {"health": "vida", "damage": "dano", "speed": "velocidad",
             "armor": "armadura", "crit": "critico", "critm": "dano_critico"}


def entrenamiento(points):
    """`detail.points` is the Omega training table, and only the 33 Omega
    creatures have it (verified against the whole cache: the card appears in
    exactly those 33 pages).

    Three groups per stat:
      `cap`   where that stat tops out with training,
      `delta` what ONE training point adds to it,
      `pcap`  how many points it takes to reach that cap.
    `pcap` is a datum from the source, NOT (cap-base)/delta: in `stegouros`
    crit damage the division gives 7.5 and paleo.gg stores 7, so the cap is one
    point short of reachable there. The bound that counts is `pcap`.

    It is omitted for the creatures that do not have it, instead of storing a
    null in 486 of the 519 entries."""
    if not points:
        return None
    return {grupo: {STAT_KEYS[k]: v for k, v in (points.get(grupo) or {}).items()
                    if k in STAT_KEYS}
            for grupo in ("cap", "delta", "pcap")}


def main():
    args = argumentos()
    refetch = args.refetch
    version = args.version
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(CARPETA_DATOS, exist_ok=True)

    anterior = version_guardada()
    if anterior == version:
        print(f"      NOTE: the dataset already says {version}. If this is a new "
              f"game version, --version was not bumped.")

    print("[1/3] dinodex index...")
    idx_html = bajar(BASE, os.path.join(CACHE, "dinodex.html"), refetch)
    nd = next_data(idx_html)
    dex = nd["props"]["pageProps"]["dex"]
    items = dex["items"]
    meta = nd["props"]["pageProps"]["meta"]
    print(f"      {len(items)} creatures. paleo.gg updated: {meta['lastModifiedDate']}")

    print("[2/3] cards of each creature...")
    criaturas = {}
    fallos = []
    for i, it in enumerate(items, 1):
        uuid = it["uuid"]
        try:
            html = bajar(f"{BASE}/{uuid}", os.path.join(CACHE, f"{uuid}.html"), refetch)
            det = next_data(html)["props"]["pageProps"]["detail"]
        except Exception as e:                                  # noqa: BLE001
            fallos.append((uuid, str(e)))
            print(f"      [{i}/{len(items)}] FALLO {uuid}: {e}")
            continue

        criaturas[uuid] = {
            "nombre": det.get("name"),
            "rareza": det.get("rarity"),
            "clase": det.get("class"),
            "tipo": det.get("hybrid_type"),
            "version": det.get("version"),
            "publicada": not det.get("unreleased", False),
            "ingredientes": det.get("ingredients") or [],
            "hijos": det.get("hybrids") or [],
            "stats": {
                "vida": det.get("health"),
                "dano": det.get("damage"),
                "velocidad": det.get("speed"),
                "armadura": det.get("armor"),
                "critico": det.get("crit"),
                "dano_critico": det.get("critm"),
            },
            "fuentes_adn": det.get("dna_source") or [],
            "mejoras": det.get("enhancements") or [],
        }
        # Only the Omega creatures carry it (33 of the 519).
        ent = entrenamiento(det.get("points"))
        if ent:
            criaturas[uuid]["entrenamiento"] = ent
        if i % 50 == 0 or i == len(items):
            print(f"      [{i}/{len(items)}]")

    if fallos:
        print(f"      WARNING: {len(fallos)} cards failed")

    # reverse index: who uses whom
    print("[3/3] verifying the graph and writing the dataset...")
    problemas = []
    for uuid, c in criaturas.items():
        for ing in c["ingredientes"]:
            if ing not in criaturas:
                problemas.append(f"{uuid}: unknown ingredient '{ing}'")
        for h in c["hijos"]:
            if h not in criaturas:
                problemas.append(f"{uuid}: unknown child '{h}'")
        if c["tipo"] != "non_hybrid" and not c["ingredientes"]:
            problemas.append(f"{uuid}: it is a hybrid but it has no ingredients")

    # cycle detection
    color = {}

    def visita(u, pila):
        if color.get(u) == 1:
            problemas.append(f"cycle detected: {' -> '.join(pila + [u])}")
            return
        if color.get(u) == 2:
            return
        color[u] = 1
        for ing in criaturas[u]["ingredientes"]:
            if ing in criaturas:
                visita(ing, pila + [u])
        color[u] = 2

    for u in criaturas:
        visita(u, [])

    salida = {
        "meta": {
            "juego": "Jurassic World Alive",
            "version_juego": version,
            "fuente": "paleo.gg/games/jurassic-world-alive/dinodex",
            "fuente_actualizada": meta["lastModifiedDate"],
            "descargado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "criaturas": len(criaturas),
            "fallos": fallos,
        },
        "criaturas": criaturas,
    }
    destino = DATOS
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(destino) / 1024
    print(f"      wrote {destino} ({kb:.0f} KB)")

    if problemas:
        print(f"\nPROBLEMS IN THE GRAPH ({len(problemas)}):")
        for p in problemas[:30]:
            print("  -", p)
    else:
        print("\nGraph intact: no broken references, no orphans, no cycles.")

    print(f"\ncreatures: {len(criaturas)}   hybrids: "
          f"{sum(1 for c in criaturas.values() if c['tipo'] != 'non_hybrid')}")


if __name__ == "__main__":
    main()
