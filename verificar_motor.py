#!/usr/bin/env python3
"""
Verificacion fuerte: se extrae el MOTOR REAL del HTML entregable
(no una copia, no la plantilla) y se ejecuta en Node. Los numeros que
devuelve se comparan contra modelo.py, cifra por cifra.

A diferencia de equivalencia.py, aqui NO hay captura de pantalla ni lectura
visual: la comparacion es numerica y automatica. Si algo difiere, falla con
codigo de salida 1.

Uso:  python3 verificar_motor.py
"""
import json, math, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from modelo import (ADN_31_35, ADN_POR_FUSION_MEDIA, COINR, COIN_31_35,
                    CREACION, L, MIN_LV, MONEDAS_FUSION, OMEGA_31_35, OMEGA_COINR,
                    OMEGA_L, TOPES_ADN, nivel_maximo)

HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")
IMG = os.path.join(RAIZ, "img")


def bloque_llaves(texto, pos):
    """Devuelve el literal {...} que empieza en pos, contando llaves y
    respetando cadenas y escapes."""
    assert texto[pos] == "{", "no empieza en una llave"
    prof = 0
    i = pos
    en_cadena = False
    esc = False
    while i < len(texto):
        ch = texto[i]
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            en_cadena = not en_cadena
        elif not en_cadena:
            if ch == "{":
                prof += 1
            elif ch == "}":
                prof -= 1
                if prof == 0:
                    return texto[pos:i + 1]
        i += 1
    raise RuntimeError("llaves sin cerrar")


def bloque_cuerpo(texto, pos_llave):
    """Devuelve el bloque {...} completo de una funcion, contando llaves.
    Necesario porque las funciones NO terminan en '};' (terminan en '}')."""
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


def extraer_motor(html):
    """Saca del HTML entregable el payload de datos y el codigo del motor.

    El bloque va de `const minLv` hasta el cierre de `costePaso`: incluye el
    modelo de costes, el inventario (invDe/fijar) y el calculo de nivel maximo.
    """
    # 1) el payload const D = {...}
    m = re.search(r"const D\s*=\s*", html)
    if not m:
        raise RuntimeError("no encuentro 'const D =' en el HTML")
    datos_txt = bloque_llaves(html, html.index("{", m.end()))

    # 2) el codigo del motor
    i = html.index("const minLv")
    p = html.index("{", html.index("function costePaso", i))
    j = p + len(bloque_cuerpo(html, p))
    motor_txt = html[i:j]

    for nec in ("costeADN", "costeMon", "adnFus", "nFus", "nivelMaximo",
                "costePaso", "nivelCreacion", "costeCreacion"):
        if nec not in motor_txt:
            raise RuntimeError("el motor extraido no contiene " + nec)
    if motor_txt.count("{") != motor_txt.count("}"):
        raise RuntimeError("bloque desequilibrado: %d vs %d"
                           % (motor_txt.count("{"), motor_txt.count("}")))
    return datos_txt, motor_txt


def referencia(cri, u, desde, hasta):
    """Espejo en Python del motor. Se apoya en modelo.py, no en copias."""
    x = cri[u]
    r = x["rareza"]
    if r == "omega":
        adn = 0
        if desde < 1:
            adn += OMEGA_L[0]
        for n in range(max(desde, 1) + 1, hasta + 1):
            adn += OMEGA_L[n - 1] if n <= 30 else OMEGA_31_35[n - 31]
        mon = 0
        for n in range(max(desde, 1) + 1, min(hasta, 30) + 1):
            mon += OMEGA_COINR[n - 1]
        if hasta > 30:
            mon += (hasta - max(max(desde, 1), 30)) * 400000
    else:
        m = MIN_LV[r]
        a = max(desde, m)
        adn = sum(L[n - m] for n in range(a + 1, min(hasta, 30) + 1))
        if hasta > 30:
            adn += (hasta - max(a, 30)) * ADN_31_35[r]
        if desde < m:
            adn += CREACION[r]
        mon = sum(COINR[n - 1] for n in range(a + 1, min(hasta, 30) + 1))
        if hasta > 30:
            mon += (hasta - max(a, 30)) * COIN_31_35
    f = math.ceil(adn / ADN_POR_FUSION_MEDIA) if adn > 0 else 0
    monf = f * MONEDAS_FUSION[r] if x["ingredientes"] else 0
    return {"adn": adn, "mon": mon, "fus": f, "monFus": monf, "tope": TOPES_ADN[r]}


def comprobar_sintaxis(html):
    """node --check sobre TODOS los bloques <script> del HTML.

    Esto va aqui, y no en un comando suelto, por un motivo concreto: una vez se
    edito el HTML despues de pasar `node --check` y el error de sintaxis no se
    detecto hasta abrir la pagina en Firefox. Con el chequeo dentro del
    verificador, es imposible que se quede atras.
    """
    bloques = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    if not bloques:
        return ["no hay bloques <script>"]
    fallos = []
    for i, b in enumerate(bloques):
        if not b.strip():
            continue
        ruta = "/tmp/jwa_sintaxis_%d.js" % i
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(b)
        r = subprocess.run(["node", "--check", ruta], capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append("bloque %d (%d bytes): %s" % (i, len(b), r.stderr.strip()[:400]))
    return fallos


def main():
    html = open(HTML, encoding="utf-8").read()

    errores_sintaxis = comprobar_sintaxis(html)
    if errores_sintaxis:
        print("FALLO DE SINTAXIS en el HTML entregable:")
        for e in errores_sintaxis:
            print("  -", e)
        print()
        print("RESULTADO: FALLO")
        return 1
    print("Sintaxis: todos los bloques <script> pasan node --check.")

    datos_txt, motor_txt = extraer_motor(html)
    print("Motor extraido del HTML entregable: %d bytes de codigo." % len(motor_txt))

    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]

    # Casos: todas las rarezas + hibridos + omega + extremos de nivel.
    casos = []
    vistas = set()
    for u, x in cri.items():
        clave = (x["rareza"], bool(x["ingredientes"]))
        if clave not in vistas:
            vistas.add(clave)
            casos.append(u)
    for extra in ("indoraptor", "trykosaurus", "paralidactylus", "aliorasuchus",
                  "koolatrodon", "arsionosaurus", "indominus_rex", "acrocanthops",
                  "93_classic_t_rex", "rajadorixis", "ankylocodon", "diplotator",
                  "dreadactylus", "preondactylus", "alankyloceratops"):
        if extra in cri and extra not in casos:
            casos.append(extra)

    # Rangos: (desde, hasta). desde=0 significa "sin crear todavia".
    rangos = [(0, 30), (0, 35), (0, 1), (1, 30), (25, 35), (30, 35), (34, 35), (0, 26)]

    esperado = {}
    for u in casos:
        for d, h in rangos:
            esperado["%s|%d|%d" % (u, d, h)] = referencia(cri, u, d, h)

    # Casos de NIVEL MAXIMO: (desde, creado, adn disponible)
    # El adn incluye valores por debajo y por encima del coste de creacion, que
    # es donde se equivoca uno: ahi el resultado tiene que ser "nivel 0".
    adns = [0, 1, 49, 50, 99, 100, 150, 300, 500, 2500, 20000,
            500000, 5000000, 50000000]
    niveles = [0, 1, 5, 6, 10, 11, 15, 16, 20, 21, 25, 26, 30, 34, 35]
    casos_nm = []
    for u in casos:
        r = cri[u]["rareza"]
        m = 1 if r == "omega" else MIN_LV[r]
        for d in niveles:
            for creado in (False, True):
                if creado and d < m:
                    continue          # una criatura creada no esta por debajo de su nacimiento
                if not creado and d != 0:
                    continue          # sin crear, el nivel de partida es 0
                for adn in adns:
                    casos_nm.append([u, d, creado, adn])

    esperado_nm = {}
    for u, d, creado, adn in casos_nm:
        r = cri[u]["rareza"]
        n, gastado, sobra = nivel_maximo(r, d, adn, creado)
        esperado_nm["%s|%d|%s|%d" % (u, d, str(creado).lower(), adn)] = {
            "nivel": n, "gastado": gastado, "sobra": sobra}

    # ---- arnes de Node: ejecuta el motor real ----
    arnes = """
const fs = require("fs");
const datos = %s;
const M = datos.modelo, C = datos.criaturas;
%s
const casos = %s, rangos = %s, casosNm = %s;
const salida = {};
for (const u of casos) {
  for (const [d, h] of rangos) {
    const r = C[u][1];
    let o;
    try {
      const adn = costeADN(r, d, h, d < minLv(r));
      const mon = costeMon(r, d, h);
      const f   = nFus(adn);
      const monFus = C[u][5].length ? f * (M.monedasFusion[r] || 0) : 0;
      o = {adn: adn, mon: mon, fus: f, monFus: monFus, tope: M.topes[r]};
    } catch (e) { o = {error: e.message}; }
    salida[u + "|" + d + "|" + h] = o;
  }
}
const salidaNm = {};
for (const [u, d, creado, adn] of casosNm) {
  const r = C[u][1];
  let o;
  try {
    const x = nivelMaximo(r, d, adn, creado);
    o = {nivel: x.nivel, gastado: x.gastado, sobra: x.sobra};
  } catch (e) { o = {error: e.message}; }
  salidaNm[u + "|" + d + "|" + creado + "|" + adn] = o;
}
process.stdout.write(JSON.stringify({base: salida, nm: salidaNm}));
""" % (datos_txt, motor_txt, json.dumps(casos), json.dumps(rangos),
       json.dumps(casos_nm))

    arnes_js = os.path.join("/tmp", "jwa_arnes.js")
    open(arnes_js, "w", encoding="utf-8").write(arnes)

    res = subprocess.run(["node", arnes_js], capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        print("FALLO: el motor no se pudo ejecutar en Node.")
        print(res.stderr[:2000])
        return 1
    todo = json.loads(res.stdout)
    obtenido, obtenido_nm = todo["base"], todo["nm"]

    # ---- comparacion ----
    fallos = []
    for clave, esp in esperado.items():
        obt = obtenido.get(clave)
        if obt is None:
            fallos.append((clave, "sin resultado"))
            continue
        if "error" in obt:
            fallos.append((clave, "ERROR JS: " + obt["error"]))
            continue
        for campo in ("adn", "mon", "fus", "monFus", "tope"):
            if obt.get(campo) != esp[campo]:
                fallos.append((clave, "campo %s: JS=%r Python=%r" % (campo, obt.get(campo), esp[campo])))

    fallos_nm = []
    for clave, esp in esperado_nm.items():
        obt = obtenido_nm.get(clave)
        if obt is None:
            fallos_nm.append((clave, "sin resultado"))
            continue
        if "error" in obt:
            fallos_nm.append((clave, "ERROR JS: " + obt["error"]))
            continue
        for campo in ("nivel", "gastado", "sobra"):
            if obt.get(campo) != esp[campo]:
                fallos_nm.append((clave, "%s: JS=%r Python=%r" % (campo, obt.get(campo), esp[campo])))

    total = len(esperado) * 5
    total_nm = len(esperado_nm) * 3

    # ---------- los tamaños que el LEEME afirma ----------
    """Un numero escrito en el LEEME tambien envejece, y ese no lo miraba nadie.
    Decia «139 KB» para un HTML que ya pesaba 239; se corrigio a 244.842 bytes y
    en la vuelta siguiente ya eran 250. La regla del proyecto es que **si un
    numero importa, tiene que haber algo que lo vuelva a calcular**, asi que aqui
    se recalcula. Cuando esto falla, el propio fallo trae la cifra buena: se copia
    al LEEME y se acaba. (Y se comparan los BYTES, no los KB, porque el KB del
    LEEME va redondeado.)

    Ojo con el patron, y esto se midio en vez de suponerse. Buscar solo
    «**N bytes (M KB)**» NO sirve: eso no comprueba que la cifra este DECLARADA
    en algun sitio, comprueba que en el fichero hay alguna linea en negrita con
    esa forma. Y hay dos — la declaracion y, mas abajo, la narracion de la
    trampa, que cita el valor viejo «244.842 bytes (239 KB)». Medido contra el
    LEEME de verdad:

        caso                                   patron sin ancla   patron anclado
        declaracion duplicada con otra cifra   PASA               falla
        declaracion reescrita (frase ausente)  PASA               falla
        reescrita y narracion borrada          PASA               falla

    Es decir: el patron viejo daba por buenas cifras que podian estar dichas dos
    veces y en desacuerdo, o no estar dichas en ninguna parte. Por eso el patron
    lleva ahora el ancla «El HTML solo pesa», que es unica, y ademas se exige que
    sea UNA SOLA: si aparecen dos, el control falla en vez de elegir una en
    silencio. (Y se comparan los BYTES, no los KB, porque el KB va redondeado.)"""
    fallos_doc = []
    leeme_ruta = os.path.join(RAIZ, "LEEME.md")
    leeme = open(leeme_ruta, encoding="utf-8").read()
    real_html = os.path.getsize(HTML)
    ms = re.findall(r"El HTML solo pesa\s*\*\*([\d.]+) bytes \(([\d.]+) KB\)\*\*", leeme)
    if not ms:
        fallos_doc.append(("LEEME, tamaño del HTML",
                           "no encuentro «El HTML solo pesa **N bytes (M KB)**»; "
                           "el HTML pesa %d bytes" % real_html))
    elif len(ms) > 1:
        fallos_doc.append(("LEEME, tamaño del HTML",
                           "la declaracion aparece %d veces (%s); tiene que ser una sola"
                           % (len(ms), " / ".join(a for a, _ in ms))))
    else:
        dicho = int(ms[0][0].replace(".", ""))
        if dicho != real_html:
            fallos_doc.append(("LEEME, tamaño del HTML",
                               "dice %s bytes y son %d (%.0f KB)"
                               % (ms[0][0], real_html, real_html / 1024)))
    fotos = [f for f in os.listdir(IMG) if f.endswith(".webp")]
    mb_fotos = sum(os.path.getsize(os.path.join(IMG, f)) for f in fotos) / 1e6
    m2 = re.findall(r"las fotos son ([\d,]+) MB", leeme)
    if not m2:
        fallos_doc.append(("LEEME, tamaño de las fotos", "no encuentro «las fotos son N MB»"))
    elif len(m2) > 1:
        fallos_doc.append(("LEEME, tamaño de las fotos",
                           "la declaracion aparece %d veces (%s); tiene que ser una sola"
                           % (len(m2), " / ".join(m2))))
    elif abs(float(m2[0].replace(",", ".")) - mb_fotos) > 0.15:
        fallos_doc.append(("LEEME, tamaño de las fotos",
                           "dice %s MB y son %.1f MB en %d webp" % (m2[0], mb_fotos, len(fotos))))

    # ---------- el entregable tiene que ser lo que produce build.py ----------
    """El 25-sep aparecio en disco un HTML de 255.844 bytes que NO era el build:
    llevaba 133 atributos `data-page-node-id` inyectados por un editor. Quitandolos
    quedaba identico byte a byte al build limpio, o sea que el producto era el
    mismo, pero la cifra del LEEME se habia medido sobre el fichero contaminado.
    Comparar el tamaño no caza eso —el contaminado simplemente pesa mas—, asi que
    se compara el CONTENIDO: se construye a un temporal y se coteja. De paso caza
    el caso de editar la plantilla y olvidar reconstruir, que es la misma familia
    de fallo: entregar algo que no es lo que dice el codigo."""
    import contextlib
    import io
    import tempfile

    import build as _build
    with tempfile.TemporaryDirectory() as td:
        ruta_esperada = os.path.join(td, "esperado.html")
        destino_original = _build.DESTINO
        _build.DESTINO = ruta_esperada
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                _build.main()
        finally:
            _build.DESTINO = destino_original
        with open(ruta_esperada, encoding="utf-8") as f:
            esperado_html = f.read()
    with open(HTML, encoding="utf-8") as f:
        real_contenido = f.read()
    if real_contenido != esperado_html:
        sello = real_contenido.count("data-page-node-id")
        pista = (", con %d «data-page-node-id» de un editor" % sello) if sello else ""
        fallos_doc.append(("entregable",
                           "no es lo que produce build.py: %d bytes en disco frente a %d recien "
                           "construidos%s" % (len(real_contenido.encode()),
                                              len(esperado_html.encode()), pista)))

    print("Casos: %d criaturas x %d rangos = %d calculos, %d campos comparados."
          % (len(casos), len(rangos), len(esperado), total))
    print("Nivel maximo: %d combinaciones (criatura x nivel x creada x ADN), %d campos."
          % (len(esperado_nm), total_nm))
    print()
    if fallos or fallos_nm or fallos_doc:
        if fallos:
            print("DISCREPANCIAS en costes: %d" % len(fallos))
            for clave, det in fallos[:20]:
                print("  %-42s %s" % (clave, det))
        if fallos_nm:
            print("DISCREPANCIAS en nivel maximo: %d" % len(fallos_nm))
            for clave, det in fallos_nm[:20]:
                print("  %-42s %s" % (clave, det))
        if fallos_doc:
            print("EL LEEME Y EL ENTREGABLE, cosas que ya no cuadran: %d" % len(fallos_doc))
            for clave, det in fallos_doc:
                print("  %-42s %s" % (clave, det))
        print()
        print("RESULTADO: FALLO")
        return 1
    print("RESULTADO: %d/%d campos de coste y %d/%d campos de nivel maximo identicos "
          "entre el motor del HTML y modelo.py." % (total, total, total_nm, total_nm))
    print("El entregable es exactamente lo que produce build.py, y los tamaños que afirma el "
          "LEEME cuadran con los ficheros (%d bytes de HTML, %.1f MB de fotos)."
          % (real_html, mb_fotos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
