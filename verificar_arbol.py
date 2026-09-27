#!/usr/bin/env python3
"""
Verificacion del ARBOL DE FUSION. Igual que verificar_motor.py, extrae el
motor REAL del HTML entregable y lo ejecuta en Node, pero aqui ademas se
ejercita `plan` y `totales` con inventarios simulados.

Se comparan los DOS criterios:
  - contarSubida = true   -> coste real (incluye subir los ingredientes)
  - contarSubida = false  -> criterio de paleo.gg (solo lo que se fusiona)

Y los dos estados de cada criatura:
  - creada = false -> se suma el ADN de creacion
  - creada = true  -> se parte del nivel que tenga

Compara el arbol nodo por nodo y los totales, contra un espejo en Python
que usa modelo.py. Si algo difiere, sale con codigo 1.

Uso:  python3 verificar_arbol.py
"""
import json, math, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from modelo import (ADN_31_35, ADN_POR_FUSION, ADN_POR_FUSION_MEDIA, COINR,
                    COIN_31_35, CREACION, L, MIN_LV, MONEDAS_FUSION,
                    NIVEL_MIN_INGREDIENTE, OMEGA_31_35, OMEGA_COINR, OMEGA_L,
                    TIER, nivel_creacion, nivel_maximo)

HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")

CAMPOS = ("rareza", "desde", "objetivo", "adnSubir", "adnNec", "monNec", "deficit",
          "fusiones", "monFus", "nivelIng", "esHoja", "creado", "maxNivel")


def bloque_llaves(texto, pos):
    assert texto[pos] == "{"
    prof, i, cad, esc = 0, pos, False, False
    while i < len(texto):
        ch = texto[i]
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            cad = not cad
        elif not cad:
            if ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof == 0:
                    return texto[pos:i + 1]
        i += 1
    raise RuntimeError("llaves sin cerrar")


def bloque_cuerpo(texto, pos_llave):
    """Las funciones terminan en '}', no en '};'. Buscar '};' corta el bloque
    a medias y Node falla con 'Unexpected end of input'."""
    prof, i, cad, esc = 0, pos_llave, False, False
    while i < len(texto):
        ch = texto[i]
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            cad = not cad
        elif not cad:
            if ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof == 0:
                    return texto[pos_llave:i + 1]
        i += 1
    raise RuntimeError("cuerpo de funcion sin cerrar")


def extraer(html):
    m = re.search(r"const D\s*=\s*", html)
    datos = bloque_llaves(html, html.index("{", m.end()))
    i = html.index("const minLv")
    p = html.index("{", html.index("function totales", i))
    j = p + len(bloque_cuerpo(html, p))
    cuerpo = html[i:j]
    for nec in ("costeADN", "costeMon", "adnFus", "nFus", "plan", "totales",
                "invDe", "fijar", "nivelMaximo"):
        if nec not in cuerpo:
            raise RuntimeError("falta " + nec + " en el bloque extraido")
    if cuerpo.count("{") != cuerpo.count("}"):
        raise RuntimeError("bloque desequilibrado: %d vs %d"
                           % (cuerpo.count("{"), cuerpo.count("}")))
    return datos, cuerpo


# ---------------- espejo en Python ----------------
def coste_adn(r, desde, hasta, crear):
    if hasta <= desde:
        return 0
    if r == "omega":
        t = OMEGA_L[0] if (crear and desde < 1) else 0
        for n in range(max(desde, 1) + 1, hasta + 1):
            t += OMEGA_L[n - 1] if n <= 30 else OMEGA_31_35[n - 31]
        return t
    m = MIN_LV[r]
    a = max(desde, m)
    t = sum(L[n - m] for n in range(a + 1, min(hasta, 30) + 1))
    if hasta > 30:
        t += (hasta - max(a, 30)) * ADN_31_35[r]
    if crear:
        t += CREACION[r]
    return t


def coste_mon(r, desde, hasta):
    if hasta <= desde:
        return 0
    a = max(desde, 1 if r == "omega" else MIN_LV.get(r, 1))
    if r == "omega":
        t = sum(OMEGA_COINR[n - 1] for n in range(a + 1, min(hasta, 30) + 1))
        if hasta > 30:
            t += (hasta - max(a, 30)) * 400000
        return t
    t = sum(COINR[n - 1] for n in range(a + 1, min(hasta, 30) + 1))
    if hasta > 30:
        t += (hasta - max(a, 30)) * COIN_31_35
    return t


def adn_fus(ri, rh):
    return ADN_POR_FUSION.get(TIER.get(rh, 0) - TIER.get(ri, 0), 0)


def n_fus(d):
    return 0 if d <= 0 else math.ceil(d / ADN_POR_FUSION_MEDIA)


def inv_de(cri, inv, u):
    """Espejo de `invDe`: `creado` es explicito y, si falta, se deduce del nivel."""
    v = inv.get(u, {})
    r = cri[u]["rareza"] if u in cri else "common"
    m = nivel_creacion(r)
    nivel = max(0, min(35, int(v.get("nivel", 0) or 0)))
    creado = bool(v["creado"]) if "creado" in v else nivel >= m
    return {"nivel": nivel, "adn": max(0, int(v.get("adn", 0) or 0)), "creado": creado}


def plan(cri, inv, uuid, objetivo, adn_extra, visto, raiz, contar_subida):
    c = cri[uuid]
    rareza, ings = c["rareza"], c["ingredientes"]
    invn = inv_de(cri, inv, uuid)
    m = nivel_creacion(rareza)
    creado = invn["creado"]
    desde = max(invn["nivel"], m) if creado else 0
    sin_crear = not creado
    adn_subir = coste_adn(rareza, desde, objetivo, sin_crear)
    cuenta = raiz or contar_subida
    adn_nec = (adn_subir if cuenta else 0) + (adn_extra or 0)
    mon_nec = coste_mon(rareza, desde, objetivo) if cuenta else 0
    deficit = max(0, adn_nec - invn["adn"])
    mx = nivel_maximo(rareza, desde, invn["adn"], creado)
    nodo = {"uuid": uuid, "nombre": c["nombre"], "rareza": rareza, "desde": desde,
            "objetivo": objetivo, "adnSubir": adn_subir, "cuentaSubir": cuenta,
            "adnNec": adn_nec, "monNec": mon_nec, "deficit": deficit,
            "tengo": invn["adn"], "extra": adn_extra or 0, "fusiones": 0, "monFus": 0,
            "nivelIng": None, "esHoja": False, "creado": creado,
            "maxNivel": mx[0], "hijos": [], "base": not ings}
    if deficit > 0 and ings and uuid not in visto:
        f = n_fus(deficit)
        nodo["fusiones"] = f
        nodo["monFus"] = f * MONEDAS_FUSION.get(rareza, 0)
        nodo["nivelIng"] = NIVEL_MIN_INGREDIENTE[rareza]
        v2 = set(visto) | {uuid}
        for ing in ings:
            ri = cri[ing]["rareza"] if ing in cri else "common"
            adn_ing = f * adn_fus(ri, rareza)
            inv_ing = inv_de(cri, inv, ing)
            actual = max(inv_ing["nivel"], nivel_creacion(ri)) if inv_ing["creado"] else 0
            obj_ing = max(nodo["nivelIng"], actual)
            nodo["hijos"].append(
                plan(cri, inv, ing, obj_ing, adn_ing, v2, False, contar_subida))
    else:
        nodo["esHoja"] = True
    return nodo


def totales(n):
    """Suma el arbol SIN contar dos veces a la misma criatura.

    Un ingrediente compartido es UNA sola reserva de ADN: lo que consume se suma
    (son fusiones distintas), pero lo que tienes se resta UNA vez.
    """
    acc = {"porUuid": {}, "nodos": 0, "hojas": 0, "repetidas": 0, "fus": 0,
           "monFus": 0, "mon": 0, "adn": 0, "adnNec": 0, "tengo": 0, "recolectar": 0}

    def rec(x):
        acc["nodos"] += 1
        acc["fus"] += x["fusiones"]
        acc["monFus"] += x["monFus"]
        p = acc["porUuid"].get(x["uuid"])
        if p is None:
            p = acc["porUuid"][x["uuid"]] = {
                "uuid": x["uuid"], "nombre": x["nombre"], "rareza": x["rareza"],
                "veces": 0, "fus": 0, "extra": 0, "desde": x["desde"],
                "objetivo": x["objetivo"], "sinCrear": False, "tengo": x["tengo"],
                "esHoja": False, "base": False, "cuentaSubir": False,
            }
        p["veces"] += 1
        p["fus"] += x["fusiones"]
        p["extra"] += x["extra"]
        p["objetivo"] = max(p["objetivo"], x["objetivo"])
        p["desde"] = min(p["desde"], x["desde"])
        p["sinCrear"] = p["sinCrear"] or not x["creado"]
        p["esHoja"] = p["esHoja"] or x["esHoja"]
        p["base"] = p["base"] or x["base"]
        p["cuentaSubir"] = p["cuentaSubir"] or x["cuentaSubir"]
        if x["esHoja"]:
            acc["hojas"] += 1
        for h in x["hijos"]:
            rec(h)

    rec(n)
    for p in acc["porUuid"].values():
        # Solo se paga la escalera si esa criatura cuenta su subida. `plan` ya lo
        # decide nodo a nodo; sumarla siempre hacia que el informe ignorase el
        # interruptor de «subir los ingredientes».
        p["escalera"] = (coste_adn(p["rareza"], p["desde"], p["objetivo"], p["sinCrear"])
                         if p["cuentaSubir"] else 0)
        p["mon"] = (coste_mon(p["rareza"], p["desde"], p["objetivo"])
                    if p["cuentaSubir"] else 0)
        p["nec"] = p["escalera"] + p["extra"]
        p["falta"] = max(0, p["nec"] - p["tengo"])
        acc["adn"] += p["falta"]
        acc["adnNec"] += p["nec"]
        acc["tengo"] += p["tengo"]
        acc["mon"] += p["mon"]
        if p["base"]:
            acc["recolectar"] += p["falta"]
        if p["veces"] > 1:
            acc["repetidas"] += 1
    return acc


def aplanar(n, ruta, salida):
    salida["/".join(ruta)] = {c: n[c] for c in CAMPOS}
    for h in n["hijos"]:
        aplanar(h, ruta + [h["uuid"]], salida)
    return salida


# ---------------- casos ----------------
# (criatura, objetivo, nivel raiz, adn raiz, creada raiz, contar_subida, inventario)
# `creada raiz = None` significa "no mandamos el campo": tiene que deducirlo.
CASOS = [
    # Alankydactylus: el arbol que se comparo contra paleo.gg
    ("alankydactylus", 30, 26, 0, True, False, {}),
    ("alankydactylus", 30, 26, 0, True, True, {}),
    ("alankydactylus", 30, 0, 0, False, True, {}),
    ("alankydactylus", 30, 0, 0, False, True,
     {"dreadactylus": {"nivel": 15, "adn": 900, "creado": True}}),
    # Raiz sin crear pero con ADN de sobra para crear
    ("indoraptor", 35, 0, 5000, False, True, {}),
    # Raiz creada y con un ingrediente a medias
    ("indoraptor", 35, 21, 100000, True, True,
     {"velociraptor": {"nivel": 20, "adn": 50000, "creado": True}}),
    ("indoraptor", 30, 21, 0, True, True,
     {"velociraptor": {"nivel": 20, "adn": 50000, "creado": True},
      "indominus_rex": {"nivel": 0, "adn": 1200, "creado": False}}),
    # Ingrediente que ya cumple de sobra: no debe generar rama
    ("trykosaurus", 30, 26, 0, True, True,
     {"tyrannosaurus_rex": {"nivel": 20, "adn": 999999, "creado": True}}),
    # Omega (escalera distinta)
    ("93_classic_t_rex", 35, 0, 0, False, True, {}),
    ("93_classic_t_rex", 35, 20, 3000, True, True, {}),
    ("93_classic_t_rex", 30, 0, 250, False, True, {}),
    # Cadenas largas y rarezas bajas
    ("ankylocodon", 30, 0, 0, False, True, {}),
    ("paralidactylus", 35, 0, 0, False, False, {}),
    ("rajadorixis", 30, 10, 20000, True, True, {}),
    # Dato heredado sin el campo `creado`
    ("diplotator", 30, 15, 4000, None, True,
     {"diplocaulus": {"nivel": 15, "adn": 100}}),
]


def clave_caso(u, obj, niv, adn, creado, cuenta):
    c = "none" if creado is None else str(creado).lower()
    return "%s|%d|%d|%d|%s|%s" % (u, obj, niv, adn, c, str(cuenta).lower())


def main():
    html = open(HTML, encoding="utf-8").read()
    datos_txt, motor_txt = extraer(html)
    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]

    for caso in CASOS:
        if caso[0] not in cri:
            print("FALLO: la criatura %r no esta en el dataset" % caso[0])
            return 1

    esperado = {}
    for u, obj, niv, adn, creado, cuenta, inv in CASOS:
        invs = {k: dict(v) for k, v in inv.items()}
        raiz = {"nivel": niv, "adn": adn}
        if creado is not None:
            raiz["creado"] = creado
        invs[u] = raiz
        t = plan(cri, invs, u, obj, 0, set(), True, cuenta)
        esperado[clave_caso(u, obj, niv, adn, creado, cuenta)] = {
            "nodos": aplanar(t, [u], {}), "tot": totales(t)}

    # ---- arnes de Node ----
    arnes = """
const fs = require("fs");
const datos = %s;
const M = datos.modelo, C = datos.criaturas;
%s
function aplanar(n, ruta, out){
  out[ruta.join("/")] = {rareza:n.rareza, desde:n.desde, objetivo:n.objetivo,
    adnSubir:n.adnSubir, adnNec:n.adnNec, monNec:n.monNec, deficit:n.deficit,
    fusiones:n.fusiones, monFus:n.monFus, nivelIng:n.nivelIng, esHoja:n.esHoja,
    creado:n.creado, maxNivel:n.max.nivel};
  n.hijos.forEach(h => aplanar(h, ruta.concat([h.uuid]), out));
  return out;
}
const casos = %s;
const salida = {};
for (const caso of casos){
  const u = caso[0], obj = caso[1], niv = caso[2], adn = caso[3],
        creado = caso[4], cuenta = caso[5], inv = caso[6];
  INV = JSON.parse(JSON.stringify(inv));
  const raiz = {nivel:niv, adn:adn};
  if (creado !== null) raiz.creado = creado;
  INV[u] = raiz;
  const t = plan(u, obj, 0, new Set(), true, cuenta);
  const ck = (creado === null ? "none" : String(creado));
  salida[u + "|" + obj + "|" + niv + "|" + adn + "|" + ck + "|" + String(cuenta)] =
    {nodos: aplanar(t, [u], {}), tot: totales(t)};
}
process.stdout.write(JSON.stringify(salida));
""" % (datos_txt, motor_txt, json.dumps(CASOS))

    ruta_js = "/tmp/jwa_arnes_arbol.js"
    open(ruta_js, "w", encoding="utf-8").write(arnes)
    res = subprocess.run(["node", ruta_js], capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        print("FALLO: el motor del arbol no se ejecuto en Node.")
        print(res.stderr[:3000])
        return 1
    obtenido = json.loads(res.stdout)

    fallos = []
    nodos_total = 0
    for clave, esp in esperado.items():
        obt = obtenido.get(clave)
        if obt is None:
            fallos.append((clave, "sin resultado"))
            continue
        en, on = esp["nodos"], obt["nodos"]
        if set(en) != set(on):
            fallos.append((clave, "nodos distintos: solo-Python=%s solo-JS=%s"
                           % (sorted(set(en) - set(on))[:4],
                              sorted(set(on) - set(en))[:4])))
        for ruta in sorted(set(en) & set(on)):
            nodos_total += 1
            for campo in CAMPOS:
                if en[ruta][campo] != on[ruta][campo]:
                    fallos.append((clave + " @ " + ruta,
                                   "%s: JS=%r Python=%r"
                                   % (campo, on[ruta][campo], en[ruta][campo])))
        for campo in ("adn", "mon", "fus", "monFus", "hojas", "recolectar", "nodos",
                      "repetidas", "adnNec", "tengo"):
            if esp["tot"][campo] != obt["tot"][campo]:
                fallos.append((clave, "total %s: JS=%r Python=%r"
                               % (campo, obt["tot"][campo], esp["tot"][campo])))
        # y la criatura por criatura, que es lo que agrega el informe
        if esp["tot"]["porUuid"] != obt["tot"]["porUuid"]:
            ej = []
            for k in sorted(set(esp["tot"]["porUuid"]) | set(obt["tot"]["porUuid"])):
                a = esp["tot"]["porUuid"].get(k)
                b = obt["tot"]["porUuid"].get(k)
                if a != b:
                    ej.append("%s: JS=%r Python=%r" % (k, b, a))
            fallos.append((clave, "por criatura: " + " | ".join(ej[:3])))

    print("Arboles: %d casos, %d nodos comparados (%d campos por nodo)."
          % (len(CASOS), nodos_total, len(CAMPOS)))
    print()
    if fallos:
        print("DISCREPANCIAS: %d" % len(fallos))
        for clave, det in fallos[:30]:
            print("  %-46s %s" % (clave, det))
        print()
        print("RESULTADO: FALLO")
        return 1
    print("RESULTADO: %d nodos y %d totales identicos entre el arbol del HTML "
          "y el espejo Python." % (nodos_total, len(CASOS)))
    print()
    # Se dice en voz alta para que nadie lea este verde como una prueba de que
    # el resultado es CORRECTO. Este verificador compara el HTML contra un
    # espejo escrito desde la misma lectura del problema: si las dos partes
    # entienden mal lo mismo, coinciden y las dos se equivocan. Paso con el
    # interruptor de «subir los ingredientes»: `totales` sumaba la escalera de
    # todas las criaturas pasara lo que pasara, y el espejo hacia lo mismo, asi
    # que los 15 totales coincidian siendo falsos. Lo que se comprueba aqui es
    # que las dos implementaciones NO se han separado, no que sean correctas.
    print("Alcance: esto comprueba que el HTML y el espejo NO se han separado, no")
    print("que sean correctos. Un malentendido comun a los dos pasa en verde.")
    print("El comportamiento se juzga en probar_estres.py, contra la pagina real.")
    print()
    print("Muestra (criterio paleo.gg, Alankydactylus 26->30):")
    for ruta, v in sorted(esperado["alankydactylus|30|26|0|true|false"]["nodos"].items()):
        print("  %-52s deficit=%-8s fus=%-6s" % (ruta, v["deficit"], v["fusiones"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
