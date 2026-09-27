#!/usr/bin/env python3
"""
Screenshots of the real interface, with no report on top. It is used to review
the look (that the images show up, that the fields do not break the layout, that
the max level block stays where it should).

Generates three PNGs in /tmp/jwa-ui/: calculadora, arbol and mios.

Usage:  python3 captura.py
"""
import os, re, shutil, subprocess

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-ui"
PERFIL = os.path.join(DIR, "perfil")

# Scenario: Indoraptor at level 21 with 1,000 DNA, target 30, and an Ingredient
# already half done. That way you see the deficit, the Fusions and the max level
# block.
GUION = r"""
<script>
(function(){
  /* The Firefox profile is the SAME across screenshots, so localStorage
     survives from one to the next: without this wipe, the second screenshot
     starts with the Stat Boost points the first one left behind and the figures
     in the image are not those of the scenario. It was seen in a screenshot: it
     showed +10 points where the script set 5. */
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
  // "Mis criaturas" NO LONGER fills itself in when you touch the tree: you have to
  // press Guardar. Without this the screenshot of that tab comes out with the empty
  // list message, and by the way that is how the new rule shows in the image:
  // 5 creatures in the tree, 1 in the list.
  document.getElementById("btnGuardar").click();
  pintarMios();
  // And a SECOND creature with ANOTHER target, so that the "Mis criaturas"
  // screenshot shows that the target belongs to each one and is not shared: two
  // rows, two different figures. Then it goes back to the Indoraptor, which is the
  // one the calculator and tree views have to show.
  // The button is looked up again EVERY TIME: `refrescar` rebuilds the calculator
  // panel, so the earlier reference is left dangling and its click() does nothing
  // (the first save did go in, the second did not).
  elegir("tyrannosaurus_rex");
  poner("nivelAct", "20");
  poner("adnTengo", "1500");
  document.getElementById("nivelObj").value = 25;
  document.getElementById("nivelObj").dispatchEvent(new Event("input", {bubbles:true}));
  document.getElementById("btnGuardar").click();
  elegir("indoraptor");
  /* Stat Boost points, so that the screenshot shows the stats panel with
     something inside instead of the zeros it starts with. The Indoraptor is
     Unique, so it has a 5-step Enhancement track. */
  if (typeof cambiarMejora === "function"){
    cambiarMejora("indoraptor", "bVida", 1); cambiarMejora("indoraptor", "bVida", 1);
    cambiarMejora("indoraptor", "bDano", 1); cambiarMejora("indoraptor", "bDano", 1);
    cambiarMejora("indoraptor", "bVel", 1);
  }
  pintarArbol(); pintarMios(); pintarStats();
  var v = new URLSearchParams(location.search).get("v") || "calc";
  // View with the toggle off: the report has to say that it is following the
  // paleo.gg criterion, or the same screen gives two answers without saying
  // which one you are looking at.
  if (v === "calc-paleo"){
    var chk = document.getElementById("chkSubida");
    chk.checked = false; chk.dispatchEvent(new Event("change", {bubbles:true}));
    v = "calc";
  }
  if (v === "yellow"){
    ponerTema("yellow");
    // The Enhancement track only exists from level 30 on, so this view raises
    // the creature to 30 before touching the steps: otherwise the controls come
    // out disabled and the screenshot does not show what the track does.
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
  /* "buscar" view: the dropdown open with a row highlighted by the KEYBOARD.
     It goes LAST on purpose: pressing a tab closes the list (the outside-click
     handler closes it), so if this went earlier, the screenshot would come out
     with the dropdown already closed. And the arrow has to be really pressed:
     the highlight does not exist until it is pressed, so without this the image
     could not prove that the keyboard works. */
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
    # The script goes AT THE END, after the main script: if it is put behind
    # <body> it runs before `elegir` or `pintarArbol` exist, and it blows up.
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
