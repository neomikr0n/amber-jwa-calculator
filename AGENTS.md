# Amber — working notes for an agent

Amber is a DNA and cost calculator for **Jurassic World Alive 3.22**. It is one
self-contained HTML file, built from `plantilla.html` + `data/jwa-3.22.json` +
`modelo.py`. Read `README.md` first; this file is what you need in order to
change the code without breaking it.

## The house rule

**Measure before asserting, and never trust a check that can pass while proving
nothing.** Everything in this project was obtained by measuring, and the places
where an earlier claim turned out to be false are written down instead of
quietly deleted. Three habits follow:

- When a code comment and `.privado/LEEME.md` disagree, the manual is the
  measured one. Re-measure rather than picking a side.
- A test that shares the code's own reading of a value proves nothing: the
  mirror is born from the same misunderstanding and passes green. Judge with the
  statement of whoever uses the thing.
- A green run means nothing until you know what it would take to make it red.
  `verificar_motor.py` exists because the engine in the browser and the model in
  Python are two independent readings of the same rules.

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

**Two of the ten need `cache/`, which is not in the repository.** It is 92 MB of
scraped pages, excluded by `.gitignore`:

    python3 verificar_fuentes.py  # reads cache/
    python3 verificar_stats.py    # reads cache/

On a fresh clone they do not return a verdict, they crash: `os.listdir` on a
directory that is not there. Regenerate it once with `python3 scrape_paleo.py`,
which downloads the dinodex, or leave those two out **and say so** rather than
counting them as passed.

## Invariants that are easy to break

- **The tool name lives in one line.** `NOMBRE` in `modelo.py`. It reaches
  exactly two places, the `<title>` and the `<h1>`. An earlier comment claimed
  three, including the footer, and it was wrong.
- **The level multiplier table is not recomputable.** `MULT_NIVEL` in
  `modelo.py`. From level 1 to 30 it is `1.05^(L-26)` up to rounding, but from 31
  to 35 it is not: those are round figures set by hand. `verificar_stats.py`
  holds this down, with the numbers.
- **A table cell is found by its column name, never by index.** Several tests
  depend on it.
- **The `<script>` blocks share one global scope.** A new `let` can silently
  kill a global. `informe_browser.comprobar_scripts` compiles them together for
  exactly this reason. A function named with one letter has already collided
  with a local variable of the same name and thrown at runtime.
- **The browser tests assert on the Spanish interface.** They pin the language
  with `window.__lang = "es"` because their assertions are written against it.
  Do not remove that pin without rewriting them.
- **`informe_browser.veredicto()` reads the row prefixes `OK ` and `FALLO `.**
  It refuses to report green when a report declares failures but carries no
  failure row, so a renamed prefix shows up as NOT judgeable instead of hiding.
- **Some tests read the generated source, not the rendered page.**
  `probar_rareza.py` parses the `RAREZAS` and `CLASE` object literals out of the
  HTML with a regular expression. Changing how those literals are written, even
  in a way the page survives, breaks the test. Read it before touching them.

## Claims that were measured false

Recorded because they were believed once, and because each one is now held down
by a test. The point is not to re-litigate them but to recognise the shape.

| The claim | What measuring showed |
|---|---|
| The tool name appears in three places, the footer among them | Two: the `<title>` and the `<h1>`. The correction reached the manual in September 2026 and the code comment later still |
| `MULT_NIVEL` differs from `1.05^(L-26)` by at most 5e-5 relative, about 0.3 health points | False. Up to 3.68 % at level 34, which is 314 points on a 6,000-health creature. The closed form holds to level 30 and fails from 31 to 35 |
| All creatures in the game are female | False, measured. The recollection was wrong, not the data |

## The size claim in the manual is live

`verificar_motor.py` checks the byte figure written in `.privado/LEEME.md`
against the delivered HTML. Any change that alters the output size breaks that
check until the manual's figure is updated. That is deliberate: it is what keeps
the manual from drifting away from the artefact it describes. Update the number,
do not relax the check.

## Language

The interface is authored in **English**. Spanish lives in `I18N_ES` inside
`plantilla.html`, keyed by the English string, so the Spanish original is
restored verbatim. The switch in the header writes `jwa322.idioma`.

Resolution order is `window.__lang`, then the stored choice, then `en`. The
injected value must win, or the tests would depend on what a previous run left
behind.

**Translating is a trap in two directions.** Data keys such as `nivel`, `adn`,
`rareza` and the JSON metadata keys stay in Spanish: they are the schema, not
prose, and translating them breaks the pipeline. And every string passed to
`i18n()` needs an entry in `I18N_ES`; a missing one does not crash, it silently
renders English inside the Spanish interface. `verificar_idioma.py` checks parity
for exactly that reason.

## Storage keys are a contract with saved data

The interface keeps the user's creatures in `localStorage` under `jwa322.mios`,
`jwa322.inventario` and `jwa322.tema`. **Renaming one silently wipes what the
user has entered**, with no error and no warning. If a key ever has to change,
read the old one and write the new one in the same step.

## What must never be published

- **Creature images.** Copyrighted game artwork. Excluded by `.gitignore` and
  downloaded locally with `descargar_imagenes.py`. The app hides each image on
  error, so it works without them.
- **`cache/`.** Scraped pages, rebuilt by `scrape_paleo.py`.
- **`.privado/`.** The deep reference, described below. Not published and not
  deployed.

The repository is **private and not deployed**, so there is no live URL. Nothing
here should assume one.

## Where the deep reference is, and how to read it

`.privado/` is not published, so a fresh clone will not have it. When it is
there, it holds the measured detail that does not belong in this file:

| Path | What it holds |
|---|---|
| `.privado/LEEME.md` | The full manual: every rule the calculator implements, how each one was measured, and the mistakes corrected along the way |
| `.privado/HISTORIA.md` | What was asked and decided while this was built, in the author's own words |
| `.privado/conversaciones/MEMORIA-DIARIA.md` | The daily working log of the build, turn by turn |
| `.privado/conocimiento/` | The domain knowledge on JWA costs and data, kept as a skill |
| `.privado/sesiones/` | Exported transcripts of the sessions that built this |

**Consult them; do not load them whole.** The manual is about 93 KB and the
history about 305 KB, against an instruction budget of 64 KB per session, so
either one loaded in full would crowd out the work itself. Search first, then
read the part you need:

    grep -n "the claim you are about to touch" .privado/LEEME.md
    sed -n '440,520p' .privado/LEEME.md

Do this before changing any cost or fusion rule. The manual records how each
number was obtained and, in several places, which earlier claim turned out to be
false — that second part is the one that saves you from repeating it.

## Working with the author

He writes in Spanish and the project is in English: conversation in Spanish,
everything committed in English.

He asks for measurement, not assurance. State the confidence behind a claim and
where it comes from; when two sources disagree, say so and give both. He has
corrected this project more than once and was right to. Do not flatter a
decision, and do not paper over a gap: say what is not known.

Nothing destructive without a way back: copy and prove the copy with a hash, and
prefer renaming or moving over deleting.
