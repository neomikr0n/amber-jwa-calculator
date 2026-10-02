#!/usr/bin/env python3
"""
Strong verification: the REAL engine is extracted from the deliverable HTML
(not a copy, not the template) and run in Node. The numbers it returns are
compared against modelo.py, figure by figure.

Unlike equivalencia.py, here there is NO screenshot and no visual reading:
the comparison is numeric and automatic. If anything differs, it fails with
exit code 1.

There is a second verdict, and it is the one that used to lie. The engine and
the deliverable are always judgeable — index.html, build.py and modelo.py are
all published — but the sizes the LEEME claims are not, because the LEEME lives
in `.privado/`, which is never published. Until 1-oct-2026 a clone got
`RESULT: FAIL` and a list of things «that no longer add up», which is exactly
what a real discrepancy prints. Now the two are separate: what does not add up
is exit 1, what cannot be read is exit 2 and says so.

Usage:  python3 verificar_motor.py
"""
import json, math, os, re, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
from modelo import (ADN_31_35, ADN_POR_FUSION_MEDIA, COINR, COIN_31_35,
                    CREACION, L, MIN_LV, MONEDAS_FUSION, OMEGA_31_35, OMEGA_COINR,
                    OMEGA_L, TOPES_ADN, nivel_maximo)
from rutas import DATOS, HTML

IMG = os.path.join(RAIZ, "img")


def bloque_llaves(texto, pos):
    """Returns the literal {...} that starts at pos, counting braces and
    respecting strings and escapes."""
    assert texto[pos] == "{", "it does not start with a brace"
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
    raise RuntimeError("unclosed braces")


def bloque_cuerpo(texto, pos_llave):
    """Returns the complete {...} block of a function, counting braces.
    Needed because functions do NOT end in '};' (they end in '}')."""
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
    raise RuntimeError("unclosed function body")


def extraer_motor(html):
    """Pulls the data payload and the engine code out of the deliverable HTML.

    The block goes from `const minLv` to the close of `costePaso`: it includes
    the cost model, the inventory (invDe/fijar) and the level-cap calculation.
    """
    # 1) the payload const D = {...}
    m = re.search(r"const D\s*=\s*", html)
    if not m:
        raise RuntimeError("cannot find 'const D =' in the HTML")
    datos_txt = bloque_llaves(html, html.index("{", m.end()))

    # 2) the engine code
    i = html.index("const minLv")
    p = html.index("{", html.index("function costePaso", i))
    j = p + len(bloque_cuerpo(html, p))
    motor_txt = html[i:j]

    for nec in ("costeADN", "costeMon", "adnFus", "nFus", "nivelMaximo",
                "costePaso", "nivelCreacion", "costeCreacion"):
        if nec not in motor_txt:
            raise RuntimeError("the extracted engine does not contain " + nec)
    if motor_txt.count("{") != motor_txt.count("}"):
        raise RuntimeError("unbalanced block: %d vs %d"
                           % (motor_txt.count("{"), motor_txt.count("}")))
    return datos_txt, motor_txt


def referencia(cri, u, desde, hasta):
    """Python mirror of the engine. It relies on modelo.py, not on copies."""
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
    """node --check over ALL the <script> blocks of the HTML.

    This goes here, and not in a one-off command, for a concrete reason: once
    the HTML was edited after passing `node --check` and the syntax error was
    not detected until opening the page in Firefox. With the check inside the
    verifier, it is impossible for it to fall behind.
    """
    bloques = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    if not bloques:
        return ["there are no <script> blocks"]
    fallos = []
    for i, b in enumerate(bloques):
        if not b.strip():
            continue
        ruta = "/tmp/jwa_sintaxis_%d.js" % i
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(b)
        r = subprocess.run(["node", "--check", ruta], capture_output=True, text=True)
        if r.returncode != 0:
            fallos.append("block %d (%d bytes): %s" % (i, len(b), r.stderr.strip()[:400]))
    return fallos


def main():
    html = open(HTML, encoding="utf-8").read()

    errores_sintaxis = comprobar_sintaxis(html)
    if errores_sintaxis:
        print("SYNTAX FAILURE in the deliverable HTML:")
        for e in errores_sintaxis:
            print("  -", e)
        print()
        print("RESULT: FAIL")
        return 1
    print("Syntax: all the <script> blocks pass node --check.")

    datos_txt, motor_txt = extraer_motor(html)
    print("Engine extracted from the deliverable HTML: %d bytes of code." % len(motor_txt))

    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]

    # Cases: all rarities + hybrids + omega + level extremes.
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

    # Ranges: (desde, hasta). desde=0 means "not created yet".
    rangos = [(0, 30), (0, 35), (0, 1), (1, 30), (25, 35), (30, 35), (34, 35), (0, 26)]

    esperado = {}
    for u in casos:
        for d, h in rangos:
            esperado["%s|%d|%d" % (u, d, h)] = referencia(cri, u, d, h)

    # LEVEL CAP cases: (desde, creado, available dna)
    # The dna includes values below and above the creation cost, which is
    # where one gets it wrong: there the result has to be "level 0".
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
                    continue          # a created creature is not below its birth
                if not creado and d != 0:
                    continue          # not created, the starting level is 0
                for adn in adns:
                    casos_nm.append([u, d, creado, adn])

    esperado_nm = {}
    for u, d, creado, adn in casos_nm:
        r = cri[u]["rareza"]
        n, gastado, sobra = nivel_maximo(r, d, adn, creado)
        esperado_nm["%s|%d|%s|%d" % (u, d, str(creado).lower(), adn)] = {
            "nivel": n, "gastado": gastado, "sobra": sobra}

    # ---- Node harness: runs the real engine ----
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
        print("FAIL: the engine could not run in Node.")
        print(res.stderr[:2000])
        return 1
    todo = json.loads(res.stdout)
    obtenido, obtenido_nm = todo["base"], todo["nm"]

    # ---- comparison ----
    fallos = []
    for clave, esp in esperado.items():
        obt = obtenido.get(clave)
        if obt is None:
            fallos.append((clave, "no result"))
            continue
        if "error" in obt:
            fallos.append((clave, "JS ERROR: " + obt["error"]))
            continue
        for campo in ("adn", "mon", "fus", "monFus", "tope"):
            if obt.get(campo) != esp[campo]:
                fallos.append((clave, "field %s: JS=%r Python=%r" % (campo, obt.get(campo), esp[campo])))

    fallos_nm = []
    for clave, esp in esperado_nm.items():
        obt = obtenido_nm.get(clave)
        if obt is None:
            fallos_nm.append((clave, "no result"))
            continue
        if "error" in obt:
            fallos_nm.append((clave, "JS ERROR: " + obt["error"]))
            continue
        for campo in ("nivel", "gastado", "sobra"):
            if obt.get(campo) != esp[campo]:
                fallos_nm.append((clave, "%s: JS=%r Python=%r" % (campo, obt.get(campo), esp[campo])))

    total = len(esperado) * 5
    total_nm = len(esperado_nm) * 3

    # ---------- the sizes the LEEME claims ----------
    """A number written in the LEEME also ages, and nobody was watching that one.
    It said «139 KB» for an HTML that already weighed 239; it was corrected to
    244,842 bytes and the next round it was already 250. The project rule is that
    **if a number matters, there has to be something that recomputes it**, so
    here it is recomputed. When this fails, the failure itself brings the right
    figure: copy it into the LEEME and done. (And the BYTES are compared, not the
    KB, because the LEEME's KB is rounded.)

    Watch out for the pattern, and this was measured instead of assumed.
    Searching only for «**N bytes (M KB)**» does NOT work: that does not check
    that the figure is DECLARED anywhere, it checks that the file has some bold
    line with that shape. And there are two — the declaration and, further down,
    the narration of the trap, which quotes the old value «244,842 bytes
    (239 KB)». Measured against the real LEEME:

        case                                   unanchored pattern  anchored pattern
        duplicate declaration with another figure   PASSES         fails
        rewritten declaration (phrase absent)       PASSES         fails
        rewritten and narration deleted             PASSES         fails

    That is to say: the old pattern accepted figures that could be stated twice
    and disagree, or not be stated anywhere at all. That is why the pattern now
    carries the anchor «El HTML solo pesa», which is unique, and it is also
    required to be a SINGLE one: if two appear, the check fails instead of
    silently choosing one. (And the BYTES are compared, not the KB, because the
    KB is rounded.)"""
    fallos_doc = []
    # What cannot be judged is kept apart from what does not add up, and the
    # difference is the whole point: both used to print as a list of things that
    # «no longer add up» followed by `RESULT: FAIL`, so a clone — where the
    # LEEME is simply not there — got a verdict that read like a real
    # discrepancy. The engine and the deliverable ARE judgeable on a clone,
    # because index.html, build.py and modelo.py are all published, so they keep
    # running and keep reporting; only the sizes the LEEME claims drop out.
    sin_leeme = []
    # The LEEME lives under .privado/ and is not published: it documents the
    # project for its author, including material about third parties that is
    # deliberately kept out of the repository and off the site. The size claims
    # it makes are still checked, which is why this reads it from there.
    leeme_ruta = os.path.join(RAIZ, ".privado", "LEEME.md")
    leeme = open(leeme_ruta, encoding="utf-8").read() if os.path.exists(leeme_ruta) else ""
    real_html = os.path.getsize(HTML)
    fotos = [f for f in os.listdir(IMG) if f.endswith(".webp")]
    mb_fotos = sum(os.path.getsize(os.path.join(IMG, f)) for f in fotos) / 1e6
    if not leeme:
        sin_leeme.append("LEEME, the two sizes it claims")
    else:
        ms = re.findall(r"El HTML solo pesa\s*\*\*([\d.]+) bytes \(([\d.]+) KB\)\*\*", leeme)
        if not ms:
            fallos_doc.append(("LEEME, HTML size",
                               "cannot find «El HTML solo pesa **N bytes (M KB)**»; "
                               "the HTML weighs %d bytes" % real_html))
        elif len(ms) > 1:
            fallos_doc.append(("LEEME, HTML size",
                               "the declaration appears %d times (%s); it has to be a single one"
                               % (len(ms), " / ".join(a for a, _ in ms))))
        else:
            dicho = int(ms[0][0].replace(".", ""))
            if dicho != real_html:
                fallos_doc.append(("LEEME, HTML size",
                                   "it says %s bytes and they are %d (%.0f KB)"
                                   % (ms[0][0], real_html, real_html / 1024)))
        m2 = re.findall(r"las fotos son ([\d,]+) MB", leeme)
        if not m2:
            fallos_doc.append(("LEEME, photo size", "cannot find «las fotos son N MB»"))
        elif len(m2) > 1:
            fallos_doc.append(("LEEME, photo size",
                               "the declaration appears %d times (%s); it has to be a single one"
                               % (len(m2), " / ".join(m2))))
        elif abs(float(m2[0].replace(",", ".")) - mb_fotos) > 0.15:
            fallos_doc.append(("LEEME, photo size",
                               "it says %s MB and they are %.1f MB in %d webp"
                               % (m2[0], mb_fotos, len(fotos))))

    # ---------- the deliverable has to be what build.py produces ----------
    """On 25-Sep an HTML of 255,844 bytes appeared on disk that was NOT the
    build: it carried 133 `data-page-node-id` attributes injected by an editor.
    Removing them left it byte-for-byte identical to the clean build, that is,
    the product was the same, but the LEEME figure had been measured on the
    contaminated file. Comparing the size does not catch that —the contaminated
    one simply weighs more—, so the CONTENT is compared: it is built to a
    temporary file and checked. Along the way it catches the case of editing the
    template and forgetting to rebuild, which is the same family of failure:
    delivering something that is not what the code says."""
    import contextlib
    import io
    import tempfile

    import build as _build
    with tempfile.TemporaryDirectory() as td:
        ruta_esperada = os.path.join(td, "esperado.html")
        destino_original = _build.HTML
        # The build has to land in the temporary directory. Pointing it at the
        # real file made `main()` overwrite the very file this check compares
        # against, so it compared something it had just repaired: it could not
        # fail, and it silently hid a stale or contaminated index.html on every
        # run. There is now a single output, so there is a single redirection —
        # and if a second output is ever added back, it has to be redirected
        # here too or this check goes blind again.
        _build.HTML = ruta_esperada
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                _build.main()
        finally:
            _build.HTML = destino_original
        with open(ruta_esperada, encoding="utf-8") as f:
            esperado_html = f.read()
    if not os.path.exists(HTML):
        fallos_doc.append(("deliverable",
                           "there is no index.html: nothing to open and nothing for the "
                           "site to serve"))
        real_contenido = ""
    else:
        with open(HTML, encoding="utf-8") as f:
            real_contenido = f.read()
    if real_contenido != esperado_html:
        sello = real_contenido.count("data-page-node-id")
        pista = (", with %d «data-page-node-id» from an editor" % sello) if sello else ""
        fallos_doc.append(("deliverable",
                           "it is not what build.py produces: %d bytes on disk against %d freshly "
                           "built%s" % (len(real_contenido.encode()),
                                        len(esperado_html.encode()), pista)))

    print("Cases: %d creatures x %d ranges = %d calculations, %d fields compared."
          % (len(casos), len(rangos), len(esperado), total))
    print("Level cap: %d combinations (creature x level x created x DNA), %d fields."
          % (len(esperado_nm), total_nm))
    print()
    if fallos or fallos_nm or fallos_doc:
        if fallos:
            print("DISCREPANCIES in costs: %d" % len(fallos))
            for clave, det in fallos[:20]:
                print("  %-42s %s" % (clave, det))
        if fallos_nm:
            print("DISCREPANCIES in level cap: %d" % len(fallos_nm))
            for clave, det in fallos_nm[:20]:
                print("  %-42s %s" % (clave, det))
        if fallos_doc:
            print("THE LEEME AND THE DELIVERABLE, things that no longer add up: %d" % len(fallos_doc))
            for clave, det in fallos_doc:
                print("  %-42s %s" % (clave, det))
        print()
        print("RESULT: FAIL")
        return 1
    if sin_leeme:
        print("RESULT: cannot judge — %s" % ", ".join(sin_leeme))
        print("        `.privado/LEEME.md` is never published, so on a clone it is not there.")
        print("        Everything else WAS judged and it agrees: the %d cost fields, the %d" % (total, total_nm))
        print("        level-cap fields and the deliverable itself. What is missing is only the")
        print("        two figures the LEEME states about this build. Exit 2, not a failure.")
        return 2
    print("RESULT: %d/%d cost fields and %d/%d level-cap fields identical "
          "between the HTML engine and modelo.py." % (total, total, total_nm, total_nm))
    print("index.html is exactly what build.py produces, and "
          "the sizes the LEEME claims match the files (%d bytes of HTML, %.1f MB "
          "of photos)." % (real_html, mb_fotos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
