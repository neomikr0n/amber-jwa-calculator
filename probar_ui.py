#!/usr/bin/env python3
"""
INTERFACE test in a real browser (headless Firefox).

The numeric verifiers (verificar_motor.py / verificar_arbol.py) cover the
maths. This covers the rest: that the fields exist, that they respond to the
keyboard, that it is saved, and that the images really load (naturalWidth > 0,
which is the only way to tell "there is an <img>" from "the dinosaur is
visible").

It writes the report into a <pre> and delivers it through a local server (see
informe_browser.py), besides leaving it in the screenshot. The script prints the
report and returns exit code 0 only if everything passes: reading the PNG by eye
is not a test.

Usage:  python3 probar_ui.py
"""
import os, re, shutil, subprocess, json
from informe_browser import arrancar, comprobar_scripts, veredicto

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-ui"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "ui.html")
SHOT = os.path.join(DIR, "ui.png")

# The report travels through here, not through a screenshot you have to read by eye.
srv = arrancar()

DIAG = r"""
<script>
/* Two traps of testing a page from inside, and how they are dodged:

   1. `loading="lazy"` delays the images until they enter the screen, so
      checking naturalWidth right after painting them gives 0 ALWAYS, and in
      a hidden container they are not even requested. Solution: they are cloned
      as eager and hidden <img>, which do block the load event. When
      load fires, they are already resolved.

   2. An event fired with dispatchEvent does NOT focus the element, so
      document.activeElement is still <body> and the test that "the focus is
      not lost" fails even though the page has nothing broken. Solution: .focus()
      before firing, as a person would do when clicking. */

// --- 1) the interactions, during parsing ---
var RES = [], FALLOS = 0, CLONES = [], FOCO_U = null;
function log(k, v){ RES.push(k + ": " + (v === undefined ? "" : v)); }
function ok(k, cond, detalle){ if (!cond) FALLOS++; log((cond ? "OK   " : "FALLO") + " " + k, detalle); }
function txt(id){ var e = document.getElementById(id); return e ? e.innerText.replace(/\s+/g," ").trim() : "(falta "+id+")"; }
function ev(el, tipo){ el.dispatchEvent(new Event(tipo, {bubbles:true})); }
/* Writes the value in one go. Useful for setting up a scenario, but it does NOT
   test typing: the field never goes through an intermediate state. */
function teclear(el, valor){
  el.focus();                 // like a real click
  el.value = valor;
  ev(el, "input");
}
/* Types DIGIT BY DIGIT with `execCommand("insertText")`, which is the only thing
   that inserts AT THE CURSOR and fires `input` like a real key. It is needed
   because the bug being watched only shows up this way: the tree repaints on
   every key, and if the cursor cannot be restored (an <input type=number> lets you
   neither read nor set it in Firefox), the next digit enters at the BEGINNING.
   With `teclear` —which writes "1500" in one go— that bug is invisible: that is why
   it stayed there without any test seeing it.
   Returns the final value and cursor. */
function teclearTecla(sel, texto){
  var vistos = [];
  for (var i = 0; i < texto.length; i++){
    var el = typeof sel === "function" ? sel() : document.querySelector(sel);
    if (!el) return {valor: "(sin campo)", cursor: null, pasos: vistos};
    el.focus();
    document.execCommand("insertText", false, texto.charAt(i));
    var d = typeof sel === "function" ? sel() : document.querySelector(sel);
    vistos.push(d.value + "@" + d.selectionStart);
  }
  var f = typeof sel === "function" ? sel() : document.querySelector(sel);
  return {valor: f ? f.value : "(sin campo)", cursor: f ? f.selectionStart : null, pasos: vistos};
}

try {
  /* Start from ZERO. The Firefox profile keeps localStorage between runs, and
     without this the test inherits the inventory and «Mis criaturas» from the
     previous execution and ends up measuring something else: it happened, and an
     inherited row made the check that the list starts empty fail. */
  localStorage.removeItem("jwa322.inventario");
  localStorage.removeItem("jwa322.mios");
  INV = {}; MIS = [];

  log("=== 0. errors loading the script ===",
      (window.__errores && window.__errores.length) ? window.__errores.join(" | ") : "none");

  /* --- search box: where it lives, and how it is handled with the keyboard ---
     Requested by n30 (25-sep-2026): the search leaves section 1 and moves up to
     the strip of the tabs; the card moves up next to the stats; and the list is
     traversed with the arrows and chosen with Enter.
     Everything goes inside a function to NOT leave global names: the
     <script> blocks share the scope, and a `var` here that collides with a `let` of
     the application leaves this diagnostic uncompiled and unrun. See
     `comprobar_scripts` in informe_browser.py. */
  (function(){
    var caja = document.getElementById("q"), drop = document.getElementById("lista");
    function tecla(k, shift){
      var e = new KeyboardEvent("keydown", {key:k, shiftKey:!!shift, bubbles:true, cancelable:true});
      caja.dispatchEvent(e);
      return e;
    }
    function resaltado(){ var e = drop.querySelector(".it.sel"); return e ? e.dataset.u : ""; }
    function abierta(){ return drop.classList.contains("on"); }
    function activa(){ var s = document.querySelector("section.on"); return s ? s.id : ""; }

    var barra = document.querySelector(".barra-sup");
    ok("the search box lives in the tab strip, OUTSIDE the calculator",
       !!barra && !!barra.querySelector("#q") && !!barra.querySelector("nav") &&
       !document.getElementById("s-calc").contains(caja),
       barra ? "strip with the search box and " + barra.querySelectorAll("nav button").length + " tabs"
             : "(there is no strip)");
    ok("the card moves up next to the stats, within the same grid",
       document.getElementById("filaElegir").contains(document.getElementById("elegida")) &&
       document.getElementById("filaElegir").contains(document.getElementById("panelStats")) &&
       document.getElementById("elegida").nextElementSibling === document.getElementById("panelStats"),
       "card and stats are siblings within the grid");

    // --- the list does NOT open by itself when using other tabs ---
    ok("the list starts closed", !abierta(), "on=" + abierta());
    elegir("indoraptor");
    document.querySelector('nav button[data-t="arbol"]').click();
    var cb = document.querySelector('#arbolCuerpo input[data-campo="creado"]');
    ok("there is a checkbox in the tree to touch", !!cb, cb ? cb.dataset.u : "(no checkbox)");
    if (cb){ cb.checked = !cb.checked; ev(cb, "change"); }
    ok("touching a checkbox in the tree does NOT unfold the search box",
       !!cb && !abierta(), "on=" + abierta() + " | tab " + activa());

    // --- keyboard ---
    document.querySelector('nav button[data-t="calc"]').click();
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    var nFilas = drop.querySelectorAll(".it").length;
    ok("typing unfolds the list", abierta() && nFilas > 1, nFilas + " rows");
    ok("and nothing stays highlighted: Enter must not take you blindly", resaltado() === "", "«" + resaltado() + "»");

    ok("ArrowDown swallows the key (otherwise the cursor would jump to the end of the text)",
       tecla("ArrowDown").defaultPrevented, "defaultPrevented");
    var s1 = resaltado();
    ok("ArrowDown highlights the first one", s1 !== "" && s1 === drop.querySelector(".it").dataset.u, s1);
    ok("and highlights ONE single row", drop.querySelectorAll(".it.sel").length === 1,
       drop.querySelectorAll(".it.sel").length + " highlighted");
    tecla("ArrowDown");
    var s2 = resaltado();
    ok("ArrowDown again goes down to the second", s2 !== "" && s2 !== s1, s1 + " -> " + s2);
    tecla("ArrowUp");
    ok("ArrowUp goes back to the first", resaltado() === s1, resaltado() + " (expected " + s1 + ")");
    tecla("ArrowUp");
    ok("ArrowUp on the first does not leave the list", resaltado() === s1, resaltado());
    ok("the arrows have not touched the field text", caja.value === "rex", caja.value);
    ok("a normal key is NOT swallowed", !tecla("a").defaultPrevented, "defaultPrevented=false");
    for (var i = 0; i < 25; i++) tecla("ArrowDown");
    var elSel = drop.querySelector(".it.sel");
    ok("after going down 25 times the highlight is still IN SIGHT (the list scrolls by itself)",
       !!elSel && elSel.offsetTop >= drop.scrollTop &&
       elSel.offsetTop + elSel.offsetHeight <= drop.scrollTop + drop.clientHeight,
       "scrollTop=" + drop.scrollTop + " offsetTop=" + (elSel ? elSel.offsetTop : "?") +
       " height=" + drop.clientHeight);

    // --- Enter takes you to the calculator, from any tab ---
    var objetivo = resaltado();
    document.querySelector('nav button[data-t="arbol"]').click();
    ok("before pressing Enter we are in the tree", activa() === "s-arbol", activa());
    caja.focus();
    tecla("Enter");
    ok("Enter takes you to the CALCULATOR even if pressed from another tab",
       activa() === "s-calc", activa());
    ok("and chooses exactly the highlighted creature", elegido === objetivo,
       "chosen=" + elegido + " | highlighted=" + objetivo);
    ok("and closes the list", !abierta(), "on=" + abierta());

    // --- a click from another tab also navigates ---
    document.querySelector('nav button[data-t="mios"]').click();
    caja.focus();
    caja.value = "indoraptor";
    ev(caja, "input");
    var fila = drop.querySelector(".it");
    fila.dispatchEvent(new MouseEvent("click", {bubbles:true}));
    ok("a click on a result from «Mis criaturas» takes you to the calculator",
       activa() === "s-calc" && elegido === fila.dataset.u, activa() + " / " + elegido);

    // --- Escape closes without choosing ---
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    var antesDeEscapar = elegido;
    ok("the list is open before Escape", abierta(), "on=" + abierta());
    tecla("Escape");
    ok("Escape closes the list", !abierta(), "on=" + abierta());
    ok("and chooses nothing", elegido === antesDeEscapar, elegido);

    // --- the accessibility state comes along ---
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    tecla("ArrowDown");
    ok("with the list open and a row highlighted, the aria says so",
       caja.getAttribute("aria-expanded") === "true" &&
       caja.getAttribute("aria-activedescendant") === "it-0",
       "expanded=" + caja.getAttribute("aria-expanded") +
       " activedescendant=" + caja.getAttribute("aria-activedescendant"));
    tecla("Escape");
    ok("and on closing both are cleared",
       caja.getAttribute("aria-expanded") === "false" && !caja.hasAttribute("aria-activedescendant"),
       "expanded=" + caja.getAttribute("aria-expanded") +
       " activedescendant=" + caja.getAttribute("aria-activedescendant"));

    // Clean state for what follows: in the calculator and with the list closed.
    irA("calc");
    cerrarLista();
  })();

  // --- search box with thumbnail ---
  document.getElementById("q").value = "indoraptor";
  ev(document.getElementById("q"), "input");
  var it = document.querySelector("#lista .it");
  ok("the search box paints a thumbnail", !!it && !!it.querySelector("img.mini"));
  /* The double of the photos is for the card, the strip and the tree. The
     dropdown KEEPS the small one on purpose: a 72px row would halve the results
     seen in the list (n30, 27-sep-2026). */
  var miniBus = it ? it.querySelector("img.mini") : null;
  var cmini = miniBus ? getComputedStyle(miniBus) : null;
  ok("the search thumbnail stays compact (30x36)",
     !!cmini && cmini.width === "30px" && cmini.height === "36px",
     cmini ? cmini.width + "x" + cmini.height : "(no thumbnail)");
  cerrarLista();

  // --- Indoraptor 21 -> 30 with 1.000 DNA: there is a deficit, hence there is a tree ---
  elegir("indoraptor");
  teclear(document.getElementById("nivelAct"), "21");
  teclear(document.getElementById("adnTengo"), "1000");
  document.getElementById("nivelObj").value = 30;
  ev(document.getElementById("nivelObj"), "input");

  ok("the card has a large image", !!document.querySelector("#elegida img.grande"));

  /* The card redesign (27-sep-2026): portrait at the NATIVE size of the WebP
     (207x250, measured on the 518 files), the name and the badges on a header
     across the top, the ingredients at the foot of the photo, the hatch/cost/cap
     line in the photo's tooltip, and «Your data» (the three fields that used to
     be section 2) to the right of the photo. Everything is MEASURED. */
  var g = document.querySelector("#elegida img.grande");
  var cg = getComputedStyle(g);
  ok("the card portrait is at the native size of the images (207x250)",
     cg.width === "207px" && cg.height === "250px", cg.width + "x" + cg.height);
  var marco = document.querySelector("#elegida .ficha .marco");
  ok("the hatch/cost/cap line is the photo's tooltip, not painted text",
     !!marco && /Nace en nivel 21/.test(marco.title) && /crear cuesta 250 ADN/.test(marco.title) &&
     /tope de ADN/.test(marco.title) &&
     document.getElementById("elegida").innerText.indexOf("Nace en") === -1,
     marco ? marco.title : "(no marco)");
  /* The header: name on the left, badges on the right, both ABOVE the photo. */
  var cab = document.querySelector("#elegida .ficha .cab");
  var rcab = cab ? cab.getBoundingClientRect() : null;
  var rgs = g.getBoundingClientRect();
  ok("the name and the badges go in a header across the top, above the photo",
     !!cab && !!cab.querySelector(".nombre") && cab.querySelectorAll(".etiquetas > *").length >= 3 &&
     rcab.bottom <= rgs.top + 1,
     cab ? cab.querySelectorAll(".etiquetas > *").length + " badges, header bottom " +
           rcab.bottom.toFixed(1) + " vs photo top " + rgs.top.toFixed(1) : "(no header)");
  /* «Your data» inside the card: the three fields keep their ids and move to the
     right of the photo, in a two-column grid. */
  var campos = document.querySelector("#elegida .campos");
  var g3 = campos ? campos.querySelector(".g3") : null;
  var cols = g3 ? getComputedStyle(g3).gridTemplateColumns.split(" ").length : 0;
  var dentro = ["nivelAct", "adnTengo", "nivelObj"].every(function(id){
    var el = document.getElementById(id); return el && campos && campos.contains(el); });
  ok("the three «Your data» fields live inside the card, with their ids",
     !!campos && dentro, dentro ? "nivelAct + adnTengo + nivelObj inside #elegida" : "(outside the card)");
  ok("and they are laid out in a two-column grid",
     cols === 2, cols + " columnas");
  var rc = campos.getBoundingClientRect();
  ok("the fields sit to the RIGHT of the photo", rc.left >= rgs.right - 1,
     "campos left " + rc.left.toFixed(1) + " vs photo right " + rgs.right.toFixed(1));
  var rp = document.querySelector("#elegida .ficha .pie").getBoundingClientRect();
  ok("the ingredients sit at the foot of the photo", rp.top >= rgs.bottom - 1,
     "pie top " + rp.top.toFixed(1) + " vs photo bottom " + rgs.bottom.toFixed(1));

  /* Switching the language has to re-render the parts painted ONCE: the labels
     of the stats panel (built by `montarStats`) and the pills of the card (built
     by `elegir`). Before, with Spanish selected the stats still said «Health».
     Everything is re-queried after each switch: the repaint replaces the nodes. */
  var leerStat = function(){
    var e = document.querySelector("#stRejilla .st-k"); return e ? e.textContent.trim() : "(no stat)"; };
  var leerTipo = function(){
    var e = document.querySelector("#elegida .ficha .cab .etiquetas .pill"); return e ? e.textContent.trim() : "(no pill)"; };
  setIdioma("en");
  var enStat = leerStat(), enTipo = leerTipo();
  setIdioma("es");
  var esStat = leerStat(), esTipo = leerTipo();
  ok("the stats labels and the card pills follow the language switch",
     enStat === "Health" && esStat === "Vida" &&
     enTipo === "Super Hybrid" && esTipo === "superhíbrido",
     "stat " + enStat + "/" + esStat + " · tipo " + enTipo + "/" + esTipo);

  // --- maximum level below the target level ---
  var mn = txt("maxNivel");
  log("--- maxNivel ---", mn);
  var mnm = /Nivel\s+(\d+)/.exec(mn);
  var nivelDicho = mnm ? Number(mnm[1]) : -1;
  var esp = nivelMaximo("unique", 21, 1000, true);
  ok("the maximum level shown matches the engine", nivelDicho === esp.nivel,
     "it says " + nivelDicho + ", the engine says " + esp.nivel);
  ok("the maximum level is NOT 0 with 1.000 DNA", nivelDicho > 0);
  ok("it says 'Ya te alcanza' only when it really reaches",
     (esp.nivel >= 30) === /Ya te alcanza/.test(mn), "level=" + esp.nivel + " target=30");
  ok("no negative figure appears in the block", !/-\d/.test(mn), mn.slice(-80));

  // --- the tree ---
  // The tab must be ACTIVATED before touching it: an element inside a
  // section in display:none cannot receive focus, so .focus() fails
  // silently and any focus test gives a false failure.
  document.querySelector('nav button[data-t="arbol"]').click();
  ok("the tree tab stays active",
     document.getElementById("s-arbol").classList.contains("on"));

  var nodos = document.querySelectorAll("#arbolCuerpo .nodo");
  log("nodes in the tree", nodos.length);
  ok("the tree goes down to the ingredients", nodos.length > 1, nodos.length + " nodes");
  var camposOk = 0, fotos = 0;
  nodos.forEach(function(n){
    if (n.querySelector("input[data-campo='nivel']") &&
        n.querySelector("input[data-campo='adn']") &&
        n.querySelector("input[data-campo='creado']")) camposOk++;
    if (n.querySelector("img.foto")) fotos++;
  });
  ok("all nodes have level+dna+created", camposOk === nodos.length, camposOk + "/" + nodos.length);
  ok("all nodes have a photo", fotos === nodos.length, fotos + "/" + nodos.length);

  // --- writing in a node ---
  var ing = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  ok("there is an editable ingredient", !!ing);
  var uuidIng = ing.dataset.u;
  teclear(ing, "123456");
  var g = INV[uuidIng];
  ok("the DNA written in the tree is saved", !!g && g.adn === 123456, JSON.stringify(g));
  var vuelto = document.querySelector("[data-u='"+uuidIng+"'][data-campo='adn']");
  ok("the field keeps the typed value", vuelto.value === "123456", vuelto.value);

  // --- typing DIGIT BY DIGIT: the cursor must not jump to the beginning ---
  // This is the bug that slipped in: with <input type=number>, Firefox does NOT let
  // you read or set the cursor (`setSelectionRange` throws InvalidStateError and
  // `selectionStart` is null), the tree is fully repainted on every key, and typing
  // "1500" ended up saving 51 with "0051" in the field. It is watched by typing for
  // real, key by key: `teclear` —which writes the whole value in one go— does not see it.
  var selAdn = "[data-u='"+uuidIng+"'][data-campo='adn']";
  var selNv  = "[data-u='"+uuidIng+"'][data-campo='nivel']";
  var relAdn = function(){ return document.querySelector(selAdn); };
  var relNv  = function(){ return document.querySelector(selNv); };

  teclear(relAdn(), "");
  var t1 = teclearTecla(relAdn, "1500");
  ok("typing 1500 digit by digit leaves 1500", t1.valor === "1500",
     "field='" + t1.valor + "' steps: " + t1.pasos.join(" "));
  ok("and the cursor ends up at the end, not at the beginning", t1.cursor === 4, "cursor=" + t1.cursor);
  ok("and 1500 is saved, not 51", INV[uuidIng].adn === 1500, "saved=" + INV[uuidIng].adn);

  teclear(relNv(), "");
  var t2 = teclearTecla(relNv, "18");
  ok("typing the level digit by digit leaves 18", t2.valor === "18",
     "field='" + t2.valor + "' steps: " + t2.pasos.join(" "));

  // Insert IN THE MIDDLE of the number, not just at the end: that is where a
  // badly restored cursor does the most damage, because the digit enters in the wrong place.
  teclear(relAdn(), "1000");
  var medio = relAdn();
  medio.focus(); medio.setSelectionRange(1, 1);
  document.execCommand("insertText", false, "9");
  ok("inserting in the middle respects the position", relAdn().value === "19000",
     "field='" + relAdn().value + "'");

  // What <input type=number> used to filter by itself (letters, signs) is now cleaned
  // by `limpiarNumero`, and without sending the cursor to the end.
  teclear(relAdn(), "");
  var conLetras = relAdn();
  conLetras.focus();
  document.execCommand("insertText", false, "1a2");
  ok("letters do not enter a DNA field", relAdn().value === "12",
     "field='" + relAdn().value + "'");
  ok("and the clean value is the one saved", invDe(uuidIng).adn === 12,
     "saved=" + invDe(uuidIng).adn);

  // --- writing the LEVEL too ---
  var campoNivel = document.querySelector("[data-u='"+uuidIng+"'][data-campo='nivel']");
  teclear(campoNivel, "17");
  var g4 = INV[uuidIng];
  ok("the level written in the tree is saved", !!g4 && g4.nivel === 17, JSON.stringify(g4));

  // --- unchecking 'Creada' ---
  var chk = document.querySelector("[data-u='"+uuidIng+"'][data-campo='creado']");
  ok("there is a 'Creada' checkbox", !!chk);
  var m2 = minLv(C[uuidIng][1]);
  chk.checked = false; ev(chk, "change");
  var g2 = INV[uuidIng];
  ok("unchecking 'Creada' saves it as not created", !!g2 && g2.creado === false, JSON.stringify(g2));
  ok("when not created, the level stays at 0", g2 && g2.nivel === 0);
  ok("the node warns of 'sin crear'", /sin crear/.test(document.querySelector("#arbolCuerpo").innerText));
  var chk2 = document.querySelector("[data-u='"+uuidIng+"'][data-campo='creado']");
  chk2.checked = true; ev(chk2, "change");
  var g3 = INV[uuidIng];
  ok("creating it again raises it to its birth level (" + m2 + ")",
     !!g3 && g3.creado === true && g3.nivel === m2, JSON.stringify(g3));

  // --- saving ---
  var json = localStorage.getItem("jwa322.inventario");
  ok("it was written to localStorage", !!json && json.length > 20, (json||"").slice(0, 120));

  // --- Mis criaturas: ONLY what is saved on purpose ---
  // Rule requested by n30 (25-sep-2026): typing in the tree is used for the calculation,
  // but it does NOT put creatures into the list. Before, «Mis criaturas» was
  // `Object.keys(INV)`, so editing the DNA of the ingredients left the whole
  // genealogical tree saved, and pressing «Guardar» was not the cause but the
  // confirmation. The list is `MIS`, and only Guardar, the × and the
  // import write to it.
  pintarMios();
  var filas = document.querySelectorAll("#miosCuerpo tbody tr");
  var tocadas = Object.keys(INV).length;
  ok("typing in the tree does NOT put anything into «Mis criaturas»", filas.length === 0,
     filas.length + " rows, with " + tocadas + " creatures touched");
  ok("but the data IS kept, so that the tree can calculate with it",
     tocadas > 0 && invDe(uuidIng).adn === 12,
     tocadas + " creatures; the ingredient with " + invDe(uuidIng).adn + " DNA");

  // Guardar inserts ONE: the chosen one.
  document.querySelector('nav button[data-t="calc"]').click();
  var btn = document.getElementById("btnGuardar");
  ok("the save button exists", !!btn);
  btn.click();
  pintarMios();
  var filas2 = document.querySelectorAll("#miosCuerpo tbody tr");
  var textoMios = document.querySelector("#miosCuerpo").innerText;
  ok("Guardar inserts EXACTLY the chosen creature", filas2.length === 1, filas2.length + " rows");
  ok("and no ingredient from the tree sneaks in",
     textoMios.toLowerCase().indexOf(C[uuidIng][0].toLowerCase()) === -1,
     C[uuidIng][0] + (textoMios.toLowerCase().indexOf(C[uuidIng][0].toLowerCase()) === -1
                      ? " does not appear" : " DOES appear"));
  ok("Mis criaturas has a maximum level column", /Nivel máx/i.test(textoMios));
  /* The boosts column exists so that it can be SEEN that the points were saved:
     without it, the datum could only be checked by opening the card, and there
     would be no way to know it is still there. */
  var cabMios = Array.prototype.map.call(document.querySelectorAll("#miosCuerpo th"),
    function(t){ return t.textContent; }).join("|");
  ok("and a boosts column, so that it can be seen that they were saved",
     /Mejoras/.test(cabMios), cabMios);
  btn.click();
  var filas3 = document.querySelectorAll("#miosCuerpo tbody tr");
  ok("pressing Guardar again does not duplicate the row", filas3.length === 1, filas3.length + " rows");
  /* The table keeps the compact thumbnail, like the search dropdown. */
  var miniTab = document.querySelector("#miosCuerpo img.mini");
  var ctab = miniTab ? getComputedStyle(miniTab) : null;
  ok("the table thumbnail stays compact (38x46)",
     !!ctab && ctab.width === "38px" && ctab.height === "46px",
     ctab ? ctab.width + "x" + ctab.height : "(no thumbnail)");

  // The saved list is persisted separately from the data.
  var guardadoMios = JSON.parse(localStorage.getItem("jwa322.mios") || "null");
  ok("the list is saved in its own localStorage key",
     Array.isArray(guardadoMios) && guardadoMios.length === 1,
     JSON.stringify(guardadoMios));

  // --- 3) what n30 asked for on 25-sep: photo strip, complete «Lleva a»,
  //        report without a «Rareza» column, and the zone instead of «se recolecta» ---
  /* None of this is judged by looking at a screenshot: it is pressed and the DOM is
     read. And each check is made against the model DATA or against a calculation
     done here, never against the HTML we have just painted: comparing the painted
     with the painted would give green even if both things were wrong. */

  // (a) the photo strip, above «Elige la criatura»
  var panel = document.getElementById("panelMisFotos");
  var tira  = document.getElementById("misFotos");
  MIS = ["indoraptor", "tyrannosaurus_rex"];
  pintarFotos();
  var fotos = tira.querySelectorAll("button[data-ir]");
  ok("the photo strip shows up when there are saved creatures",
     panel.style.display !== "none" && fotos.length === 2, fotos.length + " photos");
  var nombresTira = [];
  var coloresTiraBien = true;
  Array.prototype.forEach.call(fotos, function(b){
    var nm = b.querySelector(".tira-nm");
    nombresTira.push(nm ? nm.textContent.trim() : "(no name)");
    if (!nm || nm.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) coloresTiraBien = false;
  });
  ok("each photo carries the name of its creature, with the colour of its rarity",
     coloresTiraBien && nombresTira.length === 2, nombresTira.join(" | "));

  /* Order: by RARITY, rarest first (Apex, then Omega, then down), and the name
     only breaks ties inside the same rarity. The pair is chosen so that the two
     criteria DISAGREE: alphabetically «Allosaurus» (common) goes before
     «Ankylos Lux» (apex), so a sort that fell back to the name would come out
     backwards and this would fail. */
  MIS = ["allosaurus", "ankylos_lux"];
  pintarFotos();
  var ordenTira = Array.prototype.map.call(
    tira.querySelectorAll("button[data-ir] .tira-nm"),
    function(n){ return n.textContent.trim(); });
  ok("the strip is ordered by rarity, rarest first",
     ordenTira[0] === "Ankylos Lux" && ordenTira[1] === "Allosaurus", ordenTira.join(" | "));

  /* The photo is centred inside its card. The name below is centred, so an
     image stuck to the left edge read crooked. Measured on the first card: the
     gap on the left has to equal the gap on the right. */
  MIS = ["indoraptor", "tyrannosaurus_rex"];
  pintarFotos();
  var cajaTira = tira.querySelector("button[data-ir]");
  var imgTira  = cajaTira.querySelector("img");
  var rc = cajaTira.getBoundingClientRect(), ri = imgTira.getBoundingClientRect();
  ok("the photo is centred inside its card",
     Math.abs((ri.left - rc.left) - (rc.right - ri.right)) <= 1.5,
     "left " + (ri.left - rc.left).toFixed(1) + " vs right " + (rc.right - ri.right).toFixed(1));
  var cminT = getComputedStyle(imgTira);
  ok("the strip photo is the double of the compact one (60x72)",
     cminT.width === "60px" && cminT.height === "72px", cminT.width + "x" + cminT.height);

  // the cap: with 12 saved only 10 are shown, and it says how many there are
  MIS = Object.keys(C).slice(0, 12);
  pintarFotos();
  var n10 = tira.querySelectorAll("button[data-ir]").length;
  ok("the strip shows at most 10 photos", n10 === 10, n10 + " photos out of 12 saved");
  ok("and it warns how many it shows out of how many there are",
     /10 de 12/.test(document.getElementById("nMisFotos").textContent),
     document.getElementById("nMisFotos").textContent);

  // pressing a photo opens THAT creature, not the one that was open
  MIS = ["indoraptor", "tyrannosaurus_rex"];
  pintarFotos();
  elegir("indoraptor");
  tira.querySelector("button[data-ir='tyrannosaurus_rex']").click();
  ok("pressing a photo opens that creature in the calculator",
     elegido === "tyrannosaurus_rex" && document.getElementById("s-calc").classList.contains("on"),
     "chosen=" + elegido + ", calc tab=" +
     document.getElementById("s-calc").classList.contains("on"));

  // and with no saved creatures the block takes up no room
  MIS = []; pintarFotos();
  ok("with no saved creatures the strip takes up no room",
     panel.style.display === "none" && tira.querySelectorAll("button").length === 0,
     "display='" + panel.style.display + "'");

  // (b) «Lleva a»: the WHOLE upper branch, not just the direct children
  /* The transitive closure is calculated HERE, with code independent from the
     page's. If the card showed only the direct children, the numbers would not
     add up — and that was exactly the bug: before it said `c[6]`.
     Nundasuchus is used, which is the case that really distinguishes it: 5 levels and
     11 creatures above, with only 2 direct children. With Indoraptor nothing can
     be checked, because its upper branch is a single child and the number comes out
     the same both ways. */
  function cierre(u){
    var vistos = {}, frente = [u], niv = [];
    while (frente.length){
      var sig = [];
      frente.forEach(function(x){
        (C[x][6] || []).forEach(function(h){
          if (C[h] && h !== u && !vistos[h]){ vistos[h] = 1; sig.push(h); }
        });
      });
      if (!sig.length) break;
      niv.push(sig); frente = sig;
    }
    return niv;
  }
  var U_LLEGA = "nundasuchus";
  elegir(U_LLEGA);
  var espNiv = cierre(U_LLEGA);
  var espTotal = espNiv.reduce(function(a, n){ return a + n.length; }, 0);
  var hijosDirectos = (C[U_LLEGA][6] || []).length;
  var enLleva = document.querySelectorAll("#elegida .lleva button.ir");
  var separadores = document.querySelectorAll("#elegida .lleva > span").length;
  ok("«Lleva a» shows the WHOLE upper branch, not just the direct children",
     enLleva.length === espTotal,
     enLleva.length + " names; the transitive closure is " + espTotal +
     " in " + espNiv.length + " levels");
  ok("and that is why there are more than the direct children", espTotal > hijosDirectos,
     espTotal + " vs " + hijosDirectos + " direct children");
  ok("and it groups them by levels, so that it can be seen that some come from others",
     separadores === espNiv.length - 1,
     separadores + " separators for " + espNiv.length + " levels");
  var llevaMal = [], llevaU = [];
  Array.prototype.forEach.call(enLleva, function(b){
    llevaU.push(b.dataset.ir);
    if (b.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) llevaMal.push(C[b.dataset.ir][0]);
  });
  ok("each name in «Lleva a» carries the colour of ITS rarity", llevaMal.length === 0,
     enLleva.length + " names" + (llevaMal.length ? " | bad: " + llevaMal.join(", ") : ""));
  ok("and none is repeated, even if the graph has diamonds",
     new Set(llevaU).size === llevaU.length, llevaU.length + " names, " +
     new Set(llevaU).size + " distinct");
  var destino = enLleva[enLleva.length - 1].dataset.ir;
  enLleva[enLleva.length - 1].click();
  ok("pressing a name in «Lleva a» loads that creature in the calculator",
     elegido === destino, "chosen=" + elegido + ", expected " + destino);

  // (c) the tree report: no «Rareza» column, clickable and coloured name
  elegir("indoraptor");
  var inf = document.getElementById("informeArbol");
  var cab = [];
  Array.prototype.forEach.call(inf.querySelectorAll("thead th"), function(th){
    cab.push(th.textContent.trim());
  });
  ok("the report no longer has a «Rareza» column", cab.indexOf("Rareza") === -1, cab.join(" | "));
  /* The «Veces» one was removed on 25-sep-2026 at n30's request: «it gives no
     useful information». It is checked that it does NOT come back, just like with «Rareza». */
  ok("nor the «Veces» one, removed for giving no useful information",
     cab.indexOf("Veces") === -1, cab.join(" | "));
  ok("and the first column is still the creature", cab[0] === "Criatura", cab[0]);
  /* The TABLE cannot carry tags: the colour of the name already says the rarity, and
     a tag next to it would be saying the same thing twice. The breakdown «DNA that
     has to be collected, by rarity» below DOES carry them, and that is correct:
     there the tag is the key to the figure, not an ornament of the name. */
  ok("the report table paints no rarity tag",
     inf.querySelector("table").querySelectorAll(".tag").length === 0,
     inf.querySelector("table").querySelectorAll(".tag").length + " tags in the table");
  var nomInf = inf.querySelectorAll("tbody tr button.ir");
  var infMal = [];
  Array.prototype.forEach.call(nomInf, function(b){
    if (b.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) infMal.push(C[b.dataset.ir][0]);
  });
  ok("each name in the report carries the colour of the rarity of ITS creature",
     nomInf.length > 0 && infMal.length === 0,
     nomInf.length + " names" + (infMal.length ? " | bad: " + infMal.join(", ") : ""));
  var uInf = nomInf[1] ? nomInf[1].dataset.ir : null;
  nomInf[1].click();
  ok("pressing the name in the report loads that creature",
     !!uInf && elegido === uInf, "chosen=" + elegido + ", expected " + uInf);

  // (d) «se recolecta» no longer exists: instead, the real zone of each creature
  /* The PILL is searched for, not the text: the report prose says «hasta las que
     se recolectan», and searching for the loose string made the failure be the test's. */
  var pildorasRecolecta = 0;
  document.querySelectorAll(".pill").forEach(function(p){
    if (/^se recolecta$/i.test(p.textContent.trim())) pildorasRecolecta++;
  });
  ok("the «se recolecta» pill no longer exists anywhere",
     pildorasRecolecta === 0, pildorasRecolecta + " pills with that text");
  document.querySelector('nav button[data-t="arbol"]').click();
  pintarArbol();
  var nodosArb = document.querySelectorAll("#arbolCuerpo .nodo");
  var zonasVistas = [], zonaMal = null, nodosConZona = 0, fuera = [];
  /* The valid tags are taken from the MODEL, not from the page: if someone
     wrote a text by hand («near your house»), it would not be here and the test
     would fail. Comparing against `zonaDe` would be a mirror: the same
     misunderstanding would pass green on both sides. */
  var etiquetasValidas = {};
  Object.keys(M.locEtiquetas).forEach(function(k){
    etiquetasValidas[String(M.locEtiquetas[k]).replace(/\s*\|\s*All Day$/, "")] = 1;
  });
  Array.prototype.forEach.call(nodosArb, function(n){
    if (n.classList.contains("raiz")) return;
    var p = n.querySelector(".cab .pill");
    var inp = n.querySelector("input[data-campo='adn']");
    if (!p || !inp) return;
    nodosConZona++;
    var t = p.textContent.trim();
    zonasVistas.push(t);
    // (1) the text has to be the one the model gives for THAT creature
    if (t !== zonaDe(inp.dataset.u, true)) zonaMal = inp.dataset.u;
    // (2) and each piece has to be a model tag, not invented text
    if (t !== "sin fuente en el mapa" && t !== "solo en santuario"){
      t.split(/\s*·\s*/).forEach(function(trozo){
        if (trozo === "combate") return;
        if (!etiquetasValidas[trozo]) fuera.push(inp.dataset.u + " -> '" + trozo + "'");
      });
    }
  });
  ok("the tree ingredients show their collection zone",
     nodosConZona > 0, nodosConZona + " nodes with zone: " + zonasVistas.slice(0, 3).join(" | "));
  ok("and the zone shown is the model's, creature by creature", !zonaMal,
     zonaMal ? zonaMal + " says '" + zonaDe(zonaMal, true) + "'" : "all match");
  ok("and no piece of the zone is invented text: they all come from the model",
     fuera.length === 0, fuera.length ? fuera.slice(0, 3).join(" ;; ")
                                      : "all the pieces are in the model");
  /* The raw datum brings the time slot attached («Local Area 3 | All Day») and in the
     pill it is removed: the seven map zones are the four slots, so
     «All Day» distinguishes nothing and stretched the pill to 49 characters. */
  ok("the zone pill does not drag along the redundant time slot",
     !zonasVistas.some(function(t){ return /All Day/.test(t); }),
     zonasVistas.slice(0, 3).join(" | "));
  ok("the zone pill goes with the colour of the status pills, not with a rarity one",
     (function(){
       var z = document.querySelector("#arbolCuerpo .nodo:not(.raiz) .cab .pill");
       var r = document.querySelector("#arbolCuerpo .nodo.raiz .cab .pill");   // «raíz»
       if (!z || !r) return false;
       return getComputedStyle(z).color === getComputedStyle(r).color;
       })(), "compared with the «raíz» pill of the root node");

  /* A name in the fusion tree is the same `nombreIr` button as in the report and
     in the search list, so it hangs off the same `data-ir` contract: the test
     presses one and requires the calculator to open with THAT creature. The node
     is picked before pressing, because pressing hides the tree. */
  var enArbol = document.querySelector("#arbolCuerpo .nodo:not(.raiz) .cab button[data-ir]");
  if (enArbol){
    var uArbol = enArbol.dataset.ir;
    enArbol.dispatchEvent(new MouseEvent("click", {bubbles:true}));
    ok("a click on a name in the fusion tree opens its calculator",
       document.getElementById("s-calc").classList.contains("on") && elegido === uArbol,
       "chosen=" + elegido + " · pressed=" + uArbol + " · calc tab=" +
       document.getElementById("s-calc").classList.contains("on"));
  } else {
    ok("a click on a name in the fusion tree opens its calculator", false,
       "no clickable name in the tree");
  }

  /* The card of the chosen creature. The zone pill only has to show up if it
     says something: in a hybrid its source is `none` (248 of the 518) and «sin fuente en
     el mapa» is noise — a hybrid is not searched for, it is fused. It is checked with
     the independent criterion: empty ingredients, or a real source in the model. */
  var faltan = [], sobran = [], nBase = 0, nHib = 0;
  /* And the class badge that goes before the name. Creature by creature, because
     the label and the file both come from the value in the data: an icon that
     says «fierce» over a cunning creature would be worse than no icon. */
  var sinClase = [], claseMal = [], claseSinNombre = [];
  Object.keys(C).forEach(function(u){
    elegir(u);
    var hay = !!document.querySelector("#elegida .pill.zona");
    var esBase = !(C[u][5] && C[u][5].length);
    var tieneFuente = (C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; });
    var deberia = esBase || tieneFuente;
    if (esBase) nBase++; else nHib++;
    if (deberia && !hay) faltan.push(u);
    var im = document.querySelector("#elegida .cab .nombre img.clase-i");
    if (!im){ sinClase.push(u + " (" + C[u][10] + ")"); }
    else {
      if (im.getAttribute("src") !== "img/clase/" + C[u][10] + ".png")
        claseMal.push(u + " -> " + im.getAttribute("src"));
      /* The word travels in the alt and in the tooltip, and in SPANISH: an icon
         alone only means something to whoever already knows it, and the raw code
         («wild_card») is not a name. */
      if (!im.alt || im.title.indexOf("Clase: ") !== 0)
        claseSinNombre.push(u + " alt=" + im.alt + " title=" + im.title);
    }
    if (!deberia && hay) sobran.push(u);
  });
  ok("the zone pill is missing in none that should carry it", faltan.length === 0,
     faltan.length ? faltan.length + " without pill: " + faltan.slice(0, 6).join(", ") : "none of " + nBase + " base");
  ok("and it is not superfluous in any hybrid without a source", sobran.length === 0,
     sobran.length ? sobran.length + " with a filler pill: " + sobran.slice(0, 6).join(", ") : "none of " + nHib + " hybrids");
  ok("the 518 split between 270 without ingredients and 248 hybrids", nBase === 270 && nHib === 248,
     nBase + " base + " + nHib + " hybrids = " + (nBase + nHib));
  ok("all 518 show their class badge before the name", sinClase.length === 0,
     sinClase.length ? sinClase.length + " without badge: " + sinClase.slice(0, 6).join(", ")
                     : "518 with badge, from the class in the data");
  ok("and the badge is the file of ITS class, not another one", claseMal.length === 0,
     claseMal.length ? claseMal.slice(0, 6).join(" ;; ") : "the 7 files of img/clase/");
  ok("and the class is named in words (Spanish), not left as the raw code",
     claseSinNombre.length === 0,
     claseSinNombre.length ? claseSinNombre.slice(0, 6).join(" ;; ")
                           : "«Clase: Astuta Feroz» and the other six");
  /* The concrete case that motivates the rule: a hybrid without a source must not say
     «sin fuente en el mapa». A real one is chosen, it is not assumed. */
  var hibSinFuente = Object.keys(C).filter(function(u){
    return (C[u][5] && C[u][5].length) && !(C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; }); })[0];
  elegir(hibSinFuente);
  ok("a hybrid without a source (" + C[hibSinFuente][0] + ") does not say «sin fuente en el mapa»",
     document.querySelector("#elegida").textContent.indexOf("sin fuente en el mapa") === -1,
     "card text searched whole");
  var hibConFuente = Object.keys(C).filter(function(u){
    return (C[u][5] && C[u][5].length) && (C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; }); });
  ok("and the hybrid that DOES appear on the map keeps its pill", hibConFuente.length >= 1,
     hibConFuente.length ? hibConFuente.map(function(u){ return C[u][0]; }).join(", ") : "none");
  if (hibConFuente.length){
    elegir(hibConFuente[0]);
    var pz = document.querySelector("#elegida .pill.zona");
    ok("  (" + C[hibConFuente[0]][0] + " shows «" + (pz ? pz.textContent.trim() : "nothing") + "»)", !!pz,
       pz ? "with pill" : "without pill");
  }

  // ======================================================================
  //  The dino's stats, where «Filtrar por rareza» used to be
  // ======================================================================
  ok("the rarity filter is no longer on the page",
     !document.getElementById("fRar") &&
     document.body.innerText.indexOf("Filtrar por rareza") < 0, "");

  var panelS = document.getElementById("panelStats");
  var fichas = panelS ? panelS.querySelectorAll(".st") : [];
  ok("in its place there is a stats panel with six cards", fichas.length === 6,
     fichas.length + " cards");
  var nombresS = [], iconosS = [];
  fichas.forEach(function(f){
    nombresS.push(f.querySelector(".st-k").textContent);
    iconosS.push(f.querySelector("img").getAttribute("src"));
  });
  ok("the six cards carry their name, whole and in order",
     nombresS.join("|") === "Vida|Daño|Velocidad|Armadura|Crítico|Daño crít.",
     nombresS.join(" | "));
  ok("and their icon, different in each one", new Set(iconosS).size === 6, iconosS.join(" "));
  ok("the icons come from the project folder, not from the internet",
     iconosS.every(function(s){ return s.indexOf("img/stat/") === 0; }), iconosS.join(" "));

  /* The values at LEVEL 26 have to be EXACTLY those of the datum: at that level
     the multiplier is 1.000000 and there is nothing to scale. And the numbers of
     the comparison are written HERE, not read from the model: they are the ones
     paleo.gg shows in its own cached alacranix card. If the page invented a
     scale, this catches it. */
  function seis(){ return M.statsOrden.map(function(k){
    return document.getElementById("stV_" + k).textContent; }).join(" "); }
  /* Leaves the creature at a specific level and at zero in everything. The level is a
     PARAMETER and not a constant: taking a level for granted was the mistake of the
     first version of these tests, which accepted 30 after having set 26 and
     failed pointing at the wrong place. */
  function cero(u, niv){
    fijar(u, "nivel", niv); fijar(u, "adn", 0);
    ["bVida","bDano","bVel","mejora"].forEach(function(c){ fijar(u, c, 0); });
  }
  elegir("alacranix"); cero("alacranix", 26); pintarStats();
  var a26 = seis();
  ok("at level 26 the stats are the datum's, with no scaling at all",
     a26 === "4,250 1,650 115 40% 15% 125%", a26);

  /* The level scales HEALTH and DAMAGE and nothing else. It is a STRUCTURE
     check, not a table one: it does not depend on the multiplier being correct. */
  fijar("alacranix", "nivel", 30); pintarStats();
  var a30 = seis().split(" ");
  var b26 = a26.split(" ");
  ok("levelling up raises health and damage",
     a30[0] !== b26[0] && a30[1] !== b26[1],
     "level 26: " + b26[0] + "/" + b26[1] + "  ->  level 30: " + a30[0] + "/" + a30[1]);
  ok("and it does NOT touch speed, armor or crits",
     a30[2] === b26[2] && a30[3] === b26[3] && a30[4] === b26[4] && a30[5] === b26[5],
     a30.slice(2).join(" "));

  // --- the boost points: they are saved, added up and capped ---
  cero("alacranix", 30); pintarStats();
  var vel0 = Number(document.getElementById("stV_velocidad").textContent);
  var masV = document.querySelector('#panelStats [data-boost="bVel"][data-paso="1"]');
  var menV = document.querySelector('#panelStats [data-boost="bVel"][data-paso="-1"]');
  ok("with zero points, the minus control is off and the plus one is not",
     menV.disabled === true && masV.disabled === false, "");
  for (var i1 = 0; i1 < 5; i1++) masV.click();
  ok("five speed points raise speed by 10 (2 per point)",
     Number(document.getElementById("stV_velocidad").textContent) === vel0 + 10,
     vel0 + " -> " + document.getElementById("stV_velocidad").textContent);
  ok("and they remain saved in the inventory, not only on screen",
     INV["alacranix"] && INV["alacranix"].bVel === 5, JSON.stringify(INV["alacranix"]));
  ok("the counter shows the points out of the cap",
     /Puntos\s*5\s*de\s*30/.test(document.getElementById("stNota").innerText.replace(/\s+/g, " ")),
     document.getElementById("stNota").innerText.replace(/\s+/g, " "));
  menV.click();
  ok("and the minus control really removes one point", INV["alacranix"].bVel === 4,
     JSON.stringify(INV["alacranix"]));

  /* The cap is for the SET of the three stats, not for each one: 20 per stat AND
     the sum without exceeding the cap. It is checked through the interface path. */
  fijar("alacranix", "bVida", 20); pintarStats();
  ok("a single stat does not go over 20 points",
     document.querySelector('#panelStats [data-boost="bVida"][data-paso="1"]').disabled === true, "");
  /* The trimming of the set is NOT reachable from the controls —the plus one
     turns off before exceeding—, so it is tested through where it does enter: a direct
     write, which is the IMPORT path. */
  fijar("alacranix", "bDano", 20); fijar("alacranix", "bVel", 20); pintarStats();
  var mAl = mejDe("alacranix"), sumaAl = mAl.bVida + mAl.bDano + mAl.bVel;
  ok("an import that goes over the cap is trimmed, and it is saved trimmed",
     sumaAl === mAl.tope && sumaAl === 30, sumaAl + " of " + mAl.tope +
     "  " + JSON.stringify(INV["alacranix"]));

  /* The enhancement track. And here is what a SUPPOSITION of mine had wrong: the
     order of the steps is NOT the same in Unique and in Apex. In Apex the boost_max
     is step 3 and is worth 2; in Unique it is step 4 and is worth 1. These two cases
     were written after seeing it in a screenshot, because the code reads them from
     the datum and I had taken them for equal. */
  elegir("alacranix"); cero("alacranix", 30); pintarStats();
  ok("with no track set, the point cap is the level", topePuntos("alacranix") === 30,
     "" + topePuntos("alacranix"));
  for (var i2 = 0; i2 < 3; i2++) cambiarMejora("alacranix", "mejora", 1);
  ok("in Apex step 3 already gives +2 to the cap (its boost_max is worth 2)",
     topePuntos("alacranix") === 32, "" + topePuntos("alacranix"));
  /* The catalyst and coin icons only appear in the cost line, and that line only
     exists with a track and a step ahead: they are collected HERE so that the
     "all images load" check covers them. Without this, the three catalysts were
     not checked anywhere. */
  document.querySelectorAll("#stCoste img").forEach(function(im){
    var s2 = im.getAttribute("src");
    if (!CLONES.some(function(c){ return c.src === s2; })){
      var c2 = new Image(); c2.src = s2;
      c2.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
      document.body.appendChild(c2);
      CLONES.push({src: s2, el: c2});
    }
  });

  elegir("indoraptor"); cero("indoraptor", 30);
  for (var i3 = 0; i3 < 3; i3++) cambiarMejora("indoraptor", "mejora", 1);
  ok("in Unique step 3 does NOT touch the cap: its boost_max is at 4",
     topePuntos("indoraptor") === 30, "" + topePuntos("indoraptor"));
  cambiarMejora("indoraptor", "mejora", 1);
  ok("and step 4 gives +1, not +2", topePuntos("indoraptor") === 31, "" + topePuntos("indoraptor"));

  /* The track only exists from level 30 on, and on going down it is SAVED as 0: what
     is seen has to be what is saved, or on reloading something else would appear. */
  fijar("indoraptor", "nivel", 29); pintarStats();
  ok("below level 30 the enhancement control is off",
     document.querySelector('#panelStats [data-boost="mejora"][data-paso="1"]').disabled === true, "");
  ok("and the track is trimmed to 0 ALSO in the inventory",
     INV["indoraptor"].mejora === 0 && document.getElementById("stP_mejora").textContent === "0",
     JSON.stringify(INV["indoraptor"]));
  ok("the point cap is the level again, with no bonus",
     document.getElementById("stNota").innerText.indexOf("tope = nivel 29") > 0,
     document.getElementById("stNota").innerText.replace(/\s+/g, " "));

  /* ---------- the Omega training points (design «editable grid») ---------- */
  /* The pool is 7 per level and the increment and the cap of each stat are the
     source's own per creature. Everything here goes through the panel or through
     `fijar`, and is read back from what is painted. */
  function num(id){
    return Number((document.getElementById(id).textContent || "").replace(/[^\d-]/g, ""));
  }
  var OM = "93_classic_t_rex";
  elegir(OM); fijar(OM, "nivel", 26);
  ENT_CAMPOS.forEach(function(c){ fijar(OM, c, 0); });
  pintarStats();
  ok("an Omega shows the training controls, inside the six cards",
     document.getElementById("panelStats").getAttribute("data-ent") === "1" &&
     document.querySelectorAll("#stRejilla .st-ctl").length === 6,
     document.querySelectorAll("#stRejilla .st-ctl").length + " blocks · data-ent=" +
     document.getElementById("panelStats").getAttribute("data-ent"));
  var pozoTxt = document.getElementById("stPozo").innerText.replace(/\s+/g, " ");
  ok("the pool is 7 per level and the box says so",
     mejDe(OM).pozo === 182 && /182/.test(pozoTxt) && /7 por nivel/.test(pozoTxt),
     pozoTxt);
  /* A stat with `delta` 0 (this creature's armour) has nothing to give: its plus
     is born off, and that is what tells the user the stat cannot be trained. */
  ok("a stat with no increment has its plus off from the start",
     document.querySelector('#panelStats [data-boost="tArm"][data-paso="1"]').disabled === true &&
     document.querySelector('#panelStats [data-boost="tVida"][data-paso="1"]').disabled === false,
     "armadura off, vida on");
  var vida0 = num("stV_vida");
  document.querySelector('#panelStats [data-boost="tVida"][data-paso="1"]').click();
  ok("one training point raises health by the source's increment (35)",
     num("stV_vida") === vida0 + 35 && INV[OM].tVida === 1,
     vida0 + " -> " + num("stV_vida") + " · " + JSON.stringify(INV[OM]));
  ok("and the card says what a point is worth and where that stat tops out",
     /* The thousands separator is the language's: Spanish (es-MX) writes 6,145,
        not 6.145. The regex takes either so that it cannot pass by not matching. */
     /entrenamiento: \+35 por punto, tope 6[,.]145 \(137 puntos\)/
       .test(document.getElementById("stV_vida").closest(".st").title),
     document.getElementById("stV_vida").closest(".st").title);
  /* The per-stat cap and the shared pool, the two digits that bound every button. */
  fijar(OM, "tVida", 137); fijar(OM, "tCri", 45); pintarStats();
  ok("health reaches its cap (6.145) with exactly the 137 points the source gives",
     num("stV_vida") === 6145 && INV[OM].tVida === 137,
     num("stV_vida") + " with " + INV[OM].tVida + " points");
  ok("with the pool spent (137 + 45 = 182) every plus is off",
     document.querySelector('#panelStats [data-boost="tCri"][data-paso="1"]').disabled === true &&
     document.querySelector('#panelStats [data-boost="tVida"][data-paso="1"]').disabled === true &&
     /quedan 0/.test(document.getElementById("stPozo").innerText.replace(/\s+/g, " ")),
     document.getElementById("stPozo").innerText.replace(/\s+/g, " "));
  ok("and the minus still works, so a point can be moved somewhere else",
     document.querySelector('#panelStats [data-boost="tCri"][data-paso="-1"]').disabled === false, "");
  /* Going down a level shrinks the pool, and the points are given back in the
     order the game does it: from the last stat backwards (crit damage, crit...). */
  fijar(OM, "nivel", 11); pintarStats();
  ok("going down to level 11 trims the pool (77) taking back crit first",
     INV[OM].tVida === 77 && INV[OM].tCri === 0 && mejDe(OM).usados === 77,
     JSON.stringify({vida: INV[OM].tVida, crit: INV[OM].tCri, usados: mejDe(OM).usados}));
  /* And a creature without training is exactly the card it was. */
  elegir("indoraptor"); pintarStats();
  ok("a creature that is not an Omega keeps the panel it had",
     document.getElementById("panelStats").getAttribute("data-ent") === "0" &&
     document.querySelectorAll("#stRejilla .st-ctl").length === 6 &&
     getComputedStyle(document.querySelector("#stRejilla .st-ctl")).display === "none",
     "data-ent=" + document.getElementById("panelStats").getAttribute("data-ent") +
     " · controls hidden");
  ok("and its pool box is empty",
     document.getElementById("stPozo").innerHTML === "" && mejDe("indoraptor").pozo === undefined,
     "pozo=" + mejDe("indoraptor").pozo);

  /* ---------- the game's own numbers for an Omega (28-sep-2026) ---------- */
  /* This is the case n30 measured in the game and that the panel got WRONG: the
     app multiplied the Omega's health and damage by the level, and the game does
     not — levelling an Omega gives training POINTS, not stats. Little Eatie at
     level 21, 7 x 21 = 147 points spent (73 to health, 74 to damage), 5 health
     boosts and 3 speed ones, as read off the game's screen:
        health    (1100 + 40 x 73) x 1.125 = 4522
        damage     400 + 25 x 74           = 2250
        speed      110 + 2 x 3             =  116
     With the level multiplier the same allocation gave 4001 and 1508, which is
     exactly what n30 reported. The three numbers together are what pins the rule:
     an allocation summing to the pool cannot be off by a constant. */
  var LE = "little_eatie";
  elegir(LE); fijar(LE, "nivel", 21);
  ENT_CAMPOS.forEach(function(c){ fijar(LE, c, 0); });
  ["bVida","bDano","bVel"].forEach(function(c){ fijar(LE, c, 0); });
  fijar(LE, "bVida", 5); fijar(LE, "bVel", 3);
  fijar(LE, "tVida", 73); fijar(LE, "tDano", 74);
  pintarStats();
  ok("an Omega does NOT scale with the level: the game's Little Eatie comes out exactly",
     num("stV_vida") === 4522 && num("stV_dano") === 2250 && num("stV_velocidad") === 116,
     "vida " + num("stV_vida") + " (juego 4522) · daño " + num("stV_dano") +
     " (juego 2250) · velocidad " + num("stV_velocidad") + " (juego 116)");
  ok("and the 147 points of the game's screen are exactly the pool of 7 x 21",
     mejDe(LE).pozo === 147 && mejDe(LE).usados === 147, JSON.stringify({
       pozo: mejDe(LE).pozo, usados: mejDe(LE).usados}));
  ok("and the base does not move with the level, which is the whole point",
     statsDe(LE, 21, {bVida:0,bDano:0,bVel:0,mejora:0})[0] ===
     statsDe(LE, 35, {bVida:0,bDano:0,bVel:0,mejora:0})[0],
     "nivel 21 y 35 sin puntos: " +
     statsDe(LE, 21, {bVida:0,bDano:0,bVel:0,mejora:0})[0]);

  /* A creature without a track must not show the control, nor let it be touched. */
  elegir("tyrannosaurus_rex"); pintarStats();
  ok("a creature without a track does not show the enhancement control",
     document.getElementById("stFilaMej").style.display === "none",
     "display=" + document.getElementById("stFilaMej").style.display);
  ok("and a track cannot be set on it no matter how much it is pressed",
     cambiarMejora("tyrannosaurus_rex", "mejora", 1) === false &&
     (INV["tyrannosaurus_rex"] || {}).mejora === undefined, "");

  // ======================================================================
  //  The theme, and the tab icon
  // ======================================================================
  var selT = document.getElementById("tema");
  var opsT = selT ? Array.prototype.map.call(selT.options, function(o){ return o.value; }) : [];
  ok("there is a theme dropdown with the default, the five Amber-* and «boring»",
     opsT.join(",") === "yellow,crystal,neon,oled,liquid,cinema,boring", opsT.join(","));
  /* The VALUES are the historical names (see the comment in plantilla.html): the
     default theme's value is «yellow» and what the user reads is «Default». The
     two TRANSLATED labels are checked in Spanish, because this run is pinned to
     Spanish; the Amber-* names are proper names and are not translated. */
  var txtT = selT ? Array.prototype.map.call(selT.options, function(o){ return o.textContent.trim(); }) : [];
  ok("and the labels are Default, the five Amber-* and Boring",
     txtT.join(",") === "Predeterminado,Amber-Crystal,Amber-Neon,Amber-OLED,Amber-Liquid,Amber-Cinema,Aburrido",
     txtT.join(","));
  ok("and the label of the control is translated too",
     document.querySelector('label[for="tema"]').textContent.trim() === "Tema",
     document.querySelector('label[for="tema"]').textContent.trim());

  /* The two controls of the header have to be LEVEL at the bottom. The language
     switch has no label and the theme has one, so aligning the tops (the old
     flex-start) left the switch floating above the <select>. It is measured, not
     eyeballed: a pixel of slack for the sub-pixel rounding. */
  var rIdioma = document.querySelector(".idioma").getBoundingClientRect();
  var rTema = document.getElementById("tema").getBoundingClientRect();
  ok("the language switch and the theme select are level at the bottom",
     Math.abs(rIdioma.bottom - rTema.bottom) <= 1,
     "idioma bottom " + rIdioma.bottom.toFixed(1) + " vs tema bottom " + rTema.bottom.toFixed(1));

  /* The test that really matters: the RARITY colours cannot change
     between themes. If they did, a theme would be exactly the confusion that
     n30 asked to avoid. The COMPUTED values are looked at, not the CSS text:
     reading the file only proves that the line is written. And it is checked in
     ALL SEVEN themes, not only in the two that existed before.
     The default palette is pinned first: the Firefox profile keeps localStorage
     between runs, and measuring «whatever was left over» is how a test ends up
     asserting on the wrong palette while still passing. */
  var raiz = document.documentElement;
  ponerTema("yellow");
  var claves = ["--r-comun","--r-rara","--r-epica","--r-legendaria","--r-unica",
                "--r-apex","--r-omega","--verde","--ambar","--rojo","--azul",
                "--pill","--st-acc"];
  function colores(){ var cs = getComputedStyle(raiz); return claves.map(function(k){
    return cs.getPropertyValue(k).trim(); }); }
  function marca(){ return getComputedStyle(raiz).getPropertyValue("--marca").trim().toLowerCase(); }
  function fondo(){ var cs = getComputedStyle(document.body);
    return cs.backgroundImage + "|" + cs.backgroundColor; }
  var colD = colores(), marcaD = marca(), bgD = getComputedStyle(document.body).backgroundColor;
  var fondoD = fondo();
  ok("the default theme is the amber one, on a deep-black background",
     marcaD === "#ff6d1f" && bgD === "rgb(0, 0, 0)", marcaD + " · " + bgD);

  /* The list of themes is READ FROM THE DROPDOWN, not written here: a theme
     added tomorrow is covered by this test without touching it. */
  var OTROS = opsT.filter(function(v){ return v !== "yellow"; });
  var AMBAR = OTROS.filter(function(v){ return v !== "boring"; });
  elegir("indoraptor");   // the card carries a rarity tag, to measure it painted
  var etiquetaD = getComputedStyle(document.querySelector("#elegida .tag")).color;
  var choques = [], mismoFondo = [], etiquetas = [];
  OTROS.forEach(function(t){
    ponerTema(t);
    var c = colores();
    c.forEach(function(v, i){ if (v !== colD[i]) choques.push(t + ":" + claves[i]); });
    if (fondo() === fondoD) mismoFondo.push(t);
    var e = getComputedStyle(document.querySelector("#elegida .tag")).color;
    if (e !== etiquetaD) etiquetas.push(t + ":" + e);
  });
  /* THE RULE OF THE PROJECT: a rarity colour is a DATUM. No theme may repaint
     it, or the same creature would say two different things depending on the
     theme. It is checked on the 13 computed variables AND on a real tag. */
  ok("THE RULE: no theme touches the 13 rarity or semantic colours",
     choques.length === 0,
     choques.length ? choques.slice(0, 6).join(", ")
                    : "the " + claves.length + " intact in the " + (OTROS.length + 1) + " themes");
  ok("nor repaints a rarity tag",
     etiquetas.length === 0,
     etiquetas.length ? etiquetas.slice(0, 4).join(", ") : "the tag stays " + etiquetaD);
  ok("and every theme changes the background",
     mismoFondo.length === 0,
     mismoFondo.length ? "same as the default: " + mismoFondo.join(", ")
                       : OTROS.length + " of " + OTROS.length + " different");

  /* The five Amber-* keep the AMBER brand — that is what «on the Default base»
     means — and «boring» is the only one with the green one. */
  var marcaAmbar = AMBAR.every(function(t){ ponerTema(t); return marca() === "#ff6d1f"; });
  ponerTema("boring");
  ok("the five Amber-* keep the amber brand and «boring» keeps the green one",
     marcaAmbar && marca() === "#4ade80", "ambar=" + marcaAmbar + " verde=" + (marca() === "#4ade80"));

  /* And each one applies its OWN effect, measured on the rendered page. */
  ponerTema("crystal");
  var cCristal = getComputedStyle(document.querySelector(".panel"));
  ok("Amber-Crystal applies the glass (backdrop-filter on the panels)",
     /blur\(/.test(cCristal.backdropFilter || cCristal.webkitBackdropFilter || ""),
     cCristal.backdropFilter || cCristal.webkitBackdropFilter || "(none)");
  ponerTema("neon");
  var cNeon = getComputedStyle(document.querySelector(".panel")).boxShadow;
  ok("Amber-Neon applies its amber halo", /255,\s*145,\s*45/.test(cNeon), cNeon.slice(0, 70));
  /* Amber-OLED: the Crystal depth on deep blacks with the orange accent. The
     pure-black page and the hairline of light are what tell it from Crystal. */
  ponerTema("oled");
  var cOled = getComputedStyle(document.querySelector(".panel"));
  ok("Amber-OLED is deep-black glass (blur + a #000 page)",
     /blur\(/.test(cOled.backdropFilter || cOled.webkitBackdropFilter || "") &&
     getComputedStyle(raiz).getPropertyValue("--bg").trim() === "#000000",
     "blur=" + (cOled.backdropFilter || "(none)") +
     " · --bg=" + getComputedStyle(raiz).getPropertyValue("--bg").trim());
  var hair = getComputedStyle(document.querySelector("header"), "::after").backgroundImage;
  ok("and it draws the amber hairline of light under the header",
     /linear-gradient/.test(hair), hair.slice(0, 70));
  ponerTema("liquid");
  ok("Amber-Liquid applies the flowing background animation",
     getComputedStyle(document.body).animationName === "amberLiquido",
     getComputedStyle(document.body).animationName);
  ponerTema("cinema");
  var cCinema = getComputedStyle(document.querySelector(".panel h2")).letterSpacing;
  ok("Amber-Cinema applies its quiet heading spacing", cCinema === "1.7px", cCinema);

  /* The attribute IS the option value, and the choice is saved. */
  ponerTema("oled");
  ok("the theme is applied as an attribute on <html>",
     raiz.getAttribute("data-tema") === "oled", "" + raiz.getAttribute("data-tema"));
  ok("and it is saved for next time",
     localStorage.getItem("jwa322.tema") === "oled", "" + localStorage.getItem("jwa322.tema"));
  ponerTema("yellow");
  ok("going back to the default removes the attribute, it does not leave it at «yellow»",
     raiz.getAttribute("data-tema") === null, "" + raiz.getAttribute("data-tema"));
  ok("and the dropdown follows the theme", selT.value === "yellow", selT.value);

  /* The tab icon: the only thing seen when the focus is on another
     tab. That the <link> exists proves nothing — that the image LOADS, yes. */
  var ico = document.querySelector('link[rel="icon"]');
  ok("there is a tab icon, and it is inline so as not to depend on a file",
     !!ico && ico.href.indexOf("data:image/svg+xml") === 0,
     ico ? ico.href.slice(0, 44) + "…" : "there is no <link rel=icon>");
  if (ico){
    var ci = new Image();
    ci.src = ico.href;
    ci.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
    document.body.appendChild(ci);
    CLONES.push({src: "(tab favicon)", el: ci});
  }
  log("", "");

  // --- 2) eager clones of each image, so that they block `load` ---
  var srcs = [];
  document.querySelectorAll("img").forEach(function(im){
    var s = im.getAttribute("src");
    if (s && srcs.indexOf(s) < 0) srcs.push(s);
  });
  log("distinct images referenced", srcs.length);
  srcs.forEach(function(s){
    var c = new Image();
    c.src = s;
    c.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
    document.body.appendChild(c);      // eager by default: blocks load
    CLONES.push({src: s, el: c});
  });

  // --- the focus is checked on `load`, not here ---
  // The page repositions the focus on the next turn (setTimeout 0), so
  // checking it on the same tick would give a false failure.
  // And you have to GO BACK to the tree tab: the previous section leaves the
  // calculator active, and a field inside a section in display:none cannot
  // receive focus — .focus() fails silently and activeElement stays on BODY.
  /* And a creature with ingredients has to be CHOSEN: the tree only has child
     nodes if the chosen one is fused. Depending on the one the previous block left
     made this test fall over —with an `el is null`— as soon as someone
     touched the order of the checks. */
  elegir("indoraptor");
  document.querySelector('nav button[data-t="arbol"]').click();
  pintarArbol();
  var ingFoco = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  FOCO_U = ingFoco ? ingFoco.dataset.u : null;
  teclear(ingFoco, "777");
  ok("the typed value survives the repaint",
     !!INV[FOCO_U] && INV[FOCO_U].adn === 777, JSON.stringify(INV[FOCO_U]));
} catch (e) {
  /* An abort in the middle of the pass must NOT come out green. `log()` writes a
     note and `veredicto()` only reads the `OK ` and `FALLO ` rows, so an
     exception that cut this pass in half left a shorter «all OK» behind: it
     happened on 27-sep-2026, a helper that does not exist in this block threw and
     the run passed with 99 checks where there had been 152, with the last 53
     checks simply not running. A failure row makes it red, which is what it is. */
  RES.push("FALLO the pass could not finish: " + e.message +
           " @@ " + (e.stack || "").split("\n")[1]);
  FALLOS++;
}

// --- 3) the report, now with the images resolved ---
window.addEventListener("load", function(){
  // the focus, now with the page's asynchronous repositioning done
  if (FOCO_U){
    var ae = document.activeElement;
    ok("the tree repaints without losing focus",
       ae && ae.dataset && ae.dataset.u === FOCO_U && ae.dataset.campo === "adn",
       "expected u=" + FOCO_U + " field=adn | real: " + (ae ? ae.tagName : "nothing") +
       " u=" + (ae && ae.dataset ? ae.dataset.u : "?") +
       " field=" + (ae && ae.dataset ? ae.dataset.campo : "?"));
  }

  var bien = 0, mal = [];
  CLONES.forEach(function(c){
    if (c.el.complete && c.el.naturalWidth > 0) bien++; else mal.push(c.src);
  });
  if (CLONES.length){
    ok("all the image files load and decode", mal.length === 0,
       bien + "/" + CLONES.length + " ok" + (mal.length ? "  fail: " + mal.slice(0,3).join(", ") : ""));
    var una = CLONES[0].el;
    log("example image", una.naturalWidth + "x" + una.naturalHeight + "  " + una.src.split("/").pop());
  }
  log("", "");
  log(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===", "");

  var d = document.createElement("pre");
  d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:15px/1.5 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\n");
  document.body.appendChild(d);
__ENTREGA__
});
</script>
"""

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)
# the images are referenced as img/<uuid>.webp, relative to the HTML
enlace = os.path.join(DIR, "img")
if os.path.islink(enlace):
    if os.readlink(enlace) != IMG:
        os.unlink(enlace)          # os.remove is intercepted by the system shim
elif os.path.isdir(enlace):
    shutil.rmtree(enlace, ignore_errors=True)
if not os.path.exists(enlace):
    os.symlink(IMG, enlace)

# An error hunter BEFORE the main script: if the script blows up on
# loading, everything it defines stops existing and the symptom is "X is not defined",
# which says nothing. This gives the real error.
CAZA = r"""
<script>
window.__errores = [];
window.addEventListener("error", function(e){
  window.__errores.push((e.message || "?") + "  @@ line " + (e.lineno||"?") +
                        ":" + (e.colno||"?"));
});
</script>
"""

html = open(HTML, encoding="utf-8").read()
# Pin the language for this run: the assertions below read the Spanish
# rendering, and the app now boots in English. It goes in the <head> because
# that is where the app resolves the language, and the injected value beats
# whatever a previous run stored.
PIN = ('<script>window.__lang = "es";'
       'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
if "<head>" not in html:
    raise SystemExit("I cannot find <head> to pin the language")
html = html.replace("<head>", "<head>\n" + PIN, 1)
# The viewer may leave attributes on <body> (data-page-node-id), so it is no
# good searching for "<body>" as is.
m = re.search(r"<body[^>]*>", html)
if not m:
    raise SystemExit("the HTML has no <body>")
html = html[:m.end()] + CAZA + html[m.end():]
# Before opening the browser: if the diagnostic does not compile together with the
# application —name collision in the global scope—, the test would be left unrun and
# the symptom would be «it did not deliver the report», which says nothing. See informe_browser.
_ok_scripts, _msg_scripts = comprobar_scripts(html + DIAG, "probar_ui.py")
print(_msg_scripts)
if not _ok_scripts:
    raise SystemExit("!! " + _msg_scripts)
open(FUERA, "w", encoding="utf-8").write(html)
with open(FUERA, "a", encoding="utf-8") as f:
    f.write(DIAG.replace("__ENTREGA__", srv.js("__diag")))

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
cmd = ["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
       "--window-size", "1400,2000", "--screenshot", SHOT, "file://" + FUERA]
r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
if r.stderr.strip() and "headless" not in r.stderr:
    print("stderr:", r.stderr.strip()[:500])
print("png:", SHOT, os.path.getsize(SHOT) if os.path.exists(SHOT) else "NO")

srv.parar()
informe = srv.texto().strip()
TXT = os.path.join(DIR, "ui.txt")
open(TXT, "w", encoding="utf-8").write(informe + "\n")
print("report:", TXT)
print("-" * 72)
print(informe)
print("-" * 72)
codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)


# ---------------------------------------------------------------------------
# SECOND RUN: the photo strip, on the REAL STARTUP.
#
# It does not fit in the run above, and it is not a whim: the one above paints the
# strip FROM INSIDE the `load` event, so its <img> are inserted when the
# event has already passed and always come out half loaded. Measured: it gave 0x0 with `lazy` and
# 0x0 also with `eager`, that is, it distinguished nothing.
#
# Here `localStorage` is seeded BEFORE the main script, so that the
# `pintarFotos()` of the startup already finds the list: that is the user's
# path. And what really matters is measured —that the image is visible—, not whether the
# attribute says `lazy` or `eager`.
#
# This is the bug it catches: with `loading="lazy"`, the photos of the strip were
# NEVER loaded on startup (naturalWidth 0 in all three), even though the
# files were fine — eager clones of the SAME addresses loaded
# without a problem— and the alternative text came out in their place. With `eager` they load
# (207x250). That is why the strip is eager and the tree is still lazy.
# ---------------------------------------------------------------------------
def pasada_tira():
    DIR2 = "/tmp/jwa-ui-tira"
    PERFIL2 = os.path.join(DIR2, "perfil")
    FUERA2 = os.path.join(DIR2, "tira.html")
    SHOT2 = os.path.join(DIR2, "tira.png")
    os.makedirs(DIR2, exist_ok=True)
    os.makedirs(PERFIL2, exist_ok=True)
    enlace = os.path.join(DIR2, "img")
    if os.path.islink(enlace):
        if os.readlink(enlace) != IMG:
            os.unlink(enlace)
    if not os.path.exists(enlace):
        os.symlink(IMG, enlace)

    html = open(HTML, encoding="utf-8").read()
    # Pin the language for this run: the assertions below read the Spanish
    # rendering, and the app now boots in English. It goes in the <head>
    # because that is where the app resolves the language, and the injected
    # value beats anything a previous run stored.
    PIN = ('<script>window.__lang = "es";'
           'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
    if "<head>" not in html:
        raise SystemExit("I cannot find <head> to pin the language")
    html = html.replace("<head>", "<head>\n" + PIN, 1)
    LISTA = '["indoraptor","tyrannosaurus_rex","velociraptor"]'
    SEMILLA = (
        "<script>\n"
        "/* BEFORE the main script: the startup painting already finds the list. */\n"
        "try { localStorage.setItem('jwa322.mios', JSON.stringify(" + LISTA + ")); } catch(e){}\n"
        "</script>\n")
    marca = '<script>\n"use strict";'
    if marca not in html:
        raise SystemExit("I cannot find the main script to seed before")
    html = html.replace(marca, SEMILLA + marca, 1)

    srv2 = arrancar()
    diag = r"""
<script>
window.addEventListener("load", function(){
  var RES = [], FALLOS = 0;
  function ok(k, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + k + ": " + (d===undefined?"":d)); }
  try {
    var imgs = document.querySelectorAll("#misFotos img");
    ok("the startup paints the strip with the saved list", imgs.length === 3, imgs.length + " photos");
    var malas = [], vistas = [];
    imgs.forEach(function(im){
      vistas.push(im.getAttribute("src") + " " + im.naturalWidth + "x" + im.naturalHeight);
      if (!(im.naturalWidth > 0)) malas.push(im.getAttribute("src"));
    });
    ok("and the photos are LOADED when the startup finishes, not half-way",
       imgs.length > 0 && malas.length === 0,
       malas.length ? "not loaded: " + malas.join(", ") : vistas.join(" | "));
    // and they are really visible: an image loaded but with visibility:hidden is no good
    var ocultas = 0;
    imgs.forEach(function(im){ if (getComputedStyle(im).visibility !== "visible") ocultas++; });
    ok("and none is hidden because of a load failure", ocultas === 0, ocultas + " hidden");
    // the tree can still be lazy: 518 files at once, no
    var vagas = document.querySelectorAll('#arbolCuerpo img[loading="lazy"]').length;
    RES.push("   (informational) lazy images in the tree: " + vagas);
  } catch(e){ RES.push("!! EXCEPTION " + e.message); FALLOS++; }
  /* The marker is not decorative: `veredicto()` accepts the run ONLY if
     it finds it, and otherwise declares it failed. Without this line, the run came out
     with 0 failures and the script ended in 1 all the same. */
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var p = document.createElement("pre"); p.id = "__diag";
  p.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;" +
                    "font:13px/1.5 monospace;padding:14px;margin:0;white-space:pre-wrap";
  p.textContent = RES.join("\n"); document.body.appendChild(p);
__ENTREGA__
});
</script>"""
    open(FUERA2, "w", encoding="utf-8").write(html)
    with open(FUERA2, "a", encoding="utf-8") as f:
        f.write(diag.replace("__ENTREGA__", srv2.js("__diag")))
    _ok2, _msg2 = comprobar_scripts(html + diag, "probar_ui.py (the strip)")
    print(_msg2)
    if not _ok2:
        raise SystemExit("!! " + _msg2)

    env = dict(os.environ)
    env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
                "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR2})
    subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL2,
                    "--window-size", "1400,1400", "--screenshot", SHOT2,
                    "file://" + FUERA2], env=env, capture_output=True, text=True, timeout=180)
    srv2.parar()
    info2 = srv2.texto().strip()
    print("-" * 72)
    print("=== the photo strip, on the real startup ===")
    print(info2)
    c2, lineas2 = veredicto(info2)
    for l in lineas2:
        print(l)
    return c2


# ---------------------------------------------------------------------------
# THIRD RUN: the theme at LOAD time.
#
# The stored value is read by the inline script in the <head>, before anything
# else runs, so the only way to test it is to seed localStorage and load the page
# once per case. A single page that calls `ponerTema()` while it is already open
# cannot prove the migration: that is a property of the startup, not of the
# function.
#
# It holds down the two things a rename breaks silently:
#   a) a stored «default» —the value the OLD green theme used— is read as
#      «boring», so whoever had chosen it keeps the same look;
#   b) the new default (amber, deep black) is what gets painted with nothing
#      stored, and it carries NO attribute.
# ---------------------------------------------------------------------------
def pasada_tema():
    DIR3 = "/tmp/jwa-ui-tema"
    PERFIL3 = os.path.join(DIR3, "perfil")
    os.makedirs(DIR3, exist_ok=True)
    os.makedirs(PERFIL3, exist_ok=True)
    enlace = os.path.join(DIR3, "img")
    if os.path.islink(enlace):
        if os.readlink(enlace) != IMG:
            os.unlink(enlace)
    if not os.path.exists(enlace):
        os.symlink(IMG, enlace)

    CASOS = [
        # (name, what is stored, expected data-tema, expected brand hex)
        ("nothing stored boots in the default theme",
         'localStorage.removeItem("jwa322.tema");', None, "#ff6d1f"),
        ("a stored «yellow» keeps the default theme",
         'localStorage.setItem("jwa322.tema","yellow");', None, "#ff6d1f"),
        ("a stored «default» —the value of the old green theme— is read as «boring»",
         'localStorage.setItem("jwa322.tema","default");', "boring", "#4ade80"),
        ("a stored «boring» stays «boring»",
         'localStorage.setItem("jwa322.tema","boring");', "boring", "#4ade80"),
        # The five Amber-* themes have to SURVIVE A RELOAD: the <head> script is
        # the only thing that runs before painting, and its list is separate from
        # the dropdown's. One case per value, because a typo in one of the five
        # would not show up in the others.
        ("a stored «crystal» boots in Amber-Crystal",
         'localStorage.setItem("jwa322.tema","crystal");', "crystal", "#ff6d1f"),
        ("a stored «neon» boots in Amber-Neon",
         'localStorage.setItem("jwa322.tema","neon");', "neon", "#ff6d1f"),
        ("a stored «oled» boots in Amber-OLED",
         'localStorage.setItem("jwa322.tema","oled");', "oled", "#ff6d1f"),
        ("a stored «liquid» boots in Amber-Liquid",
         'localStorage.setItem("jwa322.tema","liquid");', "liquid", "#ff6d1f"),
        ("a stored «cinema» boots in Amber-Cinema",
         'localStorage.setItem("jwa322.tema","cinema");', "cinema", "#ff6d1f"),
    ]
    fallos = 0
    for k, (nombre, js, attr, marca) in enumerate(CASOS):
        html = open(HTML, encoding="utf-8").read()
        # The injection goes at the very start of <head>, BEFORE the inline script
        # that applies the theme: the order is the whole point of this pass.
        SEMILLA = ('<script>try { localStorage.removeItem("jwa322.idioma"); %s }'
                   ' catch(e){}</script>\n' % js)
        if "<head>" not in html:
            raise SystemExit("I cannot find <head> to seed the theme")
        html = html.replace("<head>", "<head>\n" + SEMILLA, 1)

        srv3 = arrancar()
        diag = r"""
<script>
window.addEventListener("load", function(){
  var RES = [], FALLOS = 0;
  function ok(n, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + n + ": " + (d===undefined?"":d)); }
  try {
    var raiz = document.documentElement;
    var attr = raiz.getAttribute("data-tema");
    var marca = getComputedStyle(raiz).getPropertyValue("--marca").trim().toLowerCase();
    var bg = getComputedStyle(document.body).backgroundColor;
    var valor = document.getElementById("tema").value;
    ok("__NOMBRE__", attr === __ATTR__ && marca === __MARCA__,
       "data-tema=" + attr + " · marca=" + marca + " · fondo=" + bg);
    ok("and the dropdown shows the theme that is painted",
       valor === (attr || "yellow"),
       "dropdown=" + valor + " · data-tema=" + attr);
  } catch(e){ RES.push("!! EXCEPTION " + e.message); FALLOS++; }
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var p = document.createElement("pre"); p.id = "__diag";
  p.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;" +
                    "font:13px/1.5 monospace;padding:14px;margin:0;white-space:pre-wrap";
  p.textContent = RES.join("\n"); document.body.appendChild(p);
__ENTREGA__
});
</script>"""
        diag = (diag.replace("__NOMBRE__", nombre)
                    .replace("__ATTR__", json.dumps(attr))
                    .replace("__MARCA__", json.dumps(marca)))
        diag = diag.replace("__ENTREGA__", srv3.js("__diag"))
        _ok3, _msg3 = comprobar_scripts(html + diag, "probar_ui.py (the theme)")
        if not _ok3:
            raise SystemExit("!! " + _msg3)
        destino = os.path.join(DIR3, "tema%d.html" % k)
        open(destino, "w", encoding="utf-8").write(html + diag)
        env = dict(os.environ)
        env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
                    "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR3})
        subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL3,
                        "--window-size", "1200,900", "--screenshot",
                        os.path.join(DIR3, "tema%d.png" % k), "file://" + destino],
                       env=env, capture_output=True, text=True, timeout=180)
        srv3.parar()
        print("-" * 72)
        print("=== the theme at load: %s ===" % nombre)
        info3 = srv3.texto().strip()
        print(info3)
        c3, lineas3 = veredicto(info3)
        for l in lineas3:
            print(l)
        if c3:
            fallos = 1
    return fallos


raise SystemExit(codigo or pasada_tira() or pasada_tema())
