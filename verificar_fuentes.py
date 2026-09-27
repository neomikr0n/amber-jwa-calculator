#!/usr/bin/env python3
"""
Checks where each creature is obtained from.

What it checks, and why
------------------------
1. **The labels in `LOC_ETIQUETAS` are NOT written by hand.** They are
   re-extracted from the «DNA Source» block of the paleo.gg cache, which is the
   source, and compared one by one. If paleo.gg renames a zone, this shows up in
   red instead of keeping the old text forever.
2. **Every code that uses a creature has a label.** A new code in the data with
   no label would be painted as the raw code (`local_area_5`) and nobody would
   notice until seeing it on screen.
3. **The darting / combat split is complete.** Each code belongs to one thing or
   the other; none is left unclassified. This matters because the tool shows
   «where you dart» and it CANNOT say that Arena is a darting zone: Arena is
   fought, it is not darted.
4. **The full split, by category.** How many are darted, how many are fought, how
   many only appear in the sanctuary and how many have no source. The counts are
   asserted here, so a data change does not go unnoticed.
5. **The claim about the sanctuary, measured in the way that does NOT fool
   itself.** See the comment in section 3: the previous version compared the set
   against an exact `{"sanctuary"}` and therefore reported 0 cases when in
   reality there are 4. A test that shares the misunderstanding of the data
   passes green and proves nothing.

    python3 verificar_fuentes.py     -> 0 if everything matches, 1 if not
"""
import collections
import html as H
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from modelo import LOC_COMBATE, LOC_DARDEO, LOC_ETIQUETAS

CACHE = os.path.join(RAIZ, "cache")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")

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
# 1) Re-extract the labels from the cache
# ---------------------------------------------------------------------------
# The link is `dnaSourceLoc=<code>">Label</a>`. The code carries UPPERCASE
# letters in the continents (continent_NA/SA/US): a lowercase pattern leaves them
# out and the map comes out incomplete without anything warning.
PATRON = re.compile(r'dnaSourceLoc=([A-Za-z0-9_/]+)">([^<]+)</a>')

leidas = collections.defaultdict(collections.Counter)
ficheros = [f for f in os.listdir(CACHE) if f.endswith(".html")]
for f in ficheros:
    s = open(os.path.join(CACHE, f), encoding="utf-8").read()
    i = s.find('id="dna_source"')
    if i < 0:
        continue
    for cod, lab in PATRON.findall(s[i:i + 1200]):
        leidas[cod][H.unescape(lab.strip())] += 1

print("=== 1. the labels, against the «DNA Source» block of the cache ===")
ok("the cache has cards", len(ficheros) > 500, "%d files" % len(ficheros))

ambiguas = {c: dict(v) for c, v in leidas.items() if len(v) > 1}
ok("no code has two different labels in the cache", not ambiguas,
   str(ambiguas) if ambiguas else "%d codes, all unique" % len(leidas))

for cod in sorted(leidas):
    esperado = leidas[cod].most_common(1)[0][0]
    ok("label of %s" % cod, LOC_ETIQUETAS.get(cod) == esperado,
       "modelo=%r  cache=%r" % (LOC_ETIQUETAS.get(cod), esperado))

sobran = sorted(set(LOC_ETIQUETAS) - set(leidas))
ok("there are no labels in the model that the cache does not back", not sobran,
   str(sobran) if sobran else "none")

# ---------------------------------------------------------------------------
# 2) Every code used has a label and is classified
# ---------------------------------------------------------------------------
print()
print("=== 2. coverage of the codes the data uses ===")
d = json.load(open(DATOS, encoding="utf-8"))
cri = d["criaturas"]

usados = collections.Counter()
for v in cri.values():
    for x in v.get("fuentes_adn") or []:
        usados[x["loc"]] += 1

ESPECIALES = {"none", "sanctuary"}      # they are neither darting nor combat
# `none` is not a source: it is «does not appear on the map». It has no label
# because there is nothing to label, and demanding one would be asking the data
# for what it does not say.
sinEtiqueta = sorted(c for c in usados
                     if c not in LOC_ETIQUETAS and c != "none")
ok("every code that is a source has a label", not sinEtiqueta,
   str(sinEtiqueta) if sinEtiqueta else "%d codes (+ none, which is not a source)" % len(usados))
sinClasificar = sorted(c for c in usados
                       if c not in LOC_DARDEO and c not in LOC_COMBATE
                       and c not in ESPECIALES)
ok("every code is darting, combat or special (none/sanctuary)", not sinClasificar,
   str(sinClasificar) if sinClasificar else "none loose")

solapan = sorted(set(LOC_DARDEO) & set(LOC_COMBATE))
ok("darting and combat do not overlap", not solapan, str(solapan) if solapan else "empty")

# ---------------------------------------------------------------------------
# 3) The sanctuary: the claim, measured without fooling ourselves
# ---------------------------------------------------------------------------
# WATCH OUT, here there was a real methodological failure. The previous version
# asked whether the set of sources was EXACTLY {"sanctuary"} and answered
# «0 cases», which is what was documented. But 4 creatures (alioramus,
# aquilops, arsinoitherium, titanosaurus) have [sanctuary, none]: `none` is not a
# source —it is «does not appear on the map»—, so the sanctuary IS their only
# origin and the count was wrong. The test shared the misunderstanding of the
# data and passed green.
#
# The right question is: removing `none`, is there anything left besides the
# sanctuary? `none` and `sanctuary` are excluded from the calculation; whatever
# remains are real sources.
print()
print("=== 3. the sanctuary as the only source ===")
NO_FUENTE = {"none"}


def util(u):
    return {x["loc"] for x in cri[u].get("fuentes_adn") or []} - NO_FUENTE


soloSanct = sorted(u for u in cri if util(u) == {"sanctuary"})
ok("there are creatures whose only origin is the sanctuary (not 0: there were 4)",
   len(soloSanct) == 4,
   "%d: %s" % (len(soloSanct), ", ".join(soloSanct)))
ok("and none of them is a hybrid: they are the ones you must go and find",
   all(not cri[u].get("ingredientes") for u in soloSanct),
   "the 4 with no ingredients")
# And that is why the sanctuary is NOT omitted: it is shown as «sanctuary only».
# If some day a creature with ingredients appeared here, the hybrid rule (which
# carries no pill unless it appears on the map) would lose the datum.

# ---------------------------------------------------------------------------
# 4) The measured counts, by category
# ---------------------------------------------------------------------------
# The previous version had a chain of `if/elif` with branches that could not be
# reached (`resto == {"none"}` before `resto <= {"none"}`) and an `else` that put
# anything unclassified into «sanctuary only». The numbers came out, but by
# accident. Here the category is computed once and asserted whole.
print()
print("=== 4. where each creature comes from (518) ===")
D, Cm = set(LOC_DARDEO), set(LOC_COMBATE)


def categoria(u):
    f = util(u)
    if f & D and f & Cm:
        return "ambos"
    if f & D:
        return "dardeo"
    if f & Cm:
        return "combate"
    if f == {"sanctuary"}:
        return "santuario"
    return "sin fuente"


reparto = collections.Counter(categoria(u) for u in cri)
base = [u for u, v in cri.items() if not v.get("ingredientes")]
hib = [u for u, v in cri.items() if v.get("ingredientes")]
repartoBase = collections.Counter(categoria(u) for u in base)
repartoHib = collections.Counter(categoria(u) for u in hib)

print("      %-12s %6s %8s %8s" % ("category", "all", "no ing", "hybrids"))
for k in ("dardeo", "combate", "ambos", "santuario", "sin fuente"):
    print("      %-12s %6d %8d %8d" % (k, reparto[k], repartoBase[k], repartoHib[k]))

ESPERADO = {"dardeo": 146, "combate": 107, "ambos": 2, "santuario": 4, "sin fuente": 259}
ok("the 518 split into the five categories",
   sum(reparto.values()) == len(cri) == 518,
   "%d = %d creatures" % (sum(reparto.values()), len(cri)))
ok("and each count is the measured one", all(reparto[k] == v for k, v in ESPERADO.items()),
   " | ".join("%s %d (expected %d)" % (k, reparto[k], v)
              for k, v in ESPERADO.items() if reparto[k] != v) or
   "darting %d · combat %d · both %d · sanctuary %d · no source %d"
   % tuple(reparto[k] for k in ("dardeo", "combate", "ambos", "santuario", "sin fuente")))
ok("the 270 with no ingredients and the 248 hybrids add up to the 518",
   len(base) == 270 and len(hib) == 248 and len(base) + len(hib) == len(cri),
   "%d + %d = %d" % (len(base), len(hib), len(base) + len(hib)))
ok("of the hybrids, 247 do not appear on the map and 1 does (Purrolyth)",
   repartoHib["sin fuente"] == 247 and repartoHib["combate"] == 1,
   "no source %d, combat %d" % (repartoHib["sin fuente"], repartoHib["combate"]))
ok("the 4 sanctuary ones have no ingredients, and they are the only ones",
   repartoBase["santuario"] == 4 and repartoHib["santuario"] == 0,
   "%d base, %d hybrids" % (repartoBase["santuario"], repartoHib["santuario"]))

# ---------- 6. the level a fusion requires never drops below birth ----------
"""`NIVEL_MIN_INGREDIENTE[rareza]` is «one less than the creation level of the
hybrid», and that is the level at which the report's «breed» button puts an
ingredient. But a creature CANNOT exist below the level at which its rarity is
born. If the required level fell below it, the floor of `nivelFusion` (in
`plantilla.html`) would come into play and the button would put the creature at
its birth instead of at the requested level — a silent behaviour change, exactly
what the project rule does not allow. It is measured instead of assumed."""
from modelo import MIN_LV, NIVEL_MIN_INGREDIENTE

pares = []
for u, x in cri.items():
    for ing in x["ingredientes"]:
        if ing in cri:
            pares.append((u, x["rareza"], ing, cri[ing]["rareza"]))
margenes = [NIVEL_MIN_INGREDIENTE[rp] - MIN_LV[ri] for _, rp, _, ri in pares]
ok("all the ingredients in the data exist as a creature",
   len(pares) == sum(len(x["ingredientes"]) for x in cri.values()),
   "%d parent->ingredient pairs" % len(pares))
ok("the level a fusion requires NEVER falls below the ingredient's birth level",
   all(m >= 0 for m in margenes) and pares,
   "of %d pairs, the minimum margin is %+d and the maximum %+d"
   % (len(pares), min(margenes), max(margenes)))

print()
if fallos:
    print("RESULT: %d FAILURES out of %d checks." % (len(fallos), n_ok + len(fallos)))
    for f in fallos:
        print("  - " + f)
    raise SystemExit(1)
print("RESULT: all OK (%d checks)." % n_ok)
