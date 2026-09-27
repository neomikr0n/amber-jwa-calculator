#!/usr/bin/env python3
"""
Prueba de ESTRES y de las zonas que quedaron sin tocar desde los cambios.

Cubre lo que las otras pruebas no:
  - El arbol mas grande del juego (Rajadorixis, 15 nodos): que pinte entero, con
    que profundidad REAL de anidamiento, y cuanto TARDA. El arbol se repinta en
    cada tecla, asi que el tiempo importa.
  - Techo de ADN: que avise cuando el deficit supera el tope de inventario.
  - Las cifras del modelo (fusion, topes, niveles, monedas) contra los valores
    DOCUMENTADOS. Antes se comprobaban leyendo las tablas de la pestana
    «Referencia», que se quito el 25-sep-2026: la comprobacion se reescribio para
    no perderla. (La version anterior de esta prueba usaba regexes del tipo /35/
    sobre el texto de toda la pestana: eso lo cumple hasta una tabla vacia. No
    medía nada.)
  - El bloque de nivel maximo de cada nodo, contrastado con nivelMaximo().
  - Exportar / borrar / importar PULSANDO LOS BOTONES DE VERDAD, no replicando
    su logica dentro de la prueba.

Todo es sincrono a proposito: Firefox hace la captura justo despues del evento
`load`, asi que si el informe se pintase tras un `await` la captura saldria en
blanco. Por eso el FileReader de la pagina se sustituye por un doble sincrono
(lo que se dobla es la API del navegador, no la logica de la pagina).

Uso:  python3 probar_estres.py
"""
import os, re, shutil, subprocess
import informe_browser
from informe_browser import arrancar, comprobar_scripts, veredicto

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-estres"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "estres.html")
SHOT = os.path.join(DIR, "estres.png")

# El informe viaja por aqui, no por una captura que hay que leer a ojo.
srv = arrancar()

CAZA = r"""
<script>
window.__errores = [];
window.addEventListener("error", function(e){
  window.__errores.push((e.message || "?") + " @ linea " + (e.lineno||"?"));
});
</script>
"""

DIAG = r"""
<script>
var RES = [], FALLOS = 0, CLONES = [], NOTAS = [];
var ALERTAS = [], BLOB = null, ANCLA = null, ENTRADA = null, TEXTO_BLOB = null;
function log(k, v){ RES.push(k + ": " + (v === undefined ? "" : v)); }
function ok(k, cond, detalle){ if (!cond) FALLOS++; log((cond ? "OK   " : "FALLO") + " " + k, detalle); }
function txt(id){ var e = document.getElementById(id); return e ? e.innerText.replace(/\s+/g," ").trim() : "(falta "+id+")"; }
function txc(id){ var e = document.getElementById(id); return e ? e.textContent.replace(/\s+/g," ").trim() : "(falta "+id+")"; }
/* Las cifras de un panel, en orden, sin el formato de miles. */
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
/* Indice de una cifra por su rotulo, tolerando que el rotulo se alargue.
   `indexOf` sobre el array exige coincidencia EXACTA: en cuanto el informe paso
   de «ADN que falta» a «ADN que falta en total», la busqueda devolvio -1 y la
   comprobacion fallo diciendo «cifra undefined». El fallo estaba en la prueba,
   no en la pagina. */
function indiceEtiqueta(id, patron){
  return etiquetasDe(id).findIndex(function(t){ return patron.test(t); });
}
/* --- Leer una celda por el NOMBRE de su columna, no por su posicion ---
   Dos comprobaciones de esta prueba leian `tr.querySelectorAll("td")[5]` y
   `[6]` dando por hecho el ancho de la tabla de «Mis criaturas». Cuando esa
   tabla gano la columna «Mejoras» (25-sep-2026) las dos siguieron pasando por
   los mismos indices y empezaron a comparar OTRA cosa: la de «Nivel max. hoy»
   leia el ADN (4,321 contra 31) y la del «Objetivo» leia la columna de al
   lado. La prueba no fallaba por el cambio de columnas: fallaba porque
   preguntaba «la sexta celda» cuando queria preguntar «la celda del nivel
   maximo». Ahora se pregunta por el nombre, y si la columna no existe lo dice
   en vez de devolver un numero de otra. */
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
/* Devuelve el texto de la celda de `tr` que cae bajo la columna `cabecera`.
   Si la columna no existe, o la fila tiene menos celdas que la cabecera (un
   colspan la desplaza), devuelve un texto que NO es un numero y que se lee en
   el detalle del fallo: asi el fallo dice que se rompio, y por que. */
function celdaDe(tr, cabecera){
  var tabla = tr.closest("table");
  if (!tabla) return "(la fila no esta en una tabla)";
  var i = colDe(tabla, cabecera);
  if (i < 0) return "(no hay columna «" + cabecera + "»)";
  var tds = tr.querySelectorAll("td");
  if (tds.length !== tabla.querySelectorAll("thead th").length)
    return "(la fila tiene " + tds.length + " celdas y la cabecera " +
           tabla.querySelectorAll("thead th").length + ": hay un colspan)";
  return tds[i].textContent.trim();
}
function ev(el, t){ el.dispatchEvent(new Event(t, {bubbles:true})); }
/* ¿La celda «Nivel» del informe ensena un RANGO de niveles («16 → 20»)?
   Se busca la firma completa —numero, flecha, numero— y no la flecha a secas,
   porque desde el 25-sep-2026 la flecha se usa para DOS cosas: el rango y el
   boton de criar («criar → 20», que es una accion y no un rango). Buscar el
   simbolo suelto confundiria las dos. */
function esRangoNivel(t){ return /^\d+\s*→\s*\d+/.test(String(t).trim()); }
function teclear(el, v){ el.focus(); el.value = v; ev(el, "input"); }
function medir(f, n){
  n = n || 1;
  var t0 = performance.now();
  for (var i = 0; i < n; i++) f();
  return (performance.now() - t0) / n;
}
/* Profundidad real de anidamiento de un nodo: cuantos .rama lo envuelven. */
function profundidad(nodo){
  var d = 0, el = nodo.parentElement;
  while (el){ if (el.classList && el.classList.contains("rama")) d++; el = el.parentElement; }
  return d;
}

/* Estado de partida determinista: el perfil de Firefox persiste entre
   ejecuciones, asi que sin esto la prueba arranca con lo que dejo la anterior.
   Hay que limpiar LAS DOS cosas: `INV` (los datos) y `MIS` («Mis criaturas»).
   Olvidar `MIS` hacia que el numero de fallos cambiara de una pasada a otra. */
INV = {}; MIS = []; guardar();

try {
  log("=== errores al cargar ===",
      (window.__errores && window.__errores.length) ? window.__errores.join(" | ") : "ninguno");

  // ---------- 1. EL ARBOL MAS GRANDE: Rajadorixis (15 nodos) ----------
  elegir("rajadorixis");
  teclear(document.getElementById("nivelAct"), "0");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  document.querySelector('nav button[data-t="arbol"]').click();

  var nodos = document.querySelectorAll("#arbolCuerpo .nodo");
  log("Rajadorixis: nodos pintados", nodos.length);
  ok("el arbol mas grande se pinta entero", nodos.length >= 12, nodos.length + " nodos");

  var camposOk = 0, fotos = 0, sinMax = 0;
  nodos.forEach(function(n){
    if (n.querySelector("input[data-campo='nivel']") &&
        n.querySelector("input[data-campo='adn']") &&
        n.querySelector("input[data-campo='creado']")) camposOk++;
    if (n.querySelector("img.foto")) fotos++;
    if (!n.querySelector(".maxn")) sinMax++;
  });
  ok("todos los nodos del arbol grande tienen sus campos", camposOk === nodos.length,
     camposOk + "/" + nodos.length);
  ok("todos los nodos del arbol grande tienen foto", fotos === nodos.length,
     fotos + "/" + nodos.length);
  ok("todos los nodos del arbol grande ensenan su nivel maximo", sinMax === 0,
     (nodos.length - sinMax) + "/" + nodos.length);

  var profMax = 0;
  nodos.forEach(function(n){ profMax = Math.max(profMax, profundidad(n)); });
  ok("el arbol grande tiene anidamiento real, no es plano", profMax >= 2,
     "profundidad maxima " + profMax);

  var caja = document.querySelector("#arbolCuerpo").getBoundingClientRect();
  var salidos = 0, peor = 0;
  nodos.forEach(function(n){
    var r = n.getBoundingClientRect();
    var sob = r.right - caja.right;
    if (sob > 1) salidos++;
    if (sob > peor) peor = sob;
  });
  ok("ningun nodo se sale del arbol por la derecha", salidos === 0,
     salidos + " se salen; peor exceso " + Math.round(peor) + " px");

  // ---------- 2. TIEMPO DE REPINTADO ----------
  var tPintar = medir(function(){ pintarArbol(); }, 20);
  log("pintarArbol() en el arbol de 15 nodos", tPintar.toFixed(1) + " ms");
  ok("repintar el arbol grande es rapido (<120 ms)", tPintar < 120, tPintar.toFixed(1) + " ms");

  // el caso real: teclear en un campo del fondo del arbol.
  // OJO: hay que VOLVER A BUSCAR el campo en cada vuelta. Al repintarse el arbol
  // el elemento anterior queda suelto del DOM, su evento ya no sube al contenedor
  // y las siguientes pulsaciones no hacen nada: se mide una de verdad y catorce
  // de mentira, y la media sale falsamente buena.
  function teclearFondo(){
    var f = document.querySelectorAll("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
    teclear(f[f.length - 1], String(Math.random()*1000|0));
  }
  var tTecla = medir(teclearFondo, 15);
  log("una tecla en un campo del fondo", tTecla.toFixed(1) + " ms");
  ok("teclear sigue siendo fluido (<150 ms por tecla)", tTecla < 150, tTecla.toFixed(1) + " ms");

  // La tecla en el arbol ahora repinta tambien la calculadora y el informe del
  // arbol entero, asi que hay que volver a medirlo. Y una tecla en la CALCULADORA
  // repinta el arbol: es el otro sentido de la misma ida y vuelta.
  //
  // OJO: hay que forzar ADN 0 en la raiz. Con ADN de sobra la poda deja el arbol
  // reducido a la raiz sola, y entonces la medida sale buenísima y no vale nada.
  elegir("rajadorixis");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  document.querySelector('nav button[data-t="arbol"]').click();
  var nodosR = document.querySelectorAll("#arbolCuerpo .nodo").length;
  ok("la medida de tiempo se hace con el arbol grande de verdad", nodosR >= 12, nodosR + " nodos");
  var fondo2 = document.querySelectorAll("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  ok("y con campos del fondo donde teclear", fondo2.length > 0, fondo2.length + " campos");
  var tTecla2 = medir(teclearFondo, 15);
  log("una tecla en el arbol, con la calculadora y el informe detras", tTecla2.toFixed(1) + " ms");
  ok("sigue siendo fluido (<150 ms por tecla)", tTecla2 < 150, tTecla2.toFixed(1) + " ms");

  // Y el otro sentido: teclear en la calculadora repinta el arbol de 15 nodos.
  // Valores bajos a proposito, para que el arbol no se pode mientras se mide.
  elegir("rajadorixis");
  document.querySelector('nav button[data-t="calc"]').click();
  var tCalc = medir(function(){ teclear(document.getElementById("adnTengo"), String(Math.random()*99|0)); }, 15);
  log("una tecla en la calculadora, con el arbol detras", tCalc.toFixed(1) + " ms");
  ok("y en la calculadora tambien (<150 ms por tecla)", tCalc < 150, tCalc.toFixed(1) + " ms");
  ok("al medir la calculadora el arbol sigue entero",
     document.querySelectorAll("#arbolCuerpo .nodo").length >= 12,
     document.querySelectorAll("#arbolCuerpo .nodo").length + " nodos");
  var tInforme = medir(function(){ calcular(); }, 20);
  log("calcular() entero, con el informe del arbol de " +
      document.querySelectorAll("#arbolCuerpo .nodo").length + " nodos", tInforme.toFixed(1) + " ms");
  ok("recalcular la calculadora es rapido (<120 ms)", tInforme < 120, tInforme.toFixed(1) + " ms");

  // Desglose, para saber donde se va el tiempo de una pulsacion.
  var tMios = medir(function(){ pintarMios(); }, 20);
  var tLista = medir(function(){ pintarLista(); }, 20);
  document.getElementById("lista").classList.remove("on");
  log("desglose por repintado",
      "arbol " + medir(function(){ pintarArbol(); }, 20).toFixed(1) +
      " | calcular " + tInforme.toFixed(1) +
      " | mios " + tMios.toFixed(1) +
      " | lista " + tLista.toFixed(1) + " ms");

  // ---------- 3. TECHO DE ADN ----------
  elegir("93_classic_t_rex");   // omega: tope 60.000, escalera 1->30 = 41.700
  teclear(document.getElementById("nivelAct"), "0");
  teclear(document.getElementById("adnTengo"), "0");
  document.getElementById("nivelObj").value = 35;
  ev(document.getElementById("nivelObj"), "input");
  var res = txt("resultado");
  ok("avisa del techo de ADN cuando el deficit lo supera",
     /tope de ADN/i.test(res) && /tandas/i.test(res), res.slice(0, 170));
  ok("el tope que cita es el del omega (60.000)", /60,000/.test(res), res.slice(0, 200));

  // ---------- 4. LAS CIFRAS DEL MODELO ----------
  /* Aqui estaba la comprobacion de la pestaña «Referencia», celda por celda
     contra el modelo. La pestaña se quito el 25-sep-2026 a peticion de n30, y con
     ella las cuatro tablas. Aquellas comprobaciones hacian DOS cosas a la vez:
     verificar que la tabla pintada coincidia con `M`, y que `M` tenia los valores
     buenos. Lo primero ya no existe (no hay tabla que mirar); lo segundo se queda
     aqui, contra las cifras DOCUMENTADAS, para que quitar la pestaña no se lleve
     por delante la verificacion sin que nadie se entere.
     Estos valores no se re-derivan: son los del comunicado oficial y paleo.gg,
     escritos a mano. Si el modelo cambia, esta prueba tiene que protestar. */
  /* `adnFus` indexa por el SALTO de rareza, no por la rareza: dos consecutivas
     (common→rare) saltan 1 y valen 50. Los 200/500/2000 son saltos de 2, 3 y 4,
     asi que hay que elegir los pares por su salto, no al azar. La primera
     version de esta comprobacion pedia 50/200/500/2000 a cuatro pares
     consecutivos y daba 50/50/50/50: el fallo era de la prueba. */
  ok("el coste por fusion es 50/200/500/2000 segun el SALTO de rareza",
     adnFus("common","rare") === 50 && adnFus("common","epic") === 200 &&
     adnFus("common","legendary") === 500 && adnFus("common","unique") === 2000 &&
     adnFus("rare","epic") === 50,
     [adnFus("common","rare"), adnFus("common","epic"), adnFus("common","legendary"),
      adnFus("common","unique")].join(" / ") + "  (saltos 1/2/3/4)");
  ok("el salto de rareza (tier) va de 0 a 5 en orden",
     M.tier.common === 0 && M.tier.rare === 1 && M.tier.epic === 2 &&
     M.tier.legendary === 3 && M.tier.unique === 4 && M.tier.apex === 5,
     JSON.stringify(M.tier));
  ok("los topes de ADN son los oficiales del 31-ago-2026",
     M.topes.common === 850000 && M.topes.rare === 250000 && M.topes.epic === 85000 &&
     M.topes.legendary === 25000 && M.topes.unique === 8000 && M.topes.apex === 3000,
     JSON.stringify(M.topes));
  ok("el tope del omega que usa el motor es 60.000", M.topes.omega === 60000,
     "M.topes.omega = " + nf(M.topes.omega));
  ok("los niveles de nacimiento son 1/6/11/16/21/26",
     minLv("common") === 1 && minLv("rare") === 6 && minLv("epic") === 11 &&
     minLv("legendary") === 16 && minLv("unique") === 21 && minLv("apex") === 26,
     ["common","rare","epic","legendary","unique","apex"].map(minLv).join(" / "));
  ok("el nivel minimo de ingredientes es uno menos que el de nacimiento",
     ["common","rare","epic","legendary","unique","apex"].every(function(r){
       return M.minIngrediente[r] === minLv(r) - 1;
     }),
     JSON.stringify(M.minIngrediente));
  ok("el ADN para crear es 50/100/150/200/250/300",
     M.creacion.common === 50 && M.creacion.rare === 100 && M.creacion.epic === 150 &&
     M.creacion.legendary === 200 && M.creacion.unique === 250 && M.creacion.apex === 300,
     JSON.stringify(M.creacion));
  ok("las monedas por fusion son 20/20/100/200/1000/2000",
     M.monedasFusion.common === 20 && M.monedasFusion.rare === 20 &&
     M.monedasFusion.epic === 100 && M.monedasFusion.legendary === 200 &&
     M.monedasFusion.unique === 1000 && M.monedasFusion.apex === 2000,
     JSON.stringify(M.monedasFusion));

  /* La pestana «Referencia» se quito a peticion de n30. Se comprueba que NO
     vuelve: si alguien la reintroduce, esto falla y se entera. Se mira tanto el
     boton como la seccion, porque quitar solo uno deja una pestana que no se
     puede abrir. */
  ok("ya no existe la pestana «Referencia»",
     !document.querySelector('nav button[data-t="ref"]') && !document.getElementById("s-ref"),
     "botones: " + Array.from(document.querySelectorAll("nav button")).map(function(b){ return b.dataset.t; }).join(", "));
  ok("quedan las cuatro pestanas de verdad", document.querySelectorAll("nav button").length === 4,
     document.querySelectorAll("nav button").length + " botones y " +
     document.querySelectorAll("section").length + " secciones");

  // ---------- 5. CATALIZADORES ----------
  document.querySelector('nav button[data-t="cat"]').click();
  document.getElementById("cComun").value = 20000;
  document.getElementById("cRara").value = 0;
  document.getElementById("cEpica").value = 2000;
  document.getElementById("cLegend").value = 500;
  document.getElementById("btnCat").click();
  var cat = txt("catSalida");
  ok("el planificador de catalizadores responde", cat.length > 20, cat.slice(0, 110));
  // 20000*1 + 2000*15 + 500*50 = 20.000 + 30.000 + 25.000 = 75.000
  // OJO: innerText devuelve el texto YA transformado por CSS (.cifra .k va en
  // mayusculas), asi que "Sobran" se lee "SOBRAN". De ahi el /i.
  ok("los puntos del tanque salen 75.000", /75,000/.test(cat), cat.slice(0, 130));
  ok("con 75.000 puntos no falta nada", /Sobran/i.test(cat) && /Sobran\s*0/i.test(cat.replace(/\s+/g," ")),
     cat.slice(0, 130));
  // y con menos tiene que decir cuanto falta: 1000 + 2000*15 + 500*50 = 56.000
  document.getElementById("cComun").value = 1000;
  document.getElementById("btnCat").click();
  var cat2 = txt("catSalida");
  ok("con 1.000 comunes y el resto igual dice que faltan 19.000 (75.000-56.000)",
     /Faltan/i.test(cat2) && /19,000/.test(cat2), cat2.slice(0, 130));
} catch (e) {
  log("!! EXCEPCION", e.message + " @@ " + (e.stack || "").split("\n")[1]);
}

/* ---------- 6, 7 y 8: en `load`, para que la captura los pille ---------- */
window.addEventListener("load", function(){
  try {
    // ---------- 6. EXPORTAR / BORRAR / IMPORTAR CON LOS BOTONES DE VERDAD ----------
    window.alert = function(m){ ALERTAS.push(String(m)); };
    window.confirm = function(){ return true; };
    var clickAncla = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function(){ ANCLA = this; };   // no descargamos: solo miramos
    var clickInput = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function(){
      if (this.type === "file"){ ENTRADA = this; return; }             // no abrimos dialogo
      return clickInput.apply(this, arguments);
    };
    /* El handler pasa el Blob a URL.createObjectURL para fabricar el enlace de
       descarga: interceptarlo es quedarse con el fichero que se guardaria. */
    var crearURL = URL.createObjectURL;
    URL.createObjectURL = function(b){ BLOB = b; return crearURL.apply(URL, arguments); };
    /* El Blob que el handler entrega al navegador es el fichero que se guarda:
       capturar la cadena que recibe el constructor es capturar el fichero. */
    var BlobReal = window.Blob;
    window.Blob = function(partes, opciones){
      TEXTO_BLOB = partes.join("");
      return new BlobReal(partes, opciones);
    };
    /* Doble sincrono del FileReader: se dobla la API del navegador, no la logica
       de la pagina (que es la que se esta probando). */
    var TEXTO_A_IMPORTAR = "";
    window.FileReader = function(){
      var self = this;
      self.onload = null; self.onerror = null;
      self.readAsText = function(){ self.result = TEXTO_A_IMPORTAR; if (self.onload) self.onload(); };
    };

    // inventario conocido: indoraptor a nivel 24 con 4321 de ADN, y una de sus
    // ramas destildada de "creada" para que el campo tenga que sobrevivir.
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), "24");
    teclear(document.getElementById("adnTengo"), "4321");
    document.querySelector('nav button[data-t="arbol"]').click();
    var chk = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='creado']");
    if (chk){ chk.checked = false; ev(chk, "change"); }
    /* Guardar la elegida. Ademas de dejar el fichero exportado con lista, de paso se
       comprueba la regla pedida por n30: guardar mete UNA criatura, no el arbol que
       cuelga de ella — por muy tocados que esten sus ingredientes. */
    document.querySelector('nav button[data-t="calc"]').click();
    document.getElementById("btnGuardar").click();
    ok("Guardar mete en la lista SOLO la criatura elegida",
       MIS.length === 1 && MIS[0] === "indoraptor",
       MIS.length + " en la lista (" + MIS.join(", ") + ") con " + Object.keys(INV).length +
       " criaturas tocadas en el arbol");
    var antes = JSON.parse(JSON.stringify(INV));
    var listaAntes = MIS.slice();
    log("criaturas antes de exportar", Object.keys(antes).length);

    // --- exportar ---
    document.getElementById("btnExport").click();
    ok("Exportar entrega un Blob de tipo application/json",
       !!BLOB && BLOB.type === "application/json", BLOB ? BLOB.type + " / " + BLOB.size + " bytes" : "(sin blob)");
    ok("el fichero exportado se llama jwa322-mis-criaturas.json",
       !!ANCLA && ANCLA.download === "jwa322-mis-criaturas.json",
       ANCLA ? ANCLA.download : "(no se pulso)");
    /* El fichero lleva DOS cosas desde el 25-sep-2026: los datos y la lista. Antes
       solo llevaba los datos, porque la lista era «las claves de los datos». */
    var ida = JSON.parse(TEXTO_BLOB);
    ok("el JSON exportado lleva el inventario entero",
       !!ida.inventario && JSON.stringify(ida.inventario) === JSON.stringify(antes),
       Object.keys((ida && ida.inventario) || {}).length + " criaturas, " +
       (TEXTO_BLOB||"").length + " caracteres");
    ok("y lleva la lista de «Mis criaturas» aparte",
       Array.isArray(ida.mios) && JSON.stringify(ida.mios) === JSON.stringify(listaAntes),
       JSON.stringify(ida.mios));
    var conCreado = 0;
    Object.keys(ida.inventario).forEach(function(k){ if (ida.inventario[k].creado !== undefined) conCreado++; });
    ok("el campo 'creado' sale en el fichero exportado", conCreado === Object.keys(ida.inventario).length,
       conCreado + "/" + Object.keys(ida.inventario).length);

    // --- borrar ---
    document.getElementById("btnBorrar").click();
    ok("Borrar todo vacia el inventario", Object.keys(INV).length === 0, Object.keys(INV).length + "");
    ok("Borrar todo tambien limpia lo guardado en el navegador",
       !localStorage.getItem(CLAVE) || localStorage.getItem(CLAVE) === "{}",
       JSON.stringify(localStorage.getItem(CLAVE)));
    ok("y la lista de Mis criaturas queda vacia",
       /Todav\u00eda no has guardado/.test(txt("miosCuerpo")), txt("miosCuerpo").slice(0, 70));

    // --- importar ---
    TEXTO_A_IMPORTAR = TEXTO_BLOB;
    document.getElementById("btnImport").click();
    ok("Importar abre un selector de fichero .json",
       !!ENTRADA && ENTRADA.type === "file" && ENTRADA.accept === ".json",
       ENTRADA ? (ENTRADA.type + " " + ENTRADA.accept) : "(no se creo)");
    var dt = new DataTransfer();
    dt.items.add(new File([TEXTO_BLOB], "jwa322-mis-criaturas.json", {type:"application/json"}));
    ENTRADA.files = dt.files;
    ENTRADA.dispatchEvent(new Event("change"));

    ok("la importacion recupera las mismas criaturas",
       Object.keys(INV).length === Object.keys(antes).length,
       Object.keys(INV).length + " de " + Object.keys(antes).length);
    var sinCreado = 0;
    Object.keys(INV).forEach(function(k){ if (INV[k].creado === undefined) sinCreado++; });
    ok("el campo 'creado' sobrevive a la ida y vuelta", sinCreado === 0,
       (Object.keys(INV).length - sinCreado) + " con creado, " + sinCreado + " sin el");
    ok("el nivel y el ADN sobreviven",
       INV["indoraptor"] && INV["indoraptor"].nivel === 24 && INV["indoraptor"].adn === 4321,
       JSON.stringify(INV["indoraptor"]));
    ok("el aviso dice cuantas importo",
       /Importadas \d+ criaturas/.test(ALERTAS.join(" | ")), ALERTAS.join(" | "));
    ok("lo importado se ve en Mis criaturas", /Indoraptor/i.test(txt("miosCuerpo")),
       txt("miosCuerpo").slice(0, 70));

    // la tabla de Mis criaturas tiene que ensenar el mismo nivel maximo que el motor
    var filasMios = document.querySelectorAll("#miosCuerpo tbody tr");
    var filaInd = null;
    filasMios.forEach(function(tr){ if (/Indoraptor/i.test(tr.innerText)) filaInd = tr; });
    /* Por NOMBRE de columna, no por indice: ver `celdaDe`. */
    var celdaMax = filaInd ? celdaDe(filaInd, "Nivel máx. hoy") : null;
    var invInd = invDe("indoraptor");
    var espInd = nivelMaximo("unique", invInd.creado ? Math.max(invInd.nivel, 1) : 0,
                             invInd.adn, invInd.creado).nivel;
    ok("la columna 'Nivel max. hoy' de Mis criaturas coincide con el motor",
       celdaMax !== null && Number(celdaMax) === espInd,
       "pagina " + celdaMax + " vs motor " + espInd);

    // --- un fichero que no vale ---
    var antesMalo = Object.keys(INV).length;
    TEXTO_A_IMPORTAR = "[1,2,3]";
    document.getElementById("btnImport").click();
    var dt2 = new DataTransfer();
    dt2.items.add(new File(["[1,2,3]"], "basura.json", {type:"application/json"}));
    ENTRADA.files = dt2.files;
    ENTRADA.dispatchEvent(new Event("change"));
    ok("un JSON que no es un objeto se rechaza con aviso",
       /no vale/.test(ALERTAS.join(" | ")), ALERTAS.slice(-1)[0] || "(sin aviso)");
    ok("y no toca el inventario que ya habia",
       Object.keys(INV).length === antesMalo, Object.keys(INV).length + " de " + antesMalo);

    HTMLAnchorElement.prototype.click = clickAncla;
    HTMLInputElement.prototype.click = clickInput;
    window.Blob = BlobReal;
    URL.createObjectURL = crearURL;

    // ---------- 7. el nivel maximo de la raiz, contra nivelMaximo() ----------
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), "10");
    teclear(document.getElementById("adnTengo"), "100000");
    document.querySelector('nav button[data-t="arbol"]').click();
    var raiz = document.querySelector("#arbolCuerpo .nodo.raiz");
    var mm = raiz ? raiz.querySelector(".maxn") : null;
    var dicho = mm ? (mm.innerHTML.match(/llega al <b>nivel (\d+)<\/b>/) || [])[1] : null;
    var rareza = C["indoraptor"][1];
    var espMax = nivelMaximo(rareza, 10, 100000, true, M.nivelMax);
    ok("el nivel maximo que ensena la raiz es el que calcula el motor",
       dicho !== null && Number(dicho) === espMax.nivel,
       "pagina " + dicho + " vs motor " + espMax.nivel + " (" + rareza + ", 100.000 ADN)");
    ok("y avisa de que ya cumple el objetivo",
       mm && /ya cumple el objetivo 35/.test(mm.innerHTML), mm ? mm.innerText.slice(0, 80) : "(sin bloque)");

    // ---------- 8. un clic en Mis criaturas lleva a la calculadora ----------
    // Se guarda por el boton de verdad, que es el unico que apunta el objetivo.
    // El nivel tiene que estar por encima del de nacimiento: una unica nace en
    // 21, y por debajo de ahi la criatura no puede estar creada.
    var nace = minLv(C["indoraptor"][1]);
    var lvOk = nace + 3;
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(lvOk));
    teclear(document.getElementById("adnTengo"), "7777");
    document.getElementById("nivelObj").value = 28;
    ev(document.getElementById("nivelObj"), "input");
    document.getElementById("btnGuardar").click();
    var guardado = INV["indoraptor"];
    ok("el boton Guardar apunta tambien el objetivo",
       guardado && guardado.objetivo === 28 && guardado.nivel === lvOk, JSON.stringify(guardado));

    // el tropiezo que me costo un rato: un nivel por debajo del de nacimiento
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(nace - 3));
    ev(document.getElementById("nivelAct"), "change");
    var invAbajo = invDe("indoraptor");
    ok("un nivel por debajo del de nacimiento deja la criatura sin crear",
       invAbajo.creado === false && invAbajo.nivel === 0, JSON.stringify(invAbajo));
    ok("y el campo se corrige, para que se vea lo mismo que se guarda",
       document.getElementById("nivelAct").value === "0", document.getElementById("nivelAct").value);

    // se vuelve a dejar como estaba
    elegir("indoraptor");
    teclear(document.getElementById("nivelAct"), String(lvOk));
    teclear(document.getElementById("adnTengo"), "7777");
    document.getElementById("nivelObj").value = 28;
    ev(document.getElementById("nivelObj"), "input");
    document.getElementById("btnGuardar").click();

    // nos vamos a otra criatura y a otra pestaña, para que el salto tenga que deshacer algo
    elegir("rajadorixis");
    document.getElementById("nivelObj").value = 35;
    ev(document.getElementById("nivelObj"), "input");
    /* Se guarda TAMBIEN esta. La prueba de la × necesita dos criaturas en la lista, y
       antes las habia por accidente: todo lo que se tocaba acababa en «Mis criaturas».
       Ahora hay que guardarlas a proposito, que es justo la regla nueva. */
    document.getElementById("btnGuardar").click();
    irA("mios");
    ok("estamos en Mis criaturas",
       document.getElementById("s-mios").classList.contains("on") &&
       !document.getElementById("s-calc").classList.contains("on"), "s-mios visible");

    // que la pagina vuelva arriba de verdad. La ventana de la prueba (2200 px)
    // es mas alta que el documento, asi que sin relleno no habria nada que
    // desplazar y la comprobacion pasaria sin medir nada.
    var relleno = document.createElement("div");
    relleno.style.height = "1600px";
    document.body.appendChild(relleno);

    var scrollOriginal = window.scrollTo;
    window.scrollTo(0, 500);                     // punto de partida: abajo
    var yAntes = window.scrollY;
    ok("la prueba empieza con la pagina desplazada (si no, no mediria nada)",
       yAntes > 0, "scrollY de partida " + yAntes);
    var pedidos = [];
    window.scrollTo = function(){
      pedidos.push(Array.prototype.slice.call(arguments));
      return scrollOriginal.apply(window, arguments);   // y que lo haga de verdad
    };

    var fila = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir === "indoraptor") fila = tr;
    });
    ok("la fila de la criatura lleva su identificador", !!fila, fila ? fila.dataset.ir : "(no hay fila)");
    ok("el nombre y la foto son <button> de verdad (teclado y lector de pantalla)",
       fila && fila.querySelectorAll("button.ir").length === 2,
       fila ? fila.querySelectorAll("button.ir").length + " botones" : "0");

    fila.querySelector("button.ir:not(.foto-btn)").click();

    ok("el clic lleva a la pestana Calculadora",
       document.getElementById("s-calc").classList.contains("on") &&
       !document.getElementById("s-mios").classList.contains("on"), "s-calc visible");
    ok("y deja elegida esa criatura",
       elegido === "indoraptor" && /Indoraptor/.test(txt("elegida")),
       "elegido=" + elegido + " | " + txt("elegida").slice(0, 40));
    ok("con el nivel que tenia guardado (" + lvOk + ")",
       document.getElementById("nivelAct").value === String(lvOk),
       document.getElementById("nivelAct").value);
    ok("con el ADN que tenia guardado (7.777)",
       document.getElementById("adnTengo").value === "7777", document.getElementById("adnTengo").value);
    ok("y con su nivel objetivo guardado (28), no el de la criatura anterior",
       document.getElementById("nivelObj").value === "28", document.getElementById("nivelObj").value);
    ok("la pagina pide volver arriba", pedidos.length > 0 && Number(pedidos[0][1]) === 0,
       JSON.stringify(pedidos));
    ok("y de verdad queda arriba", window.scrollY === 0,
       "scrollY " + window.scrollY + " (antes " + yAntes + ")");
    window.scrollTo = scrollOriginal;
    document.body.removeChild(relleno);

    // clic en una celda del medio (no en el nombre): tambien tiene que navegar
    irA("mios");
    fila = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir === "indoraptor") fila = tr;
    });
    fila.querySelectorAll("td")[4].click();
    ok("clic en cualquier celda de la fila tambien navega",
       document.getElementById("s-calc").classList.contains("on") && elegido === "indoraptor",
       "elegido=" + elegido);

    // y la × borra SIN llevarte a la calculadora
    irA("mios");
    var antesN = Object.keys(INV).length;
    var otra = null;
    document.querySelectorAll("#miosCuerpo tbody tr").forEach(function(tr){
      if (tr.dataset.ir !== "indoraptor") otra = tr;
    });
    ok("hay una segunda criatura para probar la ×", !!otra, antesN + " guardadas");
    otra.querySelector("[data-borrar]").click();
    ok("la × borra la criatura y NO te lleva a la calculadora",
       Object.keys(INV).length === antesN - 1 && document.getElementById("s-mios").classList.contains("on"),
       "quedan " + Object.keys(INV).length + " y la pestana activa es " +
       (document.getElementById("s-mios").classList.contains("on") ? "Mis criaturas" : "otra"));

    // y una criatura borrada ya no tiene fila
    ok("la fila borrada desaparece de la lista",
       !/Rajadorixis/i.test(txt("miosCuerpo")) && /Indoraptor/i.test(txt("miosCuerpo")),
       txt("miosCuerpo").slice(0, 60));

    // ---------- 9. editar el arbol se refleja en la CALCULADORA ----------
    // Paralidactylus es un apex mega_hybrid: es raiz de su propio arbol y nace
    // en 26. Sin crear y con 0 ADN, de 0 a 35 cuesta 3.000 (300 de crearla +
    // 2.700 de escalera). Con 300 puestos en el arbol, el deficit baja a 2.700.
    elegir("paralidactylus");
    document.getElementById("nivelObj").value = 35;
    ev(document.getElementById("nivelObj"), "input");
    document.querySelector('nav button[data-t="arbol"]').click();
    var raizP = document.querySelector("#arbolCuerpo .nodo.raiz");
    ok("Paralidactylus es la raiz de su arbol", !!raizP, raizP ? "si" : "(no hay raiz)");
    var etiq = etiquetasDe("resultado");
    var iFalta = etiq.indexOf("ADN que falta");
    var cifrasAntes = cifrasDe("resultado");
    log("calculadora antes de tocar el arbol", JSON.stringify(cifrasAntes));
    ok("la calculadora ensena el ADN que falta y parte de 3.000",
       iFalta >= 0 && cifrasAntes[iFalta] === 3000, "ADN que falta = " + cifrasAntes[iFalta]);
    var campoAntes = document.getElementById("adnTengo").value;

    var adnRaiz = raizP.querySelector("input[data-campo='adn']");
    teclear(adnRaiz, "300");
    ev(adnRaiz, "change");

    ok("el ADN puesto en la raiz del arbol llega al campo de la calculadora",
       document.getElementById("adnTengo").value === "300",
       "campo de la calculadora = " + document.getElementById("adnTengo").value + " (antes " + campoAntes + ")");
    var cifrasDespues = cifrasDe("resultado");
    ok("y el resultado de la calculadora se recalcula (3.000 - 300 = 2.700)",
       cifrasDespues[iFalta] === 2700,
       "ADN que falta = " + cifrasDespues[iFalta] + " (antes " + cifrasAntes[iFalta] + ")");

    // ---------- 10. informe completo del arbol ----------
    var inf = document.getElementById("informeArbol");
    ok("la calculadora tiene el informe del arbol", !!inf, inf ? "si" : "(no existe)");
    if (inf){
      var filasInf = inf.querySelectorAll("tbody tr");
      var nodosArbol = document.querySelectorAll("#arbolCuerpo .nodo").length;
      // El informe agrupa por criatura: una fila por criatura distinta, no por
      // aparicion en el arbol. Nunca puede haber mas filas que nodos.
      var nombresInf = [];
      inf.querySelectorAll("tbody tr:not(.total)").forEach(function(tr){
        nombresInf.push(tr.querySelector("td").textContent
          .replace(/raíz|se recolecta|sin crear/g, "").trim());
      });
      var repes = nombresInf.filter(function(x, i){ return nombresInf.indexOf(x) !== i; });
      ok("el informe lista una fila por criatura, sin repetir ninguna",
         repes.length === 0, nombresInf.length + " filas" + (repes.length ? " | repetidas: " + repes.join(", ") : ""));
      ok("y no lista mas criaturas que nodos tiene el arbol",
         nombresInf.length <= nodosArbol, nombresInf.length + " filas para " + nodosArbol + " nodos");
      ok("el informe nombra la raiz y sus ingredientes",
         /Paralidactylus/.test(txc("informeArbol")) && /Paralitrosaurus/.test(txc("informeArbol")) &&
         /Skorpiodactylus/.test(txc("informeArbol")),
         txc("informeArbol").slice(0, 90));
      log("cifras del informe", JSON.stringify(cifrasDe("informeArbol")) + " | " +
          JSON.stringify(etiquetasDe("informeArbol")));
      ok("el informe va arriba del bloque de nivel maximo",
         !!(document.getElementById("informeArbol").compareDocumentPosition(
              document.getElementById("maxNivel")) & Node.DOCUMENT_POSITION_FOLLOWING),
         "informe antes de maxNivel");
      var tb = inf.querySelector("table");
      ok("la tabla del informe cabe a lo ancho, sin scroll horizontal",
         tb.scrollWidth <= tb.clientWidth + 2,
         "scrollWidth " + tb.scrollWidth + " vs clientWidth " + tb.clientWidth);
      // la suma de la columna "Falta" tiene que ser la cifra total del informe.
      // Columnas: Criatura | Nivel | Necesario | Tienes | Falta | Fusiones
      // (la de «Rareza» se quito el 25-sep, y la de «Veces» tambien).
      /* La fila Total ya NO tiene una celda que ocupe 2: al meterle el boton
         «Criar a todas» en la columna «Nivel», la primera celda baja a
         colspan=1 y la fila pasa a tener 6 celdas, las mismas que la cabecera.
         Antes se leia `celdasTotal[3]` dando por hecho el colspan; ese indice
         ahora devuelve OTRA columna (Tienes en vez de Falta). Es la trampa 16
         —leer una celda por su posicion— mordiendo en el cambio siguiente a
         documentarla. Se lee por el NOMBRE de la columna. */
      var iF = indiceEtiqueta("informeArbol", /^ADN que falta/i);
      var sumaFalta = 0;
      inf.querySelectorAll("tbody tr:not(.total)").forEach(function(tr){
        sumaFalta += Number(celdaDe(tr, "Falta").replace(/[^\d]/g, "")) || 0;
      });
      var celdasTotal = inf.querySelector("tr.total").querySelectorAll("td");
      var totalFila = Number(celdaDe(inf.querySelector("tr.total"), "Falta").replace(/[^\d]/g, "")) || 0;
      ok("la fila Total cuadra con la suma de las filas y con la cifra de arriba",
         celdasTotal.length === 6 && iF >= 0 && totalFila === sumaFalta &&
         totalFila === cifrasDe("informeArbol")[iF],
         celdasTotal.length + " celdas | suma " + sumaFalta + " = total " + totalFila +
         " = cifra " + cifrasDe("informeArbol")[iF]);
    }

    // ---------- 11. ingrediente compartido: el ADN se descuenta UNA vez ----------
    // Indoraptor lleva Velociraptor, y su ingrediente Indominus Rex tambien: la
    // misma reserva de ADN sale en dos ramas. Restando el deficit de cada
    // aparicion se descontaba el mismo ADN dos veces y el total salia corto.
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
    ok("el arbol detecta el ingrediente compartido", vel && vel.veces === 2,
       vel ? "sale " + vel.veces + " veces" : "(no aparece)");
    var apar = [];
    (function rec(x){ if (x.uuid === "velociraptor") apar.push(x); x.hijos.forEach(rec); })(tI);
    var necSuma = apar.reduce(function(a, x){ return a + x.adnNec; }, 0);
    var naive = 0;
    (function rec(x){ naive += x.deficit; x.hijos.forEach(rec); })(tI);
    log("Velociraptor: nec por rama " + apar.map(function(x){ return x.adnNec; }).join(" + ") +
        " = " + necSuma + " | tiene 30.000 | apariciones " + apar.length);
    ok("su ADN necesario es la SUMA de las dos ramas", vel.nec === necSuma,
       vel.nec + " vs " + necSuma);
    ok("y lo que tienes se descuenta UNA vez, no una por rama",
       vel.falta === Math.max(0, necSuma - 30000), vel.falta + " (suma de deficits " +
       apar.reduce(function(a, x){ return a + x.deficit; }, 0) + ")");
    ok("el total del arbol corrige justo una reserva contada de mas",
       ttI.adn === naive + 30000,
       "total " + nf(ttI.adn) + " vs suma por apariciones " + nf(naive) + " (diferencia " +
       nf(ttI.adn - naive) + ", la reserva son 30.000)");
    /* La columna «Veces» se retiro el 25-sep-2026. Lo que hay que comprobar
       ahora es lo contrario de antes: que NO este, ni en la cabecera ni en el
       texto —la nota la citaba por su nombre—, y que la fila del Velociraptor
       siga llevando el total corregido. El contador `veces` sigue vivo detras
       (alimenta `repetidas`), pero eso lo comprueba la asercion de arriba. */
    ok("el informe sigue avisando del ingrediente compartido",
       /Velociraptor/.test(txc("informeArbol")) &&
       /varias ramas del árbol/.test(txc("informeArbol")), "informe con la nota de compartidas");
    ok("y la columna «Veces» ya no esta: ni en la cabecera ni citada en la nota",
       inf.querySelectorAll("thead th").length === 6 && !/Veces/.test(txc("informeArbol")),
       Array.prototype.map.call(inf.querySelectorAll("thead th"), function(th){
         return th.textContent.trim(); }).join(" | "));
    var filaVel = null;
    inf.querySelectorAll("tbody tr").forEach(function(tr){
      if (/Velociraptor/.test(tr.innerText)) filaVel = tr;
    });
    ok("la fila del Velociraptor tiene 6 celdas y el total corregido",
       filaVel && filaVel.querySelectorAll("td").length === 6 &&
       Number(celdaDe(filaVel, "Falta").replace(/[^\d]/g, "")) === vel.falta,
       filaVel ? filaVel.querySelectorAll("td").length + " celdas, falta " +
                 celdaDe(filaVel, "Falta") : "(sin fila)");
  } catch (e) {
    log("!! EXCEPCION en la parte de los botones", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 12. el interruptor «subir los ingredientes» ----------
  /* Esta seccion NO es un espejo del codigo: es el enunciado de lo que espera
     quien usa la pagina.

     El informe sumaba la escalera de TODAS las criaturas pasara lo que pasara,
     asi que daba exactamente la misma cifra con la casilla marcada y
     desmarcada, mientras la pestana del arbol si cambiaba. Dos vistas de la
     misma pantalla contradiciendose. La prueba del espejo Python no lo veia
     porque el espejo cometia el mismo error: cuando la prueba y el codigo se
     escriben desde la misma lectura, un malentendido comun pasa en verde. */
  try {
    var chkSub = document.getElementById("chkSubida");
    ok("existe la casilla de contar la subida", !!chkSub);

    /* Filas del informe por nombre, MAS la fila Total, todo capturado en el
       mismo instante. Leer las filas como datos y la fila Total del DOM mas
       tarde no vale: entre medias se vuelve a encender la casilla, el informe se
       repinta, y el Total que se lee ya es el de la casilla marcada. Media foto
       del estado A y media del estado B.
       El nombre es el primer nodo de texto de la primera celda; las pildoras
       («raíz», «se recolecta») van detras. */
    function filasInforme(){
      var m = {}, raiz = null;
      document.querySelectorAll("#informeArbol tbody tr:not(.total)").forEach(function(tr){
        var c = tr.querySelectorAll("td");
        var nom = (c[0].childNodes[0] && c[0].childNodes[0].textContent || "").trim();
        if (!nom) return;
        /* Por NOMBRE de columna, no por indice: ver la nota de arriba y la
           trampa 16. La celda «Nivel» puede llevar dentro el boton «criar», y
           `textContent` lo incluye, que es justo lo que hace falta leer. */
        m[nom] = {nec: Number(celdaDe(tr, "ADN necesario").replace(/[^\d]/g, "")) || 0,
                  nivel: celdaDe(tr, "Nivel"),
                  falta: Number(celdaDe(tr, "Falta").replace(/[^\d]/g, "")) || 0};
        if (tr.classList.contains("raiz-fila")) raiz = nom;
      });
      /* Columnas: Criatura | Nivel | Necesario | Tienes | Falta | Fusiones
         (la de «Rareza» y la de «Veces» se quitaron el 25-sep).
         La fila Total YA NO lleva colspan: al ganar el boton «Criar a todas» en
         la columna «Nivel», sus 6 celdas coinciden con las 6 columnas, asi que
         `celdaDe` la lee igual que a cualquier otra fila. */
      var trTot = document.querySelector("#informeArbol tbody tr.total");
      var cT = trTot ? trTot.querySelectorAll("td") : [];
      return {porNombre: m, raiz: raiz,
              nCeldasTotal: cT.length,
              totalNec: cT.length ? Number(celdaDe(trTot, "ADN necesario").replace(/[^\d]/g, "")) || 0 : -1,
              totalFalta: cT.length ? Number(celdaDe(trTot, "Falta").replace(/[^\d]/g, "")) || 0 : -1};
    }

    chkSub.checked = true; ev(chkSub, "change");          // partir del estado marcado
    var cifON = cifrasDe("informeArbol");
    var iTot = indiceEtiqueta("informeArbol", /^ADN que falta/i);
    var iRec = indiceEtiqueta("informeArbol", /^A recolectar$/i);
    var iMon = indiceEtiqueta("informeArbol", /^Monedas$/i);
    ok("el informe tiene sus cuatro cifras rotuladas", iTot >= 0 && iRec >= 0 && iMon >= 0,
       JSON.stringify(etiquetasDe("informeArbol")));
    var ON = filasInforme();
    ok("el informe marca cual es la raiz", !!ON.raiz, ON.raiz || "(ninguna fila con raiz-fila)");

    chkSub.checked = false; ev(chkSub, "change");
    var cifOFF = cifrasDe("informeArbol");
    var OFF = filasInforme();

    ok("apagar la casilla cambia el informe", cifON[iTot] !== cifOFF[iTot],
       "ADN que falta en total: " + cifON[iTot] + " con la casilla, " + cifOFF[iTot] + " sin ella");
    ok("y cambia a menos: sin subir ingredientes hace falta menos ADN",
       cifOFF[iTot] < cifON[iTot], cifOFF[iTot] + " < " + cifON[iTot]);
    ok("lo que hay que recolectar tambien baja", cifOFF[iRec] < cifON[iRec],
       cifON[iRec] + " -> " + cifOFF[iRec]);
    ok("las monedas tambien bajan", cifOFF[iMon] < cifON[iMon],
       cifON[iMon] + " -> " + cifOFF[iMon]);

    /* La raiz SIEMPRE paga su escalera: es el objetivo del calculo, no un
       ingrediente. Apagar la casilla no puede abaratarla. */
    ok("la raiz conserva su ADN necesario con la casilla apagada",
       ON.raiz && OFF.porNombre[ON.raiz] && ON.porNombre[ON.raiz].nec === OFF.porNombre[ON.raiz].nec,
       ON.raiz ? ON.raiz + ": " + ON.porNombre[ON.raiz].nec + " vs " +
                 (OFF.porNombre[ON.raiz] ? OFF.porNombre[ON.raiz].nec : "(no sale)") : "(sin raiz)");

    /* A un ingrediente solo se le puede QUITAR la escalera, nunca sumarle. */
    var comunes = Object.keys(ON.porNombre).filter(function(k){ return OFF.porNombre[k]; });
    var suben = comunes.filter(function(k){ return OFF.porNombre[k].nec > ON.porNombre[k].nec; });
    ok("ningun ingrediente sube de ADN al apagar la casilla", suben.length === 0,
       suben.length + " suben" + (suben.length ? ": " + suben.slice(0,3).join(", ") : ""));

    var bajan = comunes.filter(function(k){
      return k !== ON.raiz && OFF.porNombre[k].nec < ON.porNombre[k].nec;
    });
    ok("y al menos un ingrediente baja, que es lo que se le quita", bajan.length > 0,
       bajan.length + " de " + comunes.length + " bajan, p.ej. " + (bajan[0] || "—"));

    /* Sin subida no hay rango de niveles que ensenar para un INGREDIENTE:
       «16 → 20» haria creer que se esta pagando esa subida. La raiz es la
       excepcion: siempre paga su escalera, asi que siempre ensena su rango.

       OJO con buscar «→» a secas: desde el 25-sep la flecha se usa para DOS
       cosas —el rango de niveles («16 → 20») y el boton de criar («criar → 20»,
       que es una accion, no un rango)—. Por eso `esRangoNivel` busca la firma
       completa. Es mas preciso que antes, no mas laxo: `/→/` daba por rango
       cualquier cosa con la flecha. */
    var rangos = comunes.filter(function(k){
      return k !== ON.raiz && esRangoNivel(OFF.porNombre[k].nivel);
    });
    ok("sin subir ingredientes no se ensena ningun rango de niveles", rangos.length === 0,
       rangos.length + " filas con rango" + (rangos.length ? ": " + rangos.slice(0,3).join(", ") : ""));
    ok("y la raiz conserva su rango, porque su escalera si se paga",
       !ON.raiz || esRangoNivel(OFF.porNombre[ON.raiz].nivel),
       ON.raiz ? ON.raiz + ": " + OFF.porNombre[ON.raiz].nivel : "(sin raiz)");
    var rangosON = comunes.filter(function(k){ return esRangoNivel(ON.porNombre[k].nivel); });
    ok("con la casilla marcada si se ensenan rangos donde los hay", rangosON.length > 0,
       rangosON.length + " filas con rango");

    /* Con la casilla apagada, la misma pantalla tiene que decir con que criterio
       calcula. Si no, da dos respuestas distintas segun una casilla que esta en
       otra pestana, y ninguna de las dos se identifica. */
    ok("el informe avisa de que sigue el criterio de paleo.gg",
       /paleo\.gg/.test(txc("informeArbol")));
    chkSub.checked = true; ev(chkSub, "change");
    ok("y el aviso desaparece al volver a marcarla",
       !/criterio de paleo\.gg/.test(txc("informeArbol")));

    /* El total tiene que cuadrar con la suma de las filas en LOS DOS estados:
       si la agregacion y las filas salieran de cuentas distintas, uno de los dos
       estaria mintiendo. */
    [["con la casilla", cifON, ON], ["sin la casilla", cifOFF, OFF]].forEach(function(p){
      var sumaNec = 0, sumaFalta = 0;
      Object.keys(p[2].porNombre).forEach(function(k){
        sumaNec += p[2].porNombre[k].nec;
        sumaFalta += p[2].porNombre[k].falta;
      });
      ok("la columna «ADN necesario» del Total cuadra con las filas " + p[0],
         p[2].nCeldasTotal === 6 && p[2].totalNec === sumaNec,
         p[2].nCeldasTotal + " celdas | total " + p[2].totalNec + " vs suma de filas " + sumaNec);
      ok("y la columna «Falta» del Total tambien " + p[0],
         p[2].totalFalta === sumaFalta,
         "total " + p[2].totalFalta + " vs suma de filas " + sumaFalta);
    });
  } catch (e) {
    log("!! EXCEPCION en la parte del interruptor", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 13. EL NIVEL OBJETIVO ES DE CADA CRIATURA ----------
  /* El objetivo vivia en un solo sitio: el deslizador. Habia UNA sola escritura
     de `objetivo` en INV (la del boton «Guardar»), asi que no existia hasta
     guardar; y `elegir` conservaba el valor del deslizador en vez de restaurar el
     de la criatura, de modo que poner 30 en el Indoraptor y pasar a otro dino le
     dejaba el 30 al nuevo sin que nadie lo hubiera pedido. Pedido de n30 el
     25-sep-2026: «guarda un nivel objetivo distinto para cada dino, eso debe
     reflejarse en la calculadora y en mis criaturas». */
  try {
    localStorage.removeItem("jwa322.inventario");
    localStorage.removeItem("jwa322.mios");
    INV = {}; MIS = []; guardar();

    function objetivo(){ return Number(document.getElementById("nivelObj").value); }
    function objGuardado(u){ return INV[u] ? INV[u].objetivo : undefined; }
    function celdaObjetivo(u){
      var tr = document.querySelector('#miosCuerpo tr[data-ir="' + u + '"]');
      return tr ? celdaDe(tr, "Objetivo") : "(sin fila)";
    }

    elegir("indoraptor");
    ok("una criatura sin objetivo guardado arranca en el tope", objetivo() === 35,
       "deslizador = " + objetivo());
    teclear(document.getElementById("nivelObj"), "30");
    ok("mover el deslizador guarda el objetivo de esa criatura", objGuardado("indoraptor") === 30,
       "guardado = " + objGuardado("indoraptor"));

    elegir("tyrannosaurus_rex");
    ok("al cambiar de criatura NO se hereda el objetivo de la anterior", objetivo() === 35,
       "el t-rex aparece en " + objetivo() + " y el indoraptor tenia 30");
    teclear(document.getElementById("nivelObj"), "25");

    elegir("indoraptor");
    ok("al volver, cada criatura recupera el suyo", objetivo() === 30, "indoraptor = " + objetivo());
    elegir("tyrannosaurus_rex");
    ok("y la otra el suyo", objetivo() === 25, "t-rex = " + objetivo());

    elegir("indoraptor"); document.getElementById("btnGuardar").click();
    elegir("tyrannosaurus_rex"); document.getElementById("btnGuardar").click();
    ok("«Mis criaturas» enseña el objetivo de cada fila",
       celdaObjetivo("indoraptor") === "30" && celdaObjetivo("tyrannosaurus_rex") === "25",
       "indoraptor " + celdaObjetivo("indoraptor") + " / t-rex " + celdaObjetivo("tyrannosaurus_rex"));

    /* El arbol saca el objetivo de la raiz DEL DESLIZADOR, asi que tiene que
       enterarse al moverlo. Antes el manejador llamaba solo a `calcular`, y la
       raiz se quedaba con el objetivo anterior: la misma pantalla daba dos
       respuestas. */
    elegir("indoraptor");
    irA("arbol"); pintarArbol();
    var raiz30 = document.querySelector(".arbol .nodo.raiz").textContent.replace(/\s+/g, " ");
    ok("la raiz del arbol cita el objetivo de su criatura", /→ 30/.test(raiz30), raiz30.slice(0, 78));
    irA("calc"); teclear(document.getElementById("nivelObj"), "33");
    irA("arbol"); pintarArbol();
    var raiz33 = document.querySelector(".arbol .nodo.raiz").textContent.replace(/\s+/g, " ");
    ok("y se entera al mover el deslizador, sin quedarse con el 30",
       /→ 33/.test(raiz33) && !/→ 30/.test(raiz33), raiz33.slice(0, 78));

    /* `fijar` REEMPLAZA el objeto de INV entero: si no arrastrase el objetivo,
       teclear el ADN de un ingrediente le borraria su objetivo a la raiz. */
    irA("arbol"); pintarArbol();
    var ing = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
    var uIng = ing.dataset.u;
    teclear(ing, "999");
    ok("teclear en el arbol no borra el objetivo de la raiz", objGuardado("indoraptor") === 33,
       "ahora es " + objGuardado("indoraptor"));
    ok("y el ingrediente no se queda con un objetivo que nadie le dio",
       objGuardado(uIng) === undefined, "objetivo del ingrediente = " + objGuardado(uIng));

    var crudo = JSON.parse(localStorage.getItem("jwa322.inventario") || "{}");
    ok("el objetivo se persiste, criatura por criatura",
       crudo.indoraptor && crudo.indoraptor.objetivo === 33 &&
       crudo.tyrannosaurus_rex && crudo.tyrannosaurus_rex.objetivo === 25,
       "indoraptor " + (crudo.indoraptor && crudo.indoraptor.objetivo) +
       " / t-rex " + (crudo.tyrannosaurus_rex && crudo.tyrannosaurus_rex.objetivo));

    /* La × olvida los datos de esa criatura, objetivo incluido: si estaba
       abierta, el deslizador no puede seguir enseñando el de una criatura que ya
       no tiene datos. */
    elegir("tyrannosaurus_rex");
    irA("mios");
    var x = document.querySelector('#miosCuerpo [data-borrar="tyrannosaurus_rex"]');
    ok("hay × para el t-rex en la lista", !!x);
    if (x) x.click();
    ok("tras la ×, la criatura abierta vuelve al tope", objetivo() === 35,
       "deslizador = " + objetivo());
    irA("calc");
  } catch (e) {
    log("!! EXCEPCION en el objetivo por criatura", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- 14. criar desde el informe ----------
  /* Peticion de n30 (25-sep-2026): «cuando no esté creado un dino, despues de su
     nombre NO aparezca la leyenda "sin crear", pero en la columna "nivel" si
     aparezca, pero en lugar de "sin crear" dirá "criar" y al hacer click en la
     palabra pongas el nivel mínimo del dino, en la intersección con la fila
     donde dice "total del arbol" y "nivel" si hay al menos una criatura no
     criada habrá un texto que diga "Criar a todas"».

     Lo que hay que sujetar aqui, y por que cada cosa:
       - el estado «sin crear» sigue siendo VISIBLE, solo que en la columna del
         nivel y como accion. Si desapareciera de los dos sitios, el informe
         dejaria de decir que esa criatura no existe;
       - pulsar «criar» NO es una simulacion: tiene que cambiar el inventario de
         verdad, por la misma via que la casilla del arbol, porque el nivel se
         guarda y sale luego en la pestana del arbol y en «Mis criaturas»;
       - «Criar a todas» pone al NIVEL DE LA FUSION —no al de nacimiento, que era
         lo primero que se pidio y n30 corrigio el 25-sep: «debe poner al nivel
         minimo usable para el dinosaurio de la calculadora»—, y toca SOLO las
         que no estan creadas o las que estan POR DEBAJO de ese nivel. La RAIZ
         queda fuera: «la criatura raiz no se modifica, solamente su arbol». */
  try {
    localStorage.removeItem("jwa322.inventario");
    localStorage.removeItem("jwa322.mios");
    INV = {}; MIS = []; guardar();
    /* El escenario tiene que cubrir los CUATRO casos a la vez, porque de eso
       depende que el atajo se juzgue de verdad:
         - indoraptor      la RAIZ, creada a 25 (nace a 21, su objetivo es 30).
                           No se puede tocar, aunque no este en su objetivo.
         - indominus_rex   creada POR ENCIMA del nivel que exige la fusion (30,
                           cuando solo se le piden 20). Es el control mas
                           importante: una implementacion que «pusiera a todas en
                           el nivel de la fusion» la BAJARIA a 20, o sea que le
                           borraria al usuario 10 niveles que ya tiene. Y una que
                           «reiniciara» las creadas la bajaria a su nacimiento
                           (16). Los dos casos se ven aqui, porque 30 no es ni 20
                           ni 16.
         - tyrannosaurus_rex  creada POR DEBAJO de lo que exige la fusion: nace a
                           11 y la fusion de Indominus Rex (legendaria) la pide a
                           15. Tiene que SUBIR a 15.
         - velociraptor    SIN crear. Tiene que quedar en 20, que es lo que pide
                           la fusion de Indoraptor (unica) — no en 1, que es
                           donde nace.
       Se monta dos veces (el boton individual y el atajo cambian el inventario),
       por eso es una funcion y no una tanda de lineas sueltas. */
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
    ok("el informe tiene las filas de esta prueba",
       !!filaTRex && !!filaInd && !!filaVel && !!filaIndom,
       [["t-rex",filaTRex],["indoraptor",filaInd],["velociraptor",filaVel],["indominus",filaIndom]]
         .map(function(p){ return p[1] ? p[0]+" ok" : "SIN "+p[0]; }).join(" / "));

    /* 1) La pildora «sin crear» ya no va detras del nombre, en NINGUNA fila. */
    var conPildora = [];
    document.querySelectorAll("#informeArbol tbody tr:not(.total)").forEach(function(tr){
      if (/sin crear/.test(tr.querySelector("td").textContent)) conPildora.push(tr.querySelector("td").textContent.trim().slice(0, 30));
    });
    ok("ninguna fila del informe lleva «sin crear» detras del nombre",
       conPildora.length === 0, conPildora.join(" | ") || "ninguna");

    /* 2) Pero el estado NO se ha perdido: esta en la columna «Nivel», y ademas
          es la accion. La pildora de la pestana del arbol sigue donde estaba:
          el cambio es del INFORME, no de la pestana.
          El boton se busca en VELOCIRAPTOR, que es la unica criatura SIN CREAR
          del escenario. T-Rex tambien esta por debajo de lo que se le pide,
          pero esta CREADA, asi que no lleva boton: el atajo la alcanza igual,
          y eso se comprueba mas abajo. */
    ok("la pestaña del arbol conserva su pildora «sin crear»",
       /sin crear/.test(txt("arbolCuerpo")), "pestana del arbol");
    var btnCriar = filaVel ? filaVel.querySelector('[data-criar="velociraptor"]') : null;
    ok("una criatura sin crear lleva el boton «criar» en la columna Nivel",
       !!btnCriar && btnCriar.textContent.trim() === "criar" &&
       celdaDe(filaVel, "Nivel").indexOf("criar") === 0,
       btnCriar ? "boton «" + btnCriar.textContent.trim() + "», celda «" +
                  celdaDe(filaVel, "Nivel") + "»" : "(sin boton)");
    ok("y una ya creada NO lo lleva",
       filaInd && !filaInd.querySelector("[data-criar]") &&
       esRangoNivel(celdaDe(filaInd, "Nivel")),
       filaInd ? "celda «" + celdaDe(filaInd, "Nivel") + "»" : "(sin fila)");

    /* 3) La fila Total ofrece el atajo. OJO: el conjunto que el atajo va a tocar
          YA NO son los botones. T-Rex esta creada (a 11) y por eso no lleva
          boton, pero el atajo SI tiene que alcanzarla, porque esta por debajo
          del nivel que exige la fusion. Se mira la lista que el informe publica
          para el atajo, que sale de la misma `cri` que pinta las filas. */
    var trTot = document.querySelector("#informeArbol tbody tr.total");
    var btnTodas = trTot ? trTot.querySelector("[data-criar-todas]") : null;
    ok("la fila Total ofrece «Criar a todas» en la columna Nivel",
       !!btnTodas && btnTodas.textContent.trim() === "Criar a todas" &&
       celdaDe(trTot, "Nivel").indexOf("Criar a todas") === 0,
       (btnTodas ? "«" + btnTodas.textContent.trim() + "»" : "(sin boton)") +
       " | celda «" + celdaDe(trTot, "Nivel") + "»");

    var dichoPorCriar = {};
    POR_CRIAR.forEach(function(x){ dichoPorCriar[x.uuid] = x.nivel; });
    ok("el atajo se lleva las dos que no sirven, y NI la raiz NI la que ya esta en su nivel",
       Object.keys(dichoPorCriar).sort().join(",") === "tyrannosaurus_rex,velociraptor" &&
       dichoPorCriar.tyrannosaurus_rex === 15 && dichoPorCriar.velociraptor === 20,
       JSON.stringify(dichoPorCriar));

    /* 4) Pulsar «criar» deja la criatura EN EL NIVEL QUE EXIGE LA FUSION. Antes
          la dejaba en su nivel de nacimiento —Velociraptor es comun, o sea 1— y
          el numero de la flecha no era el que quedaba puesto: habia que subirla
          despues. n30 lo corrigio el 25-sep. */
    if (btnCriar) btnCriar.click();
    var invVel = invDe("velociraptor");
    ok("pulsar «criar» la deja en el nivel de la fusion (20), no en el de nacimiento (1)",
       invVel.creado === true && invVel.nivel === 20 && minLv(C["velociraptor"][1]) === 1,
       "creado=" + invVel.creado + " nivel=" + invVel.nivel +
       " (nace a " + minLv(C["velociraptor"][1]) + ")");
    var filaVel2 = filaInforme("Velociraptor");
    ok("y su fila deja de ofrecer criar",
       filaVel2 && !filaVel2.querySelector("[data-criar]"),
       filaVel2 ? "celda «" + celdaDe(filaVel2, "Nivel") + "»" : "(sin fila)");

    /* 5) «Criar a todas», con los CUATRO casos a la vez. Se vuelve a montar el
          escenario porque el paso 4 ya cambio el inventario. */
    montarEscenario();
    var antes = {};
    ["indoraptor","indominus_rex","tyrannosaurus_rex","velociraptor"].forEach(function(u){
      var v = invDe(u); antes[u] = {creado:v.creado, nivel:v.nivel};
    });
    log("antes de «Criar a todas»", JSON.stringify(antes));

    /* Que el escenario SIRVA para juzgar, comprobado ANTES de pulsar. Si alguno
       de estos numeros coincidiera con lo que produce una implementacion
       equivocada, la comprobacion de despues pasaria sin probar nada:
         - la raiz esta en 25; nace a 21 y su objetivo es 30, asi que ni
           «reiniciar al minimo» ni «empujar al objetivo» pasarian inadvertidos;
         - Indominus Rex esta en 30 y nace a 16: ni bajarla al nivel exigido (20)
           ni reiniciarla a su nacimiento pasarian inadvertidos; */
    ok("el escenario distingue los cuatro casos (raiz / por encima / por debajo / sin crear)",
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
    log("despues de «Criar a todas»", JSON.stringify(ahora));

    ok("«Criar a todas» NO toca la RAIZ, aunque este por debajo de su objetivo",
       ahora.indoraptor.creado === true && ahora.indoraptor.nivel === 25,
       "indoraptor: " + antes.indoraptor.nivel + " → " + ahora.indoraptor.nivel);

    ok("y NO BAJA una creada que ya estaba por encima del nivel exigido (30, se le piden 20)",
       ahora.indominus_rex.creado === true && ahora.indominus_rex.nivel === 30,
       "indominus_rex: " + antes.indominus_rex.nivel + " → " + ahora.indominus_rex.nivel);

    ok("pero SI sube una creada que estaba por debajo del nivel exigido (11 → 15)",
       ahora.tyrannosaurus_rex.creado === true && ahora.tyrannosaurus_rex.nivel === 15,
       "tyrannosaurus_rex: " + antes.tyrannosaurus_rex.nivel + " → " + ahora.tyrannosaurus_rex.nivel);

    ok("y la que no estaba creada queda creada en el nivel exigido (20)",
       ahora.velociraptor.creado === true && ahora.velociraptor.nivel === 20,
       "velociraptor: " + antes.velociraptor.nivel + " → " + ahora.velociraptor.nivel);

    /* 6) Y el atajo desaparece solo: cuando ya no queda ninguna por debajo, no
          hay nada que hacer. Si el boton siguiera ahi, el informe estaria
          ofreciendo una accion que no hace nada. */
    ok("el atajo desaparece cuando ya no queda ninguna por crear ni por debajo",
       !document.querySelector("#informeArbol [data-criar-todas]") && POR_CRIAR.length === 0,
       POR_CRIAR.length + " en la lista del atajo, " +
       document.querySelectorAll("#informeArbol [data-criar-todas]").length + " botones");
    ok("y ninguna fila del informe dice ya «sin crear»",
       !/sin crear/.test(txc("informeArbol")), "informe completo");

    /* 7) Los niveles se guardaron de verdad, no solo se pintaron: es el mismo
          dato que usan la pestana del arbol y «Mis criaturas». */
    var crudo2 = JSON.parse(localStorage.getItem("jwa322.inventario") || "{}");
    ok("lo cambiado queda guardado en el inventario",
       crudo2.tyrannosaurus_rex && crudo2.tyrannosaurus_rex.creado === true &&
       crudo2.tyrannosaurus_rex.nivel === 15 &&
       crudo2.indoraptor && crudo2.indoraptor.nivel === 25,
       "t-rex " + JSON.stringify(crudo2.tyrannosaurus_rex) +
       " | indoraptor " + JSON.stringify(crudo2.indoraptor));
  } catch (e) {
    log("!! EXCEPCION en crear desde el informe", e.message + " @@ " + (e.stack || "").split("\n")[1]);
  }

  // ---------- imagenes ----------
  var bien = 0, mal = [];
  CLONES.forEach(function(c){ if (c.el.complete && c.el.naturalWidth > 0) bien++; else mal.push(c.src); });
  if (CLONES.length)
    ok("todas las imagenes referenciadas cargan", mal.length === 0,
       bien + "/" + CLONES.length + " ok" + (mal.length ? " fallan: " + mal.slice(0,3).join(", ") : ""));

  log("", "");
  log(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===", "");
  var d = document.createElement("pre");
  d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:15px/1.5 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\n");
  document.body.appendChild(d);
__ENTREGA__
});

/* Las imagenes se comprueban con clones que SI cargan: `loading="lazy"` no carga
   nada que este en un contenedor oculto, asi que mirar los <img> de la pestana
   del arbol daria 0x0 y seria un artefacto de la prueba, no un fallo de la pagina. */
(function(){
  var srcs = [];
  document.querySelectorAll("img").forEach(function(im){
    var s = im.getAttribute("src");
    if (s && srcs.indexOf(s) < 0) srcs.push(s);
  });
  log("imagenes distintas referenciadas", srcs.length);
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
    raise SystemExit("no encuentro <head> para fijar el idioma")
html = html.replace("<head>", "<head>\n" + PIN, 1)
m = re.search(r"<body[^>]*>", html)
html = html[:m.end()] + CAZA + html[m.end():] + DIAG.replace("__ENTREGA__", srv.js("__diag"))
# Antes de abrir el navegador: si el diagnostico no compila junto a la aplicacion
# —colision de nombres en el ambito global—, la prueba se quedaria sin correr y
# el sintoma seria «no entrego el informe», que no dice nada. Ver informe_browser.
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
print("informe:", TXT)
print("-" * 72)
print(informe)
print("-" * 72)

codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)
raise SystemExit(codigo)
