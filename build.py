#!/usr/bin/env python3
"""
Builds amber-jwa-3.22.html from data/jwa-3.22.json + modelo.py.

The result is a SINGLE self-contained HTML file: no CDN, no network, no
dependencies. It opens with a double click and works offline.

    python3 build.py
"""

import json
import os

from modelo import (ADN_31_35, ADN_POR_FUSION, ADN_POR_FUSION_MEDIA, COINR,
                    BOOST_FRACCION, BOOST_VELOCIDAD, COIN_31_35,
                    COIN_OMEGA_31_35, CREACION, L, LOC_COMBATE, LOC_DARDEO,
                    LOC_ETIQUETAS, MEJORA_NIVEL_MIN, MEJORA_PASOS,
                    MIN_LV, MONEDAS_FUSION, MULT_NIVEL, NIVEL_MAX,
                    NIVEL_MIN_INGREDIENTE, NOMBRE, OMEGA_31_35, OMEGA_COINR,
                    OMEGA_L, TIER, TOPE_BOOST_STAT, TOPES_ADN, VERSION)

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(RAIZ, "data", "jwa-3.22.json")
FAVICON = os.path.join(RAIZ, "img", "favicon.svg")
DESTINO = os.path.join(RAIZ, f"amber-jwa-{VERSION}.html")
# Deploy entry point. Vercel/GitHub Pages serve index.html, so the same
# self-contained HTML is written twice: the versioned copy is the artefact a
# human double-clicks, and index.html is what the site serves.
INDICE = os.path.join(RAIZ, "index.html")

# Order of the six stats in slot 8. It is the same one the game uses and the
# same one in which paleo.gg shows them in its «Basic Stats» block.
STATS_ORDEN = ("vida", "dano", "velocidad", "armadura", "critico", "dano_critico")


def cargar_datos():
    with open(ORIGEN, encoding="utf-8") as f:
        d = json.load(f)
    cri = d["criaturas"]
    # only the fields the browser needs are kept
    compacto = {}
    for u, x in cri.items():
        s = x.get("stats") or {}
        # The enhancements are stored as [dna_cost, req, [type, value]] and only
        # Unique and Apex have them (147 of 518). The raw codes of the resources
        # and the `type` of the effect are kept: the label is resolved in the
        # browser, just as with the zones.
        mj = [[m["cost"], m["req"], [m["rwd"]["type"], m["rwd"]["value"]]]
              for m in (x.get("mejoras") or [])]
        compacto[u] = [
            x["nombre"],            # 0
            x["rareza"],            # 1
            x["tipo"],              # 2
            x["version"],           # 3
            1 if x["publicada"] else 0,  # 4
            x["ingredientes"],      # 5
            x["hijos"],             # 6
            # 7: where it is obtained, in game codes. The raw codes are kept and
            # the label is resolved in the browser against M.locEtiquetas: the
            # code is the identity and the text, presentation.
            [f["loc"] for f in x.get("fuentes_adn") or []],
            # 8: the six BASE stats, which are the LEVEL 26 ones. An empty list
            # would be a data error, not a case to contemplate.
            [s[k] for k in STATS_ORDEN],
            # 9: the enhancement track, or None if the creature does not have it.
            mj or None,
        ]
    return d["meta"], compacto


def favicon():
    """The tab icon, as a data URI.

    It goes INLINE and not as <link href="img/favicon.svg"> on purpose: that way
    the icon does not depend on the `img/` folder being next to the HTML. The SVG
    is still a real file in `img/favicon.svg`, which is the only source; here it
    is just copied.
    """
    with open(FAVICON, encoding="utf-8") as f:
        svg = f.read().strip()
    # The characters that would break an HTML attribute or a URL are encoded;
    # the rest is left readable so that the generated HTML can be reviewed by
    # eye.
    seguro = (svg.replace("%", "%25").replace("#", "%23")
                 .replace("<", "%3C").replace(">", "%3E")
                 .replace('"', "'").replace("\n", " "))
    return "data:image/svg+xml," + seguro


def main():
    meta, criaturas = cargar_datos()

    datos = {
        "meta": {
            "version": VERSION,
            "fuente": meta["fuente"],
            "fuenteActualizada": meta["fuente_actualizada"],
            "descargado": meta["descargado"],
            "total": len(criaturas),
        },
        "criaturas": criaturas,
        "modelo": {
            "L": L,
            "creacion": CREACION,
            "minLv": MIN_LV,
            "coinR": COINR,
            "adn3135": ADN_31_35,
            "coin3135": COIN_31_35,
            "coinOmega3135": COIN_OMEGA_31_35,
            "monedasFusion": MONEDAS_FUSION,
            "adnPorFusion": {str(k): v for k, v in ADN_POR_FUSION.items()},
            "tier": TIER,
            "omegaL": OMEGA_L,
            "omega3135": OMEGA_31_35,
            "omegaCoinR": OMEGA_COINR,
            "topes": TOPES_ADN,
            "media": ADN_POR_FUSION_MEDIA,
            "nivelMax": NIVEL_MAX,
            "minIngrediente": NIVEL_MIN_INGREDIENTE,
            "locDardeo": list(LOC_DARDEO),
            "locCombate": list(LOC_COMBATE),
            "locEtiquetas": LOC_ETIQUETAS,
            "multNivel": MULT_NIVEL,
            "boostVelocidad": BOOST_VELOCIDAD,
            "boostFraccion": BOOST_FRACCION,
            "topeBoostStat": TOPE_BOOST_STAT,
            "mejoraNivelMin": MEJORA_NIVEL_MIN,
            "mejoraPasos": MEJORA_PASOS,
            "statsOrden": list(STATS_ORDEN),
        },
    }

    with open(os.path.join(RAIZ, "plantilla.html"), encoding="utf-8") as f:
        html = f.read()

    carga = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("__DATOS__", carga)
    html = html.replace("__NOMBRE__", NOMBRE)
    html = html.replace("__FAVICON__", favicon())

    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write(html)
    with open(INDICE, "w", encoding="utf-8") as f:
        f.write(html)

    kb = os.path.getsize(DESTINO) / 1024
    print(f"wrote {DESTINO}  ({kb:.0f} KB)")
    print(f"wrote {INDICE}  (identical, for deployment)")
    print(f"creatures: {len(criaturas)}")


if __name__ == "__main__":
    main()
