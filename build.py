#!/usr/bin/env python3
"""
Construye calculadora-jwa-3.22.html a partir de data/jwa-3.22.json + modelo.py.

El resultado es UN SOLO fichero HTML autocontenido: sin CDN, sin red, sin
dependencias. Se abre con doble clic y funciona sin conexion.

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
DESTINO = os.path.join(RAIZ, f"calculadora-jwa-{VERSION}.html")

# Orden de los seis stats en el slot 8. Es el mismo que usa el juego y el mismo
# en el que paleo.gg los ensena en su bloque «Basic Stats».
STATS_ORDEN = ("vida", "dano", "velocidad", "armadura", "critico", "dano_critico")


def cargar_datos():
    with open(ORIGEN, encoding="utf-8") as f:
        d = json.load(f)
    cri = d["criaturas"]
    # se guardan solo los campos que el navegador necesita
    compacto = {}
    for u, x in cri.items():
        s = x.get("stats") or {}
        # Las mejoras se guardan como [coste_adn, req, [tipo, valor]] y solo las
        # tienen Unica y Apex (147 de 518). Se conservan los codigos crudos de
        # los recursos y el `type` del efecto: la etiqueta se resuelve en el
        # navegador, igual que con las zonas.
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
            # 7: donde se consigue, en codigos del juego. Se guardan los codigos
            # crudos y la etiqueta se resuelve en el navegador contra
            # M.locEtiquetas: el codigo es la identidad y el texto, presentacion.
            [f["loc"] for f in x.get("fuentes_adn") or []],
            # 8: los seis stats BASE, que son los de NIVEL 26. La lista vacia
            # seria un error de datos, no un caso a contemplar.
            [s[k] for k in STATS_ORDEN],
            # 9: la pista de mejoras, o None si la criatura no la tiene.
            mj or None,
        ]
    return d["meta"], compacto


def favicon():
    """El icono de la pestana, como data URI.

    Va EN LINEA y no como <link href="img/favicon.svg"> a proposito: asi el
    icono no depende de que la carpeta `img/` este al lado del HTML. El SVG
    sigue siendo un fichero de verdad en `img/favicon.svg`, que es la unica
    fuente; aqui solo se copia.
    """
    with open(FAVICON, encoding="utf-8") as f:
        svg = f.read().strip()
    # Los caracteres que romperian un atributo HTML o una URL se codifican; el
    # resto se deja legible para que el HTML generado se pueda revisar a ojo.
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

    kb = os.path.getsize(DESTINO) / 1024
    print(f"escrito {DESTINO}  ({kb:.0f} KB)")
    print(f"criaturas: {len(criaturas)}")


if __name__ == "__main__":
    main()
