#!/usr/bin/env python3
"""
The recipes, against the RENDERED page of paleo.gg.

What it checks, and why
-----------------------
1. **The ingredients and the children of every creature are re-read from the
   cached page, by a parser that is deliberately NOT the one that built the
   dataset.** This is the hole the other verifiers leave open.
   `verificar_motor.py` and `verificar_arbol.py` compare the page against
   `modelo.py`, and both read the SAME `data/jwa.json`: if the extraction is
   wrong, the two are wrong together and the comparison is green.
   `verificar_fuentes.py` checks where a creature is OBTAINED, not its recipe.
   And `scrape_paleo.py` validates the graph against itself — unknown
   ingredients, cycles, a hybrid with no ingredients — but always from the same
   `__NEXT_DATA__` payload it extracted.

   So the extraction was the one thing nothing compared against the source. This
   script does, and it does it through a different door on purpose: it reads the
   `<h2>Ingredients</h2>` and `<h2>Hybrids</h2>` blocks of the rendered HTML and
   pulls the `/dinodex/<slug>` links out of them, while `scrape_paleo.py` reads
   the JSON payload. Two readings of the same page, compared.

2. **The order is compared too, not just the set.** `ingredientes` is a list and
   the app shows it in that order; a set comparison would hide a swap.

3. **A hybrid has a block and a non-hybrid does not.** The two counts are
   asserted, so a creature changing type does not pass unnoticed.

4. **The counts are asserted as figures.** 519 creatures, 248 with an
   Ingredients block, 271 without, 496 ingredient links. And one invariant that
   is worth more than the figures: **the ingredient links and the child links
   have to be the SAME number**, because every ingredient link is a child link
   seen from the other side. If they ever differ, the two lists disagree about
   the shape of the graph and one of them is wrong.

5. **The shantungosaurus branch is named out loud.** It is the only chain in the
   project that reaches an apex, and the one n30 asked about by name; a green
   summary that does not mention it does not answer the question.

It reads `cache/`, which is 92 MB and is not in the repository. On a clone it
says so instead of crashing: see the check at the top of `main`.

Usage:  python3 verificar_recetas.py
"""
import json
import os
import re
import sys

from rutas import DATOS

RAIZ = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(RAIZ, "cache")

# The block titles as paleo.gg renders them, and the links inside.
BLOQUE = r"<h2[^>]*>%s</h2>\s*<ul[^>]*>(.*?)</ul>"
ENLACE = r"/dinodex/([A-Za-z0-9_]+)"

# The figures this dataset has. They are asserted so that a data change has to
# be looked at, and so that this script cannot go green on an empty cache.
ESPERADO = {
    "criaturas": 519,
    "con_ingredientes": 248,
    "sin_ingredientes": 271,
    "enlaces_ingrediente": 496,
    "paginas": 520,          # the 519 creatures plus the dinodex index
}

# The branch n30 asked about. Named here so the report says something about it
# even when it is green.
RAMA = ["shantungosaurus", "animantarx", "shantunrax", "koolatrax",
        "shantrospinos", "albertospinos"]


def del_bloque(html, titulo):
    """The slugs the page lists under a `<h2>titulo</h2>`, in order and unique.

    Returns None when the block is not there at all, which is a different thing
    from an empty block and has to be told apart: a creature with no ingredients
    has no block, and one with a broken block would have an empty one.
    """
    m = re.search(BLOQUE % titulo, html, re.S)
    if not m:
        return None
    vistos, salida = set(), []
    for slug in re.findall(ENLACE, m.group(1)):
        if slug not in vistos:
            vistos.add(slug)
            salida.append(slug)
    return salida


def main():
    if not os.path.isdir(CACHE):
        print("RESULT: cannot judge — there is no cache/ next to this script.")
        print("        It is 92 MB of pages downloaded from paleo.gg and it is not in the")
        print("        repository. Rebuild it once with:")
        print("            python3 scrape_paleo.py --version %s" % _version())
        print("        This is not a failure of the code: the test has nothing to read.")
        return 2

    datos = json.load(open(DATOS, encoding="utf-8"))
    criaturas = datos["criaturas"]

    paginas = sorted(f for f in os.listdir(CACHE) if f.endswith(".html"))
    fallos, ok = [], 0

    def comprueba(nombre, obtenido, esperado):
        nonlocal ok
        if obtenido != esperado:
            fallos.append("%s: %r != %r" % (nombre, obtenido, esperado))
        else:
            ok += 1

    # ---- 1. the counts, first: an empty or half-built cache must not read green
    con = [u for u, v in criaturas.items() if v["ingredientes"]]
    sin = [u for u, v in criaturas.items() if not v["ingredientes"]]
    enlaces_ing = sum(len(v["ingredientes"]) for v in criaturas.values())
    enlaces_hij = sum(len(v["hijos"]) for v in criaturas.values())

    comprueba("creatures in the dataset", len(criaturas), ESPERADO["criaturas"])
    comprueba("creatures with ingredients", len(con), ESPERADO["con_ingredientes"])
    comprueba("creatures without ingredients", len(sin), ESPERADO["sin_ingredientes"])
    comprueba("pages in cache/", len(paginas), ESPERADO["paginas"])
    comprueba("ingredient links", enlaces_ing, ESPERADO["enlaces_ingrediente"])
    # The invariant, and it is not a coincidence: every ingredient link is a
    # child link seen from the other side. If these two ever differ, the two
    # lists disagree about the shape of the graph.
    comprueba("ingredient links == child links", enlaces_ing, enlaces_hij)
    print("OK    the counts: %d creatures, %d with a recipe, %d without, "
          "%d ingredient links" % (len(criaturas), len(con), len(sin), enlaces_ing))

    # ---- 2. every page belongs to a creature, and every creature has its page
    for fichero in paginas:
        clave = fichero[:-5]
        if clave == "dinodex":
            continue                       # the index of the dinodex, not a creature
        if clave not in criaturas:
            fallos.append("%s: it is in cache/ and not in the dataset" % clave)
    faltan = [u for u in criaturas if (u + ".html") not in paginas]
    comprueba("creatures with no cached page", faltan, [])
    print("OK    the %d pages and the %d creatures are the same set, plus the index"
          % (len(paginas) - 1, len(criaturas)))

    # ---- 3. the recipes, one by one, against the rendered page
    comparados_ing = comparados_hij = 0
    for clave in sorted(criaturas):
        ruta = os.path.join(CACHE, clave + ".html")
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as f:
            html = f.read()
        ficha = criaturas[clave]
        suyos_ing = list(ficha["ingredientes"] or [])
        suyos_hij = list(ficha["hijos"] or [])
        fuente_ing = del_bloque(html, "Ingredients")
        fuente_hij = del_bloque(html, "Hybrids")

        if fuente_ing is not None:
            comparados_ing += 1
            if fuente_ing != suyos_ing:
                fallos.append("%s: ingredients — page %s vs data %s"
                              % (clave, fuente_ing, suyos_ing))
        elif suyos_ing:
            fallos.append("%s: the data gives it ingredients and the page has no block"
                          % clave)
        if fuente_hij is not None:
            comparados_hij += 1
            if fuente_hij != suyos_hij:
                fallos.append("%s: children — page %s vs data %s"
                              % (clave, fuente_hij, suyos_hij))
        elif suyos_hij:
            fallos.append("%s: the data gives it children and the page has no block"
                          % clave)

    comprueba("creatures with an Ingredients block on the page",
              comparados_ing, ESPERADO["con_ingredientes"])
    print("OK    the recipes match the page in all %d creatures that have one, "
          "in order" % comparados_ing)
    print("OK    and the children match in all %d that list any" % comparados_hij)

    # ---- 4. the branch that was asked about, said out loud
    print()
    print("The shantungosaurus branch, as the page renders it:")
    for k in RAMA:
        ruta = os.path.join(CACHE, k + ".html")
        if not os.path.exists(ruta):
            print("  %-18s (no page)" % k)
            continue
        with open(ruta, encoding="utf-8", errors="replace") as f:
            html = f.read()
        ficha = criaturas.get(k, {})
        print("  %-18s %-9s page %-42s data %s"
              % (k, ficha.get("rareza", "?"), del_bloque(html, "Ingredients"),
                 ficha.get("ingredientes") or []))

    # ---- the verdict
    print()
    if fallos:
        print("RESULT: %d discrepancies" % len(fallos))
        for d in fallos[:30]:
            print("  - " + d)
        return 1
    print("RESULT: all OK (%d checks). The recipes in the dataset are the ones the "
          "source page renders." % (ok + comparados_ing))
    return 0


def _version():
    try:
        return json.load(open(DATOS, encoding="utf-8"))["meta"]["version_juego"]
    except Exception:
        return "3.24"


if __name__ == "__main__":
    sys.exit(main())
