# Amber — working notes for an agent

Amber is a DNA and cost calculator for **Jurassic World Alive 3.23**. It is one
self-contained HTML file, built from `plantilla.html` + `data/jwa-3.23.json` +
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

Writes `index.html`, and that is the only output. It is generated: never edit it
by hand.

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
    python3 probar_demo.py        # the one-file demo: nothing external, nothing stale

The browser tests need Firefox at `/usr/lib/firefox/firefox`.

**Three of the eleven need material that is not in the repository.** `cache/` is
92 MB of scraped pages, excluded by `.gitignore`:

    python3 verificar_fuentes.py  # reads cache/
    python3 verificar_stats.py    # reads cache/

On a fresh clone they do not return a verdict, they crash: `os.listdir` on a
directory that is not there. Regenerate it once with `python3 scrape_paleo.py`,
which downloads the dinodex, or leave them out **and say so** rather than
counting them as passed.

`probar_demo.py` is the third: it reads `amber-demo.html`, which is built from
`.privado/` and carries copyrighted artwork, so it is not published either. On a
fresh clone it exits 2 with a message saying exactly that.

## Invariants that are easy to break

- **The Omega training table comes only from `detail.points`, and only Omegas have
  it.** `criaturas[u].entrenamiento` (scraper) → `C[u][11] = [cap, delta, pcap]` per
  stat, in the order of `M.statsOrden`. `verificar_stats.py` checks it in both
  directions against the whole cache: card and data must agree on WHICH creatures
  have it, and the three groups must match stat by stat. The bound the app uses is
  **`pcap`**, never `(cap − base) / delta`: in `stegouros` that division gives 7.5 for
  crit damage and the source stores 7, so its cap stays one point short of reachable.
- **The training pool (7 per level) is an ASSUMPTION, not a source datum.** Two
  figures from a secondary guide (level 11 → 77, level 26 → 182) land exactly on 7,
  and it lives in `PUNTOS_OMEGA_NIVEL` with both beside it. There is no official
  confirmation and the manual carries it as medium confidence. `modelo.py`,
  `verificar_stats.py` and three checks in `probar_ui.py` pin it: changing the
  constant without changing the figures turns red.
- **Training is not a cost.** It spends points, not DNA or coins, so `plan`,
  `costeADN`, `totales` and the whole cost engine must not move — `verificar_motor.py`
  and `verificar_arbol.py` compare field by field and would catch it. And the training
  controls live inside the stat cards, hidden behind `data-ent="1"` on the panel: a
  creature without training must render exactly the card it rendered before.
- **An Omega's stats do NOT scale with the level.** Its base is the level-26 value:
  levelling gives it training points, not raw stats, so `statsDe` uses `f = 1` for
  them and paleo.gg's cap is an absolute number that `pcap` points always reach. It
  was implemented the other way first — scaled like every other rarity — and n30's
  game screen showed it short. `probar_ui.py` pins the game's three numbers (4522
  health, 2250 damage, 116 speed) and goes red if the multiplier comes back.
- **The Fusion Tree is always drawn complete, and drawing costs nothing.** `plan`
  descends into the ingredients whether or not the creature still needs them; the
  subtree of a node with nothing missing is built in `soloVer` mode — painted, and
  charged zero — and those rows say «not needed» instead of inventing a levelling.
  `totales` keeps `soloVer` nodes out of `porUuid`, which is what feeds the tree
  report and the «create all» list, so every DNA and coin figure is the one of the
  tree that only had the branches that were needed. `verificar_arbol.py` holds it
  down against `plan_podado`, an **independent implementation of the old rule**
  (prune the branch that needs nothing): 8 money fields must be identical in all
  cases, and the complete tree must never draw fewer nodes. Putting the
  `deficit > 0` condition back into `plan` makes the dinos under a covered
  ingredient vanish again, which is the bug n30 reported on 27-sep-2026.
- **The output filename carries no version, and that is not cosmetic.** The
  browser keys a `file://` document's `localStorage` to the FULL PATH, and the
  app has no account and no server: that store is the only copy of n30's saved
  creatures. Renaming the artefact therefore creates an empty store and strands
  the old one, and the screen that shows is indistinguishable from data loss.
  It already happened twice: on 30-sep-2026 opening `amber-jwa-3.23.html` for
  the first time showed an empty calculator while 25 creatures sat in the store
  of `amber-jwa-3.22.html`, and the "restore" that followed copied one store
  over the other. `build.py` now writes a single `index.html`. **Do not put a
  version in that name, and do not add a second output** — if a second output
  ever comes back, `verificar_motor.py` has to be told to redirect it, or its
  check repairs the file it is measuring and goes blind.
- **The one-file demo is a PACKAGING, never a second build.** `build_demo.py`
  reads the delivered `index.html` and only puts things INSIDE it: the
  image map (`__IMAGENES__`, empty in the normal artefact, keyed by the relative
  path so a missing key is the file of always), a script that seeds the saved
  creatures into `localStorage` before the app reads them, and the opening view.
  It stamps the sha256 of the artefact it packed, and `probar_demo.py` recomputes
  it: rebuilding the artefact and forgetting the demo turns red instead of showing
  yesterday's numbers. The demo carries inlined copyrighted artwork, so it is
  gitignored; the script and the test are published.
- **The delivered HTML and `index.html` are both held against a fresh build, and the
  check must not repair what it measures.** `verificar_motor.py` rebuilds into a
  temporary directory and demands that the file on disk be exactly that, naming the
  `data-page-node-id` attributes when an editor has rewritten it (it happened on
  25-sep with 133, and again on 30-sep with 122). Redirecting only `build.DESTINO`
  left `main()` overwriting the real `index.html`, so the comparison read a file the
  test had just repaired: it could not fail, and it hid a stale `index.html` on every
  run. Both destinations are redirected. When it goes red the routine is
  `python3 build.py` and run it again — and if the working tree goes dirty after you
  open the artefact in a preview or a page editor, that is the same failure: rebuild
  before committing.
- **Motion off means off, pseudo-elements included.** The rule that switches every
  animation and transition off under `prefers-reduced-motion` has to name
  `*::before` and `*::after` as well: `*` does not reach a pseudo-element, and the
  light that runs along Amber-OLED's panel edges lives in a `::before`. An
  animation added there is invisible to `*` and keeps moving for whoever asked the
  system for less of it.
- **A rarity colour is a DATUM, not decoration: no theme may repaint it.** The
  seven rarity colours (`--r-*`) and the four semantic ones (`--verde` reaches,
  `--ambar` missing, `--rojo` error, `--azul` information) are identical in
  every theme, present and future. A theme may change backgrounds, borders,
  depth and motion, and nothing that means something. If a theme repainted the
  tags, the same creature would say two different things depending on the theme.
  `probar_ui.py` holds it down on the rendered page and **in every theme it finds
  in the dropdown** (the list is read from the `<option>` values, so a new theme
  is covered without touching the test): it compares the 13 computed variables
  against the default's, and it also compares the colour of an actual rarity tag
  painted in the creature card.
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
  **And a `catch` in a diagnostic must write a `FALLO` row, never a note:** an
  exception that truncates a pass leaves a shorter «all OK» behind, which reads
  as green. It happened: a helper that did not exist in that block threw, the
  first pass stopped at check 99 of 152 and the run still exited 0 — the falling
  check count was the only clue. `probar_ui.py` holds a smoke test for this now;
  the other two `catch` blocks were already right.
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
| Every creature's health and damage scale with the level | True for every rarity **except Omega**, measured in the game. An Omega's base is the level-26 value and levelling gives it training points, not stats: Little Eatie at level 21, 73 points to health and 74 to damage, gives 4522 health and 2250 damage with the level multiplier removed, and 4001 / 1508 with it. It had been written the other way as a «reading» of paleo.gg's table, and it was a guess |

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
- **The small UI icons ARE tracked, and that is on purpose.** `img/stat/`,
  `img/cat/`, `img/res/` and `img/clase/` are committed. The app asks for them by
  path and **hides an image it cannot load**, so an icon left out of the repository
  is a silent hole, not an error. `img/clase/` spent a while in `.gitignore`
  labelled «downloaded and never used»; it is used now —the class badge before the
  creature's name— and it is back in the repository.
- **`cache/`.** Scraped pages, rebuilt by `scrape_paleo.py`.
- **`.privado/`.** The deep reference, described below. Not published and not
  deployed.

The repository is **private and not deployed**, so there is no live URL. Nothing
here should assume one.

- **`AGENTS.local.md`.** Personal working notes for whoever is driving this
  session, listed in `.gitignore`. If the file is there, it is read at startup;
  if a clone does not have it, nothing is missing.

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
