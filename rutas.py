#!/usr/bin/env python3
"""Where the project's files are, and which version of the game they hold.

There is exactly ONE dataset and ONE deliverable, and **neither name carries the
game version**. The version lives inside the dataset, in `meta.version_juego`,
and whoever needs it reads it from there through this module.

WHY THE NAMES CARRY NO VERSION

Until 1-oct-2026 the dataset was `data/jwa-3.23.json` and the deliverable was
`amber-jwa-3.23.html`. Every game update therefore meant editing the same
literal in ten scripts, and a forgotten one produced a file that looked right
and read the wrong data.

The versioned name of the deliverable was worse than tedious, it was a data-loss
bug: a `file://` document gets its storage keyed to the FULL PATH, so a new name
is a new empty store and the saved creatures become invisible. It happened
twice. The full account is at the top of `build.py`.

So the rule is: **the version is a value inside the data, never part of a file
name.** An update changes one thing — the `--version` passed to
`scrape_paleo.py` — and nothing else in the project has to be edited.

    from rutas import DATOS, HTML, version
"""

import json
import os
import re

RAIZ = os.path.dirname(os.path.abspath(__file__))

# The dataset. Stable name on purpose: see above.
DATOS = os.path.join(RAIZ, "data", "jwa.json")

# The deliverable. Stable name on purpose, and not for tidiness: it is the path
# the browser keys the saved creatures to, and the site already serves it.
HTML = os.path.join(RAIZ, "index.html")


def version():
    """The game version, read from the dataset it belongs to.

    It is a function and not a module constant on purpose: importing this
    module must not read a 275 KB file, because most of the scripts that need
    `HTML` do not care about the version at all. Call it once and keep the
    result if you need it twice.
    """
    with open(DATOS, encoding="utf-8") as f:
        return json.load(f)["meta"]["version_juego"]


def exigir_material(ruta, motivo, arreglo, guion):
    """Stops with exit 2 — «cannot judge» — when the material is not there.

    Exit 2 and not 1, and the difference is not cosmetic. A test that cannot read
    what it verifies has not failed: it has not run. Measured on a real clone, two
    of these tests came back with a `FileNotFoundError` traceback and the reader
    goes looking for the defect in the code, where there is none.

    The message has to name three things or it is not worth having: what is
    missing, why a clone does not have it, and how to get it back. `probar_demo.py`
    has always done this; it lives here now so the rest do not each invent it.
    """
    if os.path.exists(ruta):
        return
    print("RESULT: cannot judge — %s is not there." % os.path.relpath(ruta, RAIZ))
    print("        %s" % motivo)
    print("        %s" % arreglo)
    print("        %s has not run and has not failed: it has nothing to read."
          % guion)
    raise SystemExit(2)


def inyectar_en_cabeza(html, codigo, etiqueta="the test"):
    """Puts `codigo` right after the REAL `<head ...>` tag, and returns the page.

    WHY IT IS NOT `html.replace("<head>", ...)`
    -------------------------------------------
    The editor that works on this project leaves `data-page-node-id` attributes
    on the opening tags, so the real tag becomes `<head data-page-node-id="...">`
    and the literal `"<head>"` disappears from it. But the literal string does
    NOT disappear from the file: it survives inside a comment of the
    application's own JavaScript, «…read as «boring» (the <head> script does
    that mapping)». So a naive replace found that comment first and injected the
    code INTO the middle of a `<script>` block, in the middle of a comment. The
    injected `</script>` then closed the block early, the browser painted the
    rest of the application as TEXT on the page, the application never ran, and
    the only symptom was «the browser did not deliver the report»: the test came
    out unjudgeable and the cause was nowhere in the message.

    It cost a full diagnosis on 1-oct-2026, with the screenshot as evidence.
    `probar_ui.py` had already learned the same lesson for `<body>` —«The viewer
    may leave attributes on <body>, so it is no good searching for "<body>" as
    is»— and the lesson had been applied there and nowhere else. This is that
    lesson for `<head>`, written once instead of in eight places.

    A CONTAMINATED deliverable is REFUSED, not worked around: judging it would
    judge a file that is not the one `build.py` produces, and the verdict would
    be about something the user never runs. The refusal names the cause, so the
    next person does not repeat this diagnosis.
    """
    sucio = html.count("data-page-node-id")
    if sucio:
        raise SystemExit(
            "%s: the deliverable carries %d «data-page-node-id» attributes injected by an "
            "editor, so it is not what build.py produces. This is NOT a defect of the test: "
            "restore it with `git restore index.html` and run this again." % (etiqueta, sucio))
    m = re.search(r"<head[^>]*>", html)
    if not m:
        raise SystemExit("%s: the HTML has no <head>" % etiqueta)
    return html[:m.end()] + "\n" + codigo + html[m.end():]


def enlazar_img(destino, origen):
    """Points `destino` at `origen`, replacing whatever was there.

    WHY IT DOES NOT DELETE FIRST
    ----------------------------
    `os.symlink` fails when the path exists, so the obvious move is to delete
    it, and that is what nine copies of this idiom did. Two problems, both
    measured on 1-oct-2026 while checking a fresh clone:

    · `os.unlink` does not delete on this machine: the sandbox intercepts it and
      moves the file to the trash instead. To do that it RESOLVES the link and
      builds a trash directory at the root of the mount the target lands on. A
      link pointing at a second checkout of this project lives under `/home`, so
      the shim tried `/home/.Trash-1000`, which the user cannot create, and the
      scripts died with `PermissionError: [Errno 13]` in the middle of their
      setup — before opening the browser, and naming a trash directory that has
      nothing to do with the test. That is the whole reason this function
      exists: the tests have to survive being run from two checkouts on the same
      machine, which is exactly what checking a clone means.

    · And the old `if not os.path.exists(destino): os.symlink(...)` is wrong
      when the link exists but its target does not: `exists` follows the link
      and answers False, so the `os.symlink` that follows dies with
      `FileExistsError`.

    Renaming over the link does the same job, atomically, and never touches the
    trash. The temporary name carries the pid and a counter so it cannot
    collide, and nothing is ever deleted to make room.
    """
    if os.path.isdir(destino) and not os.path.islink(destino):
        import shutil
        shutil.rmtree(destino, ignore_errors=True)
    if os.path.islink(destino) and os.readlink(destino) == origen:
        return
    tmp, n = "%s.%d" % (destino, os.getpid()), 0
    while os.path.lexists(tmp):
        n += 1
        tmp = "%s.%d.%d" % (destino, os.getpid(), n)
    os.symlink(origen, tmp)
    os.replace(tmp, destino)
