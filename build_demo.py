#!/usr/bin/env python3
"""
Packs the whole application into ONE html file, to open with a double click.

It takes the DELIVERED artefact and puts inside it:

  · every image it needs —the photos of the creatures in the saved file and the
    whole UI icon set— as data URIs, so the file does not need the `img/` folder
    next to it. It is the same reason the header mark and the tab icon already
    travel inlined;
  · a script that seeds the saved creatures BEFORE the application reads them, so
    the demo opens with those creatures loaded, in Spanish and in Amber-OLED.

The demo is a PACKAGING of the delivered artefact and never a second build of the
template: whatever `build.py` wrote is what goes inside, byte for byte, and the
sha256 of that artefact is stamped in a comment. `probar_demo.py` recomputes it,
so a demo left behind by an older artefact is caught instead of being shown.

It is NOT committed: the file carries copyrighted game artwork, which this
repository excludes on purpose (`.gitignore`).

Usage:
    python3 build_demo.py [saved.json] [output.html]

The saved file is what the interface exports with «Export JSON»: the same map of
`{jwa322, mios, inventario}` that «Import JSON» reads.
"""
import base64
import hashlib
import json
import os
import re
import sys
from datetime import date

from rutas import DATOS, HTML

RAIZ = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(RAIZ, "img")
GUARDADO = os.path.join(RAIZ, ".privado", "jwa322-mis-criaturas(2026-09-27).json")
SALIDA = os.path.join(RAIZ, "amber-demo.html")

# The creature the demo opens on, and the look it opens with. One line each.
CRIATURA = "fukuitops"
TEMA = "oled"
IDIOMA = "es"

# The folders of the interface icons. They are small and they are not optional:
# without them the stats panel, the class badge and the enhancement costs come
# out with holes.
CARPETAS_ICONO = ("stat", "cat", "res", "clase")

CLAVES = ("jwa322.inventario", "jwa322.mios", "jwa322.tema", "jwa322.idioma")
VACIO = "const IMG_EN_LINEA = {};"


def uri(ruta):
    """The file, as a data URI of the type its extension says."""
    tipo = {"webp": "image/webp", "png": "image/png", "svg": "image/svg+xml"}[
        ruta.rsplit(".", 1)[-1].lower()]
    with open(ruta, "rb") as f:
        return "data:%s;base64,%s" % (tipo, base64.b64encode(f.read()).decode("ascii"))


def cierre(cri, semilla):
    """Every creature hanging BELOW the ones given, ingredients first: the tree
    and the report of a demo creature paint its whole cascade, so their photos
    are needed too."""
    vistos, pila = set(), list(semilla)
    while pila:
        u = pila.pop()
        if u in vistos or u not in cri:
            continue
        vistos.add(u)
        pila.extend(cri[u]["ingredientes"])
    return vistos


def main():
    guardado = sys.argv[1] if len(sys.argv) > 1 else GUARDADO
    salida = sys.argv[2] if len(sys.argv) > 2 else SALIDA

    if not os.path.exists(guardado):
        raise SystemExit("!! no saved file at %s (it lives in .privado/, which is not published)"
                         % guardado)
    html = open(HTML, encoding="utf-8").read()
    if html.count(VACIO) != 1:
        raise SystemExit("!! the artefact does not carry the empty image map (%r): rebuild"
                         % VACIO)

    d = json.load(open(guardado, encoding="utf-8"))
    inv = d.get("inventario") or {}
    mios = d.get("mios") or list(inv)
    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]

    # ---- what goes inside -------------------------------------------------
    mapa, avisos = {}, []
    quiero = cierre(cri, set(inv) | set(mios))
    for u in sorted(quiero):
        if u not in cri:
            avisos.append("%s: not in the dinodex" % u)
            continue
        p = os.path.join(IMG, u + ".webp")
        if not os.path.exists(p):
            avisos.append("%s: no photo on disk" % u)
            continue
        mapa["img/%s.webp" % u] = uri(p)
    for carpeta in CARPETAS_ICONO:
        for f in sorted(os.listdir(os.path.join(IMG, carpeta))):
            if f.rsplit(".", 1)[-1].lower() in ("png", "svg", "webp"):
                mapa["img/%s/%s" % (carpeta, f)] = uri(os.path.join(IMG, carpeta, f))
    faltan = [p for p in mapa if p.startswith("img/stat/") or p.startswith("img/res/")]
    if not faltan:
        avisos.append("no UI icons found: the panel would come out with holes")

    # ---- the seed, BEFORE the application reads anything -------------------
    # Inside an IIFE and with local names on purpose: every <script> of this page
    # SHARES the global scope, and a `const D` here would kill the application's
    # own `const D` with a redeclaration error (the collision that already cost a
    # session).
    semilla = """
<script>
/* Demo: the saved creatures are seeded BEFORE the application reads them, so it
   opens with them already loaded. It is written on every open, so the demo always
   looks the same and does not depend on what the last visitor did. A file://
   document has its OWN localStorage —measured in Firefox— so this cannot touch
   the data of the real application. */
(function(){
  try {
    var g = %s;
    localStorage.setItem(%s, JSON.stringify(g.inventario || {}));
    localStorage.setItem(%s, JSON.stringify(g.mios || []));
    localStorage.setItem(%s, %s);
    localStorage.setItem(%s, %s);
  } catch (e) {}
})();
</script>
""" % (json.dumps({"inventario": inv, "mios": mios}, ensure_ascii=False),
       json.dumps(CLAVES[0]), json.dumps(CLAVES[1]), json.dumps(CLAVES[2]),
       json.dumps(TEMA), json.dumps(CLAVES[3]), json.dumps(IDIOMA))

    # ---- the opening view, AFTER the application has painted ---------------
    apertura = """
<script>
/* The screen the demo opens on. `refrescar()` is what repaints everything:
   report, tree, stats, list and photo strip. */
try { elegir(%s); refrescar(); } catch (e) {}
</script>
""" % json.dumps(CRIATURA)

    sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    marca = ("<!-- amber-demo: empaquetado de %s sha256=%s el %s · %d criaturas · %d imágenes -->"
             % (os.path.basename(HTML), sha, date.today().isoformat(), len(inv), len(mapa)))

    html = html.replace("<head>", "<head>\n" + semilla, 1)
    html = html.replace("</head>", marca + "\n</head>", 1)
    html = html.replace("</body>", apertura + "</body>", 1)
    html = html.replace(VACIO, "const IMG_EN_LINEA = " + json.dumps(mapa, ensure_ascii=False) + ";", 1)

    with open(salida, "w", encoding="utf-8") as f:
        f.write(html)

    kb = os.path.getsize(salida) / 1024
    fotos = sum(1 for p in mapa if p.endswith(".webp"))
    print("wrote %s  (%.0f KB)" % (salida, kb))
    print("  creatures in the file: %d (%d in «My Creatures»)" % (len(inv), len(mios)))
    print("  images inlined: %d  (%d photos + %d interface icons)"
          % (len(mapa), fotos, len(mapa) - fotos))
    print("  opens on: %s · theme %s · language %s" % (CRIATURA, TEMA, IDIOMA))
    print("  artefacto sha256: %s" % sha[:16])
    for a in avisos:
        print("  WARNING: %s" % a)


if __name__ == "__main__":
    main()
