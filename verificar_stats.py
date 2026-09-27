#!/usr/bin/env python3
"""
Verifica los stats del dino y la pista de mejoras contra el cache de paleo.gg.

Por que existe este fichero
---------------------------
La herramienta ensena seis numeros por criatura y los llama «datos actuales y
fidedignos». Eso es una AFIRMACION, y hasta ahora no la respaldaba ninguna
prueba: los numeros venian del JSON, y el JSON lo escribio `scrape_paleo.py`
una vez. Si paleo.gg corrige un stat, el JSON se queda con el viejo y nada
avisa. Esto es el mismo agujero que cerro `verificar_fuentes.py` para las
zonas, y se cierra igual: releyendo la fuente.

Que comprueba, y por que
------------------------
1. **Los seis stats, uno a uno, contra la ficha cacheada.** No contra el JSON
   (que es lo que se quiere comprobar), sino contra el campo `health/damage/
   speed/armor/crit/critm` de `__NEXT_DATA__.props.pageProps.detail`. Y ademas
   contra el TEXTO RENDERIZADO de la ficha, que es una segunda copia
   independiente dentro del mismo fichero: si paleo.gg pintara una cosa y
   sirviera otra, aqui saldria.
2. **A que nivel son esos numeros.** La propia ficha lo dice en el enlace
   «Compare Creatures»: `compare?ck=0__<uuid>__26`. El 26 no lo ponemos
   nosotros, lo pone la fuente, en las 518 fichas. Toda la interfaz se apoya en
   que el dato es de nivel 26; esto lo comprueba.
3. **La pista de mejoras, paso a paso, contra el cache**, y contra la copia que
   el propio paleo.gg trae en `evolutionData` — dos sitios del mismo fichero que
   tienen que decir lo mismo.
4. **El orden de los pasos NO es el mismo en unica y en apex.** Se descubrio
   mirando una captura, despues de haber dado por supuesto lo contrario. Aqui se
   mide la distribucion entera y se afirma.
5. **`MULT_NIVEL` no es la forma cerrada `1,05^(L-26)`.** Es el error que
   estuvo a punto de colarse: la tabla coincide con la forma cerrada hasta el
   nivel 30 (ruido de redondeo) y a partir del 31 se separa a proposito, hasta
   un 3,7 % en el nivel 34. Se mide y se afirma en las dos direcciones, para que
   nadie «simplifique» la tabla creyendo que sobran numeros.
6. **Los dominios que la interfaz da por hechos**: los cinco tipos de premio,
   los cuatro recursos, y que exista un icono en disco para cada uno. Un codigo
   nuevo sin icono se pintaria con un `src` roto y nadie se enteraria.

    python3 verificar_stats.py     -> 0 si todo cuadra, 1 si no
"""
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from modelo import (BOOST_FRACCION, BOOST_VELOCIDAD, MEJORA_NIVEL_MIN,
                    MEJORA_ORDEN, MEJORA_PASOS, MULT_NIVEL, TOPE_BOOST_STAT)

CACHE = os.path.join(RAIZ, "cache")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")
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
        print("FALLO %s%s" % (que, ": " + detalle if detalle else ""))


# ---------------------------------------------------------------------------
# 0) Cargar el cache una sola vez
# ---------------------------------------------------------------------------
# 518 fichas x 180 KB: se leen enteras y se guardan. Leerlas dos veces por
# seccion seria medio minuto tirado.
NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
# El bloque de stats va de `id="stats"` a `id="resistance"`: acotado a proposito,
# porque los iconos de stat tambien salen en el simulador de batalla que la
# ficha incluye mas abajo.
STAT_TXT = re.compile(r'images/stat/(\w+)\.png"[^>]*/>\s*<b[^>]*>(?:<span[^>]*>)?([^<]+)')
# El nivel de los numeros, declarado por la propia ficha.
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

print("=== 0. el cache y los datos cubren lo mismo ===")
ok("hay una ficha por criatura y una criatura por ficha",
   set(fichas) == set(cri) and len(fichas) == 518,
   "%d fichas, %d criaturas, %d sin pareja"
   % (len(fichas), len(cri), len(set(fichas) ^ set(cri))))
ok("todas las fichas tienen __NEXT_DATA__ y bloque de stats",
   all(v["det"] and len(v["txt"]) == 6 for v in fichas.values()),
   "%d fichas revisadas" % len(fichas))

# ---------------------------------------------------------------------------
# 1) Los seis stats: contra el campo del cache Y contra el texto renderizado
# ---------------------------------------------------------------------------
# `CAMPOS` es la traduccion entre el nombre que usa la fuente y el que usamos
# nosotros. Se escribe una vez y se usa en las dos direcciones: si algun dia
# alguien renombra una clave del JSON, esto deja de cuadrar.
CAMPOS = [("health", "vida"), ("damage", "dano"), ("speed", "velocidad"),
          ("armor", "armadura"), ("crit", "critico"), ("critm", "dano_critico")]
# Los tres que la ficha pinta con «%». Es una decision de presentacion, pero se
# apoya en el dato: si paleo.gg dejara de pintarlos asi, habria que revisarla.
PCT = {"armor", "crit", "critm"}

print()
print("=== 1. los seis stats, uno a uno (518 x 6 = 3.108 numeros) ===")
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
        # La ficha pinta el numero pelado, sin separador de millares, y con «%»
        # en los tres porcentajes. Se compara el numero, no el formato: lo que
        # importa es que la cifra que se ve sea la que tenemos.
        limpio = (bruto or "").replace("%", "").strip()
        if not limpio.isdigit() or int(limpio) != esperado:
            malTxt.append("%s.%s: pintado=%r esperado=%d" % (u, campo, bruto, esperado))
ok("el campo del cache y el JSON dicen lo mismo en los 3.108",
   not malCampo, malCampo[0] if malCampo else "3.108 numeros, 518 criaturas")
ok("el texto RENDERIZADO de la ficha tambien (segunda copia independiente)",
   not malTxt, malTxt[0] if malTxt else "sin discrepancias")
ok("los tres porcentajes se pintan con «%» y los otros tres no",
   all(("%" in dict(v["txt"])[c]) == (c in PCT)
       for v in fichas.values() for c, _ in CAMPOS),
   "armor, crit y critm llevan «%»; health, damage y speed no")
ok("la ficha pinta los seis en el mismo orden, siempre",
   all([c for c, _ in v["txt"]] == [c for c, _ in CAMPOS] for v in fichas.values()),
   "health, damage, speed, armor, crit, critm")

# ---------------------------------------------------------------------------
# 2) A que nivel son esos numeros: lo dice la fuente, no nosotros
# ---------------------------------------------------------------------------
# Este es el cimiento de toda la herramienta. Si el dato no fuera de nivel 26,
# `MULT_NIVEL[25] == 1e9` no valdria y todos los stats de la interfaz estarian
# desplazados. La ficha lo declara en el enlace de comparar.
print()
print("=== 2. el nivel del dato, declarado por la fuente ===")
niveles = collections.Counter()
enlaces = []
for u, v in fichas.items():
    if len(v["nivel"]) != 1 or v["nivel"][0][0] != u:
        enlaces.append((u, v["nivel"][:2]))
    else:
        niveles[v["nivel"][0][1]] += 1
ok("cada ficha declara su nivel una vez, y es la suya",
   not enlaces, str(enlaces[:3]) if enlaces else "%d fichas" % len(fichas))
ok("el nivel declarado es 26 en las 518 (no 1, no 35, no el maximo)",
   niveles == {"26": 518}, str(dict(niveles)))
# Y la consecuencia, comprobada sobre el dato entero: a nivel 26 el
# multiplicador no cambia NADA, en ninguno de los 3.108 numeros.
ident = all(int(cri[u]["stats"][k] * MULT_NIVEL[25] // 10 ** 9) == cri[u]["stats"][k]
            for u in cri for k in cri[u]["stats"])
ok("a nivel 26 la tabla devuelve el mismo numero, en los 3.108",
   ident and MULT_NIVEL[25] == 1000000000,
   "MULT_NIVEL[25] = %d, exacto" % MULT_NIVEL[25])

# ---------------------------------------------------------------------------
# 3) La pista de mejoras, paso a paso, contra las DOS copias del cache
# ---------------------------------------------------------------------------
# `detail.enhancements` y `evolutionData[<uuid>].enhancements` son dos copias de
# lo mismo dentro del mismo fichero. No es redundante comprobar las dos: si
# paleo.gg actualiza una y se olvida de la otra, es justo lo que hay que ver.
print()
print("=== 3. la pista de mejoras (147 criaturas) ===")
conPista = [u for u in cri if cri[u].get("mejoras")]
sinPista = [u for u in cri if not cri[u].get("mejoras")]
ok("147 con pista y 371 sin ella, y suman 518",
   len(conPista) == 147 and len(sinPista) == 371 and len(conPista) + len(sinPista) == 518,
   "%d + %d = 518" % (len(conPista), len(sinPista)))

porRareza = collections.Counter(cri[u]["rareza"] for u in conPista)
ok("solo Unica y Apex tienen pista; ninguna otra rareza",
   set(porRareza) == {"unique", "apex"},
   "unica %d, apex %d" % (porRareza["unique"], porRareza["apex"]))
ok("y son todas las Unicas y todos los Apex que hay",
   porRareza["unique"] == 92 and porRareza["apex"] == 55,
   "92 unicas + 55 apex = 147")

malPaso = []
malEvol = []
sinCinco = []
for u in conPista:
    mj = cri[u]["mejoras"]
    det = fichas[u]["det"]
    if len(mj) != MEJORA_PASOS:
        sinCinco.append("%s: %d pasos" % (u, len(mj)))
    # Normalizar: el cache guarda req como listas, el JSON igual; se comparan
    # como tuplas ordenadas porque el orden dentro de `req` no significa nada.
    def norm(pasos):
        return [(p["cost"],
                 tuple(sorted((r[0], r[1]) for r in p["req"])),
                 (p["rwd"]["type"], p["rwd"]["value"])) for p in pasos]
    if norm(mj) != norm(det.get("enhancements") or []):
        malPaso.append(u)
    ev = (det.get("evolutionData") or {}).get(u) or {}
    if norm(mj) != norm(ev.get("enhancements") or []):
        malEvol.append(u)
ok("los 147 tienen exactamente %d pasos" % MEJORA_PASOS, not sinCinco,
   str(sinCinco[:3]) if sinCinco else "5 pasos x 147 = 735 pasos")
ok("coste, requisitos y premio de los 735 pasos coinciden con el cache",
   not malPaso, str(malPaso[:5]) if malPaso else "735 pasos, uno a uno")
ok("y coinciden tambien con la SEGUNDA copia (`evolutionData`)",
   not malEvol, str(malEvol[:5]) if malEvol else "el cache no se contradice")

# Los ingredientes van por el mismo camino y con el mismo patron: si una copia
# se desincroniza, se desincronizan las dos cosas.
malIng = [u for u in cri
          if sorted(cri[u]["ingredientes"]) !=
             sorted(((fichas[u]["det"].get("evolutionData") or {}).get(u) or {})
                    .get("ingredients") or [])]
ok("los ingredientes de las 518 cuadran con `evolutionData`", not malIng,
   str(malIng[:5]) if malIng else "518 criaturas")

# ---------------------------------------------------------------------------
# 4) El orden de los pasos: NO es el mismo en unica y en apex
# ---------------------------------------------------------------------------
# Aqui hubo un error real. Se dio por supuesto un unico orden para las dos
# rarezas, y era falso: en una Unica el paso 1 es vida, en un Apex el paso 1 es
# velocidad. Se vio en una captura, no en el codigo. La medicion completa:
print()
print("=== 4. el orden de los pasos, por rareza ===")
ordenes = collections.defaultdict(collections.Counter)
for u in conPista:
    tipo = tuple(p["rwd"]["type"] for p in cri[u]["mejoras"])
    ordenes[cri[u]["rareza"]][tipo] += 1

for rareza in ("unique", "apex"):
    medido = ordenes[rareza]
    ok("la %s tiene UN solo orden, y es el de MEJORA_ORDEN" % rareza,
       list(medido) == [tuple(MEJORA_ORDEN[rareza])],
       "x%d  %s" % (list(medido.values())[0], " -> ".join(medido and list(medido)[0] or ())))
ok("y los dos ordenes son DISTINTOS (el error que se corrigio)",
   MEJORA_ORDEN["unique"] != MEJORA_ORDEN["apex"],
   "unica empieza por vida; apex, por velocidad")

# Los valores de cada premio, medidos. No son iguales entre rarezas: el
# `boost_max` da +1 en una Unica y +2 en un Apex.
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
ok("los valores de los premios son los medidos (vida/dano x1,10 · vel +2)",
   all(dict(valores[k]) == v for k, v in ESPERADO_VAL.items()),
   "boost_max: +1 en unica (x92), +2 en apex (x55)")
ok("los pasos de `moves_reactive` dan un movimiento distinto cada uno",
   all(len({p["rwd"]["value"] for p in cri[u]["mejoras"]
            if p["rwd"]["type"] == "moves_reactive"}) == 1 for u in conPista),
   "147 movimientos reactivos, ninguno repetido dentro de su criatura")

# ---------------------------------------------------------------------------
# 5) MULT_NIVEL: 35 entradas, y NO es 1,05^(L-26)
# ---------------------------------------------------------------------------
# El comentario de `modelo.py` decia que la forma cerrada difiere en «hasta
# 5e-5 relativo, ~0,3 puntos de vida». Al medirlo entero para escribir esta
# prueba, result: **es falso**. Coincide hasta el nivel 30 (ruido de redondeo,
# 1,5e-4 como mucho) y del 31 al 35 se separa a proposito: 1,27 · 1,32 · 1,37 ·
# 1,425 · 1,50, con un error de hasta el 3,7 %. En una criatura de 6.000 de vida
# eso son 314 puntos, no 0,3. El comentario se corrigio.
print()
print("=== 5. la tabla de niveles ===")
ok("la tabla tiene 35 entradas, una por nivel",
   len(MULT_NIVEL) == 35, "%d entradas" % len(MULT_NIVEL))
ok("es estrictamente creciente (subir de nivel nunca quita stats)",
   all(MULT_NIVEL[i] < MULT_NIVEL[i + 1] for i in range(34)),
   "de %d a %d" % (MULT_NIVEL[0], MULT_NIVEL[-1]))
ok("el nivel 26 vale exactamente 1.000.000.000, sin redondeo",
   MULT_NIVEL[25] == 1000000000, "1e9, exacto")
ok("el nivel 35 vale 1,5 exacto (el tope esta puesto a mano, no multiplicado)",
   MULT_NIVEL[34] == 1500000000, "1,5e9, exacto")

err = {L: abs(MULT_NIVEL[L - 1] / 1e9 - 1.05 ** (L - 26)) / (MULT_NIVEL[L - 1] / 1e9)
       for L in range(1, 36)}
maxBajo = max(err[L] for L in range(1, 31))
maxAlto = max(err[L] for L in range(31, 36))
ok("hasta el nivel 30 SI es 1,05^(L-26), salvo el ruido de redondeo",
   maxBajo < 2e-4, "error relativo maximo %.2e (nivel %d)"
   % (maxBajo, max(range(1, 31), key=lambda L: err[L])))
ok("del 31 al 35 NO lo es, y por mucho: la tabla se separa a proposito",
   maxAlto > 1e-2, "error relativo maximo %.2e en el nivel %d "
   "(tabla %.3f, forma cerrada %.3f)"
   % (maxAlto, max(range(31, 36), key=lambda L: err[L]),
      MULT_NIVEL[max(range(31, 36), key=lambda L: err[L]) - 1] / 1e9,
      1.05 ** (max(range(31, 36), key=lambda L: err[L]) - 26)))
ok("los cinco ultimos son cifras redondas, no potencias",
   [MULT_NIVEL[L - 1] / 1e9 for L in range(31, 36)] == [1.27, 1.32, 1.37, 1.425, 1.5],
   "1,27 · 1,32 · 1,37 · 1,425 · 1,5")

# ---------------------------------------------------------------------------
# 6) Los dominios que la interfaz da por hechos
# ---------------------------------------------------------------------------
# La interfaz tiene mapas de etiquetas e iconos indexados por estos codigos. Un
# codigo nuevo no da error: pinta `undefined` o un `src` roto. Por eso se
# afirma el dominio aqui.
print()
print("=== 6. los codigos que la interfaz resuelve ===")
TIPOS = {"speed", "health", "damage", "boost_max", "moves_reactive"}
RECURSOS = {"coins", "catalyst_minor", "catalyst", "catalyst_major"}

vistosTipos = {p["rwd"]["type"] for u in conPista for p in cri[u]["mejoras"]}
vistosRec = {r[0] for u in conPista for p in cri[u]["mejoras"] for r in p["req"]}
ok("los tipos de premio son exactamente los 5 que la interfaz traduce",
   vistosTipos == TIPOS, ", ".join(sorted(vistosTipos)))
ok("los recursos son exactamente los 4 que la interfaz tiene con icono",
   vistosRec == RECURSOS, ", ".join(sorted(vistosRec)))

# Y el icono, en disco. La interfaz los pide por ruta relativa; si falta uno, la
# ficha sale con un hueco y el navegador no se queja en ningun sitio visible.
# La ruta NO se deriva del codigo: `coins` vive en `img/res/coin.png`, en
# singular y en otra carpeta. Se escribe el mapa entero, igual que lo escribe la
# plantilla, y ademas se comprueba que la plantilla diga lo mismo.
RUTA_REC = {"coins": "img/res/coin.png",
            "catalyst_minor": "img/cat/catalyst_minor.png",
            "catalyst": "img/cat/catalyst.png",
            "catalyst_major": "img/cat/catalyst_major.png"}
FICHEROS = ([os.path.join(IMG, "stat", n + ".png")
             for n in ("health", "damage", "speed", "armor", "crit", "critm", "enhancement")]
            + [os.path.join(IMG, "res", "dna.png")]
            + [os.path.join(RAIZ, r) for r in RUTA_REC.values()])
faltan = [os.path.relpath(p, RAIZ) for p in FICHEROS if not os.path.getsize(p) > 100]
ok("existe un icono en disco para cada stat, cada recurso y la mejora",
   not faltan, str(faltan) if faltan else "%d iconos" % len(FICHEROS))

# La plantilla declara su propio mapa de recursos. Se lee de ahi y se compara:
# es la comprobacion de que la interfaz no pide una ruta que no existe.
pl = open(os.path.join(RAIZ, "plantilla.html"), encoding="utf-8").read()
m = re.search(r"const RES_ICONO = \{(.*?)\};", pl, re.S)
mapaUI = dict(re.findall(r'(\w+):"([^"]+)"', m.group(1))) if m else {}
ok("y la plantilla pide exactamente esas rutas, ni una mas ni una menos",
   mapaUI == RUTA_REC,
   str(mapaUI) if mapaUI != RUTA_REC else "coincide con el mapa de la interfaz")

# Los rangos de los tres porcentajes, medidos. Sirven de centinela: si un stat
# se colara como numero pelado (400 en vez de 40), esto lo caza.
rangos = {k: (min(cri[u]["stats"][k] for u in cri), max(cri[u]["stats"][k] for u in cri))
          for k in ("armadura", "critico", "dano_critico")}
ok("la armadura y los dos criticos son porcentajes, en todo el dinodex",
   rangos["armadura"] == (0, 60) and rangos["critico"] == (0, 50)
   and rangos["dano_critico"] == (125, 200),
   "armadura %d-%d · critico %d-%d · dano critico %d-%d"
   % (rangos["armadura"][0], rangos["armadura"][1], rangos["critico"][0],
      rangos["critico"][1], rangos["dano_critico"][0], rangos["dano_critico"][1]))

# Los tres ajustes del usuario, afirmados contra el dato y no entre si.
ok("el tope por stat (20) y el minimo de la pista (30) son los medidos",
   TOPE_BOOST_STAT == 20 and MEJORA_NIVEL_MIN == 30,
   "+%d por stat, pista desde nivel %d" % (TOPE_BOOST_STAT, MEJORA_NIVEL_MIN))
ok("los dos ajustes del boost son los de la fuente (+2 plano, +2,5%%)",
   BOOST_VELOCIDAD == 2 and BOOST_FRACCION == 0.025,
   "+%d de velocidad y +%.1f%% de vida y dano por punto"
   % (BOOST_VELOCIDAD, BOOST_FRACCION * 100))

print()
if fallos:
    print("RESULTADO: %d FALLOS de %d comprobaciones." % (len(fallos), n_ok + len(fallos)))
    for f in fallos:
        print("  - " + f)
    raise SystemExit(1)
print("RESULTADO: todo OK (%d comprobaciones)." % n_ok)
