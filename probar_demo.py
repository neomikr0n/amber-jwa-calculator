#!/usr/bin/env python3
"""
The DEMO, opened in a real browser: one file, no `img/` folder next to it.

`build_demo.py` packs the delivered artefact, the creature photos, the interface
icons and a saved file into a single HTML. This opens that file and demands what
the demo promises, because a demo that is broken is worse than no demo: it is the
one that gets shown to somebody.

What it checks
--------------
1. **It is not stale.** The demo carries the sha256 of the artefact it was packed
   from; it is recomputed here. Touching the template, rebuilding the artefact and
   forgetting the demo turns this red instead of showing yesterday's numbers.
2. **Nothing comes from outside.** Every `<img>` in the document has a `data:` URI
   and the creature card's portrait really loaded (`naturalWidth > 0`): the whole
   point of a single file is that it does not need the folder.
3. **The creatures are inside**: 25 in the inventory, 4 in «My Creatures», every
   one of them a creature of the dinodex.
4. **The screen it promises**: Fukuitops, level 34, with the report showing work
   to do (not a row of zeros).
5. **The look**: Spanish and Amber-OLED.

It needs a demo built from `.privado/`, which is not published: on a fresh clone
`amber-demo.html` does not exist. Then this does not return a verdict, it says so
and stops — it is NOT counted as green.

    python3 probar_demo.py     -> 0 if everything matches, 1 if not
"""
import hashlib
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from informe_browser import arrancar, comprobar_scripts, veredicto

DEMO = os.path.join(RAIZ, "amber-demo.html")
ARTEFACTO = os.path.join(RAIZ, "index.html")
DIR = "/tmp/jwa-demo"
PERFIL = os.path.join(DIR, "perfil")

INVENTARIO = 25
MIOS = 4
CRIATURA = "fukuitops"
NIVEL = 34

if not os.path.exists(DEMO):
    print("!! there is no amber-demo.html: it is built from .privado/, which is not")
    print("   published, so on a fresh clone this test is NOT judgeable.")
    print("   python3 build.py && python3 build_demo.py")
    raise SystemExit(2)

# ---------------------------------------------------------------- 1) staleness
fuente = open(DEMO, encoding="utf-8").read()
m = re.search(r"<!-- amber-demo: empaquetado de (\S+) sha256=([0-9a-f]{64}) el (\S+) · "
              r"(\d+) criaturas · (\d+) imágenes -->", fuente)
fresco = None
if not m:
    print("FAIL the demo does not carry its packing mark: rebuild it with build_demo.py")
elif m.group(1) != os.path.basename(ARTEFACTO):
    print("FAIL the demo was packed from %s, not from %s" % (m.group(1), os.path.basename(ARTEFACTO)))
else:
    real = hashlib.sha256(open(ARTEFACTO, "rb").read()).hexdigest()
    fresco = (m.group(2) == real)
    print("%s the demo was packed from the CURRENT artefact (%s, %s)"
          % ("OK   " if fresco else "FAIL ", m.group(2)[:16], m.group(3)))
    print("OK    and it says how much it carries: %s creatures, %s images"
          % (m.group(4), m.group(5)))

# ---------------------------------------------------------------- 2..5) browser
DIAG = """
<pre id="__diag" style="display:none"></pre>
<script>
window.addEventListener("load", function(){
  var RES = [], FALLOS = 0;
  function ok(n, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + n + ": " +
    (d === undefined ? "" : d)); }
  try {
    var imgs = Array.prototype.slice.call(document.querySelectorAll("img"));
    var fuera = imgs.filter(function(i){
      return (i.getAttribute("src") || "").indexOf("data:") !== 0; });
    /* A broken image is one the browser FINISHED with and has no width. A
       `loading="lazy"` one that is still below the fold has not finished, and
       counting it would be a false alarm: it was, in the first version. */
    var rotas = imgs.filter(function(i){
      return i.complete && i.naturalWidth === 0; });
    var cargadas = imgs.filter(function(i){ return i.naturalWidth > 0; });
    ok("every image in the page is inlined and none is broken",
       fuera.length === 0 && rotas.length === 0,
       imgs.length + " imágenes · fuera=" + fuera.length + " rotas=" + rotas.length +
       " cargadas=" + cargadas.length);
    var grande = document.querySelector("#elegida .grande");
    ok("the creature card shows its portrait",
       !!grande && grande.naturalWidth > 0,
       grande ? (grande.getAttribute("src") || "").slice(0, 24) + "… " + grande.naturalWidth + "px"
              : "no portrait");
    var uuids = Object.keys(INV), lista = MIS || [];
    ok("the saved creatures are inside",
       uuids.length === __INV__ && lista.length === __MIOS__ &&
       uuids.every(function(u){ return !!C[u]; }) && lista.every(function(u){ return !!C[u]; }),
       uuids.length + " en el inventario, " + lista.length + " en «Mis criaturas»");
    ok("it opens on the promised creature and level",
       elegido === __CRIATURA__ && invDe(elegido).nivel === __NIVEL__,
       "elegido=" + elegido + " nivel=" + invDe(elegido).nivel);
    var cifras = document.querySelectorAll("#resultado .cifra .v");
    var texto = Array.prototype.map.call(cifras, function(c){ return c.textContent; }).join(" ");
    ok("the report shows work to do, not a row of zeros",
       cifras.length > 0 && /[1-9]/.test(texto), texto.slice(0, 60));
    var raiz = document.documentElement;
    ok("it opens in Spanish and in Amber-OLED",
       raiz.getAttribute("data-tema") === "oled" &&
       getComputedStyle(raiz).getPropertyValue("--marca").trim().toLowerCase() === "#ff6d1f",
       "tema=" + raiz.getAttribute("data-tema") + " idioma=" + raiz.lang +
       " · pestañas=" + Array.prototype.map.call(document.querySelectorAll("nav button"),
         function(b){ return b.textContent.trim(); }).slice(0, 2).join("/"));
  } catch (e) {
    RES.push("FALLO the demo threw: " + e.message);
    FALLOS++;
  }
  RES.push(FALLOS ? "=== FALLOS: " + FALLOS + " ===" : "=== TODO OK ===");
  document.getElementById("__diag").textContent = RES.join("\\n");
  __ENTREGA__
});
</script>
"""

os.makedirs(PERFIL, exist_ok=True)
env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})

DIAG = (DIAG.replace("__INV__", str(INVENTARIO)).replace("__MIOS__", str(MIOS))
            .replace("__CRIATURA__", json.dumps(CRIATURA)).replace("__NIVEL__", str(NIVEL)))

srv = arrancar()
diag = DIAG.replace("__ENTREGA__", srv.js("__diag"))
pagina = fuente + diag
_ok, _msg = comprobar_scripts(pagina, "probar_demo.py")
if not _ok:
    raise SystemExit("!! " + _msg)
destino = os.path.join(DIR, "demo.html")
open(destino, "w", encoding="utf-8").write(pagina)
subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                "--window-size", "1400,900", "--screenshot", os.path.join(DIR, "demo.png"),
                "file://" + destino],
               env=env, capture_output=True, text=True, timeout=180)
codigo, lineas = veredicto(srv.texto())
srv.parar()
print(srv.texto().strip())
print("-" * 72)
for l in lineas:
    print(l)

if m is None or not fresco:
    codigo = 1
sys.exit(codigo)
