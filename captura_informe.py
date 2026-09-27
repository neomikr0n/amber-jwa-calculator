#!/usr/bin/env python3
"""Captura SOLO el informe del arbol, para revisarlo a ojo.

Es el sexto encuadre que le falta a `captura.py`: aquel saca las cinco vistas
completas, y el informe del arbol es una pieza de la pestana «Calculadora» que en
una captura de pagina entera se pierde entre el buscador, los campos y el bloque
de nivel maximo.

DOS COSAS QUE ME COSTARON UNA CAPTURA EN BLANCO, y que hay que respetar:

  1. **El informe NO vive en la pestana «Arbol».** `#informeArbol` esta dentro de
     `#s-calc` (linea ~460 de plantilla.html). Llamar a `irA("arbol")` esconde
     justo la seccion que se quiere mirar, y la captura sale negra.
  2. **Esconder los hermanos con `display:none` no basta** si un ancestro lleva la
     clase `on`/`off` que gobierna las pestanas: el informe queda dentro de algo
     oculto y no se ve. Hay que llevarselo a un body limpio, con sus `<style>`,
     que es lo que hace el guion de abajo.

Uso:  python3 captura_informe.py            # tema «default», estado de partida
      python3 captura_informe.py yellow     # tema «yellow»
      python3 captura_informe.py default --despues   # tras pulsar «Criar a todas»

El estado de partida lleva un ingrediente CREADO POR DEBAJO del nivel que exige
la fusion (Tyrannosaurus Rex a 11, cuando la fusion pide 15): es el caso que n30
pidio el 25-sep-2026, y sin el la captura no ensenaria nada nuevo. Con
`--despues` se pulsa el atajo antes de fotografiar, y ahi se ve el resultado:
todas al nivel de la fusion y el atajo desaparecido.
"""
import os, sys, subprocess

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "calculadora-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")

TEMA = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "default"
DESPUES = "--despues" in sys.argv
SUFIJO = "" if TEMA == "default" else "-" + TEMA
DIR = "/tmp/jwa-informe" + SUFIJO + ("-despues" if DESPUES else "")
PERFIL = os.path.join(DIR, "perfil")
SALIDA = os.path.join(DIR, "informe" + SUFIJO + ("-despues" if DESPUES else "") + ".png")

# Escenario: la raiz creada a 25 y los TRES ingredientes sin crear, que es lo que
# hace falta para que se vean los botones «criar» y el atajo «Criar a todas».
# El nivel 25 de la raiz no es casual: su minimo es 21, asi que el control del
# atajo es degenerado a proposito (ver `probar_estres.py`, seccion 14).
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

  /* El caso que cambio: un ingrediente creado, pero POR DEBAJO del nivel que
     exige la fusion. T-Rex nace a 11 y la fusion de Indominus Rex lo pide a 15,
     asi que la fila ensena «11 → 15» y «Criar a todas» tiene que subirlo. */
  if (typeof fijar === "function"){ fijar("tyrannosaurus_rex", "nivel", 11); }
  refrescar();

  /* Con --despues se pulsa el atajo ANTES de aislar el informe: el clic
     repinta, y lo que se fotografia es el resultado. */
  if (__DESPUES__){
    var at = document.querySelector('#informeArbol [data-criar-todas]');
    if (at) at.click();
  }

  /* Aislar el informe en un body limpio, con sus hojas de estilo. */
  var inf = document.getElementById("informeArbol");
  var hojas = Array.prototype.slice.call(document.querySelectorAll("style"));
  var copia = inf.cloneNode(true);
  document.body.innerHTML = "";
  hojas.forEach(function(s){ document.body.appendChild(s); });
  document.body.appendChild(copia);
  document.body.style.background = "#0d1117";
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
