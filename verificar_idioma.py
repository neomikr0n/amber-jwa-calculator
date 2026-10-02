#!/usr/bin/env python3
"""Language checks: dictionary parity, English default, and pin precedence.

Three things are checked, and the third is the one that matters most:

  1. PARITY. Every string the code hands to i18n(), and every data-i18n /
     data-i18n-html attribute in the static markup, has an entry in I18N_ES.
     A missing key does not crash: it silently renders English inside the
     Spanish interface, which is how a translation rots without anyone
     noticing. This check is static; it needs no browser.

  2. DEFAULT. With nothing stored and nothing injected, the page renders in
     English.

  3. PRECEDENCE. With Spanish stored, an injected window.__lang = "en" must
     win. Without this, the rest of the suite would be asserting on whatever
     language the previous run happened to leave behind, and a green run would
     not mean what it says.

A fourth pass, stored Spanish with no injection, is included because it is the
only place that proves the Spanish column of the dictionary actually reaches
the screen.

Usage:  python3 verificar_idioma.py
"""
import html as html_mod
import json
import os
import re
import subprocess
import sys

from informe_browser import arrancar, comprobar_scripts, veredicto

from rutas import HTML, enlazar_img, inyectar_en_cabeza

RAIZ = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-idioma"
PERFIL = os.path.join(DIR, "perfil")

# ---------------------------------------------------------------- 1) paridad
fuente = open(HTML, encoding="utf-8").read()

usadas = set()
# The second alternative has to be [^"\\]|\\. — one backslash followed by any
# character. Written with one backslash too many it stops matching every key
# that contains an escaped quote, which is most of the HTML fragments, and the
# check then reports them as unused while proving nothing about them.
for m in re.finditer(r"i18n\((\'([^\']*)\'|\"((?:[^\"\\]|\\.)*)\")", fuente):
    if m.group(2) is not None:
        usadas.add(m.group(2))
    else:
        usadas.add(json.loads('"%s"' % m.group(3)))
for m in re.finditer(r"data-i18n(?:-html|-placeholder)?=\"([^\"]*)\"", fuente):
    usadas.add(html_mod.unescape(m.group(1)))

i = fuente.index("const I18N_ES = {")
j = fuente.index("\n};", i)
definidas = {json.loads(k) for k in re.findall(r'^  ("(?:[^"\\]|\\.)*"):', fuente[i:j], re.M)}

huerfanas = sorted(usadas - definidas)
sin_usar = sorted(definidas - usadas)

fallos_estaticos = []
if huerfanas:
    fallos_estaticos.append(
        "keys used that are NOT in the dictionary: %d, e.g. %s"
        % (len(huerfanas), " | ".join(repr(h[:60]) for h in huerfanas[:3])))
if not definidas:
    fallos_estaticos.append("no I18N_ES dictionary found in the deliverable")

print("dictionary: %d entries | keys used: %d | unused: %d"
      % (len(definidas), len(usadas), len(sin_usar)))

# --------------------------------------------------------- 2, 3 y 4) navegador
PIN_EN = '<script>window.__lang = "en";</script>\n'
GUARDA_ES = '<script>try { localStorage.setItem("jwa322.idioma","es"); } catch (e) {}</script>\n'
GUARDA_NADA = '<script>try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n'

CASOS = [
    # (name, injection into <head>, expected lang, expected label, expected placeholder)
    ("with nothing stored it boots in English",
     GUARDA_NADA, "en", "Calculator", "Type a name… (e.g. Indoraptor)"),
    ("the injected value beats the stored one",
     GUARDA_ES + PIN_EN, "en", "Calculator", "Type a name… (e.g. Indoraptor)"),
    ("with Spanish stored and no pin, it renders in Spanish",
     GUARDA_ES, "es", "Calculadora", "Escribe un nombre… (ej. Indoraptor)"),
]

DIAG = r"""
<script>
window.addEventListener("load", function(){
  var RES = [], FALLOS = 0;
  function ok(nombre, cond, visto){
    if (cond) RES.push("OK    " + nombre);
    else { RES.push("FALLO " + nombre + (visto ? ": " + visto : "")); FALLOS++; }
  }
  var lang = document.documentElement.lang;
  var b = document.querySelector('[data-t="calc"]');
  var etiqueta = b ? b.textContent.trim() : "(sin boton)";
  /* The search placeholder is an ATTRIBUTE, and the bug this covers was exactly
     that: every visible string was translated except the placeholder, which
     stayed Spanish in the English interface. */
  var q = document.getElementById("q");
  var ph = q ? q.getAttribute("placeholder") : "(sin campo)";
  ok("__NOMBRE__", lang === __LANG__ && etiqueta === __ETIQ__ && ph === __PLACE__,
     "lang=" + lang + " etiqueta=" + etiqueta + " placeholder=" + ph);
  /* The switch marks the language in use with aria-pressed; it has to be set in
     BOTH languages. With the old `if (LANG !== "en") aplicarIdioma()` a page
     booting in English left both buttons with no pressed state. */
  var pulsado = null;
  document.querySelectorAll("[data-idioma]").forEach(function(el){
    if (el.getAttribute("aria-pressed") === "true") pulsado = el.dataset.idioma;
  });
  ok("the language switch marks the language in use", pulsado === lang,
     "pressed=" + pulsado + " lang=" + lang);

  /* The strings that only exist AFTER choosing a creature —the report, the tree,
     the stats panel, the create buttons— are not in the starting page, so a scan
     of the startup would miss them. The scenario is built here and the DOM is
     scanned, titles and placeholders included, which is where the Spanish leaked
     in the first place. */
  try {
    MIS = ["indoraptor", "allosaurus", "ankylos_lux"]; pintarFotos();
    elegir("indoraptor");
    function poner(id, v){ var e = document.getElementById(id); e.value = v;
      e.dispatchEvent(new Event("input", {bubbles:true})); }
    poner("nivelAct", "21"); poner("adnTengo", "100"); poner("nivelObj", "30");
    document.querySelector('nav button[data-t="arbol"]').click();
    pintarArbol(); refrescar();
  } catch (e) {
    ok("the scenario used for the language scan could be built", false, e.message);
  }
  if (lang === "en"){
    var texto = document.body.innerText;
    document.querySelectorAll("[title],[placeholder],[aria-label]").forEach(function(el){
      ["title","placeholder","aria-label"].forEach(function(a){
        var v = el.getAttribute(a); if (v) texto += "\n" + v;
      });
    });
    var re = /\b(Escribe|Llevar|Pone|Criar|subir|subes|compartida|compartidas|fusionar|publicar|recién|santuario|combate|tuyo|Elige|Todavía|nace|Resultado|Necesitas)\b/;
    var m = re.exec(texto);
    ok("the English interface has no Spanish fragment left", !m,
       m ? "found «" + m[0] + "»" : "none of the 19 markers");
  }
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var p = document.createElement("pre"); p.id = "__diag";
  p.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;" +
                    "font:13px/1.5 monospace;padding:14px;margin:0;white-space:pre-wrap";
  p.textContent = RES.join("\n"); document.body.appendChild(p);
__ENTREGA__
});
</script>"""

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)
# The page loads img/ relatively: the symlink puts the photos within reach.
enlazar_img(os.path.join(DIR, "img"), IMGDIR)

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})

resultados = []
for k, (nombre, inyeccion, lang_esp, etiq_esp, place_esp) in enumerate(CASOS):
    pagina = inyectar_en_cabeza(fuente, inyeccion, "verificar_idioma.py")
    diag = DIAG.replace("__NOMBRE__", nombre).replace("__LANG__", json.dumps(lang_esp)) \
               .replace("__ETIQ__", json.dumps(etiq_esp)) \
               .replace("__PLACE__", json.dumps(place_esp))
    srv = arrancar()
    diag = diag.replace("__ENTREGA__", srv.js("__diag"))
    destino = os.path.join(DIR, "caso%d.html" % k)
    open(destino, "w", encoding="utf-8").write(pagina + diag)
    _ok, _msg = comprobar_scripts(pagina + diag, "verificar_idioma.py")
    if not _ok:
        raise SystemExit("!! " + _msg)
    subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                    "--window-size", "1200,900",
                    "--screenshot", os.path.join(DIR, "caso%d.png" % k),
                    "file://" + destino],
                   env=env, capture_output=True, text=True, timeout=180)
    codigo, lineas = veredicto(srv.texto())
    srv.parar()
    resultados.append(codigo)
    for l in lineas:
        print(l)

if fallos_estaticos:
    for f in fallos_estaticos:
        print("FAIL dictionary parity: " + f)
    resultados.append(1)

print("-" * 72)
salida = 0 if all(c == 0 for c in resultados) and not fallos_estaticos else 1
print("RESULT: %s" % ("all OK" if salida == 0
                         else "FAIL (%d of %d checks with a problem)"
                              % (len([c for c in resultados if c]) + len(fallos_estaticos),
                                 len(CASOS) + 1)))
sys.exit(salida)
