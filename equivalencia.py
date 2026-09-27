#!/usr/bin/env python3
"""
Equivalencia: los numeros que calcula el HTML (JS) deben ser IDENTICOS a los que
calcula modelo.py (Python), criatura por criatura.

Por que existe, teniendo verificar_motor.py
-------------------------------------------
`verificar_motor.py` SACA el motor del HTML y lo corre en Node: comprueba las
funciones puras contra el modelo. Esta prueba hace lo contrario: deja el motor
DENTRO de la pagina y llama a `costeADN` / `costeMon` / `nFus` en el navegador,
que es el camino que recorre el usuario. Si alguien cambia como la pagina
entrega los datos (no lo que calcula), esta es la que se entera.

Como se juzga
-------------
El navegador pinta su salida en un <pre> y la entrega con un XHR SINCRONO al
servidor local de `informe_browser.py`; la comparacion la hace Python.

Antes esta prueba NO comparaba nada: volcaba su salida a un PNG, imprimia los
valores esperados por stdout y ahi lo dejaba. Siempre salia con codigo 0, asi
que no podia fallar. Ahora cada fila es un OK o un FALLO y el codigo de salida
es 1 si algo discrepa, 2 si el navegador no llego a entregar el informe.
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

# criaturas de prueba: mezcla de rarezas y de tipos
PRUEBA = ["indoraptor", "trykosaurus", "paralidactylus", "aliorasuchus",
          "koolatrodon", "arsionosaurus", "indominus_rex", "acrocanthops",
          "93_classic_t_rex", "rajadorixis", "ankylocodon", "diplotator"]

cri = json.load(open(os.path.join(RAIZ, "data", "jwa-3.22.json")))["criaturas"]


# ---------------- referencia en Python ----------------
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

# ---------------- prueba en el navegador ----------------
DIAG = """
<script>
/* En `load`, no al parsear: el motor de la pagina se monta en su propio manejador
   de `load`, y este script va despues, asi que para cuando corre ya existen C,
   costeADN y compania. Al parsear todavia no. */
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
os.makedirs(PERFIL, exist_ok=True)     # Firefox NO crea el perfil: sin esto muere con
                                       # "Could not find profile folder" y no hay captura

# `img/` al lado: la pagina pide las fotos y sin el directorio salen errores de
# consola que no hacen falta para juzgar esto, pero ensucian el diagnostico.
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
html = open(os.path.join(RAIZ, "amber-jwa-3.22.html"), encoding="utf-8").read()
PIN = ('<script>window.__lang = "es";'
       'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
if "<head>" not in html:
    raise SystemExit("no encuentro <head> para fijar el idioma")
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

# ---------------- comparacion ----------------
lineas, fallos = [], []
vistas = set()
for l in informe.splitlines():
    l = l.strip()
    if not l:
        continue
    partes = l.split("|")
    if len(partes) < 6:
        fallos.append(l)
        lineas.append("FALLO fila mal formada: %r" % l)
        continue
    u, h, adn, mon, f, monf = partes[0], partes[1], partes[2], partes[3], partes[4], partes[5]
    clave = "%s|%s" % (u, h)
    vistas.add(clave)
    esp = ESPERADO.get(clave)
    if esp is None:
        fallos.append(clave)
        lineas.append("FALLO %s: la pagina devolvio una criatura que no se pidio" % clave)
        continue
    try:
        got = (int(adn), int(mon), int(f), int(monf))
    except ValueError:
        fallos.append(clave)
        lineas.append("FALLO %s: no son numeros -> %s" % (clave, l))
        continue
    if got == esp:
        lineas.append("OK   %-22s nivel %-2s  ADN %-10d monedas %-10d fusiones %-6d mon.fus %d"
                      % (u, h, got[0], got[1], got[2], got[3]))
    else:
        fallos.append(clave)
        det = ["ADN", "monedas", "fusiones", "mon.fus"]
        cual = ", ".join("%s %d != %d" % (det[i], got[i], esp[i])
                         for i in range(4) if got[i] != esp[i])
        lineas.append("FALLO %-22s nivel %-2s  %s" % (u, h, cual))

faltan = sorted(set(ESPERADO) - vistas)
for c in faltan:
    fallos.append(c)
    lineas.append("FALLO %s: la pagina no devolvio esta fila" % c)

for l in lineas:
    print(l)
print()
if fallos:
    print("RESULTADO: %d FALLOS de %d filas." % (len(fallos), len(ESPERADO)))
    raise SystemExit(1)
print("RESULTADO: %d/%d filas identicas entre el motor del HTML (en el navegador) y modelo.py."
      % (len(ESPERADO), len(ESPERADO)))
