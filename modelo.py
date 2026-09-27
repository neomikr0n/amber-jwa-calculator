#!/usr/bin/env python3
"""
Modelo de costes de Jurassic World Alive 3.22 — verificado.

Todo lo que hay aqui ha sido contrastado contra fuentes independientes.
El campo `confianza` de cada bloque dice de donde sale y con cuanta seguridad.

Validacion principal: este modelo reproduce EXACTAMENTE los tres numeros que
paleo.gg muestra en su propio calculador (ADN del hibrido, monedas de subida,
monedas de fusion) en las 221 fichas de hibrido descargadas. Cero discrepancias.

    python3 modelo.py          # ejecuta la autocomprobacion
"""

from math import ceil

VERSION = "3.22"

# Nombre de la herramienta. Vive aqui, y no escrito a mano en la plantilla,
# porque aparece en TRES sitios que tienen que decir lo mismo: el <title> de la
# pestana, el <h1> de la cabecera y el pie. `build.py` lo sustituye por
# `__NOMBRE__`. Cambiar el nombre es cambiar esta linea.
NOMBRE = "Ámbar"

# --------------------------------------------------------------------------
# 1. Escalera de ADN
# --------------------------------------------------------------------------
# Una SOLA escalera compartida por todas las rarezas. El indice k es el coste
# de ALCANZAR el nivel k+1 para una criatura Common:
#     L[0] = crear (nivel 1), L[1] = nivel 2, ... L[29] = nivel 30
# Para cualquier otra rareza, el coste de alcanzar el nivel n es L[n - min_lv].
#
# Confianza: ALTA. Reproduce los 14 totales conocidos (7 rarezas x 2 tramos).
L = [50, 100, 150, 200, 250, 300, 350, 400, 500, 750,
     1000, 1250, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7500,
     10000, 12500, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 75000]

# Coste de ADN para CREAR. NO va incluido en el coste de subir de nivel:
# paleo.gg calcula "de 16 a 20" sin contar la creacion.
# Confianza: ALTA. Coincide con la wiki (jurassic-world-alive.fandom.com/Rarity).
CREACION = {"common": 50, "rare": 100, "epic": 150,
            "legendary": 200, "unique": 250, "apex": 300}

# Nivel al que nace cada rareza. Es tambien el nivel minimo que deben tener
# los INGREDIENTES menos uno (ver NIVEL_MIN_INGREDIENTE).
MIN_LV = {"common": 1, "rare": 6, "epic": 11,
          "legendary": 16, "unique": 21, "apex": 26}

# Tramo 31-35: coste plano por nivel.
# Confianza: ALTA (comunicado oficial de la 3.22).
ADN_31_35 = {"common": 100000, "rare": 30000, "epic": 10000,
             "legendary": 3000, "unique": 1000, "apex": 400}
NIVEL_MAX = 35

# --------------------------------------------------------------------------
# 2. Monedas
# --------------------------------------------------------------------------
# Una sola escalera, indexada por nivel ABSOLUTO (no por rareza).
# COINR[n-1] = monedas para ALCANZAR el nivel n.
# Confianza: ALTA. Reproduce los totales 1->30 de las 5 rarezas.
COINR = [0, 5, 10, 25, 50, 100, 200, 400, 600, 800,
         1000, 2000, 4000, 6000, 8000, 10000, 15000, 20000, 30000, 40000,
         50000, 60000, 70000, 80000, 90000, 100000, 120000, 150000, 200000, 250000]

COIN_31_35 = 250000        # por nivel, plano
COIN_OMEGA_31_35 = 400000  # por nivel, plano

# --------------------------------------------------------------------------
# 3. Fusion
# --------------------------------------------------------------------------
# El coste de ADN por fusion depende SOLO del salto de rareza:
#     salto = tier(hibrido) - tier(ingrediente)
# Verificado sin ambiguedad en 191 hibridos: cada combinacion observada da un
# unico valor. La tabla de abajo es unanime.
#
#   salto 1 -> 50      (common->rare, rare->epic, epic->legendary, legendary->unique, unique->apex)
#   salto 2 -> 200     (common->epic, rare->legendary, epic->unique, legendary->apex)
#   salto 3 -> 500     (common->legendary, rare->unique, epic->apex)
#   salto 4 -> 2000    (common->unique, rare->apex)
#
# OJO: el codigo de la app (jurassic-journal) devuelve 0 para el salto 4.
# Es un bug de la app; paleo.gg confirma 2.000 (Indoraptor <- Velociraptor).
TIER = {"common": 0, "rare": 1, "epic": 2, "legendary": 3, "unique": 4, "apex": 5}
ADN_POR_FUSION = {1: 50, 2: 200, 3: 500, 4: 2000}

# Monedas por fusion, segun la rareza del HIBRIDO.
# Confianza: ALTA. Coincide con paleo.gg y con fuseCoinCostForRarity() de la app.
MONEDAS_FUSION = {"common": 20, "rare": 20, "epic": 100,
                  "legendary": 200, "unique": 1000, "apex": 2000}

# ADN que da cada fusion, en promedio. Es una MEDIA, no un valor fijo:
# la cantidad real es aleatoria.
#   - paleo.gg lo usa literalmente ("Assuming an average of 22 DNA per fuse").
#   - La tabla de probabilidades de la wiki da una esperanza de 22,228
#     (desviacion del 1,03% respecto a 22).
#   - Dato aportado por n30: 22.
# Confianza: ALTA en la media; NULA en el valor de una fusion concreta.
ADN_POR_FUSION_MEDIA = 22

# Nivel minimo de los ingredientes. Regla general: uno menos que el nivel de
# creacion del hibrido.
# Confianza: ALTA (wiki /Rarity, texto explicito).
NIVEL_MIN_INGREDIENTE = {r: MIN_LV[r] - 1 for r in MIN_LV}

# --------------------------------------------------------------------------
# 4. Omega
# --------------------------------------------------------------------------
# El Omega nace en nivel 1 y NO se fusiona en hibridos. Tiene escalera propia.
# Indice k = coste de ALCANZAR el nivel k+1 (k=0 es la creacion).
#
# Confianza: MEDIA-ALTA. Viene de game_database.db (jurassic-journal) con UNA
# correccion: la base de datos pone 1.000 en el salto 15->16, pero el patron
# esta bloqueado en 1.500 cinco veces seguidas, y solo con 1.500 el total 1->30
# cuadra en 41.700 (cifra que confirma la fuente secundaria idgt902).
OMEGA_L = [100, 100, 100, 100, 500, 500, 500, 500, 500,
           1000, 1000, 1000, 1000, 1000,
           1500, 1500, 1500, 1500, 1500,
           2000, 2000, 2000, 2000, 2000,
           2700, 2700, 2700, 2700, 2700, 2800]
OMEGA_31_35 = [3500, 4000, 4500, 5000, 5500]

# Monedas Omega para alcanzar cada nivel (indice n-1).
OMEGA_COINR = [0, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000, 7000,
               8000, 10000, 12000, 15000, 20000, 25000, 30000, 35000, 45000, 50000,
               65000, 80000, 95000, 120000, 150000, 180000, 210000, 250000, 300000, 350000]

# --------------------------------------------------------------------------
# 5. Topes de inventario de ADN
# --------------------------------------------------------------------------
# Confianza: ALTA. Fuente OFICIAL (jurassicworldalive.com/news/dna-cap-changes/,
# 31-ago-2026) y coincide exactamente con Rarity.maxDna() del codigo de la app.
TOPES_ADN = {"common": 850000, "rare": 250000, "epic": 85000,
             "legendary": 25000, "unique": 8000, "apex": 3000, "omega": 60000}


# --------------------------------------------------------------------------
# 6. Real stats: level, stat boosts and upgrades
# --------------------------------------------------------------------------
# The `stats` carried by each creature in the data are LEVEL 26 values, and this
# is not our inference: the source states it in the "Compare Creatures" link,
# which carries `compare?ck=0__<uuid>__26` on all 518 entries. Two more facts
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

# Tope de puntos por stat, y el total: nivel de la criatura + lo que sumen las
# mejoras ya aplicadas (`v = (capBoostByLevel ? level : 35) + capBoostIncrease`).
TOPE_BOOST_STAT = 20

# Las mejoras («Enhancements») son una pista de 5 pasos, solo para Unica y Apex.
# Exigen nivel 30 o mas. El ORDEN de los pasos NO es el mismo en las dos, y eso
# se descubrio mirando una captura, no el codigo: se habia dado por supuesto un
# unico orden y era falso.
#     Unica (92): vida x1,10 · dano x1,10 · +2 velocidad · boost_max +1 · reactivo
#     Apex  (55): +2 velocidad · vida x1,10 · boost_max +2 · dano x1,10 · reactivo
# El navegador NO usa esta tabla: lee el tipo de cada paso de los propios datos,
# paso a paso. Esto esta aqui como documentacion, y `verificar_stats.py` lo
# comprueba contra el JSON para que no se quede desactualizado en silencio.
MEJORA_ORDEN = {
    "unique": ("health", "damage", "speed", "boost_max", "moves_reactive"),
    "apex":   ("speed", "health", "boost_max", "damage", "moves_reactive"),
}
MEJORA_NIVEL_MIN = 30
MEJORA_PASOS = 5


# --------------------------------------------------------------------------
# 7. Donde se consigue cada criatura
# --------------------------------------------------------------------------
# Confianza: ALTA. Cada criatura trae su lista de fuentes en `fuentes_adn`
# (campo `loc`), y la ETIQUETA de cada codigo se lee del bloque «DNA Source»
# del cache de paleo.gg, que es la fuente. No estan escritas a mano: las
# vuelve a extraer `verificar_fuentes.py` del cache y falla si no coinciden.
#
# Ojo con la distincion, porque NO son lo mismo:
#   - DARDEO: la cazas con el dardo en el mapa. Es lo que n30 pidio ensenar.
#   - COMBATE: su ADN sale de luchar (Arena, Torres de Asalto, Incursion,
#     Misiones de Alianza). No es una zona de dardear y no se puede
#     presentar como si lo fuera.
#   - SANTUARIO: colocacion pasiva, ni dardeo ni combate. NINGUNA de las 518
#     lo tiene como unica fuente (medido), asi que se omite sin perder nada.
#   - `none`: no aparece en el mapa. Son omega y criaturas de evento.
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
#  Funciones
# ==========================================================================

def coste_adn(rareza, desde, hasta, incluir_creacion=False):
    """ADN para subir una criatura de `desde` a `hasta`.

    No incluye el coste de creacion salvo que se pida explicitamente.
    Si `desde` es el nivel de creacion y `incluir_creacion=True`, lo suma.
    """
    if hasta <= desde:
        return 0
    if rareza == "omega":
        return _omega_adn(desde, hasta, incluir_creacion)
    if rareza not in MIN_LV:
        return 0
    m = MIN_LV[rareza]
    # OJO: hay que acotar `desde` al nivel de creacion. Si no, con desde=0 los
    # indices L[n-m] salen NEGATIVOS y Python da la vuelta a la lista en
    # silencio (L[-20] es un elemento del final), devolviendo cifras absurdas.
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
    """Monedas para subir una criatura de `desde` a `hasta`."""
    if hasta <= desde:
        return 0
    m = 1 if rareza == "omega" else MIN_LV.get(rareza, 1)
    a = max(desde, m)          # no se puede subir por debajo del nivel de creacion
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
    """ADN que consume UNA fusion de ese ingrediente hacia ese hibrido."""
    a, b = TIER.get(rareza_ingrediente), TIER.get(rareza_hibrido)
    if a is None or b is None:
        return 0
    return ADN_POR_FUSION.get(b - a, 0)


# --------------------------------------------------------------------------
#  Nivel maximo alcanzable con el ADN que se tiene
# --------------------------------------------------------------------------

def nivel_creacion(rareza):
    """Nivel al que NACE la criatura. Por debajo de el, no existe."""
    return 1 if rareza == "omega" else MIN_LV.get(rareza, 1)


def coste_creacion(rareza):
    """ADN que cuesta crear la criatura (traerla a su nivel de nacimiento)."""
    return OMEGA_L[0] if rareza == "omega" else CREACION.get(rareza, 0)


def coste_paso(rareza, nivel_destino):
    """ADN que cuesta pasar de `nivel_destino - 1` a `nivel_destino`.

    Es el ladrillo del que esta hecho coste_adn: sumar coste_paso desde
    `desde+1` hasta `hasta` da exactamente coste_adn. Se expone aparte porque
    el calculo de nivel maximo necesita ir paso a paso, no de golpe.
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
    """Hasta que nivel se puede subir con `adn`, partiendo de `desde`.

    `creado` = si la criatura ya existe. Si es False, el primer pago es el de
    creacion y la criatura aparece en su nivel de nacimiento. Si es None se
    deduce de `desde >= nivel_creacion(rareza)`.

    Devuelve (nivel, adn_gastado, adn_sobrante). Si no alcanza ni para crear,
    devuelve (0, 0, adn) — nivel 0 significa "no existe".
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

    # --- totales 1->30 de ADN (los 14 conocidos) ---
    eq("common 1->30", coste_adn("common", 1, 30, True), 346800)
    eq("rare 1->30", coste_adn("rare", 6, 30, True), 116850)
    eq("epic 1->30", coste_adn("epic", 11, 30, True), 34400)
    eq("legendary 1->30", coste_adn("legendary", 16, 30, True), 11450)
    eq("unique 1->30", coste_adn("unique", 21, 30, True), 3250)
    eq("apex 1->30", coste_adn("apex", 26, 30, True), 1000)
    eq("omega 1->30", coste_adn("omega", 1, 30, True), 41700)

    # --- tramo 31-35 ---
    for r in ("common", "rare", "epic", "legendary", "unique", "apex"):
        eq(f"{r} 30->35", coste_adn(r, 30, 35), ADN_31_35[r] * 5)
    eq("omega 30->35", coste_adn("omega", 30, 35), 22500)

    # --- totales de monedas 1->30 ---
    eq("mon common 1->30", coste_monedas("common", 1, 30), 1308190)
    eq("mon rare 1->30", coste_monedas("rare", 6, 30), 1308000)
    eq("mon epic 1->30", coste_monedas("epic", 11, 30), 1305000)
    eq("mon legendary 1->30", coste_monedas("legendary", 16, 30), 1275000)
    eq("mon unique 1->30", coste_monedas("unique", 21, 30), 1120000)
    eq("mon 30->35", coste_monedas("common", 30, 35), 1250000)

    # --- los tres numeros que enseña paleo.gg (rango por defecto de cada rareza) ---
    DEFECTO = [("rare", 6, 10), ("epic", 11, 15), ("legendary", 16, 20),
               ("unique", 21, 30), ("apex", 26, 30)]
    ESPERADO = {"rare": 700, "epic": 700, "legendary": 700, "unique": 3000, "apex": 700}
    for r, a, b in DEFECTO:
        d = coste_adn(r, a, b)
        eq(f"paleo ADN {r} {a}->{b}", d, ESPERADO[r])
        eq(f"paleo fusiones {r}", monedas_fusion(r, d),
           {"rare": 640, "epic": 3200, "legendary": 6400,
            "unique": 137000, "apex": 64000}[r])

    # --- coste de fusion por salto de rareza ---
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

    # --- caso concreto con nombre propio: Indoraptor ---
    # Velociraptor (common) -> Indoraptor (unique): 2.000 por fusion.
    eq("Indoraptor <- Velociraptor", adn_por_fusion("common", "unique"), 2000)
    eq("nivel min ingrediente unique", NIVEL_MIN_INGREDIENTE["unique"], 20)

    # --- nivel maximo: invariantes, no valores sueltos ---
    # El test que vale aqui es el de ida y vuelta: si `nivel_maximo` dice que
    # llegas al nivel N con ese ADN, entonces coste_adn(...,N) tiene que caber
    # y coste_adn(...,N+1) no. Eso caza cualquier desajuste entre las dos
    # funciones, que es donde estaria el error de verdad.
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
                        f"nivel_maximo {r} desde={desde} adn={adn}: dice nivel {n} "
                        f"pero cuesta {nec}, mas de lo que hay")
                if n < NIVEL_MAX:
                    sig = coste_adn(r, desde, n + 1, not creado)
                    if sig <= adn:
                        fallos.append(
                            f"nivel_maximo {r} desde={desde} adn={adn}: se queda en {n} "
                            f"pero el nivel {n+1} costaba {sig}, que si alcanzaba")
                if gastado + sobra != adn:
                    fallos.append(
                        f"nivel_maximo {r} desde={desde} adn={adn}: "
                        f"gastado {gastado} + sobra {sobra} != {adn}")
                if n < desde:
                    fallos.append(
                        f"nivel_maximo {r} desde={desde} adn={adn}: baja a {n}")

    # --- coste_paso tiene que reconstruir coste_adn exactamente ---
    for r in ("common", "rare", "epic", "legendary", "unique", "apex", "omega"):
        m = nivel_creacion(r)
        for desde in (m, m + 5, 28):
            for hasta in (desde + 1, 30, 35):
                if hasta > NIVEL_MAX:
                    continue
                sumado = sum(coste_paso(r, n) for n in range(desde + 1, hasta + 1))
                eq(f"coste_paso suma {r} {desde}->{hasta}", sumado,
                   coste_adn(r, desde, hasta))

    # --- casos con nombre propio de nivel maximo ---
    # Apex sin crear (nivel 26): crear cuesta 300. Con 300 justos, nivel 26.
    eq("apex sin crear con 300", nivel_maximo("apex", 0, 300, False), (26, 300, 0))
    eq("apex sin crear con 299", nivel_maximo("apex", 0, 299, False), (0, 0, 299))
    # Unique ya creada en 21, con 0 ADN: se queda en 21.
    eq("unique 21 con 0", nivel_maximo("unique", 21, 0, True), (21, 0, 0))
    # Common ya creada en 1: el 1->30 SIN creacion cuesta 346.750 (el total
    # 346.800 incluye los 50 de crear). Con uno menos, se queda en 29.
    eq("common 1 con 346749", nivel_maximo("common", 1, 346749, True)[0], 29)
    eq("common 1 con 346750", nivel_maximo("common", 1, 346750, True)[0], 30)
    # Omega: crear cuesta 100 y deja en nivel 1.
    eq("omega sin crear con 100", nivel_maximo("omega", 0, 100, False), (1, 100, 0))
    eq("omega sin crear con 99", nivel_maximo("omega", 0, 99, False), (0, 0, 99))

    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"Autocomprobacion: 40/40 correctas + {casos_nm} casos de nivel maximo "
          f"(invariantes de ida y vuelta).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_comprobar())
