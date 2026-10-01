#!/usr/bin/env python3
"""
STRESS test and test of the areas that were left untouched since the changes.

It covers what the other tests do not:
  - The largest tree in the game (Rajadorixis, 15 nodes): that it paints in full,
    with what REAL nesting depth, and how long it TAKES. The tree is repainted on
    every keystroke, so time matters.
  - DNA cap: that it warns when the deficit exceeds the inventory cap.
  - The figures of the model (Fusions, caps, Levels, Coins) against the
    DOCUMENTED values. They used to be checked by reading the tables of the
    «Referencia» tab, which was removed on 25-sep-2026: the check was rewritten
    so as not to lose it. (The previous version of this test used regexes of the
    /35/ kind over the text of the whole tab: even an empty table satisfies that.
    It measured nothing.)
  - The maximum Level block of each node, contrasted with nivelMaximo().
  - Export / delete / import by PRESSING THE REAL BUTTONS, not replicating
    their logic inside the test.

Everything is synchronous on purpose: Firefox takes the screenshot right after
the `load` event, so if the report were painted after an `await` the screenshot
would come out blank. That is why the page's FileReader is replaced with a
synchronous double (what is doubled is the browser API, not the page's logic).

Usage:  python3 probar_estres.py
"""
import os, re, shutil, subprocess
import informe_browser
from informe_browser import arrancar, comprobar_scripts, veredicto

from rutas import HTML

RAIZ = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-estres"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "estres.html")
SHOT = os.path.join(DIR, "estres.png")

# The report travels through here, not through a screenshot that has to be read by eye.
srv = arrancar()

CAZA = r"""
<script>
window.__errores = [];
window.addEventListener("error", function(e){
  window.__errores.push((e.message || "?") + " @ line " + (e.lineno||"?"));
});
</script>
"""

DIAG = r"""
<script>
var RES = [], FALLOS = 0, CLONES = [], NOTAS = [];
var ALERTAS = [], BLOB = null, ANCLA = null, ENTRADA = null, TEXTO_BLOB = null;
function log(k, v){ RES.push(k + ": " + (v === undefined ? "" : v)); }
function ok(k, cond, detalle){ if (!cond) FALLOS++; log((cond ? "OK   " : "FALLO") + " " + k, detalle); }
function txt(id){ var e = document.getElementById(id); return e ? e.innerText.replace(/\s+/g," ").trim() : "(missing "+id+")"; }
function txc(id){ var e = document.getElementById(id); return e ? e.textContent.replace(/\s+/g," ").trim() : "(missing "+id+")"; }
/* The figures of a panel, in order, without the thousands format. */
function cifrasDe(id){
  return Array.prototype.map.call(document.querySelectorAll("#" + id + " .cifra .v"), function(e){
    return Number(e.textContent.replace(/[^\d]/g, "")) || 0;
  });
}
function etiquetasDe(id){
  return Array.prototype.map.call(document.querySelectorAll("#" + id + " .cifra .k"), function(e){
    return e.textContent.trim();
  });
}
/* Index of a figure by its label, tolerating the label getting longer.
   `indexOf` over the array demands an EXACT match: as soon as the report went
   from «ADN que falta» to «ADN que falta en total», the search returned -1 and
   the check failed saying «figure undefined». The fault was in the test,
   not in the page. */
function indiceEtiqueta(id, patron){
  return etiquetasDe(id).findIndex(function(t){ return patron.test(t); });
}
/* --- Read a cell by the NAME of its column, not by its position ---
   Two checks of this test read `tr.querySelectorAll("td")[5]` and
   `[6]` taking the width of the «Mis criaturas» table for granted. When that
   table gained the «Mejoras» column (25-sep-2026) both kept going through the
   same indices and started comparing SOMETHING ELSE: the «Nivel max. hoy» one
   read the DNA (4,321 versus 31) and the «Objetivo» one read the column next
   to it. The test did not fail because of the column change: it failed because
   it was asking for «the sixth cell» when it meant to ask for «the cell of the
   maximum level». Now it asks by name, and if the column does not exist it says
   so instead of returning a number from another one. */
function sinTildes(s){
  return String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "")
         .toLowerCase().replace(/\s+/g, " ").trim();
}
function colDe(tabla, cabecera){
  var ths = tabla.querySelectorAll("thead th");
  var q = sinTildes(cabecera);
  for (var i = 0; i < ths.length; i++) if (sinTildes(ths[i].textContent) === q) return i;
  return -1;
}
/* Returns the text of the `tr` cell that falls under the `cabecera` column.
   If the column does not exist, or the row has fewer cells than the header (a
   colspan shifts it), it returns a text that is NOT a number and that is read in
   the detail of the failure: that way the failure says what broke, and why. */
function celdaDe(tr, cabecera){
  var tabla = tr.closest("table");
  if (!tabla) return "(the row is not in a table)";
  var i = colDe(tabla, cabecera);
  if (i < 0) return "(there is no «" + cabecera + "» column)";
  var tds = tr.querySelectorAll("td");
  if (tds.length !== tabla.querySelectorAll("thead th").length)
    return "(the row has " + tds.length + " cells and the header " +
           tabla.querySelectorAll("thead th").length + ": there is a colspan)";
  return tds[i].textContent.trim();
}
function ev(el, t){ el.dispatchEvent(new Event(t, {bubbles:true})); }
/* Does the «Nivel» cell of the report show a RANGE of levels («16 → 20»)?
   The full signature is looked for —number, arrow, number— and not the arrow on
   its own, because since 25-sep-2026 the arrow is used for TWO things: the range
   and the breed button («criar → 20», which is an action and not a range).
   Looking for the loose symbol would confuse the two. */
function esRangoNivel(t){ return /^\d+\s*→\s*\d+/.test(String(t).trim()); }
function teclear(el, v){ el.focus(); el.value = v; ev(el, "input"); }
function medir(f, n){
  n = n || 1;
  var t0 = performance.now();
  for (var i = 0; i < n; i++) f();
  return (performance.now() - t0) / n;
}
/* Real nesting depth of a node: how many .rama wrap it. */
function profundidad(nodo){
  var d = 0, el = nodo.parentElement;
  while (el){ if (el.classList && el.classList.contains("rama")) d++; el = el.parentElement; }
  return d;
}

/* Deterministic starting state: the Firefox profile persists between
   runs, so without this the test starts with whatever the previous one left.
   BOTH things have to be cleared: `INV` (the data) and `MIS` («Mis criaturas»).
   Forgetting `MIS` made the number of failures change from one run to the next. */
INV = {}; MIS = []; guardar();

try {
  log("=== errors on load ===",
      (window.__errores && window.__errores.length) ? window.__errores.join(" | ") : "none");

  // ---------- 1. THE LARGEST TREE: Rajadorixis (15 nodes) ----------
  elegir("rajadorixis");
  teclear(document.getElementById("nivelAct"), "0");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  document.querySelector('nav button[data-t="arbol"]').click();

  var nodos = document.querySelectorAll("#arbolCuerpo .nodo");
  log("Rajadorixis: nodes painted", nodos.length);
  ok("the largest tree paints in full", nodos.length >= 12, nodos.length + " nodes");

  var camposOk = 0, fotos = 0, sinMax = 0;
  nodos.forEach(function(n){
    if (n.querySelector("input[data-campo='nivel']") &&
        n.querySelector("input[data-campo='adn']") &&
        n.querySelector("input[data-campo='creado']")) camposOk++;
    if (n.querySelector("img.foto")) fotos++;
    if (!n.querySelector(".maxn")) sinMax++;
  });
  ok("all the nodes of the large tree have their fields", camposOk === nodos.length,
     camposOk + "/" + nodos.length);
  ok("all the nodes of the large tree have a photo", fotos === nodos.length,
     fotos + "/" + nodos.length);
  ok("all the nodes of the large tree show their maximum level", sinMax === 0,
     (nodos.length - sinMax) + "/" + nodos.length);

  var profMax = 0;
  nodos.forEach(function(n){ profMax = Math.max(profMax, profundidad(n)); });
  ok("the large tree has real nesting, it is not flat", profMax >= 2,
     "maximum depth " + profMax);

  var caja = document.querySelector("#arbolCuerpo").getBoundingClientRect();
  var salidos = 0, peor = 0;
  nodos.forEach(function(n){
    var r = n.getBoundingClientRect();
    var sob = r.right - caja.right;
    if (sob > 1) salidos++;
    if (sob > peor) peor = sob;
  });
  ok("no node overflows the tree on the right", salidos === 0,
     salidos + " overflow; worst excess " + Math.round(peor) + " px");

  // ---------- 2. REPAINT TIME ----------
  var tPintar = medir(function(){ pintarArbol(); }, 20);
  log("pintarArbol() on the 15-node tree", tPintar.toFixed(1) + " ms");
  ok("repainting the large tree is fast (<120 ms)", tPintar < 120, tPintar.toFixed(1) + " ms");

  // the real case: typing in a field at the bottom of the tree.
  // WATCH OUT: the field has to be LOOKED UP AGAIN on every pass. When the tree
  // is repainted the previous element is left detached from the DOM, its event
  // no longer bubbles up to the container and the following keystrokes do
  // nothing: one is measured for real and fourteen are fake, and the average
  // comes out falsely good.
  function teclearFondo(){
    var f = document.querySelectorAll("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
    teclear(f[f.length - 1], String(Math.random()*1000|0));
  }
  var tTecla = medir(teclearFondo, 15);
  log("one keystroke in a field at the bottom", tTecla.toFixed(1) + " ms");
  ok("typing is still fluid (<150 ms per keystroke)", tTecla < 150, tTecla.toFixed(1) + " ms");

  // A keystroke in the tree now also repaints the calculator and the report of
  // the whole tree, so it has to be measured again. And a keystroke in the
  // CALCULATOR repaints the tree: it is the other direction of the same round trip.
  //
  // WATCH OUT: DNA 0 has to be forced at the root. With DNA to spare the pruning
  // leaves the tree reduced to the root alone, and then the measurement comes out
  // great and is worth nothing.
  elegir("rajadorixis");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  document.querySelector('nav button[data-t="arbol"]').click();
  var nodosR = document.querySelectorAll("#arbolCuerpo .nodo").length;
  ok("the time measurement is done with the real large tree", nodosR >= 12, nodosR + " nodes");
  var fondo2 = document.querySelectorAll("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  ok("and with fields at the bottom to type in", fondo2.length > 0, fondo2.length + " fields");
  var tTecla2 = medir(teclearFondo, 15);
  log("one keystroke in the tree, with the calculator and the report behind it", tTecla2.toFixed(1) + " ms");
  ok("it is still fluid (<150 ms per keystroke)", tTecla2 < 150, tTecla2.toFixed(1) + " ms");

  // And the other direction: typing in the calculator repaints the 15-node tree.
  // Low values on purpose, so that the tree is not pruned while it is measured.
  elegir("rajadorixis");
  document.querySelector('nav button[data-t="calc"]').click();
  var tCalc = medir(function(){ teclear(document.getElementById("adnTengo"), String(Math.random()*99|0)); }, 15);
  log("one keystroke in the calculator, with the tree behind it", tCalc.toFixed(1) + " ms");
  ok("and in the calculator too (<150 ms per keystroke)", tCalc < 150, tCalc.toFixed(1) + " ms");
  ok("when measuring the calculator the tree is still whole",
     document.querySelectorAll("#arbolCuerpo .nodo").length >= 12,
     document.querySelectorAll("#arbolCuerpo .nodo").length + " nodes");
  var tInforme = medir(function(){ calcular(); }, 20);
  log("calcular() in full, with the report of the tree of " +
      document.querySelectorAll("#arbolCuerpo .nodo").length + " nodes", tInforme.toFixed(1) + " ms");
  ok("recalculating the calculator is fast (<120 ms)", tInforme < 120, tInforme.toFixed(1) + " ms");

  // Breakdown, to know where the time of a keystroke goes.
  var tMios = medir(function(){ pintarMios(); }, 20);
  var tLista = medir(function(){ pintarLista(); }, 20);
  document.getElementById("lista").classList.remove("on");
  log("repaint breakdown",
      "tree " + medir(function(){ pintarArbol(); }, 20).toFixed(1) +
      " | calculate " + tInforme.toFixed(1) +
      " | mios " + tMios.toFixed(1) +
      " | list " + tLista.toFixed(1) + " ms");

  // ---------- 3. DNA CAP ----------
  elegir("93_classic_t_rex");   // omega: cap 60.000, ladder 1->30 = 41.700
  teclear(document.getElementById("nivelAct"), "0");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  var res = txt("resultado");
  ok("it warns about the DNA cap when the deficit exceeds it",
     /tope de ADN/i.test(res) && /tandas/i.test(res), res.slice(0, 170));
  ok("the cap it quotes is the omega's (60.000)", /60,000/.test(res), res.slice(0, 200));

  // ---------- 4. THE FIGURES OF THE MODEL ----------
  /* Here was the check of the «Referencia» tab, cell by cell, against the model.
     The tab was removed on 25-sep-2026 at n30's request, and with it the four
     tables. Those checks did TWO things at once: verify that the painted table
     matched `M`, and that `M` had the right values. The first no longer exists
     (there is no table to look at); the second stays here, against the
     DOCUMENTED figures, so that removing the tab does not take the verification
     down with it without anyone noticing.
     These values are not re-derived: they are the ones from the official
     announcement and paleo.gg, written by hand. If the model changes, this test
     has to protest. */
  /* `adnFus` indexes by the Rarity JUMP, not by the Rarity: two consecutive ones
     (common→rare) jump 1 and are worth 50. The 200/500/2000 are jumps of 2, 3
     and 4, so the pairs have to be chosen by their jump, not at random. The first
     version of this check asked four consecutive pairs for 50/200/500/2000 and
     gave 50/50/50/50: the fault was in the test. */
  ok("the cost per Fusion is 50/200/500/2000 according to the Rarity JUMP",
     adnFus("common","rare") === 50 && adnFus("common","epic") === 200 &&
     adnFus("common","legendary") === 500 && adnFus("common","unique") === 2000 &&
     adnFus("rare","epic") === 50,
     [adnFus("common","rare"), adnFus("common","epic"), adnFus("common","legendary"),
      adnFus("common","unique")].join(" / ") + "  (jumps 1/2/3/4)");
  ok("the Rarity jump (tier) goes from 0 to 5 in order",
     M.tier.common === 0 && M.tier.rare === 1 && M.tier.epic === 2 &&
     M.tier.legendary === 3 && M.tier.unique === 4 && M.tier.apex === 5,
     JSON.stringify(M.tier));
  ok("the DNA caps are the official ones of 31-ago-2026",
     M.topes.common === 850000 && M.topes.rare === 250000 && M.topes.epic === 85000 &&
     M.topes.legendary === 25000 && M.topes.unique === 8000 && M.topes.apex === 3000,
     JSON.stringify(M.topes));
  ok("the omega cap used by the engine is 60.000", M.topes.omega === 60000,
     "M.topes.omega = " + nf(M.topes.omega));
  ok("the birth Levels are 1/6/11/16/21/26",
     minLv("common") === 1 && minLv("rare") === 6 && minLv("epic") === 11 &&
     minLv("legendary") === 16 && minLv("unique") === 21 && minLv("apex") === 26,
     ["common","rare","epic","legendary","unique","apex"].map(minLv).join(" / "));
  ok("the minimum Ingredient Level is one less than the birth one",
     ["common","rare","epic","legendary","unique","apex"].every(function(r){
       return M.minIngrediente[r] === minLv(r) - 1;
     }),
     JSON.stringify(M.minIngrediente));
  ok("the DNA to create is 50/100/150/200/250/300",
     M.creacion.common === 50 && M.creacion.rare === 100 && M.creacion.epic === 150 &&
     M.creacion.legendary === 200 && M.creacion.unique === 250 && M.creacion.apex === 300,
     JSON.stringify(M.creacion));
  ok("the Coins per Fusion are 20/20/100/200/1000/2000",
     M.monedasFusion.common === 20 && M.monedasFusion.rare === 20 &&
     M.monedasFusion.epic === 100 && M.monedasFusion.legendary === 200 &&
     M.monedasFusion.unique === 1000 && M.monedasFusion.apex === 2000,
     JSON.stringify(M.monedasFusion));

  /* The «Referencia» tab was removed at n30's request. It is checked that it does
     NOT come back: if someone reintroduces it, this fails and they find out. Both
     the button and the section are looked at, because removing only one leaves a
     tab that cannot be opened. */
  ok("the «Referencia» tab no longer exists",
     !document.querySelector('nav button[data-t="ref"]') && !document.getElementById("s-ref"),
     "buttons: " + Array.from(document.querySelectorAll("nav button")).map(function(b){ return b.dataset.t; }).join(", "));
  ok("the four real tabs remain", document.querySelectorAll("nav button").length === 4,
     document.querySelectorAll("nav button").length + " buttons and " +
     document.querySelectorAll("section").length + " sections");

  // ---------- 5. CATALYSTS ----------
  document.querySelector('nav button[data-t="cat"]').click();
  document.getElementById("cComun").value = 20000;
  document.getElementById("cRara").value = 0;
  document.getElementById("cEpica").value = 2000;
  document.getElementById("cLegend").value = 500;
  document.getElementById("btnCat").click();
  var cat = txt("catSalida");
  ok("the catalyst planner responds", cat.length > 20, cat.slice(0, 110));
  // 20000*1 + 2000*15 + 500*50 = 20.000 + 30.000 + 25.000 = 75.000
  // WATCH OUT: innerText returns the text ALREADY transformed by CSS (.cifra .k
  // is uppercase), so "Sobran" reads as "SOBRAN". Hence the /i.
  ok("the tank points come out to 75.000", /75,000/.test(cat), cat.slice(0, 130));
  ok("with 75.000 points nothing is missing", /Sobran/i.test(cat) && /Sobran\s*0/i.test(cat.replace(/\s+/g," ")),
     cat.slice(0, 130));
  // and with less it has to say how much is missing: 1000 + 2000*15 + 500*50 = 56.000
  document.getElementById("cComun").value = 1000;
  document.getElementById("btnCat").click();
  var cat2 = txt("catSalida");
  ok("with 1.000 commons and the rest the same it says 19.000 are missing (75.000-56.000)",
     /Faltan/i.test(cat2) && /19,000/.test(cat2), cat2.slice(0, 130));

  /* The tier has to AGREE with the eight observed recipes this same screen
     prints below. It did not: the rule read the DNA UNITS and contradicted three
     of them — it called «2.000 Epic + 3.500 Rare + 625 Legendary» Silver while
     the table says 36 Gold. A rule and a table that disagree inside one screen
     are worse than either alone, because both look authoritative. The rule now
     follows the category that puts the most POINTS in the tank and reproduces
     all eight; this pins them so it cannot drift back.
     The expected label is built with `i18n` and not written out: the tier is
     translated, and this test runs in Spanish. */
  var T = {Gold: i18n("Gold"), Silver: i18n("Silver"), Bronze: i18n("Bronze")};
  var RECETAS = [
    [0,     3500, 2000, 625,  "Gold"],
    [10500, 0,    2000, 690,  "Gold"],
    [0,     0,    0,    1500, "Gold"],
    [20000, 0,    2000, 500,  "Silver"],
    [0,     5000, 2000, 500,  "Silver"],
    [0,     18750, 0,   0,    "Silver"],
    [25500, 0,    1634, 500,  "Bronze"],
    [75000, 0,    0,    0,    "Bronze"]
  ];
  var malas = [];
  RECETAS.forEach(function(r){
    document.getElementById("cComun").value = r[0];
    document.getElementById("cRara").value = r[1];
    document.getElementById("cEpica").value = r[2];
    document.getElementById("cLegend").value = r[3];
    document.getElementById("btnCat").click();
    var v = document.querySelectorAll("#catSalida .cifra")[1]
              .querySelector(".v").textContent.trim();
    if (v !== T[r[4]])
      malas.push(r[0]+"C "+r[1]+"R "+r[2]+"E "+r[3]+"L -> "+v+" (la tabla dice "+T[r[4]]+")");
  });
  ok("the tier agrees with the eight observed recipes the same screen prints",
     malas.length === 0, malas.length ? malas.join(" · ") : "8 de 8");
} catch (e) {
  log("!! EXCEPTION", e.message + " @@ " + (e.stack || "").split("\n")[1]);
}

/* ---------- 6, 7 and 8: in `load`, so the screenshot catches them ---------- */
window.addEventListener("load", function(){
  try {
    // ---------- 6. EXPORT / DELETE / IMPORT WITH THE REAL BUTTONS ----------
    window.alert = function(m){ ALERTAS.push(String(m)); };
    window.confirm = function(){ return true; };
    var clickAncla = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function(){ ANCLA = this; };   // we do not download: we only look
    var clickInput = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function(){
      if (this.type === "file"){ ENTRADA = this; return; }             // we do not open a dialog
      return clickInput.apply(this, arguments);
    };
    /* The handler passes the Blob to URL.createObjectURL to build the download
       link: intercepting it is keeping the file that would be saved. */
    var crearURL = URL.createObjectURL;
    URL.createObjectURL = function(b){ BLOB = b; return crearURL.apply(URL, arguments); };
    /* The Blob that the handler hands to the browser is the file that gets
       saved: capturing the string the constructor receives is capturing the file. */
    var BlobReal = window.Blob;
    window.Blob = function(partes, opciones){
      TEXTO_BLOB = partes.join("");
      return new BlobReal(partes, opciones);
    };
    /* Synchronous double of the FileReader: what is doubled is the browser API,
       not the page's logic (which is the one being tested). */
    var TEXTO_A_IMPORTAR = "";
    window.FileReader = function(){
      var self = this;
      self.onload = null; self.onerror = null;
      self.readAsText = function(){ self.result = TEXTO_A_IMPORTAR; if (self.onload) self.onload(); };
    };

    // known inventory: indoraptor at level 24 with 4321 DNA, and one of its
    // branches unchecked from "creada" so that the field has to survive.
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), "24");
    teclear(document.getElementById("adnTengo"), "4321");
    document.querySelector('nav button[data-t="arbol"]').click();
    var chk = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='creado']");
    if (chk){ chk.checked = false; ev(chk, "change"); }
    /* Save the chosen one. Besides leaving the exported file with a list, this also
       checks the rule requested by n30: saving puts ONE creature in, not the tree
       hanging from it — no matter how touched its ingredients are. */
    document.querySelector('nav button[data-t="calc"]').click();
    document.getElementById("btnGuardar").click();
    ok("Guardar puts ONLY the chosen creature in the list",
       MIS.length === 1 && MIS[0] === "indoraptor",
       MIS.length + " in the list (" + MIS.join(", ") + ") with " + Object.keys(INV).length +
       " creatures touched in the tree");
    var antes = JSON.parse(JSON.stringify(INV));
    var listaAntes = MIS.slice();
    log("creatures before exporting", Object.keys(antes).length);

    // --- export ---
    document.getElementById("btnExport").click();
    ok("Exportar delivers a Blob of type application/json",
       !!BLOB && BLOB.type === "application/json", BLOB ? BLOB.type + " / " + BLOB.size + " bytes" : "(no blob)");
    ok("the exported file is called jwa322-mis-criaturas.json",
       !!ANCLA && ANCLA.download === "jwa322-mis-criaturas.json",
       ANCLA ? ANCLA.download : "(not pressed)");
    /* The file carries TWO things since 25-sep-2026: the data and the list. Before
       it only carried the data, because the list was «the keys of the data». */
    var ida = JSON.parse(TEXTO_BLOB);
    ok("the exported JSON carries the whole inventory",
       !!ida.inventario && JSON.stringify(ida.inventario) === JSON.stringify(antes),
       Object.keys((ida && ida.inventario) || {}).length + " creatures, " +
       (TEXTO_BLOB||"").length + " characters");
    ok("and it carries the «Mis criaturas» list separately",
       Array.isArray(ida.mios) && JSON.stringify(ida.mios) === JSON.stringify(listaAntes),
       JSON.stringify(ida.mios));
    var conCreado = 0;
    Object.keys(ida.inventario).forEach(function(k){ if (ida.inventario[k].creado !== undefined) conCreado++; });
    ok("the 'creado' field comes out in the exported file", conCreado === Object.keys(ida.inventario).length,
       conCreado + "/" + Object.keys(ida.inventario).length);

    // --- delete ---
    document.getElementById("btnBorrar").click();
    ok("Borrar todo empties the inventory", Object.keys(INV).length === 0, Object.keys(INV).length + "");
    ok("Borrar todo also clears what is stored in the browser",
       !localStorage.getItem(CLAVE) || localStorage.getItem(CLAVE) === "{}",
       JSON.stringify(localStorage.getItem(CLAVE)));
    ok("and the Mis criaturas list is left empty",
       /Todav\u00eda no has guardado/.test(txt("miosCuerpo")), txt("miosCuerpo").slice(0, 70));

    // --- import ---
    TEXTO_A_IMPORTAR = TEXTO_BLOB;
    document.getElementById("btnImport").click();
    ok("Importar opens a .json file picker",
       !!ENTRADA && ENTRADA.type === "file" && ENTRADA.accept === ".json",
       ENTRADA ? (ENTRADA.type + " " + ENTRADA.accept) : "(not created)");
    var dt = new DataTransfer();
    dt.items.add(new File([TEXTO_BLOB], "jwa322-mis-criaturas.json", {type:"application/json"}));
    ENTRADA.files = dt.files;
    ENTRADA.dispatchEvent(new Event("change"));

    ok("the import recovers the same creatures",
       Object.keys(INV).length === Object.keys(antes).length,
       Object.keys(INV).length + " of " + Object.keys(antes).length);
    var sinCreado = 0;
    Object.keys(INV).forEach(function(k){ if (INV[k].creado === undefined) sinCreado++; });
    ok("the 'creado' field survives the round trip", sinCreado === 0,
       (Object.keys(INV).length - sinCreado) + " with creado, " + sinCreado + " without it");
    ok("the level and the DNA survive",
       INV["indoraptor"] && INV["indoraptor"].nivel === 24 && INV["indoraptor"].adn === 4321,
       JSON.stringify(INV["indoraptor"]));
    ok("the notice says how many it imported",
       /Importadas \d+ criaturas/.test(ALERTAS.join(" | ")), ALERTAS.join(" | "));
    ok("what was imported is visible in Mis criaturas", /Indoraptor/i.test(txt("miosCuerpo")),
       txt("miosCuerpo").slice(0, 70));

    // the Mis criaturas table has to show the same maximum level as the engine
    var filasMios = document.querySelectorAll("#miosCuerpo tbody tr");
    var filaInd = null;
    filasMios.forEach(function(tr){ if (/Indoraptor/i.test(tr.innerText)) filaInd = tr; });
    /* By column NAME, not by index: see `celdaDe`. */
    var celdaMax = filaInd ? celdaDe(filaInd, "Nivel máx. hoy") : null;
    var invInd = invDe("indoraptor");
    var espInd = nivelMaximo("unique", invInd.creado ? Math.max(invInd.nivel, 1) : 0,
                             invInd.adn, invInd.creado).nivel;
    ok("the 'Nivel max. hoy' column of Mis criaturas matches the engine",
       celdaMax !== null && Number(celdaMax) === espInd,
       "page " + celdaMax + " vs engine " + espInd);

    // --- a file that is no good ---
    var antesMalo = Object.keys(INV).length;
    TEXTO_A_IMPORTAR = "[1,2,3]";
    document.getElementById("btnImport").click();
    var dt2 = new DataTransfer();
    dt2.items.add(new File(["[1,2,3]"], "basura.json", {type:"application/json"}));
    ENTRADA.files = dt2.files;
    ENTRADA.dispatchEvent(new Event("change"));
    ok("a JSON that is not an object is rejected with a notice",
       /no vale/.test(ALERTAS.join(" | ")), ALERTAS.slice(-1)[0] || "(no notice)");
    ok("and it does not touch the inventory that was already there",
       Object.keys(INV).length === antesMalo, Object.keys(INV).length + " of " + antesMalo);

    HTMLAnchorElement.prototype.click = clickAncla;
    HTMLInputElement.prototype.click = clickInput;
    window.Blob = BlobReal;
    URL.createObjectURL = crearURL;

    // ---------- 7. the maximum level of the root, against nivelMaximo() ----------
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), "10");
    teclear(document.getElementById("adnTengo"), "100000");
    document.querySelector('nav button[data-t="arbol"]').click();
    var raiz = document.querySelector("#arbolCuerpo .nodo.raiz");
    var mm = raiz ? raiz.querySelector(".maxn") : null;
    var dicho = mm ? (mm.innerHTML.match(/llega al <b>nivel (\d+)<\/b>/) || [])[1] : null;
    var rareza = C["indoraptor"][1];
    var espMax = nivelMaximo(rareza, 10, 100000, true, M.nivelMax);
    ok("the maximum level the root shows is the one the engine calculates",
       dicho !== null && Number(dicho) === espMax.nivel,
       "page " + dicho + " vs engine " + espMax.nivel + " (" + rareza + ", 100.000 DNA)");
    ok("and it warns that it already meets the target",
       mm && /ya cumple el objetivo 35/.test(mm.innerHTML), mm ? mm.innerText.slice(0, 80) : "(no block)");

    // ---------- 8. a click in Mis criaturas takes you to the calculator ----------
    // It is saved through the real button, which is the only one that records the target.
    // The level has to be above the birth one: a unique one is born at
    // 21, and below that the creature cannot be created.
    var nace = minLv(C["indoraptor"][1]);
    var lvOk = nace + 3;
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(lvOk));
    teclear(document.getElementById("adnTengo"), "7777");
    document.getElementById("nivelObj").value = 28;
    ev(document.getElementById("nivelObj"), "input");
    document.getElementById("btnGuardar").click();
    var guardado = INV["indoraptor"];
    ok("the Guardar button also records the target",
       guardado && guardado.objetivo === 28 && guardado.nivel === lvOk, JSON.stringify(guardado));

    // the stumble that cost me a while: a level below the birth one
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(nace - 3));
    ev(document.getElementById("nivelAct"), "change");
    var invAbajo = invDe("indoraptor");
    ok("a level below the birth one leaves the creature not created",
       invAbajo.creado === false && invAbajo.nivel === 0, JSON.stringify(invAbajo));
    ok("and the field is corrected, so that what is seen is what is saved",
       document.getElementById("nivelAct").value === "0", document.getElementById("nivelAct").value);

    // it is put back the way it was
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(lvOk));
    teclear(document.getElementById("adnTengo"), "7777");
    document.getElementById("nivelObj").value = 28;
    ev(document.getElementById("nivelObj"), "input");
    document.getElementById("btnGuardar").click();

    // we go to another creature and another tab, so that the jump has to undo something
    elegir("rajadorixis");
    document.getElementById("nivelObj").value = 35;
    ev(document.getElementById("nivelObj"), "input");
    /* This one is saved TOO. The × test needs two creatures in the list, and
       before they were there by accident: everything that was touched ended up in
       «Mis criaturas». Now they have to be saved on purpose, which is precisely
       the new rule. */
    document.getElementById("btnGuardar").click();
    irA("mios");
    ok("we are in Mis criaturas",
       document.getElementById("s-mios").classList.contains("on") &&
       !document.getElementById("s-calc").classList.contains("on"), "s-mios visible");

    // that the page really goes back to the top. The test window (2200 px)
    // is taller than the document, so without padding there would be nothing to
    // scroll and the check would pass without measuring anything.
    var relleno = document.createElement("div");
    relleno.style.height = "1600px";
    document.body.appendChild(relleno);

    var scrollOriginal = window.scrollTo;
    window.scrollTo(0, 500);                     // starting point: at the bottom
    var yAntes = window.scrollY;
    ok("the test starts with the page scrolled (otherwise it would measure nothing)",
       yAntes > 0, "starting scrollY " + yAntes);
    var pedidos = [];
    window.scrollTo = function(){
      pedidos.push(Array.prototype.slice.call(arguments));
      return scrollOriginal.apply(window, arguments);   // and that it really does it
    };

    var fila = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir === "indoraptor") fila = tr;
    });
    ok("the creature row carries its identifier", !!fila, fila ? fila.dataset.ir : "(no row)");
    ok("the name and the photo are real <button>s (keyboard and screen reader)",
       fila && fila.querySelectorAll("button.ir").length === 2,
       fila ? fila.querySelectorAll("button.ir").length + " buttons" : "0");

    fila.querySelector("button.ir:not(.foto-btn)").click();

    ok("the click takes you to the Calculadora tab",
       document.getElementById("s-calc").classList.contains("on") &&
       !document.getElementById("s-mios").classList.contains("on"), "s-calc visible");
    ok("and it leaves that creature chosen",
       elegido === "indoraptor" && /Indoraptor/.test(txt("elegida")),
       "elegido=" + elegido + " | " + txt("elegida").slice(0, 40));
    ok("with the level it had saved (" + lvOk + ")",
       document.getElementById("nivelAct").value === String(lvOk),
       document.getElementById("nivelAct").value);
    ok("with the DNA it had saved (7.777)",
       document.getElementById("adnTengo").value === "7777", document.getElementById("adnTengo").value);
    ok("and with its saved target level (28), not the previous creature's",
       document.getElementById("nivelObj").value === "28", document.getElementById("nivelObj").value);
    ok("the page asks to go back to the top", pedidos.length > 0 && Number(pedidos[0][1]) === 0,
       JSON.stringify(pedidos));
    ok("and it really ends up at the top", window.scrollY === 0,
       "scrollY " + window.scrollY + " (before " + yAntes + ")");
    window.scrollTo = scrollOriginal;
    document.body.removeChild(relleno);

    // click on a middle cell (not on the name): it also has to navigate
    irA("mios");
    fila = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir === "indoraptor") fila = tr;
    });
    fila.querySelectorAll("td")[4].click();
    ok("a click on any cell of the row also navigates",
       document.getElementById("s-calc").classList.contains("on") && elegido === "indoraptor",
       "elegido=" + elegido);

    // and the × deletes WITHOUT taking you to the calculator
    irA("mios");
    var antesN = Object.keys(INV).length;
    var otra = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir !== "indoraptor") otra = tr;
    });
    ok("there is a second creature to test the ×", !!otra, antesN + " saved");
    otra.querySelector("[data-borrar]").click();
    ok("the × deletes the creature and does NOT take you to the calculator",
       Object.keys(INV).length === antesN - 1 && document.getElementById("s-mios").classList.contains("on"),
       "there remain " + Object.keys(INV).length + " and the active tab is " +
       (document.getElementById("s-mios").classList.contains("on") ? "Mis criaturas" : "another"));

    // and a deleted creature no longer has a row
    ok("the deleted row disappears from the list",
       !/Rajadorixis/i.test(txt("miosCuerpo")) && /Indoraptor/i.test(txt("miosCuerpo")),
       txt("miosCuerpo").slice(0, 60));

    // ---------- 9. editing the tree is reflected in the CALCULATOR ----------
    // Paralidactylus is an apex mega_hybrid: it is the root of its own tree and is
    // born at 26. Not created and with 0 DNA, from 0 to 35 costs 3.000 (300 to
    // create it + 2.700 of ladder). With 300 put in the tree, the deficit drops
    // to 2.700.
    elegir("paralidactylus");
    document.getElementById("nivelObj").value = 35;
    ev(document.getElementById("nivelObj"), "input");
    document.querySelector('nav button[data-t="arbol"]').click();
    var raizP = document.querySelector("#arbolCuerpo .nodo.raiz");
    ok("Paralidactylus is the root of its tree", !!raizP, raizP ? "yes" : "(no root)");
    var etiq = etiquetasDe("resultado");
    var iFalta = etiq.indexOf("ADN que falta");
    var cifrasAntes = cifrasDe("resultado");
    log("calculator before touching the tree", JSON.stringify(cifrasAntes));
    ok("the calculator shows the missing DNA and starts from 3.000",
       iFalta >= 0 && cifrasAntes[iFalta] === 3000, "missing DNA = " + cifrasAntes[iFalta]);
    var campoAntes = document.getElementById("adnTengo").value;

    var adnRaiz = raizP.querySelector("input[data-campo='adn']");
    teclear(adnRaiz, "300");
    ev(adnRaiz, "change");

    ok("the DNA put in the root of the tree reaches the calculator field",
       document.getElementById("adnTengo").value === "300",
       "calculator field = " + document.getElementById("adnTengo").value + " (before " + campoAntes + ")");
    var cifrasDespues = cifrasDe("resultado");
    ok("and the calculator result is recalculated (3.000 - 300 = 2.700)",
       cifrasDespues[iFalta] === 2700,
       "missing DNA = " + cifrasDespues[iFalta] + " (before " + cifrasAntes[iFalta] + ")");

    // ---------- 10. full report of the tree ----------
    var inf = document.getElementById("informeArbol");
    ok("the calculator has the tree report", !!inf, inf ? "yes" : "(does not exist)");
    if (inf){
      var filasInf = inf.querySelectorAll("tbody tr");
      var nodosArbol = document.querySelectorAll("#arbolCuerpo .nodo").length;
      // The report groups by creature: one row per distinct creature, not per
      // appearance in the tree. There can never be more rows than nodes.
      var nombresInf = [];
      inf.querySelectorAll("tbody tr:not(.total)").forEach(function(tr){
        nombresInf.push(tr.querySelector("td").textContent
          .replace(/raíz|se recolecta|sin crear/g, "").trim());
      });
      var repes = nombresInf.filter(function(x, i){ return nombresInf.indexOf(x) !== i; });
      ok("the report lists one row per creature, without repeating any",
         repes.length === 0, nombresInf.length + " rows" + (repes.length ? " | repeated: " + repes.join(", ") : ""));
      ok("and it does not list more creatures than the tree has nodes",
         nombresInf.length <= nodosArbol, nombresInf.length + " rows for " + nodosArbol + " nodes");
      ok("the report names the root and its ingredients",
         /Paralidactylus/.test(txc("informeArbol")) && /Paralitrosaurus/.test(txc("informeArbol")) &&
         /Skorpiodactylus/.test(txc("informeArbol")),
         txc("informeArbol").slice(0, 90));
      log("report figures", JSON.stringify(cifrasDe("informeArbol")) + " | " +
          JSON.stringify(etiquetasDe("informeArbol")));
      ok("the report goes above the maximum level block",
         !!(document.getElementById("informeArbol").compareDocumentPosition(
              document.getElementById("maxNivel")) & Node.DOCUMENT_POSITION_FOLLOWING),
         "report before maxNivel");
      var tb = inf.querySelector("table");
      ok("the report table fits across, without horizontal scroll",
         tb.scrollWidth <= tb.clientWidth + 2,
         "scrollWidth " + tb.scrollWidth + " vs clientWidth " + tb.clientWidth);
      // the sum of the "Falta" column has to be the total figure of the report.
      // Columns: Criatura | Nivel | Necesario | Tienes | Falta | Fusiones
      // (the «Rareza» one was removed on 25-sep, and the «Veces» one too).
      /* The Total row no longer has a cell that spans 2: when the «Criar a todas»
         button was put into the «Nivel» column, the first cell drops to
         colspan=1 and the row ends up with 6 cells, the same as the header.
         Before, `celdasTotal[3]` was read taking the colspan for granted; that
         index now returns ANOTHER column (Tienes instead of Falta). It is trap 16
         —reading a cell by its position— biting on the change right after
         documenting it. It is read by the NAME of the column. */
      var iF = indiceEtiqueta("informeArbol", /^ADN que falta/i);
      var sumaFalta = 0;
      inf.querySelectorAll("tbody tr:not(.total)").forEach(function(tr){
        sumaFalta += Number(celdaDe(tr, "Falta").replace(/[^\d]/g, "")) || 0;
      });
      var celdasTotal = inf.querySelector("tr.total").querySelectorAll("td");
      var totalFila = Number(celdaDe(inf.querySelector("tr.total"), "Falta").replace(/[^\d]/g, "")) || 0;
      ok("the Total row matches the sum of the rows and the figure above",
         celdasTotal.length === 6 && iF >= 0 && totalFila === sumaFalta &&
         totalFila === cifrasDe("informeArbol")[iF],
         celdasTotal.length + " cells | sum " + sumaFalta + " = total " + totalFila +
         " = figure " + cifrasDe("informeArbol")[iF]);
    }

    // ---------- 11. shared ingredient: the DNA is subtracted ONCE ----------
    // Indoraptor carries Velociraptor, and its Indominus Rex ingredient too: the
    // same DNA pool shows up in two branches. Subtracting the deficit of each
    // appearance subtracted the same DNA twice and the total came out short.
    elegir("indoraptor");
    document.getElementById("nivelObj").value = 30;
    ev(document.getElementById("nivelObj"), "input");
    teclear(document.getElementById("nivelAct"), "21");
    teclear(document.getElementById("adnTengo"), "1000");
    fijar("indominus_rex", "nivel", 16); fijar("indominus_rex", "adn", 400);
    fijar("velociraptor", "nivel", 20);  fijar("velociraptor", "adn", 30000);
    refrescar();

    var tI = plan("indoraptor", 30, 0, new Set(), true, contarSubida);
    var ttI = totales(tI);
    var vel = ttI.porUuid["velociraptor"];
    ok("the tree detects the shared ingredient", vel && vel.veces === 2,
       vel ? "it appears " + vel.veces + " times" : "(does not appear)");
    var apar = [];
    (function rec(x){ if (x.uuid === "velociraptor") apar.push(x); x.hijos.forEach(rec); })(tI);
    var necSuma = apar.reduce(function(a, x){ return a + x.adnNec; }, 0);
    var naive = 0;
    (function rec(x){ naive += x.deficit; x.hijos.forEach(rec); })(tI);
    log("Velociraptor: needed per branch " + apar.map(function(x){ return x.adnNec; }).join(" + ") +
        " = " + necSuma + " | has 30.000 | appearances " + apar.length);
    ok("its needed DNA is the SUM of the two branches", vel.nec === necSuma,
       vel.nec + " vs " + necSuma);
    ok("and what you have is subtracted ONCE, not once per branch",
       vel.falta === Math.max(0, necSuma - 30000), vel.falta + " (sum of deficits " +
       apar.reduce(function(a, x){ return a + x.deficit; }, 0) + ")");
    ok("the tree total corrects exactly one pool counted too many",
       ttI.adn === naive + 30000,
       "total " + nf(ttI.adn) + " vs sum per appearances " + nf(naive) + " (difference " +
       nf(ttI.adn - naive) + ", the pool is 30.000)");
    /* The «Veces» column was withdrawn on 25-sep-2026. What has to be checked now
       is the opposite of before: that it is NOT there, neither in the header nor
       in the text —the note cited it by name—, and that the Velociraptor row
       still carries the corrected total. The `veces` counter is still alive
       behind the scenes (it feeds `repetidas`), but that is checked by the
       assertion above. */
    ok("the report still warns about the shared ingredient",
       /Velociraptor/.test(txc("informeArbol")) &&
       /varias ramas del árbol/.test(txc("informeArbol")), "report with the shared note");
    ok("and the «Veces» column is no longer there: neither in the header nor cited in the note",
       inf.querySelectorAll("thead th").length === 6 && !/Veces/.test(txc("informeArbol")),
       Array.prototype.map.call(inf.querySelectorAll("thead th"), function(th){
         return th.textContent.trim(); }).join(" | "));
    var filaVel = null;
    inf.querySelectorAll("tbody tr").forEach(function(tr){
      if (/Velociraptor/.test(tr.innerText)) filaVel = tr;
    });
    ok("the Velociraptor row has 6 cells and the corrected total",
       filaVel && filaVel.querySelectorAll("td").length === 6 &&
       Number(celdaDe(filaVel, "Falta").replace(/[^\d]/g, "")) === vel.falta,
       filaVel ? filaVel.querySelectorAll("td").length + " cells, missing " +
                 celdaDe(filaVel, "Falta") : "(no row)");
  } catch (e) {
    log("!! EXCEPTION in the buttons part", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 12. the «subir los ingredientes» switch ----------
  /* This section is NOT a mirror of the code: it is the statement of what the
     person using the page expects.

     The report added the ladder of ALL the creatures no matter what, so it gave
     exactly the same figure with the checkbox checked and unchecked, while the
     tree tab did change. Two views of the same screen contradicting each other.
     The Python mirror test did not see it because the mirror made the same
     mistake: when the test and the code are written from the same reading, a
     common misunderstanding passes in green. */
  try {
    var chkSub = document.getElementById("chkSubida");
    ok("the checkbox for counting the level-up exists", !!chkSub);

    /* Report rows by name, PLUS the Total row, all captured at the same
       instant. Reading the rows as data and the Total row from the DOM later is
       no good: in between the checkbox is turned back on, the report is
       repainted, and the Total that is read is already the one with the checkbox
       checked. Half a picture of state A and half of state B.
       The name is the first text node of the first cell; the pills
       («raíz», «se recolecta») come after it. */
    function filasInforme(){
      var m = {}, raiz = null;
      document.querySelectorAll("#informeArbol tbody tr:not(.total)").forEach(function(tr){
        var c = tr.querySelectorAll("td");
        var nom = (c[0].childNodes[0] && c[0].childNodes[0].textContent || "").trim();
        if (!nom) return;
        /* By column NAME, not by index: see the note above and trap 16. The
           «Nivel» cell may contain the «criar» button, and `textContent` includes
           it, which is exactly what needs to be read. */
        m[nom] = {nec: Number(celdaDe(tr, "ADN necesario").replace(/[^\d]/g, "")) || 0,
                  nivel: celdaDe(tr, "Nivel"),
                  falta: Number(celdaDe(tr, "Falta").replace(/[^\d]/g, "")) || 0};
        if (tr.classList.contains("raiz-fila")) raiz = nom;
      });
      /* Columns: Criatura | Nivel | Necesario | Tienes | Falta | Fusiones
         (the «Rareza» one and the «Veces» one were removed on 25-sep).
         The Total row no longer carries a colspan: when it gained the «Criar a
         todas» button in the «Nivel» column, its 6 cells match the 6 columns, so
         `celdaDe` reads it the same as any other row. */
      var trTot = document.querySelector("#informeArbol tbody tr.total");
      var cT = trTot ? trTot.querySelectorAll("td") : [];
      return {porNombre: m, raiz: raiz,
              nCeldasTotal: cT.length,
              totalNec: cT.length ? Number(celdaDe(trTot, "ADN necesario").replace(/[^\d]/g, "")) || 0 : -1,
              totalFalta: cT.length ? Number(celdaDe(trTot, "Falta").replace(/[^\d]/g, "")) || 0 : -1};
    }

    chkSub.checked = true; ev(chkSub, "change");          // start from the checked state
    var cifON = cifrasDe("informeArbol");
    var iTot = indiceEtiqueta("informeArbol", /^ADN que falta/i);
    var iRec = indiceEtiqueta("informeArbol", /^A recolectar$/i);
    var iMon = indiceEtiqueta("informeArbol", /^Monedas$/i);
    ok("the report has its four labelled figures", iTot >= 0 && iRec >= 0 && iMon >= 0,
       JSON.stringify(etiquetasDe("informeArbol")));
    var ON = filasInforme();
    ok("the report marks which one is the root", !!ON.raiz, ON.raiz || "(no row with raiz-fila)");

    chkSub.checked = false; ev(chkSub, "change");
    var cifOFF = cifrasDe("informeArbol");
    var OFF = filasInforme();

    ok("turning the checkbox off changes the report", cifON[iTot] !== cifOFF[iTot],
       "total missing DNA: " + cifON[iTot] + " with the checkbox, " + cifOFF[iTot] + " without it");
    ok("and it changes to less: without levelling up ingredients less DNA is needed",
       cifOFF[iTot] < cifON[iTot], cifOFF[iTot] + " < " + cifON[iTot]);
    ok("what has to be gathered also drops", cifOFF[iRec] < cifON[iRec],
       cifON[iRec] + " -> " + cifOFF[iRec]);
    ok("the Coins also drop", cifOFF[iMon] < cifON[iMon],
       cifON[iMon] + " -> " + cifOFF[iMon]);

    /* The root ALWAYS pays its ladder: it is the target of the calculation, not an
       ingredient. Turning the checkbox off cannot make it cheaper. */
    ok("the root keeps its needed DNA with the checkbox off",
       ON.raiz && OFF.porNombre[ON.raiz] && ON.porNombre[ON.raiz].nec === OFF.porNombre[ON.raiz].nec,
       ON.raiz ? ON.raiz + ": " + ON.porNombre[ON.raiz].nec + " vs " +
                 (OFF.porNombre[ON.raiz] ? OFF.porNombre[ON.raiz].nec : "(does not come out)") : "(no root)");

    /* An ingredient can only have its ladder TAKEN AWAY, never added to. */
    var comunes = Object.keys(ON.porNombre).filter(function(k){ return OFF.porNombre[k]; });
    var suben = comunes.filter(function(k){ return OFF.porNombre[k].nec > ON.porNombre[k].nec; });
    ok("no ingredient goes up in DNA when the checkbox is turned off", suben.length === 0,
       suben.length + " go up" + (suben.length ? ": " + suben.slice(0,3).join(", ") : ""));

    var bajan = comunes.filter(function(k){
      return k !== ON.raiz && OFF.porNombre[k].nec < ON.porNombre[k].nec;
    });
    ok("and at least one ingredient drops, which is what is taken away from it", bajan.length > 0,
       bajan.length + " of " + comunes.length + " drop, e.g. " + (bajan[0] || "—"));

    /* Without the level-up there is no level range to show for an INGREDIENT:
       «16 → 20» would make you believe that level-up is being paid for. The root
       is the exception: it always pays its ladder, so it always shows its range.

       WATCH OUT about looking for «→» on its own: since 25-sep the arrow is used
       for TWO things —the level range («16 → 20») and the breed button
       («criar → 20», which is an action, not a range)—. That is why
       `esRangoNivel` looks for the full signature. It is more precise than
       before, not more lax: `/→/` took anything with the arrow for a range. */
    var rangos = comunes.filter(function(k){
      return k !== ON.raiz && esRangoNivel(OFF.porNombre[k].nivel);
    });
    ok("without levelling up ingredients no level range is shown", rangos.length === 0,
       rangos.length + " rows with a range" + (rangos.length ? ": " + rangos.slice(0,3).join(", ") : ""));
    ok("and the root keeps its range, because its ladder is indeed paid",
       !ON.raiz || esRangoNivel(OFF.porNombre[ON.raiz].nivel),
       ON.raiz ? ON.raiz + ": " + OFF.porNombre[ON.raiz].nivel : "(no root)");
    var rangosON = comunes.filter(function(k){ return esRangoNivel(ON.porNombre[k].nivel); });
    ok("with the checkbox checked ranges are shown where there are any", rangosON.length > 0,
       rangosON.length + " rows with a range");

    /* With the checkbox off, the same screen has to say by what criterion it
       calculates. Otherwise it gives two different answers depending on a checkbox
       that is in another tab, and neither of the two identifies itself. */
    ok("the report warns that it follows paleo.gg's criterion",
       /paleo\.gg/.test(txc("informeArbol")));
    chkSub.checked = true; ev(chkSub, "change");
    ok("and the notice disappears when it is checked again",
       !/criterio de paleo\.gg/.test(txc("informeArbol")));

    /* The total has to match the sum of the rows in BOTH states: if the
       aggregation and the rows came from different calculations, one of the two
       would be lying. */
    [["with the checkbox", cifON, ON], ["without the checkbox", cifOFF, OFF]].forEach(function(p){
      var sumaNec = 0, sumaFalta = 0;
      Object.keys(p[2].porNombre).forEach(function(k){
        sumaNec += p[2].porNombre[k].nec;
        sumaFalta += p[2].porNombre[k].falta;
      });
      ok("the «ADN necesario» column of the Total matches the rows " + p[0],
         p[2].nCeldasTotal === 6 && p[2].totalNec === sumaNec,
         p[2].nCeldasTotal + " cells | total " + p[2].totalNec + " vs sum of rows " + sumaNec);
      ok("and the «Falta» column of the Total too " + p[0],
         p[2].totalFalta === sumaFalta,
         "total " + p[2].totalFalta + " vs sum of rows " + sumaFalta);
    });
  } catch (e) {
    log("!! EXCEPTION in the switch part", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 13. THE TARGET LEVEL BELONGS TO EACH CREATURE ----------
  /* The target lived in a single place: the slider. There was only ONE write of
     `objetivo` in INV (the one from the «Guardar» button), so it did not exist
     until saving; and `elegir` kept the slider's value instead of restoring the
     creature's, so that setting 30 on the Indoraptor and moving to another dino
     left the 30 on the new one without anyone having asked for it. Request from
     n30 on 25-sep-2026: «guarda un nivel objetivo distinto para cada dino, eso
     debe reflejarse en la calculadora y en mis criaturas». */
  try {
    localStorage.removeItem("jwa322.inventario");
    localStorage.removeItem("jwa322.mios");
    INV = {}; MIS = []; guardar();

    function objetivo(){ return Number(document.getElementById("nivelObj").value); }
    function objGuardado(u){ return INV[u] ? INV[u].objetivo : undefined; }
    function celdaObjetivo(u){
      var tr = document.querySelector('#miosCuerpo tr[data-ir="' + u + '"]');
      return tr ? celdaDe(tr, "Objetivo") : "(no row)";
    }

    elegir("indoraptor");
    ok("a creature without a saved target starts at the cap", objetivo() === 35,
       "slider = " + objetivo());
    teclear(document.getElementById("nivelObj"), "30");
    ok("moving the slider saves that creature's target", objGuardado("indoraptor") === 30,
       "saved = " + objGuardado("indoraptor"));

    elegir("tyrannosaurus_rex");
    ok("when changing creature the previous one's target is NOT inherited", objetivo() === 35,
       "the t-rex appears at " + objetivo() + " and the indoraptor had 30");
    teclear(document.getElementById("nivelObj"), "25");

    elegir("indoraptor");
    ok("on returning, each creature recovers its own", objetivo() === 30, "indoraptor = " + objetivo());
    elegir("tyrannosaurus_rex");
    ok("and the other one its own", objetivo() === 25, "t-rex = " + objetivo());

    elegir("indoraptor"); document.getElementById("btnGuardar").click();
    elegir("tyrannosaurus_rex"); document.getElementById("btnGuardar").click();
    ok("«Mis criaturas» shows the target of each row",
       celdaObjetivo("indoraptor") === "30" && celdaObjetivo("tyrannosaurus_rex") === "25",
       "indoraptor " + celdaObjetivo("indoraptor") + " / t-rex " + celdaObjetivo("tyrannosaurus_rex"));

    /* The tree takes the target of the root FROM THE SLIDER, so it has to find
       out when it is moved. Before, the handler only called `calcular`, and the
       root kept the previous target: the same screen gave two answers. */
    elegir("indoraptor");
    irA("arbol"); pintarArbol();
    var raiz30 = document.querySelector(".arbol .nodo.raiz").textContent.replace(/\s+/g, " ");
    ok("the root of the tree quotes its creature's target", /→ 30/.test(raiz30), raiz30.slice(0, 78));
    irA("calc"); teclear(document.getElementById("nivelObj"), "33");
    irA("arbol"); pintarArbol();
    var raiz33 = document.querySelector(".arbol .nodo.raiz").textContent.replace(/\s+/g, " ");
    ok("and it finds out when the slider is moved, without keeping the 30",
       /→ 33/.test(raiz33) && !/→ 30/.test(raiz33), raiz33.slice(0, 78));

    /* `fijar` REPLACES the whole INV object: if it did not carry the target
       along, typing the DNA of an ingredient would erase the root's target. */
    irA("arbol"); pintarArbol();
    var ing = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
    var uIng = ing.dataset.u;
    teclear(ing, "999");
    ok("typing in the tree does not erase the root's target", objGuardado("indoraptor") === 33,
       "now it is " + objGuardado("indoraptor"));
    ok("and the ingredient does not keep a target that nobody gave it",
       objGuardado(uIng) === undefined, "ingredient target = " + objGuardado(uIng));

    var crudo = JSON.parse(localStorage.getItem("jwa322.inventario") || "{}");
    ok("the target is persisted, creature by creature",
       crudo.indoraptor && crudo.indoraptor.objetivo === 33 &&
       crudo.tyrannosaurus_rex && crudo.tyrannosaurus_rex.objetivo === 25,
       "indoraptor " + (crudo.indoraptor && crudo.indoraptor.objetivo) +
       " / t-rex " + (crudo.tyrannosaurus_rex && crudo.tyrannosaurus_rex.objetivo));

    /* The × forgets that creature's data, target included: if it was open, the
       slider cannot keep showing the one of a creature that no longer has data. */
    elegir("tyrannosaurus_rex");
    irA("mios");
    var x = document.querySelector('#miosCuerpo [data-borrar="tyrannosaurus_rex"]');
    ok("there is a × for the t-rex in the list", !!x);
    if (x) x.click();
    ok("after the ×, the open creature goes back to the cap", objetivo() === 35,
       "slider = " + objetivo());
    irA("calc");
  } catch (e) {
    log("!! EXCEPTION in the target per creature", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 14. breeding from the report ----------
  /* Request from n30 (25-sep-2026): «cuando no esté creado un dino, despues de su
     nombre NO aparezca la leyenda "sin crear", pero en la columna "nivel" si
     aparezca, pero en lugar de "sin crear" dirá "criar" y al hacer click en la
     palabra pongas el nivel mínimo del dino, en la intersección con la fila
     donde dice "total del arbol" y "nivel" si hay al menos una criatura no
     criada habrá un texto que diga "Criar a todas"».

     What has to be pinned down here, and why each thing:
       - the «sin crear» state is still VISIBLE, only in the level column and as
         an action. If it disappeared from both places, the report would stop
         saying that creature does not exist;
       - pressing «criar» is NOT a simulation: it has to change the inventory for
         real, through the same path as the tree checkbox, because the level is
         saved and then shows up in the tree tab and in «Mis criaturas»;
       - «Criar a todas» sets the LEVEL OF THE FUSION —not the birth one, which
         was the first thing asked for and n30 corrected on 25-sep: «debe poner
         al nivel minimo usable para el dinosaurio de la calculadora»—, and it
         touches ONLY the ones that are not created or the ones that are BELOW
         that level. The ROOT is left out: «la criatura raiz no se modifica,
         solamente su arbol». */
  try {
    localStorage.removeItem("jwa322.inventario");
    localStorage.removeItem("jwa322.mios");
    INV = {}; MIS = []; guardar();
    /* The scenario has to cover the FOUR cases at once, because whether the
       shortcut is judged for real depends on it:
         - indoraptor      the ROOT, created at 25 (born at 21, its target is 30).
                           It cannot be touched, even if it is not at its target.
         - indominus_rex   created ABOVE the level the fusion demands (30, when
                           only 20 is asked of it). It is the most important
                           control: an implementation that «put them all at the
                           fusion level» would LOWER it to 20, that is, it would
                           erase 10 levels the user already has. And one that
                           «reset» the created ones would lower it to its birth
                           (16). Both cases are visible here, because 30 is
                           neither 20 nor 16.
         - tyrannosaurus_rex  created BELOW what the fusion demands: it is born at
                           11 and the Indominus Rex fusion (legendary) asks for it
                           at 15. It has to GO UP to 15.
         - velociraptor    NOT created. It has to end up at 20, which is what the
                           Indoraptor fusion (unique) asks for — not at 1, which
                           is where it is born.
       It is assembled twice (the individual button and the shortcut change the
       inventory), which is why it is a function and not a batch of loose lines. */
    function montarEscenario(){
      localStorage.removeItem("jwa322.inventario");
      localStorage.removeItem("jwa322.mios");
      INV = {}; MIS = []; guardar();
      elegir("indoraptor");
      document.getElementById("nivelObj").value = 30;
      ev(document.getElementById("nivelObj"), "input");
      teclear(document.getElementById("nivelAct"), "25");
      teclear(document.getElementById("adnTengo"), "1000");
      fijar("indominus_rex", "nivel", 30);
      fijar("tyrannosaurus_rex", "nivel", 11);
      refrescar();
    }
    montarEscenario();

    function filaInforme(nom){
      var f = null;
      document.querySelectorAll("#informeArbol tbody tr:not(.total)").forEach(function(tr){
        if (tr.querySelector("td").textContent.indexOf(nom) === 0) f = tr;
      });
      return f;
    }
    var filaTRex = filaInforme("Tyrannosaurus Rex");
    var filaInd = filaInforme("Indoraptor");
    var filaVel = filaInforme("Velociraptor");
    var filaIndom = filaInforme("Indominus Rex");
    ok("the report has the rows of this test",
       !!filaTRex && !!filaInd && !!filaVel && !!filaIndom,
       [["t-rex",filaTRex],["indoraptor",filaInd],["velociraptor",filaVel],["indominus",filaIndom]]
         .map(function(p){ return p[1] ? p[0]+" ok" : "WITHOUT "+p[0]; }).join(" / "));

    /* 1) The «sin crear» pill no longer goes after the name, in ANY row. */
    var conPildora = [];
    document.querySelectorAll("#informeArbol tbody tr:not(.total)").forEach(function(tr){
      if (/sin crear/.test(tr.querySelector("td").textContent)) conPildora.push(tr.querySelector("td").textContent.trim().slice(0, 30));
    });
    ok("no row of the report carries «sin crear» after the name",
       conPildora.length === 0, conPildora.join(" | ") || "none");

    /* 2) But the state is NOT lost: it is in the «Nivel» column, and it is also
          the action. The tree tab's pill is still where it was: the change is in
          the REPORT, not in the tab.
          The button is looked for in VELOCIRAPTOR, which is the only creature
          NOT CREATED in the scenario. T-Rex is also below what is asked of it,
          but it is CREATED, so it does not carry a button: the shortcut reaches
          it anyway, and that is checked further down. */
    ok("the tree tab keeps its «sin crear» pill",
       /sin crear/.test(txt("arbolCuerpo")), "tree tab");
    var btnCriar = filaVel ? filaVel.querySelector('[data-criar="velociraptor"]') : null;
    ok("a creature not created carries the «criar» button in the Nivel column",
       !!btnCriar && btnCriar.textContent.trim() === "criar" &&
       celdaDe(filaVel, "Nivel").indexOf("criar") === 0,
       btnCriar ? "button «" + btnCriar.textContent.trim() + "», cell «" +
                  celdaDe(filaVel, "Nivel") + "»" : "(no button)");
    ok("and one already created does NOT carry it",
       filaInd && !filaInd.querySelector("[data-criar]") &&
       esRangoNivel(celdaDe(filaInd, "Nivel")),
       filaInd ? "cell «" + celdaDe(filaInd, "Nivel") + "»" : "(no row)");

    /* 3) The Total row offers the shortcut. WATCH OUT: the set the shortcut is
          going to touch is NO LONGER the buttons. T-Rex is created (at 11) and
          that is why it does not carry a button, but the shortcut DOES have to
          reach it, because it is below the level the fusion demands. The list
          that the report publishes for the shortcut is looked at, which comes
          from the same `cri` that paints the rows. */
    var trTot = document.querySelector("#informeArbol tbody tr.total");
    var btnTodas = trTot ? trTot.querySelector("[data-criar-todas]") : null;
    ok("the Total row offers «Criar a todas» in the Nivel column",
       !!btnTodas && btnTodas.textContent.trim() === "Criar a todas" &&
       celdaDe(trTot, "Nivel").indexOf("Criar a todas") === 0,
       (btnTodas ? "«" + btnTodas.textContent.trim() + "»" : "(no button)") +
       " | cell «" + celdaDe(trTot, "Nivel") + "»");

    var dichoPorCriar = {};
    POR_CRIAR.forEach(function(x){ dichoPorCriar[x.uuid] = x.nivel; });
    ok("the shortcut takes the two that do not work, and NEITHER the root NOR the one already at its level",
       Object.keys(dichoPorCriar).sort().join(",") === "tyrannosaurus_rex,velociraptor" &&
       dichoPorCriar.tyrannosaurus_rex === 15 && dichoPorCriar.velociraptor === 20,
       JSON.stringify(dichoPorCriar));

    /* 4) Pressing «criar» leaves the creature AT THE LEVEL THE FUSION DEMANDS.
          Before it left it at its birth level —Velociraptor is common, that is,
          1— and the number on the arrow was not the one left in place: it had to
          be raised afterwards. n30 corrected it on 25-sep. */
    if (btnCriar) btnCriar.click();
    var invVel = invDe("velociraptor");
    ok("pressing «criar» leaves it at the fusion level (20), not at the birth one (1)",
       invVel.creado === true && invVel.nivel === 20 && minLv(C["velociraptor"][1]) === 1,
       "created=" + invVel.creado + " level=" + invVel.nivel +
       " (born at " + minLv(C["velociraptor"][1]) + ")");
    var filaVel2 = filaInforme("Velociraptor");
    ok("and its row stops offering to breed",
       filaVel2 && !filaVel2.querySelector("[data-criar]"),
       filaVel2 ? "cell «" + celdaDe(filaVel2, "Nivel") + "»" : "(no row)");

    /* 5) «Criar a todas», with the FOUR cases at once. The scenario is assembled
          again because step 4 already changed the inventory. */
    montarEscenario();
    var antes = {};
    ["indoraptor","indominus_rex","tyrannosaurus_rex","velociraptor"].forEach(function(u){
      var v = invDe(u); antes[u] = {creado:v.creado, nivel:v.nivel};
    });
    log("before «Criar a todas»", JSON.stringify(antes));

    /* That the scenario is GOOD for judging, checked BEFORE pressing. If any of
       these numbers coincided with what a wrong implementation produces, the
       check afterwards would pass without proving anything:
         - the root is at 25; it is born at 21 and its target is 30, so neither
           «reset to the minimum» nor «push to the target» would go unnoticed;
         - Indominus Rex is at 30 and is born at 16: neither lowering it to the
           required level (20) nor resetting it to its birth would go unnoticed; */
    ok("the scenario distinguishes the four cases (root / above / below / not created)",
       antes.indoraptor.nivel === 25 && minLv(C["indoraptor"][1]) === 21 &&
       antes.indominus_rex.nivel === 30 && minLv(C["indominus_rex"][1]) === 16 &&
       antes.tyrannosaurus_rex.nivel === 11 && minLv(C["tyrannosaurus_rex"][1]) === 11 &&
       antes.velociraptor.creado === false,
       JSON.stringify(antes));

    var btnTodas2 = document.querySelector("#informeArbol tbody tr.total [data-criar-todas]");
    if (btnTodas2) btnTodas2.click();

    var ahora = {};
    ["indoraptor","indominus_rex","tyrannosaurus_rex","velociraptor"].forEach(function(u){
      var v = invDe(u); ahora[u] = {creado:v.creado, nivel:v.nivel};
    });
    log("after «Criar a todas»", JSON.stringify(ahora));

    ok("«Criar a todas» does NOT touch the ROOT, even if it is below its target",
       ahora.indoraptor.creado === true && ahora.indoraptor.nivel === 25,
       "indoraptor: " + antes.indoraptor.nivel + " → " + ahora.indoraptor.nivel);

    ok("and it does NOT LOWER one already created that was above the required level (30, 20 is asked of it)",
       ahora.indominus_rex.creado === true && ahora.indominus_rex.nivel === 30,
       "indominus_rex: " + antes.indominus_rex.nivel + " → " + ahora.indominus_rex.nivel);

    ok("but it DOES raise one created that was below the required level (11 → 15)",
       ahora.tyrannosaurus_rex.creado === true && ahora.tyrannosaurus_rex.nivel === 15,
       "tyrannosaurus_rex: " + antes.tyrannosaurus_rex.nivel + " → " + ahora.tyrannosaurus_rex.nivel);

    ok("and the one that was not created is left created at the required level (20)",
       ahora.velociraptor.creado === true && ahora.velociraptor.nivel === 20,
       "velociraptor: " + antes.velociraptor.nivel + " → " + ahora.velociraptor.nivel);

    /* 6) And the shortcut disappears on its own: when there is no one left below,
          there is nothing to do. If the button were still there, the report would
          be offering an action that does nothing. */
    ok("the shortcut disappears when there is no one left to create or below",
       !document.querySelector("#informeArbol [data-criar-todas]") && POR_CRIAR.length === 0,
       POR_CRIAR.length + " in the shortcut list, " +
       document.querySelectorAll("#informeArbol [data-criar-todas]").length + " buttons");
    ok("and no row of the report says «sin crear» any more",
       !/sin crear/.test(txc("informeArbol")), "full report");

    /* 7) The levels were really saved, not just painted: it is the same data
          used by the tree tab and «Mis criaturas». */
    var crudo2 = JSON.parse(localStorage.getItem("jwa322.inventario") || "{}");
    ok("what was changed is really saved in the inventory",
       crudo2.tyrannosaurus_rex && crudo2.tyrannosaurus_rex.creado === true &&
       crudo2.tyrannosaurus_rex.nivel === 15 &&
       crudo2.indoraptor && crudo2.indoraptor.nivel === 25,
       "t-rex " + JSON.stringify(crudo2.tyrannosaurus_rex) +
       " | indoraptor " + JSON.stringify(crudo2.indoraptor));
  } catch (e) {
    log("!! EXCEPTION in breeding from the report", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- images ----------
  var bien = 0, mal = [];
  CLONES.forEach(function(c){ if (c.el.complete && c.el.naturalWidth > 0) bien++; else mal.push(c.src); });
  if (CLONES.length)
    ok("all the referenced images load", mal.length === 0,
       bien + "/" + CLONES.length + " ok" + (mal.length ? " fail: " + mal.slice(0,3).join(", ") : ""));

  log("", "");
  log(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===", "");
  var d = document.createElement("pre");
  d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:15px/1.5 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\n");
  document.body.appendChild(d);
__ENTREGA__
});

/* The images are checked with clones that DO load: `loading="lazy"` does not load
   anything that is in a hidden container, so looking at the <img> of the tree tab
   would give 0x0 and would be an artifact of the test, not a failure of the page. */
(function(){
  var srcs = [];
  document.querySelectorAll("img").forEach(function(im){
    var s = im.getAttribute("src");
    if (s && srcs.indexOf(s) < 0) srcs.push(s);
  });
  log("distinct images referenced", srcs.length);
  srcs.forEach(function(s){
    var c = new Image(); c.src = s;
    c.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
    document.body.appendChild(c);
    CLONES.push({src: s, el: c});
  });
})();
</script>
"""

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

html = open(HTML, encoding="utf-8").read()
# Pin the language for this run. The assertions below are written against the
# Spanish rendering, and the app now boots in English. window.__lang beats
# whatever a previous run stored, so the result does not depend on leftover
# state; the storage is cleared too, as a second line of defence. It must go in
# the <head>: the app resolves the language while parsing it.
PIN = ('<script>window.__lang = "es";'
       'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
if "<head>" not in html:
    raise SystemExit("I cannot find <head> to pin the language")
html = html.replace("<head>", "<head>\n" + PIN, 1)
m = re.search(r"<body[^>]*>", html)
html = html[:m.end()] + CAZA + html[m.end():] + DIAG.replace("__ENTREGA__", srv.js("__diag"))
# Before opening the browser: if the diagnostic does not compile together with
# the application —name collision in the global scope—, the test would not run
# and the symptom would be «it did not deliver the report», which says nothing.
# See informe_browser.
_ok_scripts, _msg_scripts = comprobar_scripts(html, "probar_estres.py")
print(_msg_scripts)
if not _ok_scripts:
    raise SystemExit("!! " + _msg_scripts)
open(FUERA, "w", encoding="utf-8").write(html)

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
r = subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                    "--window-size", "1400,2200", "--screenshot", SHOT, "file://" + FUERA],
                   env=env, capture_output=True, text=True, timeout=240)
if r.stderr.strip() and "headless" not in r.stderr:
    print("stderr:", r.stderr.strip()[:400])
print("png:", SHOT, os.path.getsize(SHOT) if os.path.exists(SHOT) else "NO")

srv.parar()
informe = srv.texto().strip()

TXT = os.path.join(DIR, "estres.txt")
open(TXT, "w", encoding="utf-8").write(informe + "\n")
print("report:", TXT)
print("-" * 72)
print(informe)
print("-" * 72)

codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)
raise SystemExit(codigo)
