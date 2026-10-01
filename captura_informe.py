#!/usr/bin/env python3
"""Captures ONLY the tree report, to review it by eye.

It is the sixth frame that `captura.py` is missing: that one takes the five full
views, and the tree report is a piece of the "Calculadora" tab that in a
whole-page screenshot gets lost among the search box, the fields and the max
level block.

TWO THINGS THAT COST ME A BLANK SCREENSHOT, and that must be respected:

  1. **The report does NOT live in the "Arbol" tab.** `#informeArbol` is inside
     `#s-calc` (line ~460 of plantilla.html). Calling `irA("arbol")` hides
     exactly the section you want to look at, and the screenshot comes out black.
  2. **Hiding the siblings with `display:none` is not enough** if an ancestor
     carries the `on`/`off` class that governs the tabs: the report ends up
     inside something hidden and cannot be seen. It has to be moved to a clean
     body, with its `<style>`, which is what the script below does.

Usage:  python3 captura_informe.py             # the default theme, starting state
      python3 captura_informe.py boring      # the «Boring» theme
      python3 captura_informe.py --despues   # after pressing "Criar a todas"

The starting state carries an Ingredient CREATED BELOW the level the Fusion
requires (Tyrannosaurus Rex at 11, when the Fusion asks for 15): it is the case
n30 asked for on 25-sep-2026, and without it the screenshot would show nothing
new. With `--despues` the shortcut is pressed before taking the photo, and there
you see the result: all of them at the Fusion level and the shortcut gone.
"""
import os, sys, subprocess

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "index.html")
IMG = os.path.join(RAIZ, "img")

TEMA = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "yellow"
DESPUES = "--despues" in sys.argv
SUFIJO = "" if TEMA == "yellow" else "-" + TEMA
DIR = "/tmp/jwa-informe" + SUFIJO + ("-despues" if DESPUES else "")
PERFIL = os.path.join(DIR, "perfil")
SALIDA = os.path.join(DIR, "informe" + SUFIJO + ("-despues" if DESPUES else "") + ".png")

# Scenario: the root created at 25 and the THREE Ingredients not created, which
# is what is needed for the "criar" buttons and the "Criar a todas" shortcut to
# show. The root level 25 is not casual: its minimum is 21, so the shortcut
# control is degenerate on purpose (see `probar_estres.py`, section 14).
GUION = r"""
<script>
(function(){
  INV = {}; MIS = []; guardar(); ponerTema("__TEMA__");
  elegir("indoraptor");
  function poner(id, v){ var e = document.getElementById(id); e.focus(); e.value = v;
    e.dispatchEvent(new Event("input", {bubbles:true})); }
  poner("nivelAct", "25");
  poner("adnTengo", "1000");
  document.getElementById("nivelObj").value = 30;
  document.getElementById("nivelObj").dispatchEvent(new Event("input", {bubbles:true}));
  if (typeof fijar === "function"){ fijar("velociraptor", "adn", 30000); }

  /* The case that changed: an Ingredient created, but BELOW the level the
     Fusion requires. T-Rex is born at 11 and the Indominus Rex Fusion asks for
     it at 15, so the row shows "11 → 15" and "Criar a todas" has to raise it. */
  if (typeof fijar === "function"){ fijar("tyrannosaurus_rex", "nivel", 11); }
  refrescar();

  /* With --despues the shortcut is pressed BEFORE isolating the report: the
     click repaints, and what is photographed is the result. */
  if (__DESPUES__){
    var at = document.querySelector('#informeArbol [data-criar-todas]');
    if (at) at.click();
  }

  /* Isolate the report into a clean body, with its style sheets. */
  var inf = document.getElementById("informeArbol");
  var hojas = Array.prototype.slice.call(document.querySelectorAll("style"));
  var copia = inf.cloneNode(true);
  document.body.innerHTML = "";
  hojas.forEach(function(s){ document.body.appendChild(s); });
  document.body.appendChild(copia);
  /* The background comes from the theme the page is wearing, not from a
     hardcoded hex: with the amber default, the old slate grey left a band that
     belonged to no theme. The variable is the source of truth. */
  document.body.style.background =
    getComputedStyle(document.documentElement).getPropertyValue("--bg").trim() || "#000000";
  document.body.style.margin = "0";
  document.body.style.padding = "16px";
  document.body.style.width = "1080px";
})();
</script>
""".replace("__TEMA__", TEMA).replace("__DESPUES__", "true" if DESPUES else "false")

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)
enlace = os.path.join(DIR, "img")
if not os.path.exists(enlace):
    os.symlink(IMG, enlace)

ruta = os.path.join(DIR, "informe.html")
open(ruta, "w", encoding="utf-8").write(open(HTML, encoding="utf-8").read() + GUION)

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                "--window-size", "1120,1250", "--screenshot", SALIDA, "file://%s" % ruta],
               env=env, capture_output=True, text=True, timeout=180)
print("informe (%s) -> %s %s" % (TEMA, SALIDA,
      os.path.getsize(SALIDA) if os.path.exists(SALIDA) else "NO"))
