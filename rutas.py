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
