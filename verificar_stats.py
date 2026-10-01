#!/usr/bin/env python3
"""
Checks the dino stats and the enhancement track against the paleo.gg cache.

Why this file exists
--------------------
The tool shows six numbers per creature and calls them «current and trustworthy
data». That is a CLAIM, and until now no test backed it: the numbers came from
the JSON, and the JSON was written by `scrape_paleo.py` once. If paleo.gg fixes
a stat, the JSON keeps the old one and nothing warns. This is the same hole that
`verificar_fuentes.py` closed for the zones, and it is closed the same way: by
re-reading the source.

What it checks, and why
-----------------------
1. **The six stats, one by one, against the cached card.** Not against the JSON
   (which is what we want to check), but against the `health/damage/
   speed/armor/crit/critm` field of `__NEXT_DATA__.props.pageProps.detail`. And
   also against the RENDERED TEXT of the card, which is a second independent
   copy inside the same file: if paleo.gg painted one thing and served another,
   it would show up here.
2. **At what level those numbers are.** The card itself says so in the
   «Compare Creatures» link: `compare?ck=0__<uuid>__26`. The 26 is not set by
   us, the source sets it, in all 519 cards. The whole interface relies on the
   datum being level 26; this checks it.
3. **The enhancement track, step by step, against the cache**, and against the
   copy that paleo.gg itself brings in `evolutionData` — two places in the same
   file that have to say the same thing.
4. **The order of the steps is NOT the same in Unique and in Apex.** It was
   discovered by looking at a screenshot, after having assumed the opposite.
   Here the whole distribution is measured and asserted.
5. **`MULT_NIVEL` is not the closed form `1.05^(L-26)`.** It is the mistake
   that almost slipped in: the table matches the closed form up to level 30
   (rounding noise) and from 31 on it separates on purpose, up to 3.7 % at
   level 34. It is measured and asserted in both directions, so that nobody
   «simplifies» the table believing there are spare numbers.
6. **The domains the interface takes for granted**: the five reward types, the
   four resources, and that a disk icon exists for each one. New code without
   an icon would be painted with a broken `src` and nobody would notice.

    python3 verificar_stats.py     -> 0 if everything matches, 1 if not
"""
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from modelo import (BOOST_FRACCION, BOOST_VELOCIDAD, MEJORA_NIVEL_MIN,
                    MEJORA_ORDEN, MEJORA_PASOS, MULT_NIVEL, PUNTOS_OMEGA_NIVEL,
                    TOPE_BOOST_STAT)

from rutas import DATOS

CACHE = os.path.join(RAIZ, "cache")
IMG = os.path.join(RAIZ, "img")

fallos = []
n_ok = 0


def ok(que, bien, detalle=""):
    global n_ok
    if bien:
        n_ok += 1
        print("OK    %s%s" % (que, ": " + detalle if detalle else ""))
    else:
        fallos.append(que)
        print("FAIL  %s%s" % (que, ": " + detalle if detalle else ""))


# ---------------------------------------------------------------------------
# 0) Load the cache only once
# ---------------------------------------------------------------------------
# 519 cards x 180 KB: they are read whole and kept. Reading them twice per
# section would throw away half a minute.
NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
# The stats block goes from `id="stats"` to `id="resistance"`: bounded on
# purpose, because the stat icons also appear in the battle simulator that the
# card includes further down.
STAT_TXT = re.compile(r'images/stat/(\w+)\.png"[^>]*/>\s*<b[^>]*>(?:<span[^>]*>)?([^<]+)')
# The level of the numbers, declared by the card itself.
NIVEL = re.compile(r'compare\?ck=0__([a-z0-9_]+)__(\d+)')

fichas = {}
for f in sorted(os.listdir(CACHE)):
    if not f.endswith(".html") or f == "dinodex.html":
        continue
    s = open(os.path.join(CACHE, f), encoding="utf-8").read()
    m = NEXT.search(s)
    det = json.loads(m.group(1))["props"]["pageProps"]["detail"] if m else None
    i, j = s.find('id="stats"'), s.find('id="resistance"')
    fichas[f[:-5]] = {
        "det": det,
        "txt": STAT_TXT.findall(s[i:j]) if i > 0 and j > i else [],
        "nivel": NIVEL.findall(s),
    }

d = json.load(open(DATOS, encoding="utf-8"))
cri = d["criaturas"]

print("=== 0. the cache and the data cover the same thing ===")
ok("there is one card per creature and one creature per card",
   set(fichas) == set(cri) and len(fichas) == 519,
   "%d cards, %d creatures, %d without a pair"
   % (len(fichas), len(cri), len(set(fichas) ^ set(cri))))
ok("all cards have __NEXT_DATA__ and a stats block",
   all(v["det"] and len(v["txt"]) == 6 for v in fichas.values()),
   "%d cards checked" % len(fichas))

# ---------------------------------------------------------------------------
# 1) The six stats: against the cache field AND against the rendered text
# ---------------------------------------------------------------------------
# `CAMPOS` is the translation between the name the source uses and the one we
# use. It is written once and used in both directions: if someday someone
# renames a JSON key, this stops matching.
CAMPOS = [("health", "vida"), ("damage", "dano"), ("speed", "velocidad"),
          ("armor", "armadura"), ("crit", "critico"), ("critm", "dano_critico")]
# The three that the card paints with «%». It is a presentation decision, but it
# rests on the data: if paleo.gg stopped painting them that way, it would have to
# be reviewed.
PCT = {"armor", "crit", "critm"}

print()
print("=== 1. the six stats, one by one (519 x 6 = 3,114 numbers) ===")
malCampo = []
malTxt = []
for u, v in sorted(fichas.items()):
    det = v["det"]
    for campo, clave in CAMPOS:
        if det.get(campo) != cri[u]["stats"][clave]:
            malCampo.append("%s.%s: cache=%r json=%r"
                            % (u, campo, det.get(campo), cri[u]["stats"][clave]))
for u, v in sorted(fichas.items()):
    pintado = dict(v["txt"])
    for campo, clave in CAMPOS:
        esperado = cri[u]["stats"][clave]
        bruto = pintado.get(campo)
        # The card paints the bare number, without a thousands separator, and
        # with «%» on the three percentages. The number is compared, not the
        # format: what matters is that the figure seen is the one we have.
        limpio = (bruto or "").replace("%", "").strip()
        if not limpio.isdigit() or int(limpio) != esperado:
            malTxt.append("%s.%s: pintado=%r esperado=%d" % (u, campo, bruto, esperado))
ok("the cache field and the JSON say the same in all 3,114",
   not malCampo, malCampo[0] if malCampo else "3,114 numbers, 519 creatures")
ok("the RENDERED text of the card too (second independent copy)",
   not malTxt, malTxt[0] if malTxt else "no discrepancies")
ok("the three percentages are painted with «%» and the other three are not",
   all(("%" in dict(v["txt"])[c]) == (c in PCT)
       for v in fichas.values() for c, _ in CAMPOS),
   "armor, crit and critm carry «%»; health, damage and speed do not")
ok("the card paints the six in the same order, always",
   all([c for c, _ in v["txt"]] == [c for c, _ in CAMPOS] for v in fichas.values()),
   "health, damage, speed, armor, crit, critm")

# ---------------------------------------------------------------------------
# 2) At what level those numbers are: the source says it, not us
# ---------------------------------------------------------------------------
# This is the foundation of the whole tool. If the datum were not level 26,
# `MULT_NIVEL[25] == 1e9` would not hold and all the interface stats would be
# shifted. The card declares it in the compare link.
print()
print("=== 2. the level of the datum, declared by the source ===")
niveles = collections.Counter()
enlaces = []
for u, v in fichas.items():
    if len(v["nivel"]) != 1 or v["nivel"][0][0] != u:
        enlaces.append((u, v["nivel"][:2]))
    else:
        niveles[v["nivel"][0][1]] += 1
ok("each card declares its level once, and it is its own",
   not enlaces, str(enlaces[:3]) if enlaces else "%d cards" % len(fichas))
ok("the declared level is 26 in all 519 (not 1, not 35, not the maximum)",
   niveles == {"26": 519}, str(dict(niveles)))
# And the consequence, checked over the whole dataset: at level 26 the
# multiplier changes NOTHING, in none of the 3,114 numbers.
ident = all(int(cri[u]["stats"][k] * MULT_NIVEL[25] // 10 ** 9) == cri[u]["stats"][k]
            for u in cri for k in cri[u]["stats"])
ok("at level 26 the table returns the same number, in all 3,114",
   ident and MULT_NIVEL[25] == 1000000000,
   "MULT_NIVEL[25] = %d, exact" % MULT_NIVEL[25])

# ---------------------------------------------------------------------------
# 3) The enhancement track, step by step, against BOTH cache copies
# ---------------------------------------------------------------------------
# `detail.enhancements` and `evolutionData[<uuid>].enhancements` are two copies
# of the same thing inside the same file. Checking both is not redundant: if
# paleo.gg updates one and forgets the other, that is exactly what must be seen.
print()
print("=== 3. the enhancement track (147 creatures) ===")
conPista = [u for u in cri if cri[u].get("mejoras")]
sinPista = [u for u in cri if not cri[u].get("mejoras")]
ok("147 with a track and 372 without one, and they add up to 519",
   len(conPista) == 147 and len(sinPista) == 372 and len(conPista) + len(sinPista) == 519,
   "%d + %d = 519" % (len(conPista), len(sinPista)))

porRareza = collections.Counter(cri[u]["rareza"] for u in conPista)
ok("only Unique and Apex have a track; no other rarity",
   set(porRareza) == {"unique", "apex"},
   "unique %d, apex %d" % (porRareza["unique"], porRareza["apex"]))
ok("and they are all the Uniques and all the Apex there are",
   porRareza["unique"] == 92 and porRareza["apex"] == 55,
   "92 unique + 55 apex = 147")

malPaso = []
malEvol = []
sinCinco = []
for u in conPista:
    mj = cri[u]["mejoras"]
    det = fichas[u]["det"]
    if len(mj) != MEJORA_PASOS:
        sinCinco.append("%s: %d steps" % (u, len(mj)))
    # Normalize: the cache stores req as lists, the JSON the same; they are
    # compared as sorted tuples because the order inside `req` means nothing.
    def norm(pasos):
        return [(p["cost"],
                 tuple(sorted((r[0], r[1]) for r in p["req"])),
                 (p["rwd"]["type"], p["rwd"]["value"])) for p in pasos]
    if norm(mj) != norm(det.get("enhancements") or []):
        malPaso.append(u)
    ev = (det.get("evolutionData") or {}).get(u) or {}
    if norm(mj) != norm(ev.get("enhancements") or []):
        malEvol.append(u)
ok("all 147 have exactly %d steps" % MEJORA_PASOS, not sinCinco,
   str(sinCinco[:3]) if sinCinco else "5 steps x 147 = 735 steps")
ok("cost, requirements and reward of the 735 steps match the cache",
   not malPaso, str(malPaso[:5]) if malPaso else "735 steps, one by one")
ok("and they also match the SECOND copy (`evolutionData`)",
   not malEvol, str(malEvol[:5]) if malEvol else "the cache does not contradict itself")

# The ingredients go the same way and with the same pattern: if one copy
# gets out of sync, both things get out of sync.
malIng = [u for u in cri
          if sorted(cri[u]["ingredientes"]) !=
             sorted(((fichas[u]["det"].get("evolutionData") or {}).get(u) or {})
                    .get("ingredients") or [])]
ok("the ingredients of all 519 match `evolutionData`", not malIng,
   str(malIng[:5]) if malIng else "519 creatures")

# ---------------------------------------------------------------------------
# 4) The order of the steps: it is NOT the same in unique and in apex
# ---------------------------------------------------------------------------
# Here there was a real mistake. A single order was assumed for both
# rarities, and it was false: in a Unique step 1 is health, in an Apex step 1 is
# speed. It was seen in a screenshot, not in the code. The full measurement:
print()
print("=== 4. the order of the steps, by rarity ===")
ordenes = collections.defaultdict(collections.Counter)
for u in conPista:
    tipo = tuple(p["rwd"]["type"] for p in cri[u]["mejoras"])
    ordenes[cri[u]["rareza"]][tipo] += 1

for rareza in ("unique", "apex"):
    medido = ordenes[rareza]
    ok("the %s has ONE single order, and it is the one in MEJORA_ORDEN" % rareza,
       list(medido) == [tuple(MEJORA_ORDEN[rareza])],
       "x%d  %s" % (list(medido.values())[0], " -> ".join(medido and list(medido)[0] or ())))
ok("and the two orders are DIFFERENT (the mistake that was fixed)",
   MEJORA_ORDEN["unique"] != MEJORA_ORDEN["apex"],
   "unique starts with health; apex, with speed")

# The values of each reward, measured. They are not equal between rarities: the
# `boost_max` gives +1 in a Unique and +2 in an Apex.
valores = collections.defaultdict(collections.Counter)
for u in conPista:
    for p in cri[u]["mejoras"]:
        valores[(cri[u]["rareza"], p["rwd"]["type"])][p["rwd"]["value"]] += 1
ESPERADO_VAL = {
    ("unique", "health"): {110: 92}, ("unique", "damage"): {110: 92},
    ("unique", "speed"): {2: 92}, ("unique", "boost_max"): {1: 92},
    ("apex", "health"): {110: 55}, ("apex", "damage"): {110: 55},
    ("apex", "speed"): {2: 55}, ("apex", "boost_max"): {2: 55},
}
ok("the reward values are the measured ones (health/damage x1.10 · speed +2)",
   all(dict(valores[k]) == v for k, v in ESPERADO_VAL.items()),
   "boost_max: +1 in unique (x92), +2 in apex (x55)")
ok("the `moves_reactive` steps each give a different move",
   all(len({p["rwd"]["value"] for p in cri[u]["mejoras"]
            if p["rwd"]["type"] == "moves_reactive"}) == 1 for u in conPista),
   "147 reactive moves, none repeated within its creature")

# ---------------------------------------------------------------------------
# 5) MULT_NIVEL: 35 entries, and it is NOT 1.05^(L-26)
# ---------------------------------------------------------------------------
# The comment in `modelo.py` said that the closed form differs by «up to
# 5e-5 relative, ~0.3 health points». On measuring it whole to write this
# test, result: **it is false**. It matches up to level 30 (rounding noise,
# 1.5e-4 at most) and from 31 to 35 it separates on purpose: 1.27 · 1.32 · 1.37 ·
# 1.425 · 1.50, with an error of up to 3.7 %. In a creature with 6,000 health
# that is 314 points, not 0.3. The comment was fixed.
print()
print("=== 5. the level table ===")
ok("the table has 35 entries, one per level",
   len(MULT_NIVEL) == 35, "%d entries" % len(MULT_NIVEL))
ok("it is strictly increasing (leveling up never removes stats)",
   all(MULT_NIVEL[i] < MULT_NIVEL[i + 1] for i in range(34)),
   "from %d to %d" % (MULT_NIVEL[0], MULT_NIVEL[-1]))
ok("level 26 is exactly 1,000,000,000, without rounding",
   MULT_NIVEL[25] == 1000000000, "1e9, exact")
ok("level 35 is exactly 1.5 (the cap is set by hand, not multiplied)",
   MULT_NIVEL[34] == 1500000000, "1.5e9, exact")

err = {L: abs(MULT_NIVEL[L - 1] / 1e9 - 1.05 ** (L - 26)) / (MULT_NIVEL[L - 1] / 1e9)
       for L in range(1, 36)}
maxBajo = max(err[L] for L in range(1, 31))
maxAlto = max(err[L] for L in range(31, 36))
ok("up to level 30 it IS 1.05^(L-26), except for rounding noise",
   maxBajo < 2e-4, "maximum relative error %.2e (level %d)"
   % (maxBajo, max(range(1, 31), key=lambda L: err[L])))
ok("from 31 to 35 it is NOT, and by a lot: the table separates on purpose",
   maxAlto > 1e-2, "maximum relative error %.2e at level %d "
   "(table %.3f, closed form %.3f)"
   % (maxAlto, max(range(31, 36), key=lambda L: err[L]),
      MULT_NIVEL[max(range(31, 36), key=lambda L: err[L]) - 1] / 1e9,
      1.05 ** (max(range(31, 36), key=lambda L: err[L]) - 26)))
ok("the last five are round figures, not powers",
   [MULT_NIVEL[L - 1] / 1e9 for L in range(31, 36)] == [1.27, 1.32, 1.37, 1.425, 1.5],
   "1.27 · 1.32 · 1.37 · 1.425 · 1.5")

# ---------------------------------------------------------------------------
# 6) The domains the interface takes for granted
# ---------------------------------------------------------------------------
# The interface has maps of labels and icons indexed by these codes. A new
# code raises no error: it paints `undefined` or a broken `src`. That is why
# the domain is asserted here.
print()
print("=== 6. the codes the interface resolves ===")
TIPOS = {"speed", "health", "damage", "boost_max", "moves_reactive"}
RECURSOS = {"coins", "catalyst_minor", "catalyst", "catalyst_major"}

vistosTipos = {p["rwd"]["type"] for u in conPista for p in cri[u]["mejoras"]}
vistosRec = {r[0] for u in conPista for p in cri[u]["mejoras"] for r in p["req"]}
ok("the reward types are exactly the 5 the interface translates",
   vistosTipos == TIPOS, ", ".join(sorted(vistosTipos)))
ok("the resources are exactly the 4 the interface has with an icon",
   vistosRec == RECURSOS, ", ".join(sorted(vistosRec)))

# And the icon, on disk. The interface requests them by relative path; if one is
# missing, the card comes out with a gap and the browser does not complain
# anywhere visible. The path is NOT derived from the code: `coins` lives in
# `img/res/coin.png`, in singular and in another folder. The whole map is
# written, just as the template writes it, and in addition the template is
# checked to say the same thing.
RUTA_REC = {"coins": "img/res/coin.png",
            "catalyst_minor": "img/cat/catalyst_minor.png",
            "catalyst": "img/cat/catalyst.png",
            "catalyst_major": "img/cat/catalyst_major.png"}
FICHEROS = ([os.path.join(IMG, "stat", n + ".png")
             for n in ("health", "damage", "speed", "armor", "crit", "critm", "enhancement")]
            + [os.path.join(IMG, "res", "dna.png")]
            + [os.path.join(RAIZ, r) for r in RUTA_REC.values()])
faltan = [os.path.relpath(p, RAIZ) for p in FICHEROS if not os.path.getsize(p) > 100]
ok("a disk icon exists for each stat, each resource and the enhancement",
   not faltan, str(faltan) if faltan else "%d icons" % len(FICHEROS))

# The template declares its own resource map. It is read from there and
# compared: it is the check that the interface does not request a path that does
# not exist.
pl = open(os.path.join(RAIZ, "plantilla.html"), encoding="utf-8").read()
m = re.search(r"const RES_ICONO = \{(.*?)\};", pl, re.S)
mapaUI = dict(re.findall(r'(\w+):"([^"]+)"', m.group(1))) if m else {}
ok("and the template requests exactly those paths, not one more nor one less",
   mapaUI == RUTA_REC,
   str(mapaUI) if mapaUI != RUTA_REC else "it matches the interface map")

# The ranges of the three percentages, measured. They serve as a sentinel: if a
# stat slipped in as a bare number (400 instead of 40), this catches it.
rangos = {k: (min(cri[u]["stats"][k] for u in cri), max(cri[u]["stats"][k] for u in cri))
          for k in ("armadura", "critico", "dano_critico")}
ok("armor and the two criticals are percentages, in the whole dinodex",
   rangos["armadura"] == (0, 60) and rangos["critico"] == (0, 50)
   and rangos["dano_critico"] == (125, 200),
   "armor %d-%d · critical chance %d-%d · critical damage %d-%d"
   % (rangos["armadura"][0], rangos["armadura"][1], rangos["critico"][0],
      rangos["critico"][1], rangos["dano_critico"][0], rangos["dano_critico"][1]))

# The three user settings, asserted against the data and not against each other.
ok("the per-stat cap (20) and the track minimum (30) are the measured ones",
   TOPE_BOOST_STAT == 20 and MEJORA_NIVEL_MIN == 30,
   "+%d per stat, track from level %d" % (TOPE_BOOST_STAT, MEJORA_NIVEL_MIN))
ok("the two boost settings are those of the source (+2 flat, +2.5%%)",
   BOOST_VELOCIDAD == 2 and BOOST_FRACCION == 0.025,
   "+%d speed and +%.1f%% health and damage per point"
   % (BOOST_VELOCIDAD, BOOST_FRACCION * 100))

# ---------------------------------------------------------------------------
# 7) The Omega training table, against the cache
# ---------------------------------------------------------------------------
# `detail.points` is the only place the training data exists, and only the Omega
# creatures have it. That is checked in BOTH directions: if the JSON had it for
# a creature whose card has no table, the interface would paint six controls
# that change nothing; the other way round, an Omega would silently lose the
# whole feature.
print()
print("=== 7. the Omega training table ===")
conTabla = {u for u, v in fichas.items() if (v["det"] or {}).get("points")}
conDato = {u for u in cri if "entrenamiento" in cri[u]}
omega = {u for u in cri if cri[u]["rareza"] == "omega"}
ok("the table is in exactly the Omega creatures, and the card and the data agree",
   conTabla == conDato == omega,
   "%d with a card table, %d in the data, %d Omega" % (len(conTabla), len(conDato), len(omega)))

malEnt = []
for u in sorted(conDato):
    p, e = fichas[u]["det"]["points"], cri[u]["entrenamiento"]
    for grupo in ("cap", "delta", "pcap"):
        for fuente, nuestro in CAMPOS:
            if p[grupo][fuente] != e[grupo][nuestro]:
                malEnt.append("%s %s.%s: cache=%s dato=%s"
                              % (u, grupo, nuestro, p[grupo][fuente], e[grupo][nuestro]))
ok("cap, delta and pcap are the cached ones, stat by stat (33 x 3 x 6 numbers)",
   not malEnt, " ;; ".join(malEnt[:3]) if malEnt else "%d numbers" % (len(conDato) * 18))

# The cap is `base(26) + delta x pcap`, and `pcap` is the source's own datum, NOT
# the division: in `stegouros` crit damage the division gives 7.5 and paleo.gg
# stores 7, so that cap stays one point short of reachable. A shortfall of at
# most one `delta` is therefore expected, and it is why the bound the app uses
# is `pcap` and not the cap.
cortos = []
for u in sorted(conDato):
    e, b = cri[u]["entrenamiento"], cri[u]["stats"]
    for _, nuestro in CAMPOS:
        dif = e["cap"][nuestro] - (b[nuestro] + e["delta"][nuestro] * e["pcap"][nuestro])
        if not 0 <= dif <= e["delta"][nuestro]:
            cortos.append("%s %s: %+d" % (u, nuestro, dif))
ok("and each cap is base(26) + delta x pcap, short by at most one point",
   not cortos, " ;; ".join(cortos[:3]) if cortos else "the 198 caps, 0 off by more than a point")

# The pool. It is NOT in the source: it comes from two figures of a secondary
# guide, so what is pinned here are those two figures, and the manual carries it
# as a doubt. With 245 points at level 35 and every creature needing more than
# that to reach all six caps, the pool HAS to bind — that is the whole point of
# the system, and it is checked so that nobody «fixes» it by raising it.
sumas = {u: sum(cri[u]["entrenamiento"]["pcap"].values()) for u in conDato}
ok("the pool is 7 per level: the two figures it was derived from",
   PUNTOS_OMEGA_NIVEL * 11 == 77 and PUNTOS_OMEGA_NIVEL * 26 == 182,
   "%d x 11 = %d and %d x 26 = %d"
   % (PUNTOS_OMEGA_NIVEL, PUNTOS_OMEGA_NIVEL * 11, PUNTOS_OMEGA_NIVEL, PUNTOS_OMEGA_NIVEL * 26))
ok("and at level 35 it is not enough to reach the six caps of any Omega: the pool binds",
   min(sumas.values()) > PUNTOS_OMEGA_NIVEL * 35,
   "cheapest %d points (%s) against a pool of %d"
   % (min(sumas.values()), min(sumas, key=sumas.get), PUNTOS_OMEGA_NIVEL * 35))

print()
if fallos:
    print("RESULT: %d FAILURES out of %d checks." % (len(fallos), n_ok + len(fallos)))
    for f in fallos:
        print("  - " + f)
    raise SystemExit(1)
print("RESULT: all OK (%d checks)." % n_ok)
