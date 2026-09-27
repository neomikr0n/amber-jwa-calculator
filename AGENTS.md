# Amber — working notes for an agent

Amber is a DNA and cost calculator for **Jurassic World Alive 3.22**. It is a
single self-contained HTML file, built from `plantilla.html` + `data/jwa-3.22.json`
+ `modelo.py`. Read `README.md` first; this file is what you need in order to
change the code without breaking it.

## Build and run

    python3 build.py

Writes `amber-jwa-3.22.html` (the artefact a human opens) and `index.html` (what
the site serves). Both are generated: never edit them by hand.

Python 3 only, no third-party dependencies.

## Run everything before committing

    python3 modelo.py             # 40 self-check cases plus level-cap invariants
    python3 verificar_motor.py    # the HTML engine against modelo.py, field by field
    python3 verificar_arbol.py    # the fusion tree, node by node
    python3 verificar_fuentes.py  # ingredient relationships and fusion levels
    python3 verificar_stats.py    # stats, boosts and the level multiplier table
    python3 equivalencia.py       # the engine in a real browser vs modelo.py
    python3 probar_ui.py          # interface behaviour in a real browser
    python3 probar_estres.py      # cost and tree edge cases
    python3 probar_rareza.py      # rarity colours and contrast
    python3 verificar_idioma.py   # dictionary parity, English default, pin precedence

The browser tests need Firefox at `/usr/lib/firefox/firefox`.

## Invariants that are easy to break

- **The tool name lives in one line.** `NOMBRE` in `modelo.py`. It reaches
  exactly two places, the `<title>` and the `<h1>`: counting the occurrences in
  the delivered HTML gives two. An earlier comment claimed three, including the
  footer, and it was wrong.
- **The level multiplier table is not recomputable.** `MULT_NIVEL` in
  `modelo.py`. From level 1 to 30 it is `1.05^(L-26)` up to rounding, but from 31
  to 35 it is not: those are round figures set by hand. `verificar_stats.py`
  holds this down.
- **A table cell is found by its column name, never by index.** Several tests
  depend on it.
- **The `<script>` blocks share one global scope.** A new `let` can silently
  kill a global. `informe_browser.comprobar_scripts` compiles them together for
  exactly this reason.
- **The browser tests assert on the Spanish interface.** They pin the language
  with `window.__lang = "es"` because their assertions are written against it.
  Do not remove that pin without rewriting them.
- **`informe_browser.veredicto()` reads the row prefixes `OK ` and `FALLO `.**
  It now refuses to report green when a report declares failures but carries no
  failure row, so a renamed prefix shows up instead of hiding.

## Language

The interface is authored in **English**. Spanish lives in `I18N_ES` inside
`plantilla.html`, keyed by the English string, so the Spanish original is
restored verbatim. The switch in the header writes `jwa322.idioma`.

Resolution order is `window.__lang`, then the stored choice, then `en`. The
injected value must win, or the tests would depend on what a previous run left
behind.

Data keys such as `nivel`, `adn`, `rareza` and the JSON metadata keys stay in
Spanish: they are the schema, not prose. Translating them breaks the pipeline.

## What must never be published

- **Creature images.** Copyrighted game artwork. Excluded by `.gitignore` and
  downloaded locally with `descargar_imagenes.py`. The app hides each image on
  error, so it works without them.
- **`cache/`.** Scraped pages, rebuilt by `scrape_paleo.py`.
- **`.privado/`.** The deep reference: the full project manual, the migrated
  skill, the conversation history and the daily working memory. Not published
  and not deployed.

## Third party

Creature data comes from paleo.gg, which the app credits on screen. `LICENSE`
covers the code only; `NOTICE` records what is third-party, which trademarks
belong to their owners, and why the artwork is not distributed.
