#!/usr/bin/env python3
"""The proof that verificar_version.py knows how to fail, and that the update
procedure holds.

Two things are checked here, and both are about the guard rather than about the
page:

  1. RED, CONTROL BY CONTROL. Each of the six checks in verificar_version.py is
     broken on purpose, one at a time, and the run has to come back with exit 1
     naming what was broken. A check that cannot fail proves nothing: the first
     version of the <title> check looked for the sentence «somewhere in the
     file», the TITULO literals contain it, and breaking the title left it
     green. That is the trap AGENTS.md warns about — a check that shares the
     datum it measures.

  2. THE 3.24 DRY RUN. The version is raised to 3.24 in the dataset and nowhere
     else, and the whole procedure is walked: build.py must put 3.24 in the four
     places the page shows it, verificar_version.py must fail naming the four
     documents that were left behind, and updating those four must bring it back
     to green. It answers the question the refactor exists for: what does an
     update actually cost?

THIS SCRIPT MUTATES THE FILES IT CHECKS. It saves their bytes, does the damage,
and restores them, verifying the sha256 of every one. That is why it refuses to
start on a file that differs from its committed version: if it ever dies in the
middle, `git checkout -- <file>` is a complete recovery.

    python3 probar_version.py
"""

import hashlib
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- the damages
# (title, file, old text, new text, what the failure has to name)
ROTURAS = [
    ("the version in the <title>",
     "index.html",
     "<title>Amber — Jurassic World Alive 3.23 DNA calculator</title>",
     "<title>Amber — Jurassic World Alive 3.22 DNA calculator</title>",
     "index.html, the <title>"),

    ("the version inside the embedded data",
     "index.html",
     '"meta":{"version":"3.23"',
     '"meta":{"version":"3.22"',
     "embedded data"),

    ("the version written by hand in the template",
     "plantilla.html",
     '<h1>__NOMBRE__ <span class="v">JWA __VERSION__</span></h1>',
     '<h1>__NOMBRE__ <span class="v">JWA 3.23</span></h1>',
     "carries the bare version"),

    ("the version the README states",
     "README.md",
     "A DNA and cost calculator for Jurassic World Alive 3.23.",
     "A DNA and cost calculator for Jurassic World Alive 3.22.",
     "README.md"),

    ("the frozen jwa322 identifier",
     "plantilla.html",
     '"jwa322.inventario"',
     '"jwa324.inventario"',
     "storage prefix"),

    # The damage is assembled from pieces on purpose: this file has to name a
    # versioned path in order to inject one, and verificar_version.py scans
    # every .py in the root, this one included. Written whole, the test would
    # flag its own test data and the dry run below could never go green.
    ("a versioned path written in the code",
     "probar.py",
     'DIR = "/tmp/jwa-test"',
     'DIR = "/tmp/jwa-test"\nPRUEBA = "data/jwa-' + "3.24" + '.json"',
     "versioned path"),
]

# ------------------------------------------------------------- the 3.24 dry run
# The one authored value, and the four prose lines the verifier has to point at.
ENSAYO_DATO = ("data/jwa.json", '"version_juego":"3.23"', '"version_juego":"3.24"')
ENSAYO_DOCS = [
    ("README.md", "A DNA and cost calculator for Jurassic World Alive 3.23.",
     "A DNA and cost calculator for Jurassic World Alive 3.24."),
    ("NOTICE", "Amber — Jurassic World Alive 3.23 DNA calculator",
     "Amber — Jurassic World Alive 3.24 DNA calculator"),
    ("AGENTS.md", "calculator for **Jurassic World Alive 3.23**",
     "calculator for **Jurassic World Alive 3.24**"),
    (".privado/LEEME.md", "# Ámbar — calculadora de ADN de Jurassic World Alive 3.23",
     "# Ámbar — calculadora de ADN de Jurassic World Alive 3.24"),
]
ENSAYO_EN_LA_PAGINA = [
    ("the <title>", "Jurassic World Alive 3.24 DNA calculator</title>"),
    ("the <h1> badge", '<span class="v">JWA 3.24</span>'),
    ("TITULO, English", '"Jurassic World Alive 3.24 DNA calculator"'),
    ("TITULO, Spanish", '"calculadora de ADN de Jurassic World Alive 3.24"'),
    ("the embedded data", '"meta":{"version":"3.24"'),
]

VIGILADOS = sorted({r[1] for r in ROTURAS}
                   | {ENSAYO_DATO[0]}
                   | {d[0] for d in ENSAYO_DOCS}
                   | {"index.html"})

fallos = []


def fallo(que, detalle):
    fallos.append((que, detalle))


def ruta_de(rel):
    return os.path.join(RAIZ, rel)


def lee(rel):
    with open(ruta_de(rel), encoding="utf-8") as f:
        return f.read()


def escribe(rel, texto):
    with open(ruta_de(rel), "w", encoding="utf-8") as f:
        f.write(texto)


def sha(rel):
    with open(ruta_de(rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def corre(*args):
    r = subprocess.run([sys.executable] + list(args), cwd=RAIZ,
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def sucio(rel):
    """True if the file differs from the committed version.

    Not a tidiness check: it is what makes the restore path trustworthy. If the
    script dies half way, `git checkout -- <file>` puts back exactly what was
    there, and that is only true of a clean file.
    """
    r = subprocess.run(["git", "diff", "--quiet", "--", rel], cwd=RAIZ)
    return r.returncode != 0


# --------------------------------------------------------------- the setup
# A document that is not THERE and a document that is DIRTY are two different
# things, and this test used to answer «FAIL» to both. A clone does not have
# `.privado/LEEME.md`, and `FAIL — cannot start` reads as «something is broken»,
# which is a false claim about a repository that is exactly as it should be. The
# two are counted apart and the exit code says which happened: 1 is a real
# problem, 2 is «cannot judge».
guardado = {}
faltan = []
for rel in VIGILADOS:
    if not os.path.exists(ruta_de(rel)):
        faltan.append(rel)
        continue
    if sucio(rel):
        fallo("setup", "%s differs from its committed version. Commit it or "
                       "restore it first: this test mutates it and leans on git "
                       "to make the restore trustworthy." % rel)
    with open(ruta_de(rel), "rb") as f:
        guardado[rel] = f.read()

if fallos or faltan:
    if fallos:
        print("RESULT: FAIL — cannot start")
        for que, detalle in fallos:
            print("  · %s\n      %s" % (que, detalle))
        if faltan:
            print("  (and %d more are not in the repository at all: %s)"
                  % (len(faltan), ", ".join(faltan)))
        sys.exit(1)
    print("RESULT: cannot judge — this test cannot start, and that is not a failure.")
    for rel in faltan:
        print("  · %s is not there" % rel)
    print("      It mutates the documents it watches and leans on git to restore them,")
    print("      so it cannot run without them. `.privado/` is never published: on a")
    print("      clone, leave this one out and say so. Exit 2 means «cannot judge».")
    sys.exit(2)

originales = {rel: hashlib.sha256(b).hexdigest() for rel, b in guardado.items()}


def restaura_todo(motivo):
    for rel, bytes_originales in guardado.items():
        with open(ruta_de(rel), "wb") as f:
            f.write(bytes_originales)
        if sha(rel) != originales[rel]:
            print("  NO SE PUDO RESTAURAR %s (%s). Usa: git checkout -- %s"
                  % (rel, motivo, rel))
            return False
    return True


try:
    # ------------------------------------------------------------------ 0
    print("== 0. It starts green, and running it green touches nothing ==")
    code, out = corre("verificar_version.py")
    arranca_verde = code == 0
    if not arranca_verde:
        fallo("green start", "verificar_version.py does not pass before we break "
                             "anything, so nothing below would prove anything")
        print(out)
    antes = {rel: os.stat(ruta_de(rel)).st_mtime_ns for rel in VIGILADOS}
    corre("verificar_version.py")
    despues = {rel: os.stat(ruta_de(rel)).st_mtime_ns for rel in VIGILADOS}
    tocados = [rel for rel in VIGILADOS if antes[rel] != despues[rel]]
    if tocados:
        fallo("side effect", "it changes the mtime of %s: a check must not repair "
                             "what it measures" % ", ".join(tocados))
    elif arranca_verde:
        print("   green, and no mtime moved.")

    # ------------------------------------------------------------------ 1
    print()
    print("== 1. Every control knows how to fail (%d of them) ==" % len(ROTURAS))
    for titulo, rel, viejo, nuevo, esperado in ROTURAS:
        texto = lee(rel)
        if texto.count(viejo) != 1:
            fallo(titulo, "the anchor appears %d times in %s, not once"
                  % (texto.count(viejo), rel))
            continue
        escribe(rel, texto.replace(viejo, nuevo, 1))
        code, out = corre("verificar_version.py")
        restaura_todo(titulo)
        if code != 1:
            fallo(titulo, "it came back GREEN (exit %d). The control does not "
                          "work." % code)
        elif esperado not in out:
            fallo(titulo, "it failed but the message does not name %r" % esperado)
        else:
            print("   red, and it names it: %s" % titulo)

    # ------------------------------------------------------------------ 2
    print()
    print("== 2. The 3.24 dry run ==")
    texto = lee(ENSAYO_DATO[0])
    if texto.count(ENSAYO_DATO[1]) != 1:
        fallo("dry run", "the anchor in %s is not unique" % ENSAYO_DATO[0])
    else:
        escribe(ENSAYO_DATO[0], texto.replace(ENSAYO_DATO[1], ENSAYO_DATO[2], 1))
        code, out = corre("build.py")
        if code != 0:
            fallo("dry run", "build.py failed: %s" % out.strip().splitlines()[-1:])
        else:
            html = lee("index.html")
            for nombre, aguja in ENSAYO_EN_LA_PAGINA:
                if aguja not in html:
                    fallo("dry run, %s" % nombre,
                          "the page does not show 3.24 by itself: %r is missing"
                          % aguja)
            print("   raising the version in the dataset alone put 3.24 in the "
                  "%d places the page shows it." % len(ENSAYO_EN_LA_PAGINA))

        code, out = corre("verificar_version.py")
        if code != 1:
            fallo("dry run", "verificar_version.py did not fail while the four "
                             "documents were still on 3.23")
        else:
            for rel, _, _ in ENSAYO_DOCS:
                if rel not in out:
                    fallo("dry run", "the failure does not name %s" % rel)
            print("   and it failed, naming the four documents left behind.")

        for rel, viejo, nuevo in ENSAYO_DOCS:
            texto = lee(rel)
            if texto.count(viejo) != 1:
                fallo("dry run, %s" % rel, "the anchor is not unique")
                continue
            escribe(rel, texto.replace(viejo, nuevo, 1))
        code, out = corre("verificar_version.py")
        if code != 0:
            fallo("dry run", "updating the four documents did not bring it back "
                             "to green")
        else:
            print("   updating those four brought it back to green.")
        print("   Cost of the update: 1 authored value + %d prose lines. "
              "0 code files, 0 paths." % len(ENSAYO_DOCS))
finally:
    print()
    print("== 3. Everything back in place ==")
    for rel, bytes_originales in guardado.items():
        with open(ruta_de(rel), "wb") as f:
            f.write(bytes_originales)
        bien = sha(rel) == originales[rel]
        if not bien:
            fallo("restore", "%s did NOT come back. git checkout -- %s" % (rel, rel))
        print("   %s %s" % ("ok  " if bien else "MAL ", rel))

print()
if fallos:
    print("RESULT: FAIL — %d problem%s" % (len(fallos), "s" if len(fallos) != 1 else ""))
    for que, detalle in fallos:
        print("  · %s\n      %s" % (que, detalle))
    sys.exit(1)
print("RESULT: PASS — every control fails when it should, and the update "
      "procedure holds end to end.")
