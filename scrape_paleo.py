#!/usr/bin/env python3
"""
Downloads the complete dinodex from paleo.gg for Jurassic World Alive.

paleo.gg is Next.js: it serves all the data inside <script id="__NEXT_DATA__">.
No browser is needed. A normal request is enough.

Usage:
    python3 scrape_paleo.py            # uses the cache, only downloads what is missing
    python3 scrape_paleo.py --refetch  # downloads everything again

Output:
    cache/dinodex.html          index
    cache/<uuid>.html           raw card of each creature
    data/jwa-3.22.json          normalized dataset
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(RAIZ, "cache")
DATA = os.path.join(RAIZ, "data")
BASE = "https://www.paleo.gg/games/jurassic-world-alive/dinodex"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
RETARDO = 0.25       # seconds between requests, out of politeness
REINTENTOS = 3


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


def main():
    refetch = "--refetch" in sys.argv
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(DATA, exist_ok=True)

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
            "version_juego": "3.22",
            "fuente": "paleo.gg/games/jurassic-world-alive/dinodex",
            "fuente_actualizada": meta["lastModifiedDate"],
            "descargado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "criaturas": len(criaturas),
            "fallos": fallos,
        },
        "criaturas": criaturas,
    }
    destino = os.path.join(DATA, "jwa-3.22.json")
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
