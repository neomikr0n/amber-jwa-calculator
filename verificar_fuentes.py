#!/usr/bin/env python3
"""
Verifica de donde se consigue cada criatura.

Que comprueba, y por que
-------------------------
1. **Las etiquetas de `LOC_ETIQUETAS` NO estan escritas a mano.** Se vuelven a
   extraer del bloque «DNA Source» del cache de paleo.gg, que es la fuente, y se
   comparan una a una. Si paleo.gg renombra una zona, esto sale en rojo en vez de
   quedarse con el texto viejo para siempre.
2. **Todo codigo que use una criatura tiene etiqueta.** Un codigo nuevo en los
   datos sin etiqueta se pintaria como el codigo crudo (`local_area_5`) y nadie
   se enteraria hasta verlo en pantalla.
3. **El reparto dardeo / combate esta completo.** Cada codigo es de una cosa o de
   la otra; ninguno se queda sin clasificar. Esto importa porque la herramienta
   ensena «donde se dardea» y NO puede decir que Arena es una zona de dardear:
   Arena se pelea, no se dardea.
4. **El reparto completo, por categoria.** Cuantas se dardean, cuantas se pelean,
   cuantas solo salen en el santuario y cuantas no tienen fuente. Los recuentos se
   afirman aqui, asi que un cambio de datos no pasa inadvertido.
5. **La afirmacion sobre el santuario, medida de la forma que NO se engana a si
   misma.** Ver el comentario de la seccion 3: la version anterior comparaba el
   conjunto contra `{"sanctuary"}` exacto y por eso daba 0 casos cuando en realidad
   son 4. Una prueba que comparte el malentendido del dato pasa en verde y no
   prueba nada.

    python3 verificar_fuentes.py     -> 0 si todo cuadra, 1 si no
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
        print("FALLO %s%s" % (que, ": " + detalle if detalle else ""))


# ---------------------------------------------------------------------------
# 1) Reextraer las etiquetas del cache
# ---------------------------------------------------------------------------
# El enlace es `dnaSourceLoc=<codigo>">Etiqueta</a>`. El codigo lleva MAYUSCULAS
# en los continentes (continent_NA/SA/US): un patron en minusculas los deja fuera
# y el mapa sale incompleto sin que nada avise.
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

print("=== 1. las etiquetas, contra el bloque «DNA Source» del cache ===")
ok("el cache tiene fichas", len(ficheros) > 500, "%d ficheros" % len(ficheros))

ambiguas = {c: dict(v) for c, v in leidas.items() if len(v) > 1}
ok("ningun codigo tiene dos etiquetas distintas en el cache", not ambiguas,
   str(ambiguas) if ambiguas else "%d codigos, todos univocos" % len(leidas))

for cod in sorted(leidas):
    esperado = leidas[cod].most_common(1)[0][0]
    ok("etiqueta de %s" % cod, LOC_ETIQUETAS.get(cod) == esperado,
       "modelo=%r  cache=%r" % (LOC_ETIQUETAS.get(cod), esperado))

sobran = sorted(set(LOC_ETIQUETAS) - set(leidas))
ok("no hay etiquetas en el modelo que el cache no respalde", not sobran,
   str(sobran) if sobran else "ninguna")

# ---------------------------------------------------------------------------
# 2) Todo codigo usado tiene etiqueta y esta clasificado
# ---------------------------------------------------------------------------
print()
print("=== 2. cobertura de los codigos que usan los datos ===")
d = json.load(open(DATOS, encoding="utf-8"))
cri = d["criaturas"]

usados = collections.Counter()
for v in cri.values():
    for x in v.get("fuentes_adn") or []:
        usados[x["loc"]] += 1

ESPECIALES = {"none", "sanctuary"}      # no son ni dardeo ni combate
# `none` no es una fuente: es «no aparece en el mapa». No tiene etiqueta porque
# no hay nada que etiquetar, y exigirsela seria pedirle al dato lo que no dice.
sinEtiqueta = sorted(c for c in usados
                     if c not in LOC_ETIQUETAS and c != "none")
ok("todo codigo que es una fuente tiene etiqueta", not sinEtiqueta,
   str(sinEtiqueta) if sinEtiqueta else "%d codigos (+ none, que no es fuente)" % len(usados))
sinClasificar = sorted(c for c in usados
                       if c not in LOC_DARDEO and c not in LOC_COMBATE
                       and c not in ESPECIALES)
ok("todo codigo es dardeo, combate o especial (none/sanctuary)", not sinClasificar,
   str(sinClasificar) if sinClasificar else "ninguno suelto")

solapan = sorted(set(LOC_DARDEO) & set(LOC_COMBATE))
ok("dardeo y combate no se solapan", not solapan, str(solapan) if solapan else "vacio")

# ---------------------------------------------------------------------------
# 3) El santuario: la afirmacion, medida sin enganarse
# ---------------------------------------------------------------------------
# OJO, aqui hubo un fallo real de metodo. La version anterior preguntaba si el
# conjunto de fuentes era EXACTAMENTE {"sanctuary"} y respondia «0 casos», que es
# lo que se documento. Pero 4 criaturas (alioramus, aquilops, arsinoitherium,
# titanosaurus) tienen [sanctuary, none]: `none` no es una fuente —es «no sale en
# el mapa»—, asi que el santuario SI es su unico origen y el recuento estaba mal.
# La prueba compartia el malentendido del dato y pasaba en verde.
#
# La pregunta correcta es: quitando `none`, ¿queda algo mas que el santuario?
# `none` y `sanctuary` se excluyen del calculo; lo que sobre son fuentes de verdad.
print()
print("=== 3. el santuario como unica fuente ===")
NO_FUENTE = {"none"}


def util(u):
    return {x["loc"] for x in cri[u].get("fuentes_adn") or []} - NO_FUENTE


soloSanct = sorted(u for u in cri if util(u) == {"sanctuary"})
ok("hay criaturas cuyo unico origen es el santuario (no 0: eran 4)", len(soloSanct) == 4,
   "%d: %s" % (len(soloSanct), ", ".join(soloSanct)))
ok("y ninguna es un hibrido: son las que hay que ir a buscar",
   all(not cri[u].get("ingredientes") for u in soloSanct),
   "las 4 sin ingredientes")
# Y por eso el santuario NO se omite: se enseña como «solo en santuario». Si algun
# dia una criatura con ingredientes apareciera aqui, la regla del hibrido (que no
# lleva pildora salvo que salga en el mapa) perderia el dato.

# ---------------------------------------------------------------------------
# 4) Los recuentos medidos, por categoria
# ---------------------------------------------------------------------------
# La version anterior tenia una cadena de `if/elif` con ramas que no podian
# alcanzarse (`resto == {"none"}` antes de `resto <= {"none"}`) y un `else` que
# metia en «solo santuario» cualquier cosa no clasificada. Los numeros salian, pero
# por accidente. Aqui la categoria se calcula una vez y se afirma entera.
print()
print("=== 4. de donde sale cada criatura (518) ===")
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

print("      %-12s %6s %8s %8s" % ("categoria", "todas", "sin ing", "hibridos"))
for k in ("dardeo", "combate", "ambos", "santuario", "sin fuente"):
    print("      %-12s %6d %8d %8d" % (k, reparto[k], repartoBase[k], repartoHib[k]))

ESPERADO = {"dardeo": 146, "combate": 107, "ambos": 2, "santuario": 4, "sin fuente": 259}
ok("las 518 se reparten en las cinco categorias",
   sum(reparto.values()) == len(cri) == 518,
   "%d = %d criaturas" % (sum(reparto.values()), len(cri)))
ok("y cada recuento es el medido", all(reparto[k] == v for k, v in ESPERADO.items()),
   " | ".join("%s %d (esperado %d)" % (k, reparto[k], v)
              for k, v in ESPERADO.items() if reparto[k] != v) or
   "dardeo %d · combate %d · ambos %d · santuario %d · sin fuente %d"
   % tuple(reparto[k] for k in ("dardeo", "combate", "ambos", "santuario", "sin fuente")))
ok("las 270 sin ingredientes y los 248 hibridos suman las 518",
   len(base) == 270 and len(hib) == 248 and len(base) + len(hib) == len(cri),
   "%d + %d = %d" % (len(base), len(hib), len(base) + len(hib)))
ok("de los hibridos, 247 no salen en el mapa y 1 si (Purrolyth)",
   repartoHib["sin fuente"] == 247 and repartoHib["combate"] == 1,
   "sin fuente %d, combate %d" % (repartoHib["sin fuente"], repartoHib["combate"]))
ok("los 4 del santuario son sin ingredientes, y son los unicos",
   repartoBase["santuario"] == 4 and repartoHib["santuario"] == 0,
   "%d base, %d hibridos" % (repartoBase["santuario"], repartoHib["santuario"]))

# ---------- 6. el nivel que exige una fusion nunca baja del nacimiento ----------
"""`NIVEL_MIN_INGREDIENTE[rareza]` es «uno menos que el nivel de creacion del
hibrido», y ese es el nivel al que el boton «criar» del informe pone a un
ingrediente. Pero una criatura NO PUEDE existir por debajo del nivel al que nace
su rareza. Si el nivel exigido quedara por debajo, el suelo de `nivelFusion` (en
`plantilla.html`) entraria en juego y el boton pondria la criatura en su
nacimiento en vez de en el nivel pedido — un cambio de comportamiento silencioso,
justo lo que la regla del proyecto no permite. Se mide en vez de suponerlo."""
from modelo import MIN_LV, NIVEL_MIN_INGREDIENTE

pares = []
for u, x in cri.items():
    for ing in x["ingredientes"]:
        if ing in cri:
            pares.append((u, x["rareza"], ing, cri[ing]["rareza"]))
margenes = [NIVEL_MIN_INGREDIENTE[rp] - MIN_LV[ri] for _, rp, _, ri in pares]
ok("todos los ingredientes de los datos existen como criatura",
   len(pares) == sum(len(x["ingredientes"]) for x in cri.values()),
   "%d pares padre->ingrediente" % len(pares))
ok("el nivel que exige una fusion NUNCA queda por debajo del nacimiento del ingrediente",
   all(m >= 0 for m in margenes) and pares,
   "de %d pares, el margen minimo es %+d y el maximo %+d"
   % (len(pares), min(margenes), max(margenes)))

print()
if fallos:
    print("RESULTADO: %d FALLOS de %d comprobaciones." % (len(fallos), n_ok + len(fallos)))
    for f in fallos:
        print("  - " + f)
    raise SystemExit(1)
print("RESULTADO: todo OK (%d comprobaciones)." % n_ok)
