#!/usr/bin/env python3
"""One version, in one place, and it reaches everywhere it is shown.

The game version appears in four places in the delivered page —the <title>, the
<h1> badge and the two TITULO strings— and in four documents. All of them are
written from a single authored value: `meta.version_juego` of data/jwa.json.

Before this file existed the number was hand-written in three independent places
in the code (`scrape_paleo.py`, `modelo.py`, `plantilla.html`) and nothing
compared them, so an update could ship a page whose title said one version and
whose embedded data said another. Nothing would have noticed.

It also pins the two names that must NOT carry a version, because getting those
wrong costs data instead of time:

  · `index.html` — the deliverable. A `file://` document keys its storage to the
    FULL PATH, so a versioned name is a new, empty store. The full account is at
    the top of build.py.

  · `jwa322` — the localStorage prefix, the export mark and the exported file
    name. Same trap, one step removed: renaming it makes every saved creature
    invisible, silently.

Usage:  python3 verificar_version.py
"""

import ast
import os
import re
import sys

from rutas import DATOS, HTML, RAIZ, version

fallos = []


def fallo(que, detalle):
    fallos.append((que, detalle))


def lee(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def sin_comentarios(texto):
    """The template with its comments removed.

    Comments are prose: they exist to explain, and explaining this file's rules
    means naming the version and naming __VERSION__. What has to be checked is
    the markup and the code that is actually delivered, so the checks below run
    on this, and a comment is free to say «3.23» or «jwa324.inventario» while
    illustrating the trap.
    """
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", texto, flags=re.S)


# --------------------------------------------------------------------------
# 1. The two names that carry no version
# --------------------------------------------------------------------------
if os.path.basename(DATOS) != "jwa.json":
    fallo("rutas.DATOS",
          "the dataset has to be called jwa.json, and it is called %r"
          % os.path.basename(DATOS))
if os.path.basename(HTML) != "index.html":
    fallo("rutas.HTML",
          "the deliverable has to be called index.html, and it is called %r"
          % os.path.basename(HTML))

# `data/` holds exactly one dataset. The versioned ones used to sit here next to
# each other, and the failure mode was editing the wrong one: a file that looks
# like the source, is not read by anything, and states an older version.
en_data = sorted(f for f in os.listdir(os.path.dirname(DATOS))
                 if f.endswith(".json"))
if en_data != [os.path.basename(DATOS)]:
    fallo("data/",
          "it has to hold exactly one dataset, %s, and it holds: %s. A versioned "
          "dataset left here looks like the source and is read by nothing."
          % (os.path.basename(DATOS), ", ".join(en_data) or "nothing"))

# --------------------------------------------------------------------------
# 2. The four places the page shows it
# --------------------------------------------------------------------------
v = version()
html = lee(HTML)

# Each pattern is anchored to the ELEMENT it belongs to, and that is not
# cosmetic: a plain «the string is somewhere in the file» passed in green when
# the <title> was broken, because the TITULO literals contain the same sentence.
# A check that shares the datum it is checking cannot fail.
SITIOS = [
    ("the <title>",
     r"<title>[^<]*Jurassic World Alive %s DNA calculator[^<]*</title>" % re.escape(v)),
    ("the <h1> badge",
     r'<span class="v">JWA %s</span>' % re.escape(v)),
    ("TITULO, English",
     r'"Jurassic World Alive %s DNA calculator"' % re.escape(v)),
    ("TITULO, Spanish",
     r'"calculadora de ADN de Jurassic World Alive %s"' % re.escape(v)),
]
for nombre, patron in SITIOS:
    if not re.search(patron, html):
        fallo("index.html, %s" % nombre,
              "does not match %s. The dataset says the version is %s: rebuild "
              "with `python3 build.py`." % (patron, v))

# The version that travels INSIDE the page, in the embedded data. If this one
# disagreed with the title, the page would contradict itself and nothing else
# would say so.
m = re.search(r'"meta":\{"version":"([^"]*)"', html)
if not m:
    fallo("index.html, embedded data",
          "cannot find meta.version in the built page")
elif m.group(1) != v:
    fallo("index.html, embedded data",
          "meta.version says %r and the dataset says %r" % (m.group(1), v))

# --------------------------------------------------------------------------
# 3. The template carries no bare version
# --------------------------------------------------------------------------
plantilla = lee(os.path.join(RAIZ, "plantilla.html"))
efectiva = sin_comentarios(plantilla)


def es_procedencia(linea):
    """The two sentences that name a version on purpose.

    They are a provenance claim —«verified against the official 3.23 release
    notes»—, not the current version. It stays true for ever, and templating it
    would make the page assert something nobody verified the moment the version
    is bumped. So they are the ONE exception, and they are named here rather
    than tolerated everywhere.
    """
    return "release notes" in linea or "comunicado oficial" in linea


for n, linea in enumerate(efectiva.splitlines(), 1):
    if v in linea and not es_procedencia(linea):
        fallo("plantilla.html:%d" % n,
              "carries the bare version %s. It has to be __VERSION__, which "
              "build.py fills from the dataset." % v)

n_ver = efectiva.count("__VERSION__")
if n_ver != 4:
    fallo("plantilla.html",
          "__VERSION__ appears %d times and it has to appear exactly 4: the "
          "<title>, the <h1> badge and the two TITULO strings. If a fifth "
          "place now shows the version, add it to SITIOS in this file too."
          % n_ver)

# --------------------------------------------------------------------------
# 4. The documents that state it
# --------------------------------------------------------------------------
DOCS = [
    ("README.md", r"A DNA and cost calculator for Jurassic World Alive ([\d.]+)\."),
    ("NOTICE", r"^Amber — Jurassic World Alive ([\d.]+) DNA calculator"),
    ("AGENTS.md", r"calculator for \*\*Jurassic World Alive ([\d.]+)\*\*"),
    (".privado/LEEME.md",
     r"^# Ámbar — calculadora de ADN de Jurassic World Alive ([\d.]+)"),
]
for rel, patron in DOCS:
    ruta = os.path.join(RAIZ, rel)
    if not os.path.exists(ruta):
        fallo(rel, "the file is not there, and it states the version")
        continue
    dicho = re.findall(patron, lee(ruta), re.M)
    if not dicho:
        fallo(rel, "cannot find the version claim. If the sentence was "
                   "rewritten, update this pattern; if it was deleted, put the "
                   "version somewhere in the file and point this at it.")
    elif len(dicho) > 1:
        fallo(rel, "the claim appears %d times (%s); it has to be a single one "
                   "or they can disagree" % (len(dicho), " / ".join(dicho)))
    elif dicho[0] != v:
        fallo(rel, "it says %s and the dataset says %s" % (dicho[0], v))

# --------------------------------------------------------------------------
# 5. The frozen jwa322 identifier
# --------------------------------------------------------------------------
# A version bump is exactly when someone is tempted to «tidy» this prefix. The
# browser keys saved data to it, so renaming it does not migrate anything: it
# hides every saved creature behind an empty calculator.
prefijos = set(re.findall(r"jwa\d+", efectiva))
if prefijos != {"jwa322"}:
    fallo("plantilla.html, storage prefix",
          "the only jwa<digits> identifier allowed is jwa322, and I found %s. "
          "jwa322 is frozen: it is the storage key, NOT the game version."
          % (", ".join(sorted(prefijos)) if prefijos else "none"))

CLAVES = [
    ('"jwa322.tema"', "the theme key"),
    ('"jwa322.idioma"', "the language key"),
    ('"jwa322.inventario"', "the inventory key"),
    ('"jwa322.mios"', "the «my creatures» key"),
    ("{jwa322: 1,", "the export mark"),
    ('"jwa322-mis-criaturas.json"', "the exported file name"),
]
for aguja, que in CLAVES:
    if aguja not in efectiva:
        fallo("plantilla.html, %s" % que,
              "I cannot find %s. It is part of the frozen jwa322 identifier: "
              "renaming it hides every saved creature." % aguja)

# --------------------------------------------------------------------------
# 6. No script builds a path with a version in it
# --------------------------------------------------------------------------
def literales_de_codigo(ruta):
    """Every string literal in the file EXCEPT the docstrings.

    Prose is allowed to write `data/jwa-3.23.json` when it is telling the story
    of what happened —that is history and it should stay—. Code is not allowed
    to build a path out of it. Docstrings are where the prose lives, so they are
    the only thing skipped, and what is left is exactly the code.
    """
    arbol = ast.parse(lee(ruta), filename=ruta)
    docstrings = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            cuerpo = getattr(nodo, "body", [])
            if (cuerpo and isinstance(cuerpo[0], ast.Expr)
                    and isinstance(cuerpo[0].value, ast.Constant)
                    and isinstance(cuerpo[0].value.value, str)):
                docstrings.add(id(cuerpo[0].value))
    return [(n.value, n.lineno) for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


# `jwa-` followed by a digit is a version inside a name, which is the bug this
# file exists to prevent. A scratch directory called /tmp/jwa-test is not that,
# and it does not match. The second needle is spelled in two pieces so that this
# line, which has to name it, does not match itself.
EN_EL_NOMBRE = (re.compile(r"jwa-\d"), re.compile("amber" + "-jwa"))

# Only the scripts in the root: the ones that ship. `.privado/` holds private
# notes and one-off scripts that legitimately point at the old artefacts.
for nombre in sorted(f for f in os.listdir(RAIZ) if f.endswith(".py")):
    for texto, linea in literales_de_codigo(os.path.join(RAIZ, nombre)):
        if any(p.search(texto) for p in EN_EL_NOMBRE):
            fallo("%s:%d" % (nombre, linea),
                  "the code builds a versioned path (%r). Use rutas.DATOS or "
                  "rutas.HTML: the version lives inside the data, never in a "
                  "file name." % texto)

# --------------------------------------------------------------------------
print("Game version: %s   (authored once, in %s)"
      % (v, os.path.relpath(DATOS, RAIZ)))
print("Checked: the 4 places the page shows it, the version inside the embedded")
print("         data, the 4 documents that state it, the two names that carry")
print("         no version, the frozen jwa322 identifier, data/ holding a single")
print("         dataset, and every .py in the root for versioned paths.")
print()
if fallos:
    print("RESULT: FAIL — %d problem%s" % (len(fallos), "s" if len(fallos) != 1 else ""))
    for que, detalle in fallos:
        print("  · %s" % que)
        print("      %s" % detalle)
    sys.exit(1)
print("RESULT: PASS — one version, and every place that shows it agrees.")
