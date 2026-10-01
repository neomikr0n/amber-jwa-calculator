#!/usr/bin/env python3
"""
Cost model for Jurassic World Alive — verified.

The game version is NOT written here. It lives in `data/jwa.json`
(`meta.version_juego`) and is read through `rutas.version()`; a copy in this
file would be one more place to forget on an update, and nothing would compare
it against the data. This file holds the model, the data holds the version.

Everything in here has been checked against independent sources.
The `confianza` field of each block says where it comes from and how safe it is.

Main validation: this model reproduces EXACTLY the three numbers that paleo.gg
shows in its own calculator (hybrid DNA, level-up coins, fusion coins) on the
221 downloaded hybrid entries. Zero discrepancies.

    python3 modelo.py          # runs the self-check
"""

from math import ceil

# Tool name. It lives here, and not hard-written in the template, because it
# appears in TWO places that have to say the same thing: the <title> of the tab
# and the <h1> of the header. `build.py` replaces it by `__NOMBRE__`. Changing
# the name is changing this line.
#
# An earlier version of this comment said THREE places and included the footer.
# It was false: counting the occurrences in the delivered HTML gives two, and
# the footer carries no name. The claim was corrected in the LEEME and left
# standing here; it is corrected here too.
NOMBRE = "Amber"

# --------------------------------------------------------------------------
# 1. DNA ladder
# --------------------------------------------------------------------------
# A SINGLE ladder shared by all rarities. The index k is the cost of REACHING
# level k+1 for a Common creature:
#     L[0] = create (level 1), L[1] = level 2, ... L[29] = level 30
# For any other rarity, the cost of reaching level n is L[n - min_lv].
#
# Confidence: HIGH. Reproduces the 14 known totals (7 rarities x 2 ranges).
L = [50, 100, 150, 200, 250, 300, 350, 400, 500, 750,
     1000, 1250, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7500,
     10000, 12500, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 75000]

# DNA cost to CREATE. It is NOT included in the level-up cost:
# paleo.gg computes "from 16 to 20" without counting the creation.
# Confidence: HIGH. Matches the wiki (jurassic-world-alive.fandom.com/Rarity).
CREACION = {"common": 50, "rare": 100, "epic": 150,
            "legendary": 200, "unique": 250, "apex": 300}

# Level at which each rarity is born. It is also the minimum level that the
# INGREDIENTS must have, minus one (see NIVEL_MIN_INGREDIENTE).
MIN_LV = {"common": 1, "rare": 6, "epic": 11,
          "legendary": 16, "unique": 21, "apex": 26}

# Range 31-35: flat cost per level.
# Confidence: HIGH (official 3.22 announcement).
ADN_31_35 = {"common": 100000, "rare": 30000, "epic": 10000,
             "legendary": 3000, "unique": 1000, "apex": 400}
NIVEL_MAX = 35

# --------------------------------------------------------------------------
# 2. Coins
# --------------------------------------------------------------------------
# A single ladder, indexed by ABSOLUTE level (not by rarity).
# COINR[n-1] = coins to REACH level n.
# Confidence: HIGH. Reproduces the 1->30 totals of the 5 rarities.
COINR = [0, 5, 10, 25, 50, 100, 200, 400, 600, 800,
         1000, 2000, 4000, 6000, 8000, 10000, 15000, 20000, 30000, 40000,
         50000, 60000, 70000, 80000, 90000, 100000, 120000, 150000, 200000, 250000]

COIN_31_35 = 250000        # per level, flat
COIN_OMEGA_31_35 = 400000  # per level, flat

# --------------------------------------------------------------------------
# 3. Fusion
# --------------------------------------------------------------------------
# The DNA cost per fusion depends ONLY on the rarity jump:
#     salto = tier(hybrid) - tier(ingredient)
# Verified unambiguously in 191 hybrids: every observed combination gives a
# single value. The table below is unanimous.
#
#   jump 1 -> 50      (common->rare, rare->epic, epic->legendary, legendary->unique, unique->apex)
#   jump 2 -> 200     (common->epic, rare->legendary, epic->unique, legendary->apex)
#   jump 3 -> 500     (common->legendary, rare->unique, epic->apex)
#   jump 4 -> 2000    (common->unique, rare->apex)
#
# WARNING: the app code (jurassic-journal) returns 0 for the jump 4.
# It is an app bug; paleo.gg confirms 2,000 (Indoraptor <- Velociraptor).
TIER = {"common": 0, "rare": 1, "epic": 2, "legendary": 3, "unique": 4, "apex": 5}
ADN_POR_FUSION = {1: 50, 2: 200, 3: 500, 4: 2000}

# Coins per fusion, depending on the rarity of the HYBRID.
# Confidence: HIGH. Matches paleo.gg and the app's fuseCoinCostForRarity().
MONEDAS_FUSION = {"common": 20, "rare": 20, "epic": 100,
                  "legendary": 200, "unique": 1000, "apex": 2000}

# DNA that each fusion gives, on average. It is an AVERAGE, not a fixed value:
# the real amount is random.
#   - paleo.gg uses it literally ("Assuming an average of 22 DNA per fuse").
#   - The wiki probability table gives an expectation of 22.228
#     (deviation of 1.03% with respect to 22).
#   - Data contributed by n30: 22.
# Confidence: HIGH on the average; NULL on the value of a specific fusion.
ADN_POR_FUSION_MEDIA = 22

# Minimum level of the ingredients. General rule: one less than the creation
# level of the hybrid.
# Confidence: HIGH (wiki /Rarity, explicit text).
NIVEL_MIN_INGREDIENTE = {r: MIN_LV[r] - 1 for r in MIN_LV}

# --------------------------------------------------------------------------
# 4. Omega
# --------------------------------------------------------------------------
# Omega is born at level 1 and is NOT fused into hybrids. It has its own ladder.
# Index k = cost of REACHING level k+1 (k=0 is the creation).
#
# Confidence: MEDIUM-HIGH. It comes from game_database.db (jurassic-journal)
# with ONE correction: the database puts 1.000 in the 15->16 jump, but the
# pattern is blocked at 1.500 five times in a row, and only with 1.500 does the
# 1->30 total square at 41.700 (a figure confirmed by the secondary source
# idgt902).
OMEGA_L = [100, 100, 100, 100, 500, 500, 500, 500, 500,
           1000, 1000, 1000, 1000, 1000,
           1500, 1500, 1500, 1500, 1500,
           2000, 2000, 2000, 2000, 2000,
           2700, 2700, 2700, 2700, 2700, 2800]
OMEGA_31_35 = [3500, 4000, 4500, 5000, 5500]

# Omega coins to reach each level (index n-1).
OMEGA_COINR = [0, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7000,
               8000, 10000, 12000, 15000, 20000, 25000, 30000, 35000, 45000, 50000,
               65000, 80000, 95000, 120000, 150000, 180000, 210000, 250000, 300000, 350000]

# Omega TRAINING POINTS: the pool an Omega can spend on its six stats is
# `PUNTOS_OMEGA_NIVEL x level`, so the pool is a total earned by levelling, not
# a per-level allowance.
#
# Confidence: MEDIUM. Two figures from idgt902's guide «Training Smarter: How to
# Optimize Omega Creatures» (27-Apr-2025, the same author the catalysts came
# from): a level 26 Omega is given 182 points, and one at level 11 has earned 77.
# Both land exactly on 7 per level (7x1 = 7, so a level 1 Omega starts with 7),
# and it is the only rule that fits the two. There is NO official confirmation:
# jurassicworldalive.com serves the announcement through JavaScript and the wiki
# refuses automated requests, so this is a secondary source with two consistent
# points, not an official number. It is stated as a doubt in the manual, and
# `verificar_stats.py` pins the two figures so that changing this constant
# without changing them turns red.
#
# What each point BUYS is not here: it is per creature and comes in the data, in
# `criaturas[u].entrenamiento` (cap, delta and pcap per stat).
PUNTOS_OMEGA_NIVEL = 7

# --------------------------------------------------------------------------
# 5. DNA inventory caps
# --------------------------------------------------------------------------
# Confidence: HIGH. OFFICIAL source (jurassicworldalive.com/news/dna-cap-changes/,
# 31-Aug-2026) and it matches exactly Rarity.maxDna() of the app code.
TOPES_ADN = {"common": 850000, "rare": 250000, "epic": 85000,
             "legendary": 25000, "unique": 8000, "apex": 3000, "omega": 60000}


# --------------------------------------------------------------------------
# 6. Real stats: level, stat boosts and upgrades
# --------------------------------------------------------------------------
# The `stats` carried by each creature in the data are LEVEL 26 values, and this
# is not our inference: the source states it in the "Compare Creatures" link,
# which carries `compare?ck=0__<uuid>__26` on all 519 entries. Two more facts
# agree: the level-26 multiplier is exactly 1.000000 (see MULT_NIVEL) and the
# rendered text of the entry shows those same numbers (alacranix: 4250 / 1650 /
# 115 / 40% / 15% / 125%, identical to the JSON). `verificar_stats.py` checks
# all three against the local cache, not against this file.
#
# MULT_NIVEL[L-1] is the factor applied to HEALTH and DAMAGE at level L, in
# billionths: stat(L) = floor(stat26 * MULT_NIVEL[L-1] / 1e9).
# Speed, armour and both crit values do NOT scale with level.
#
# Confidence: HIGH. These are the game's own level multipliers, obtained through
# paleo.gg and cross-checked against the stat values it renders. They are used
# as a table instead of being recomputed on purpose, and the reason was measured
# rather than assumed (`verificar_stats.py`, section 5):
#   - from level 1 to 30 the table IS 1.05^(L-26), up to rounding noise
#     (maximum relative error 1.5e-4, at level 4);
#   - from 31 to 35 it is NOT: those are round figures set by hand —1.27 · 1.32 ·
#     1.37 · 1.425 · 1.5— and the closed form drifts by up to 3.68 % (level 34:
#     1.425 vs 1.477). On a creature with 6,000 health that is 314 points, not a
#     rounding decimal.
# An earlier comment in this same place claimed "differs by up to 5e-5 relative,
# ~0.3 health points": it was FALSE, which is why the claim now carries the
# measured numbers and a test that holds it down.
MULT_NIVEL = [
    295300006, 310100002, 325600013, 341800003, 358899993,
    376899986, 395699996, 415499992, 436300010, 458100013,
    480999984, 505099983, 530299987, 556800003, 584700088,
    613899955, 644599990, 676800003, 710699996, 746200027,
    783499984, 822699966, 863799972, 906999969, 952399978,
    1000000000, 1050000000, 1102500000, 1157600021, 1215500030,
    1270000000, 1320000000, 1370000000, 1425000000, 1500000000,
]

# Each stat-boost point adds this:
#   speed: +2 flat   ·   health and damage: +2.5% on the already scaled value
# Confidence: MEDIUM-HIGH. Measured against the source page.
BOOST_VELOCIDAD = 2
BOOST_FRACCION = 0.025

# Cap of points per stat, and the total: level of the creature + whatever the
# already applied boosts add up to (`v = (capBoostByLevel ? level : 35) + capBoostIncrease`).
TOPE_BOOST_STAT = 20

# The enhancements («Enhancements») are a 5-step track, only for Unique and Apex.
# They require level 30 or more. The ORDER of the steps is NOT the same in the
# two, and that was discovered by looking at a screenshot, not the code: a
# single order had been taken for granted and it was false.
#     Unique (92): health x1.10 · damage x1.10 · +2 speed · boost_max +1 · reactive
#     Apex  (55): +2 speed · health x1.10 · boost_max +2 · damage x1.10 · reactive
# The browser does NOT use this table: it reads the type of each step from the
# data itself, step by step. This is here as documentation, and `verificar_stats.py`
# checks it against the JSON so that it does not silently go stale.
MEJORA_ORDEN = {
    "unique": ("health", "damage", "speed", "boost_max", "moves_reactive"),
    "apex":   ("speed", "health", "boost_max", "damage", "moves_reactive"),
}
MEJORA_NIVEL_MIN = 30
MEJORA_PASOS = 5


# --------------------------------------------------------------------------
# 7. Where each creature is obtained
# --------------------------------------------------------------------------
# Confidence: HIGH. Each creature carries its list of sources in `fuentes_adn`
# (field `loc`), and the LABEL of each code is read from the «DNA Source»
# block of the paleo.gg cache, which is the source. They are not written by
# hand: `verificar_fuentes.py` extracts them again from the cache and fails if
# they do not match.
#
# Watch out for the distinction, because they are NOT the same thing:
#   - DARTING: you hunt it with the dart on the map. This is what n30 asked to
#     show.
#   - COMBAT: its DNA comes from fighting (Arena, Strike Towers, Raid,
#     Alliance Missions). It is not a darting zone and it cannot be presented
#     as if it were one.
#   - SANCTUARY: passive placement, neither darting nor combat. NONE of the 519
#     has it as its only source (measured), so it is omitted without losing
#     anything.
#   - `none`: it does not appear on the map. They are omega and event creatures.
LOC_DARDEO = ("local_area_1", "local_area_2", "local_area_3", "local_area_4",
              "park", "short_range", "everywhere",
              "continent_NA/SA/US", "continent_EU/US", "continent_AF/AN/AS/OC/US")
LOC_COMBATE = ("arena", "strike_towers", "raid", "alliance_missions")
LOC_ETIQUETAS = {
    "alliance_missions":        "Alliance Missions",
    "arena":                    "Arena",
    "continent_AF/AN/AS/OC/US": "Continental Asia & Rest Of World",
    "continent_EU/US":          "Continental Europe",
    "continent_NA/SA/US":       "Continental Americas",
    "everywhere":               "Everywhere | All Day",
    "local_area_1":             "Local Area 1 | All Day",
    "local_area_2":             "Local Area 2 | All Day",
    "local_area_3":             "Local Area 3 | All Day",
    "local_area_4":             "Local Area 4 | All Day",
    "park":                     "Park | All Day",
    "raid":                     "Raid",
    "sanctuary":                "Sanctuary",
    "short_range":              "Short Range | All Day",
    "strike_towers":            "Strike Towers",
}


# ==========================================================================
#  Functions
# ==========================================================================

def coste_adn(rareza, desde, hasta, incluir_creacion=False):
    """DNA to level up a creature from `desde` to `hasta`.

    It does not include the creation cost unless it is explicitly requested.
    If `desde` is the creation level and `incluir_creacion=True`, it adds it.
    """
    if hasta <= desde:
        return 0
    if rareza == "omega":
        return _omega_adn(desde, hasta, incluir_creacion)
    if rareza not in MIN_LV:
        return 0
    m = MIN_LV[rareza]
    # WARNING: `desde` has to be clamped to the creation level. Otherwise, with
    # desde=0 the indices L[n-m] come out NEGATIVE and Python wraps the list
    # around silently (L[-20] is an element from the end), returning absurd
    # figures.
    a = max(desde, m)
    t = sum(L[n - m] for n in range(a + 1, min(hasta, 30) + 1))
    if hasta > 30:
        t += (hasta - max(a, 30)) * ADN_31_35[rareza]
    if incluir_creacion:
        t += CREACION[rareza]
    return t


def _omega_adn(desde, hasta, incluir_creacion=False):
    t = 0
    if desde == 1 and incluir_creacion:
        t += OMEGA_L[0]
    for n in range(desde + 1, hasta + 1):
        t += OMEGA_L[n - 1] if n <= 30 else OMEGA_31_35[n - 31]
    return t


def coste_monedas(rareza, desde, hasta):
    """Coins to level up a creature from `desde` to `hasta`."""
    if hasta <= desde:
        return 0
    m = 1 if rareza == "omega" else MIN_LV.get(rareza, 1)
    a = max(desde, m)          # you cannot level up below the creation level
    if rareza == "omega":
        t = sum(OMEGA_COINR[n - 1] for n in range(a + 1, min(hasta, 30) + 1))
        if hasta > 30:
            t += (hasta - max(a, 30)) * COIN_OMEGA_31_35
        return t
    t = sum(COINR[n - 1] for n in range(a + 1, min(hasta, 30) + 1))
    if hasta > 30:
        t += (hasta - max(a, 30)) * COIN_31_35
    return t


def adn_por_fusion(rareza_ingrediente, rareza_hibrido):
    """DNA that ONE fusion of that ingredient into that hybrid consumes."""
    a, b = TIER.get(rareza_ingrediente), TIER.get(rareza_hibrido)
    if a is None or b is None:
        return 0
    return ADN_POR_FUSION.get(b - a, 0)


# --------------------------------------------------------------------------
#  Maximum level reachable with the DNA you have
# --------------------------------------------------------------------------

def nivel_creacion(rareza):
    """Level at which the creature is BORN. Below it, it does not exist."""
    return 1 if rareza == "omega" else MIN_LV.get(rareza, 1)


def coste_creacion(rareza):
    """DNA it costs to create the creature (bring it to its birth level)."""
    return OMEGA_L[0] if rareza == "omega" else CREACION.get(rareza, 0)


def coste_paso(rareza, nivel_destino):
    """DNA it costs to move from `nivel_destino - 1` to `nivel_destino`.

    It is the brick that coste_adn is made of: adding coste_paso from
    `desde+1` up to `hasta` gives exactly coste_adn. It is exposed separately
    because the maximum level calculation needs to go step by step, not in one
    go.
    """
    if nivel_destino <= 0:
        return 0
    if rareza == "omega":
        if nivel_destino <= 30:
            return OMEGA_L[nivel_destino - 1]
        return OMEGA_31_35[nivel_destino - 31] if nivel_destino <= NIVEL_MAX else 0
    m = MIN_LV.get(rareza)
    if m is None:
        return 0
    if nivel_destino < m:
        return 0
    if nivel_destino <= 30:
        return L[nivel_destino - m]
    return ADN_31_35[rareza] if nivel_destino <= NIVEL_MAX else 0


def nivel_maximo(rareza, desde, adn, creado=None, tope=NIVEL_MAX):
    """Up to which level it can be raised with `adn`, starting from `desde`.

    `creado` = whether the creature already exists. If it is False, the first
    payment is the creation one and the creature appears at its birth level. If
    it is None it is deduced from `desde >= nivel_creacion(rareza)`.

    Returns (level, adn_spent, adn_left_over). If it is not even enough to
    create, it returns (0, 0, adn) — level 0 means "it does not exist".
    """
    if adn is None or adn < 0:
        adn = 0
    m = nivel_creacion(rareza)
    if creado is None:
        creado = desde >= m

    if not creado:
        c = coste_creacion(rareza)
        if adn < c:
            return 0, 0, adn
        adn -= c
        gastado = c
        nivel = m
    else:
        nivel = max(desde, m)
        gastado = 0

    while nivel < tope:
        paso = coste_paso(rareza, nivel + 1)
        if paso <= 0 or paso > adn:
            break
        adn -= paso
        gastado += paso
        nivel += 1
    return nivel, gastado, adn


def fusiones_necesarias(adn_faltante, media=ADN_POR_FUSION_MEDIA):
    """Numero de fusiones para conseguir `adn_faltante`, a 22 ADN por fusion."""
    if adn_faltante <= 0:
        return 0
    return ceil(adn_faltante / media)


def adn_ingrediente(rareza_ingrediente, rareza_hibrido, adn_faltante_hibrido):
    """ADN del ingrediente que hay que reunir para cubrir el deficit del hibrido."""
    return fusiones_necesarias(adn_faltante_hibrido) * adn_por_fusion(
        rareza_ingrediente, rareza_hibrido)


def monedas_fusion(rareza_hibrido, adn_faltante_hibrido):
    """Monedas que cuesta ejecutar las fusiones necesarias."""
    return fusiones_necesarias(adn_faltante_hibrido) * MONEDAS_FUSION.get(
        rareza_hibrido, 0)


# ==========================================================================
#  Autocomprobacion
# ==========================================================================

def _comprobar():
    fallos = []

    def eq(nombre, obtenido, esperado):
        if obtenido != esperado:
            fallos.append(f"{nombre}: {obtenido} != {esperado}")

    # --- 1->30 DNA totals (the 14 known ones) ---
    eq("common 1->30", coste_adn("common", 1, 30, True), 346800)
    eq("rare 1->30", coste_adn("rare", 6, 30, True), 116850)
    eq("epic 1->30", coste_adn("epic", 11, 30, True), 34400)
    eq("legendary 1->30", coste_adn("legendary", 16, 30, True), 11450)
    eq("unique 1->30", coste_adn("unique", 21, 30, True), 3250)
    eq("apex 1->30", coste_adn("apex", 26, 30, True), 1000)
    eq("omega 1->30", coste_adn("omega", 1, 30, True), 41700)

    # --- the Omega training pool ---
    # The two figures the rule was derived from, so that touching the constant
    # without touching them turns red. See PUNTOS_OMEGA_NIVEL.
    eq("omega pool at level 11", PUNTOS_OMEGA_NIVEL * 11, 77)
    eq("omega pool at level 26", PUNTOS_OMEGA_NIVEL * 26, 182)
    eq("omega pool at level 35", PUNTOS_OMEGA_NIVEL * 35, 245)

    # --- 31-35 range ---
    for r in ("common", "rare", "epic", "legendary", "unique", "apex"):
        eq(f"{r} 30->35", coste_adn(r, 30, 35), ADN_31_35[r] * 5)
    eq("omega 30->35", coste_adn("omega", 30, 35), 22500)

    # --- 1->30 coin totals ---
    eq("mon common 1->30", coste_monedas("common", 1, 30), 1308190)
    eq("mon rare 1->30", coste_monedas("rare", 6, 30), 1308000)
    eq("mon epic 1->30", coste_monedas("epic", 11, 30), 1305000)
    eq("mon legendary 1->30", coste_monedas("legendary", 16, 30), 1275000)
    eq("mon unique 1->30", coste_monedas("unique", 21, 30), 1120000)
    eq("mon 30->35", coste_monedas("common", 30, 35), 1250000)

    # --- the three numbers paleo.gg shows (default range of each rarity) ---
    DEFECTO = [("rare", 6, 10), ("epic", 11, 15), ("legendary", 16, 20),
               ("unique", 21, 30), ("apex", 26, 30)]
    ESPERADO = {"rare": 700, "epic": 700, "legendary": 700, "unique": 3000, "apex": 700}
    for r, a, b in DEFECTO:
        d = coste_adn(r, a, b)
        eq(f"paleo ADN {r} {a}->{b}", d, ESPERADO[r])
        eq(f"paleo fusiones {r}", monedas_fusion(r, d),
           {"rare": 640, "epic": 3200, "legendary": 6400,
            "unique": 137000, "apex": 64000}[r])

    # --- fusion cost per rarity jump ---
    eq("common->rare", adn_por_fusion("common", "rare"), 50)
    eq("common->epic", adn_por_fusion("common", "epic"), 200)
    eq("common->legendary", adn_por_fusion("common", "legendary"), 500)
    eq("common->unique", adn_por_fusion("common", "unique"), 2000)
    eq("rare->epic", adn_por_fusion("rare", "epic"), 50)
    eq("rare->legendary", adn_por_fusion("rare", "legendary"), 200)
    eq("rare->unique", adn_por_fusion("rare", "unique"), 500)
    eq("epic->legendary", adn_por_fusion("epic", "legendary"), 50)
    eq("epic->unique", adn_por_fusion("epic", "unique"), 200)
    eq("epic->apex", adn_por_fusion("epic", "apex"), 500)
    eq("legendary->unique", adn_por_fusion("legendary", "unique"), 50)
    eq("legendary->apex", adn_por_fusion("legendary", "apex"), 200)
    eq("unique->apex", adn_por_fusion("unique", "apex"), 50)

    # --- specific case with its own name: Indoraptor ---
    # Velociraptor (common) -> Indoraptor (unique): 2,000 per fusion.
    eq("Indoraptor <- Velociraptor", adn_por_fusion("common", "unique"), 2000)
    eq("nivel min ingrediente unique", NIVEL_MIN_INGREDIENTE["unique"], 20)

    # --- maximum level: invariants, not loose values ---
    # The test that is worth it here is the round trip: if `nivel_maximo` says
    # that you reach level N with that DNA, then coste_adn(...,N) has to fit
    # and coste_adn(...,N+1) must not. That catches any mismatch between the
    # two functions, which is where the real error would be.
    casos_nm = 0
    for r in ("common", "rare", "epic", "legendary", "unique", "apex", "omega"):
        m = nivel_creacion(r)
        for desde in (0, 1, m, m + 3, 15, 20, 25, 30, 34, 35):
            if desde < m and desde != 0:
                continue
            creado = desde >= m
            for adn in (0, 1, 49, 50, 99, 100, 150, 500, 2500, 20000,
                        500000, 5000000, 50000000):
                n, gastado, sobra = nivel_maximo(r, desde, adn, creado)
                casos_nm += 1
                nec = coste_adn(r, desde, n, not creado)
                if nec > adn:
                    fallos.append(
                        f"nivel_maximo {r} desde={desde} adn={adn}: says level {n} "
                        f"but it costs {nec}, more than there is")
                if n < NIVEL_MAX:
                    sig = coste_adn(r, desde, n + 1, not creado)
                    if sig <= adn:
                        fallos.append(
                            f"nivel_maximo {r} desde={desde} adn={adn}: it stays at {n} "
                            f"but level {n+1} cost {sig}, which was reachable")
                if gastado + sobra != adn:
                    fallos.append(
                        f"nivel_maximo {r} desde={desde} adn={adn}: "
                        f"spent {gastado} + left over {sobra} != {adn}")
                if n < desde:
                    fallos.append(
                        f"nivel_maximo {r} desde={desde} adn={adn}: drops to {n}")

    # --- coste_paso has to reconstruct coste_adn exactly ---
    for r in ("common", "rare", "epic", "legendary", "unique", "apex", "omega"):
        m = nivel_creacion(r)
        for desde in (m, m + 5, 28):
            for hasta in (desde + 1, 30, 35):
                if hasta > NIVEL_MAX:
                    continue
                sumado = sum(coste_paso(r, n) for n in range(desde + 1, hasta + 1))
                eq(f"coste_paso suma {r} {desde}->{hasta}", sumado,
                   coste_adn(r, desde, hasta))

    # --- named cases of maximum level ---
    # Apex not created (level 26): creating costs 300. With exactly 300, level 26.
    eq("apex sin crear con 300", nivel_maximo("apex", 0, 300, False), (26, 300, 0))
    eq("apex sin crear con 299", nivel_maximo("apex", 0, 299, False), (0, 0, 299))
    # Unique already created at 21, with 0 DNA: it stays at 21.
    eq("unique 21 con 0", nivel_maximo("unique", 21, 0, True), (21, 0, 0))
    # Common already created at 1: the 1->30 WITHOUT creation costs 346,750 (the
    # 346,800 total includes the 50 for creating). With one less, it stays at 29.
    eq("common 1 con 346749", nivel_maximo("common", 1, 346749, True)[0], 29)
    eq("common 1 con 346750", nivel_maximo("common", 1, 346750, True)[0], 30)
    # Omega: creating costs 100 and leaves it at level 1.
    eq("omega sin crear con 100", nivel_maximo("omega", 0, 100, False), (1, 100, 0))
    eq("omega sin crear con 99", nivel_maximo("omega", 0, 99, False), (0, 0, 99))

    if fallos:
        print(f"FAILURES ({len(fallos)}):")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"Self-check: 40/40 correct + {casos_nm} maximum level cases "
          f"(round-trip invariants).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_comprobar())
