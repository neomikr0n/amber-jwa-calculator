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
