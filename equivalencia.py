#!/usr/bin/env python3
"""
Equivalence: the numbers the HTML (JS) computes must be IDENTICAL to those
computed by modelo.py (Python), creature by creature.

Why it exists, given verificar_motor.py
---------------------------------------
`verificar_motor.py` TAKES the engine out of the HTML and runs it in Node: it
checks the pure functions against the model. This test does the opposite: it
leaves the engine INSIDE the page and calls `costeADN` / `costeMon` / `nFus` in
the browser, which is the path the user takes. If someone changes how the page
delivers the data (not what it computes), this is the one that finds out.

How it is judged
----------------
The browser paints its output into a <pre> and delivers it with a SYNCHRONOUS
XHR to the local server of `informe_browser.py`; the comparison is done by
Python.

Before, this test compared NOTHING: it dumped its output to a PNG, printed the
expected values to stdout and left it there. It always exited with code 0, so
it could not fail. Now every row is an OK or a FALLO and the exit code is 1 if
anything disagrees, 2 if the browser never delivered the report.
"""
import json, math, os, shutil, subprocess, sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from modelo import (ADN_31_35, ADN_POR_FUSION_MEDIA, COINR, COIN_31_35,
                    CREACION, L, MIN_LV, MONEDAS_FUSION, OMEGA_31_35, OMEGA_COINR,
                    OMEGA_L, TOPES_ADN)
from informe_browser import arrancar, veredicto

DIR = "/tmp/jwa-test"
FUERA = os.path.join(DIR, "eq.html")
SHOT = os.path.join(DIR, "eq.png")
PERFIL = os.path.join(DIR, "perfil3")

# test creatures: a mix of rarities and types
PRUEBA = ["indoraptor", "trykosaurus", "paralidactylus", "aliorasuchus",
          "koolatrodon", "arsionosaurus", "indominus_rex", "acrocanthops",
          "93_classic_t_rex", "rajadorixis", "ankylocodon", "diplotator"]

cri = json.load(open(os.path.join(RAIZ, "data", "jwa-3.23.json")))["criaturas"]


# ---------------- reference in Python ----------------
def ref(u, desde, hasta):
    x = cri[u]
    r = x["rareza"]
    if r == "omega":
        m = 1
        adn = 0
        if desde < 1:
            adn += OMEGA_L[0]
        for n in range(max(desde, 1) + 1, hasta + 1):
            adn += OMEGA_L[n - 1] if n <= 30 else OMEGA_31_35[n - 31]
        mon = 0
        for n in range(max(desde, m) + 1, min(hasta, 30) + 1):
            mon += OMEGA_COINR[n - 1]
        if hasta > 30:
            mon += (hasta - max(max(desde, m), 30)) * 400000
        f = math.ceil(adn / ADN_POR_FUSION_MEDIA) if adn > 0 else 0
        return adn, mon, f, 0
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
    return adn, mon, f, monf


ESPERADO = {}
for u in PRUEBA:
    for hasta in (30, 35):
        ESPERADO["%s|%d" % (u, hasta)] = ref(u, 0, hasta)

# ---------------- test in the browser ----------------
DIAG = """
<script>
/* On `load`, not while parsing: the page engine is set up in its own `load`
   handler, and this script goes after it, so by the time it runs C, costeADN
   and company already exist. While parsing they do not. */
window.addEventListener("load", function(){
  var us = __US__, hs = [30, 35], out = [];
  for (var i=0;i<us.length;i++){
    for (var j=0;j<hs.length;j++){
      var u = us[i], h = hs[j];
      try {
        var c = C[u], r = c[1], m = minLv(r);
        var adn = costeADN(r, 0, h, true);
        var mon = costeMon(r, 0, h);
        var f = nFus(adn);
        var monf = c[5].length ? f * (M.monedasFusion[r]||0) : 0;
        out.push(u + "|" + h + "|" + adn + "|" + mon + "|" + f + "|" + monf);
      } catch(e){ out.push(u + "|" + h + "|ERROR|" + e.message); }
    }
  }
  var d = document.createElement("pre");
  d.id = "__eq";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:16px/1.5 monospace;padding:12px;margin:0;overflow:auto;white-space:pre";
  d.textContent = out.join("\\n");
  document.body.appendChild(d);
__ENTREGA__
});
</script>
"""

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)     # Firefox does NOT create the profile: without this it dies with
                                       # "Could not find profile folder" and there is no screenshot

# `img/` alongside: the page asks for the photos and without the directory you
# get console errors that are not needed to judge this, but they clutter the
# diagnostic output.
en = os.path.join(DIR, "img"); IMG = os.path.join(RAIZ, "img")
if os.path.islink(en):
    if os.readlink(en) != IMG:
        os.unlink(en)
if not os.path.exists(en):
    os.symlink(IMG, en)

srv = arrancar()
DIAG = DIAG.replace("__US__", json.dumps(PRUEBA)).replace("__ENTREGA__", srv.js("__eq"))

# The page is loaded from a copy, so the language pin goes here. It has to be
# inside the <head>: that is where the app resolves the language, and the
# injected value beats whatever a previous run stored.
html = open(os.path.join(RAIZ, "index.html"), encoding="utf-8").read()
PIN = ('<script>window.__lang = "es";'
       'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
if "<head>" not in html:
    raise SystemExit("cannot find <head> to pin the language")
html = html.replace("<head>", "<head>\n" + PIN, 1)
open(FUERA, "w", encoding="utf-8").write(html + DIAG)

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                "--window-size", "1200,900", "--screenshot", SHOT, "file://" + FUERA],
               env=env, capture_output=True, text=True, timeout=180)
srv.parar()

informe = srv.texto().strip()
if not informe:
    print(veredicto("")[1][0])
    raise SystemExit(2)

# ---------------- comparison ----------------
lineas, fallos = [], []
vistas = set()
for l in informe.splitlines():
    l = l.strip()
    if not l:
        continue
    partes = l.split("|")
    if len(partes) < 6:
        fallos.append(l)
        lineas.append("FALLO malformed row: %r" % l)
        continue
    u, h, adn, mon, f, monf = partes[0], partes[1], partes[2], partes[3], partes[4], partes[5]
    clave = "%s|%s" % (u, h)
    vistas.add(clave)
    esp = ESPERADO.get(clave)
    if esp is None:
        fallos.append(clave)
        lineas.append("FALLO %s: the page returned a creature that was not requested" % clave)
        continue
    try:
        got = (int(adn), int(mon), int(f), int(monf))
    except ValueError:
        fallos.append(clave)
        lineas.append("FALLO %s: they are not numbers -> %s" % (clave, l))
        continue
    if got == esp:
        lineas.append("OK   %-22s level %-2s  DNA %-10d Coins %-10d Fusions %-6d mon.fus %d"
                      % (u, h, got[0], got[1], got[2], got[3]))
    else:
        fallos.append(clave)
        det = ["DNA", "Coins", "Fusions", "mon.fus"]
        cual = ", ".join("%s %d != %d" % (det[i], got[i], esp[i])
                         for i in range(4) if got[i] != esp[i])
        lineas.append("FALLO %-22s level %-2s  %s" % (u, h, cual))

faltan = sorted(set(ESPERADO) - vistas)
for c in faltan:
    fallos.append(c)
    lineas.append("FALLO %s: the page did not return this row" % c)

for l in lineas:
    print(l)
print()
if fallos:
    print("RESULT: %d FALLOs out of %d rows." % (len(fallos), len(ESPERADO)))
    raise SystemExit(1)
print("RESULT: %d/%d rows identical between the HTML engine (in the browser) and modelo.py."
      % (len(ESPERADO), len(ESPERADO)))
