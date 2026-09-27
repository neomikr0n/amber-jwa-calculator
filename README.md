# Amber

**A DNA and cost calculator for Jurassic World Alive 3.22.**

Amber answers one question: how much DNA, how many coins and how many fusions
does it take to bring any creature in the game up to the level you want — and
which ingredients, in cascade, you need in order to fuse the hybrids on the way.

It is a single self-contained HTML file. No server, no CDN, no build step to run
it. Open it and it works offline, with your data stored in your own browser.

**Live site:** _not published yet_

---

## What it does

- **Calculator.** Pick any of the 518 creatures, set the level you have and the
  level you want, and it returns the DNA, the coins and the number of fusions
  required, plus what you are missing given the DNA you already hold.
- **Fusion tree.** The full ingredient cascade for any hybrid, creature by
  creature, down to the ones you simply dart in the wild. Every node is
  editable: type a level and a DNA figure, or untick *Created*, and everything
  hanging from it recalculates.
- **My creatures.** Everything you enter is saved in the browser, with a target
  level per creature, and exportable as JSON.
- **Real stats.** Health, damage, speed, armour and both critical values at any
  level, with the enhancement track and its cost.
- **Catalysts.** A recombination planner, marked in the interface as unverified
  data because the rates are not published by the game.
- **Two languages.** English by default, Spanish behind the switch in the
  header. The interface is authored in English and Spanish lives in a
  dictionary inside the file, so both languages travel in the same HTML.

## Build it

Only Python 3 is needed. There are no third-party dependencies.

```bash
python3 build.py
```

That writes two identical files: `amber-jwa-3.22.html`, the versioned artefact
you open by double-clicking, and `index.html`, which is what the site serves.
Neither is edited by hand.

## Regenerate the data

The creature data is committed, so this is only needed when the game updates.

```bash
python3 scrape_paleo.py          # rebuilds cache/ and data/jwa-3.22.json
python3 descargar_imagenes.py    # optional: fetches the creature photos
```

`scrape_paleo.py` downloads the dinodex and writes `cache/`, which is about
92 MB and is not in the repository: it is a regenerable cache, and it is listed
in `.gitignore`.

`descargar_imagenes.py` fetches the 518 creature images into `img/`. They are
**not** in the repository and are not published on the site, because they are
copyrighted game artwork. See `NOTICE`. Without them the calculator still works:
each image hides itself on error and the layout falls back to names and figures.

## Tests

The calculator is verified against an independent Python model of the same
costs, and against the source pages. Every script is standalone:

```bash
python3 modelo.py             # 40 self-check cases plus level-cap invariants
python3 verificar_motor.py    # the HTML engine against modelo.py, field by field
python3 verificar_arbol.py    # the fusion tree, node by node
python3 verificar_fuentes.py  # ingredient relationships and fusion levels
python3 verificar_stats.py    # stats, boosts and the level multiplier table
python3 equivalencia.py       # the engine inside a real browser vs modelo.py
python3 probar_ui.py          # interface behaviour in a real browser
python3 probar_estres.py      # cost and tree edge cases
python3 probar_rareza.py      # rarity colours and contrast
python3 verificar_idioma.py   # dictionary parity, English default, pin precedence
```

The browser tests need Firefox at `/usr/lib/firefox/firefox` and pin the
interface language to Spanish, which is the language their assertions are
written in.

## Where the data comes from

Creature data is extracted from **[paleo.gg](https://paleo.gg)**, which the
application credits on screen. Costs and fusion rules were cross-checked against
the site's own calculator, against the official 3.22 release notes, and against
the `jurassic-journal` database.

The DNA per fusion is an **average of 22**: each fusion returns a random amount,
so the computed number of fusions is an estimate, not a promise.

## Licence

Source code: **Apache License 2.0** — see `LICENSE`.

Third-party data, trademarks and the artwork that is deliberately not
distributed: see `NOTICE`. In short, the licence covers the code in this
repository and does not extend to the game data, and this is an unofficial fan
project with no connection to the game's owners.

## Notes

- **The deployed site shows no creature photos.** They are copyrighted game
  artwork and are excluded on purpose. Clone the repository and run
  `descargar_imagenes.py` to see them locally.
- **Advertising is a deliberate later decision, not an oversight.** If ads are
  ever added, the sensible order is to ask the rights holders first; monetising
  a fan tool built on someone else's game changes its legal character, and no
  software licence changes that.
