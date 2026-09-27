#!/usr/bin/env python3
"""
Capturas de la interfaz real, sin informe encima. Sirve para revisar el aspecto
(que las imagenes se vean, que los campos no rompan la maquetacion, que el
bloque de nivel maximo quede donde debe).

Genera tres PNG en /tmp/jwa-ui/: calculadora, arbol y mios.

Uso:  python3 captura.py
"""
import os, re, shutil, subprocess

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "calculadora-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-ui"
PERFIL = os.path.join(DIR, "perfil")

# Escenario: Indoraptor a nivel 21 con 1.000 ADN, objetivo 30, y un ingrediente
# ya a medias. Asi se ven deficit, fusiones y el bloque de nivel maximo.
GUION = r"""
<script>
(function(){
  /* El perfil de Firefox es el MISMO entre capturas, asi que localStorage
     sobrevive de una a otra: sin este borrado, la segunda captura arranca con
     los puntos de mejora que dejo la primera y las cifras de la imagen no son
     las del escenario. Se vio en una captura: ponia +10 puntos donde el guion
     ponia 5. */
  INV = {}; MIS = []; guardar(); ponerTema("default");
  elegir("indoraptor");
  function poner(id, v){ var e = document.getElementById(id); e.focus(); e.value = v;
    e.dispatchEvent(new Event("input", {bubbles:true})); }
  poner("nivelAct", "21");
  poner("adnTengo", "1000");
  document.getElementById("nivelObj").value = 30;
  document.getElementById("nivelObj").dispatchEvent(new Event("input", {bubbles:true}));
  if (typeof fijar === "function"){
    fijar("indominus_rex", "nivel", 16);
    fijar("indominus_rex", "adn", 400);
    fijar("velociraptor", "nivel", 20);
    fijar("velociraptor", "adn", 30000);
  }
  pintarArbol(); pintarMios();
  // «Mis criaturas» ya NO se llena sola al tocar el arbol: hay que pulsar Guardar.
  // Sin esto la captura de esa pestaña sale con el mensaje de lista vacia, y de paso
  // asi se ve la regla nueva en la imagen: 5 criaturas en el arbol, 1 en la lista.
  document.getElementById("btnGuardar").click();
  pintarMios();
  // Y una SEGUNDA criatura con OTRO objetivo, para que la captura de «Mis
  // criaturas» ensene que el objetivo es de cada una y no uno compartido: dos
  // filas, dos cifras distintas. Luego se vuelve al Indoraptor, que es el que
  // tienen que ensenar las vistas de la calculadora y del arbol.
  // El boton se vuelve a buscar CADA VEZ: `refrescar` rehace el panel de la
  // calculadora, asi que la referencia de antes queda suelta en el aire y su
  // click() no hace nada (el primer guardado si entraba, el segundo no).
  elegir("tyrannosaurus_rex");
  poner("nivelAct", "20");
  poner("adnTengo", "1500");
  document.getElementById("nivelObj").value = 25;
  document.getElementById("nivelObj").dispatchEvent(new Event("input", {bubbles:true}));
  document.getElementById("btnGuardar").click();
  elegir("indoraptor");
  /* Puntos de mejora, para que la captura ensene el panel de stats con algo
     dentro y no con los ceros del arranque. El Indoraptor es Unica, asi que
     tiene pista de 5 pasos. */
  if (typeof cambiarMejora === "function"){
    cambiarMejora("indoraptor", "bVida", 1); cambiarMejora("indoraptor", "bVida", 1);
    cambiarMejora("indoraptor", "bDano", 1); cambiarMejora("indoraptor", "bDano", 1);
    cambiarMejora("indoraptor", "bVel", 1);
  }
  pintarArbol(); pintarMios(); pintarStats();
  var v = new URLSearchParams(location.search).get("v") || "calc";
  // Vista con el interruptor apagado: el informe tiene que decir que esta
  // siguiendo el criterio de paleo.gg, o la misma pantalla da dos respuestas
  // sin decir cual se esta viendo.
  if (v === "calc-paleo"){
    var chk = document.getElementById("chkSubida");
    chk.checked = false; chk.dispatchEvent(new Event("change", {bubbles:true}));
    v = "calc";
  }
  if (v === "yellow"){
    ponerTema("yellow");
    // La pista de mejoras solo existe a partir del nivel 30, asi que esta vista
    // sube la criatura a 30 antes de tocar los pasos: si no, los mandos salen
    // apagados y la captura no ensena lo que hace la pista.
    poner("nivelAct", "30");
    poner("adnTengo", "6000");
    cambiarMejora("indoraptor", "mejora", 1);
    cambiarMejora("indoraptor", "mejora", 1);
    cambiarMejora("indoraptor", "mejora", 1);
    pintarArbol(); pintarMios(); pintarStats();
    v = "calc";
  }
  document.querySelectorAll("nav button").forEach(function(b){
    if (b.dataset.t === v) b.click();
  });
  /* Vista «buscar»: el desplegable abierto con una fila resaltada por el
     TECLADO. Va la ULTIMA a proposito: pulsar una pestaña cierra la lista (el
     manejador de clic de fuera la cierra), asi que si esto fuera antes, la
     captura saldria con el desplegable ya cerrado. Y hay que pulsar la flecha
     de verdad: el resaltado no existe hasta que se pulsa, de modo que sin esto
     la imagen no podria demostrar que el teclado funciona. */
  if (v === "buscar"){
    var caja = document.getElementById("q");
    caja.value = "rex";
    caja.dispatchEvent(new Event("input", {bubbles:true}));
    for (var k = 0; k < 3; k++)
      caja.dispatchEvent(new KeyboardEvent("keydown", {key:"ArrowDown", bubbles:true, cancelable:true}));
  }
})();
</script>
"""


def preparar():
    os.makedirs(DIR, exist_ok=True)
    os.makedirs(PERFIL, exist_ok=True)
    enlace = os.path.join(DIR, "img")
    if os.path.islink(enlace):
        if os.readlink(enlace) != IMG:
            os.unlink(enlace)
    elif os.path.isdir(enlace):
        shutil.rmtree(enlace, ignore_errors=True)
    if not os.path.exists(enlace):
        os.symlink(IMG, enlace)


def capturar(vista, salida, alto):
    html = open(HTML, encoding="utf-8").read()
    # El guion va AL FINAL, despues del script principal: si se mete detras de
    # <body> se ejecuta antes de que existan `elegir` ni `pintarArbol`, y revienta.
    html = html + GUION
    ruta = os.path.join(DIR, "cap-%s.html" % vista)
    open(ruta, "w", encoding="utf-8").write(html)
    env = dict(os.environ)
    env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
                "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
    subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                    "--window-size", "1400,%d" % alto, "--screenshot", salida,
                    "file://%s?v=%s" % (ruta, vista)],
                   env=env, capture_output=True, text=True, timeout=180)
    return os.path.exists(salida)


preparar()
for vista, alto in (("calc", 1900), ("calc-paleo", 1500), ("yellow", 1900),
                    ("arbol", 2100), ("mios", 1000), ("buscar", 900)):
    p = os.path.join(DIR, "cap-%s.png" % vista)
    print(vista, "->", p, os.path.getsize(p) if capturar(vista, p, alto) else "NO")
