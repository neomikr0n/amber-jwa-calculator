#!/usr/bin/env python3
"""
Prueba de INTERFAZ en navegador real (Firefox headless).

Los verificadores numericos (verificar_motor.py / verificar_arbol.py) cubren las
matematicas. Esto cubre lo otro: que los campos existan, que respondan al teclado,
que se guarde, y que las imagenes carguen de verdad (naturalWidth > 0, que es la
unica forma de distinguir "hay un <img>" de "se ve el dinosaurio").

Escribe el informe en un <pre> y lo entrega por un servidor local (ver
informe_browser.py), ademas de dejarlo en la captura. El script imprime el
informe y devuelve codigo de salida 0 solo si todo pasa: leer el PNG a ojo no
es una prueba.

Uso:  python3 probar_ui.py
"""
import os, re, shutil, subprocess
from informe_browser import arrancar, comprobar_scripts, veredicto

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.22.html")
IMG = os.path.join(RAIZ, "img")
DIR = "/tmp/jwa-ui"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "ui.html")
SHOT = os.path.join(DIR, "ui.png")

# El informe viaja por aqui, no por una captura que hay que leer a ojo.
srv = arrancar()

DIAG = r"""
<script>
/* Dos trampas de probar una pagina desde dentro, y como se esquivan:

   1. `loading="lazy"` retrasa las imagenes hasta que entran en pantalla, asi
      que comprobar naturalWidth justo despues de pintarlas da 0 SIEMPRE, y en
      un contenedor oculto ni siquiera llegan a pedirse. Solucion: se clonan
      como <img> ansiosos y ocultos, que si bloquean el evento load. Cuando
      load dispara, ya estan resueltas.

   2. Un evento lanzado con dispatchEvent NO enfoca el elemento, asi que
      document.activeElement sigue siendo <body> y la prueba de "no se pierde
      el foco" falla sin que la pagina tenga nada roto. Solucion: .focus()
      antes de disparar, como haria una persona al hacer clic. */

// --- 1) las interacciones, durante el parseo ---
var RES = [], FALLOS = 0, CLONES = [], FOCO_U = null;
function log(k, v){ RES.push(k + ": " + (v === undefined ? "" : v)); }
function ok(k, cond, detalle){ if (!cond) FALLOS++; log((cond ? "OK   " : "FALLO") + " " + k, detalle); }
function txt(id){ var e = document.getElementById(id); return e ? e.innerText.replace(/\s+/g," ").trim() : "(falta "+id+")"; }
function ev(el, tipo){ el.dispatchEvent(new Event(tipo, {bubbles:true})); }
/* Escribe el valor de golpe. Vale para preparar un escenario, pero NO prueba el
   tecleo: el campo nunca pasa por un estado intermedio. */
function teclear(el, valor){
  el.focus();                 // como un clic de verdad
  el.value = valor;
  ev(el, "input");
}
/* Teclea DIGITO A DIGITO con `execCommand("insertText")`, que es lo unico que
   inserta EN EL CURSOR y dispara `input` como una tecla de verdad. Hace falta
   porque el fallo que se viene a vigilar solo aparece asi: el arbol se repinta en
   cada tecla, y si el cursor no se puede devolver (un <input type=number> no deja
   ni leerlo ni fijarlo en Firefox), el digito siguiente entra por el PRINCIPIO.
   Con `teclear` —que escribe "1500" de una vez— ese fallo es invisible: por eso
   estuvo ahi sin que ninguna prueba lo viera.
   Devuelve el valor y el cursor finales. */
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
  /* Arrancar de CERO. El perfil de Firefox conserva localStorage entre pasadas, y
     sin esto la prueba hereda el inventario y «Mis criaturas» de la ejecucion
     anterior y acaba midiendo otra cosa: paso, y una fila heredada hizo fallar la
     comprobacion de que la lista empieza vacia. */
  localStorage.removeItem("jwa322.inventario");
  localStorage.removeItem("jwa322.mios");
  INV = {}; MIS = [];

  log("=== 0. errores al cargar el script ===",
      (window.__errores && window.__errores.length) ? window.__errores.join(" | ") : "ninguno");

  /* --- buscador: donde vive, y como se maneja con el teclado ---
     Pedido por n30 (25-sep-2026): la busqueda sale del apartado 1 y sube a la
     franja de las pestañas; la ficha sube a la par de los stats; y la lista se
     recorre con las flechas y se elige con Enter.
     Todo va dentro de una funcion para NO dejar nombres globales: los bloques
     <script> comparten el ambito, y un `var` aqui que choque con un `let` de la
     aplicacion deja este diagnostico sin compilar y sin ejecutar. Ver
     `comprobar_scripts` en informe_browser.py. */
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
    ok("el buscador vive en la franja de las pestañas, FUERA de la calculadora",
       !!barra && !!barra.querySelector("#q") && !!barra.querySelector("nav") &&
       !document.getElementById("s-calc").contains(caja),
       barra ? "franja con el buscador y " + barra.querySelectorAll("nav button").length + " pestañas"
             : "(no hay franja)");
    ok("la ficha sube a la par de los stats, dentro de la misma rejilla",
       document.getElementById("filaElegir").contains(document.getElementById("elegida")) &&
       document.getElementById("filaElegir").contains(document.getElementById("panelStats")) &&
       document.getElementById("elegida").nextElementSibling === document.getElementById("panelStats"),
       "ficha y stats son hermanos dentro de la rejilla");

    // --- la lista NO se abre sola al usar otras pestañas ---
    ok("la lista arranca cerrada", !abierta(), "on=" + abierta());
    elegir("indoraptor");
    document.querySelector('nav button[data-t="arbol"]').click();
    var cb = document.querySelector('#arbolCuerpo input[data-campo="creado"]');
    ok("hay una casilla en el arbol que tocar", !!cb, cb ? cb.dataset.u : "(sin casilla)");
    if (cb){ cb.checked = !cb.checked; ev(cb, "change"); }
    ok("tocar una casilla del arbol NO despliega el buscador",
       !!cb && !abierta(), "on=" + abierta() + " | pestaña " + activa());

    // --- teclado ---
    document.querySelector('nav button[data-t="calc"]').click();
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    var nFilas = drop.querySelectorAll(".it").length;
    ok("al escribir se despliega la lista", abierta() && nFilas > 1, nFilas + " filas");
    ok("y no queda nada resaltado: Enter no debe llevar a ciegas", resaltado() === "", "«" + resaltado() + "»");

    ok("ArrowDown se traga la tecla (si no, el cursor saltaria al final del texto)",
       tecla("ArrowDown").defaultPrevented, "defaultPrevented");
    var s1 = resaltado();
    ok("ArrowDown resalta la primera", s1 !== "" && s1 === drop.querySelector(".it").dataset.u, s1);
    ok("y resalta UNA sola fila", drop.querySelectorAll(".it.sel").length === 1,
       drop.querySelectorAll(".it.sel").length + " resaltadas");
    tecla("ArrowDown");
    var s2 = resaltado();
    ok("ArrowDown otra vez baja a la segunda", s2 !== "" && s2 !== s1, s1 + " -> " + s2);
    tecla("ArrowUp");
    ok("ArrowUp vuelve a la primera", resaltado() === s1, resaltado() + " (esperado " + s1 + ")");
    tecla("ArrowUp");
    ok("ArrowUp en la primera no se sale de la lista", resaltado() === s1, resaltado());
    ok("las flechas no han tocado el texto del campo", caja.value === "rex", caja.value);
    ok("una tecla normal NO se traga", !tecla("a").defaultPrevented, "defaultPrevented=false");
    for (var i = 0; i < 25; i++) tecla("ArrowDown");
    var elSel = drop.querySelector(".it.sel");
    ok("tras bajar 25 veces el resaltado sigue A LA VISTA (la lista se desplaza sola)",
       !!elSel && elSel.offsetTop >= drop.scrollTop &&
       elSel.offsetTop + elSel.offsetHeight <= drop.scrollTop + drop.clientHeight,
       "scrollTop=" + drop.scrollTop + " offsetTop=" + (elSel ? elSel.offsetTop : "?") +
       " alto=" + drop.clientHeight);

    // --- Enter lleva a la calculadora, desde cualquier pestaña ---
    var objetivo = resaltado();
    document.querySelector('nav button[data-t="arbol"]').click();
    ok("antes de pulsar Enter estamos en el arbol", activa() === "s-arbol", activa());
    caja.focus();
    tecla("Enter");
    ok("Enter lleva a la CALCULADORA aunque se pulse desde otra pestaña",
       activa() === "s-calc", activa());
    ok("y elige justo la criatura resaltada", elegido === objetivo,
       "elegido=" + elegido + " | resaltado=" + objetivo);
    ok("y cierra la lista", !abierta(), "on=" + abierta());

    // --- un clic desde otra pestaña tambien navega ---
    document.querySelector('nav button[data-t="mios"]').click();
    caja.focus();
    caja.value = "indoraptor";
    ev(caja, "input");
    var fila = drop.querySelector(".it");
    fila.dispatchEvent(new MouseEvent("click", {bubbles:true}));
    ok("un clic en un resultado desde «Mis criaturas» lleva a la calculadora",
       activa() === "s-calc" && elegido === fila.dataset.u, activa() + " / " + elegido);

    // --- Escape cierra sin elegir ---
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    var antesDeEscapar = elegido;
    ok("la lista esta abierta antes de Escape", abierta(), "on=" + abierta());
    tecla("Escape");
    ok("Escape cierra la lista", !abierta(), "on=" + abierta());
    ok("y no elige nada", elegido === antesDeEscapar, elegido);

    // --- el estado de accesibilidad acompaña ---
    caja.focus();
    caja.value = "rex";
    ev(caja, "input");
    tecla("ArrowDown");
    ok("con la lista abierta y una fila resaltada, el aria lo dice",
       caja.getAttribute("aria-expanded") === "true" &&
       caja.getAttribute("aria-activedescendant") === "it-0",
       "expanded=" + caja.getAttribute("aria-expanded") +
       " activedescendant=" + caja.getAttribute("aria-activedescendant"));
    tecla("Escape");
    ok("y al cerrar se limpian los dos",
       caja.getAttribute("aria-expanded") === "false" && !caja.hasAttribute("aria-activedescendant"),
       "expanded=" + caja.getAttribute("aria-expanded") +
       " activedescendant=" + caja.getAttribute("aria-activedescendant"));

    // Estado limpio para lo que sigue: en la calculadora y con la lista cerrada.
    irA("calc");
    cerrarLista();
  })();

  // --- buscador con miniatura ---
  document.getElementById("q").value = "indoraptor";
  ev(document.getElementById("q"), "input");
  var it = document.querySelector("#lista .it");
  ok("el buscador pinta miniatura", !!it && !!it.querySelector("img.mini"));
  cerrarLista();

  // --- Indoraptor 21 -> 30 con 1.000 ADN: hay deficit, luego hay arbol ---
  elegir("indoraptor");
  teclear(document.getElementById("nivelAct"), "21");
  teclear(document.getElementById("adnTengo"), "1000");
  document.getElementById("nivelObj").value = 30;
  ev(document.getElementById("nivelObj"), "input");

  ok("la ficha tiene imagen grande", !!document.querySelector("#elegida img.grande"));

  // --- nivel maximo bajo el nivel objetivo ---
  var mn = txt("maxNivel");
  log("--- maxNivel ---", mn);
  var mnm = /Nivel\s+(\d+)/.exec(mn);
  var nivelDicho = mnm ? Number(mnm[1]) : -1;
  var esp = nivelMaximo("unique", 21, 1000, true);
  ok("el nivel maximo mostrado coincide con el motor", nivelDicho === esp.nivel,
     "dice " + nivelDicho + ", el motor dice " + esp.nivel);
  ok("el nivel maximo NO es 0 con 1.000 ADN", nivelDicho > 0);
  ok("dice 'Ya te alcanza' solo cuando de verdad alcanza",
     (esp.nivel >= 30) === /Ya te alcanza/.test(mn), "nivel=" + esp.nivel + " objetivo=30");
  ok("no aparece ninguna cifra negativa en el bloque", !/-\d/.test(mn), mn.slice(-80));

  // --- el arbol ---
  // Hay que ACTIVAR la pestaña antes de tocarla: un elemento dentro de una
  // seccion en display:none no puede recibir el foco, asi que .focus() falla en
  // silencio y cualquier prueba de foco da un falso fallo.
  document.querySelector('nav button[data-t="arbol"]').click();
  ok("la pestaña del arbol queda activa",
     document.getElementById("s-arbol").classList.contains("on"));

  var nodos = document.querySelectorAll("#arbolCuerpo .nodo");
  log("nodos en el arbol", nodos.length);
  ok("el arbol baja a los ingredientes", nodos.length > 1, nodos.length + " nodos");
  var camposOk = 0, fotos = 0;
  nodos.forEach(function(n){
    if (n.querySelector("input[data-campo='nivel']") &&
        n.querySelector("input[data-campo='adn']") &&
        n.querySelector("input[data-campo='creado']")) camposOk++;
    if (n.querySelector("img.foto")) fotos++;
  });
  ok("todos los nodos tienen nivel+adn+creada", camposOk === nodos.length, camposOk + "/" + nodos.length);
  ok("todos los nodos tienen foto", fotos === nodos.length, fotos + "/" + nodos.length);

  // --- escribir en un nodo ---
  var ing = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  ok("hay un ingrediente editable", !!ing);
  var uuidIng = ing.dataset.u;
  teclear(ing, "123456");
  var g = INV[uuidIng];
  ok("el ADN escrito en el arbol se guarda", !!g && g.adn === 123456, JSON.stringify(g));
  var vuelto = document.querySelector("[data-u='"+uuidIng+"'][data-campo='adn']");
  ok("el campo conserva el valor tecleado", vuelto.value === "123456", vuelto.value);

  // --- tecleo DIGITO A DIGITO: el cursor no puede saltar al principio ---
  // Este es el fallo que se colo: con <input type=number>, Firefox NO deja leer ni
  // fijar el cursor (`setSelectionRange` lanza InvalidStateError y `selectionStart`
  // es null), el arbol se repinta entero en cada tecla, y teclear "1500" acababa
  // guardando 51 con "0051" en el campo. Se vigila tecleando de verdad, tecla a
  // tecla: `teclear` —que escribe el valor entero de una vez— no lo ve.
  var selAdn = "[data-u='"+uuidIng+"'][data-campo='adn']";
  var selNv  = "[data-u='"+uuidIng+"'][data-campo='nivel']";
  var relAdn = function(){ return document.querySelector(selAdn); };
  var relNv  = function(){ return document.querySelector(selNv); };

  teclear(relAdn(), "");
  var t1 = teclearTecla(relAdn, "1500");
  ok("teclear 1500 digito a digito deja 1500", t1.valor === "1500",
     "campo='" + t1.valor + "' pasos: " + t1.pasos.join(" "));
  ok("y el cursor acaba al final, no al principio", t1.cursor === 4, "cursor=" + t1.cursor);
  ok("y se guarda 1500, no 51", INV[uuidIng].adn === 1500, "guardado=" + INV[uuidIng].adn);

  teclear(relNv(), "");
  var t2 = teclearTecla(relNv, "18");
  ok("teclear el nivel digito a digito deja 18", t2.valor === "18",
     "campo='" + t2.valor + "' pasos: " + t2.pasos.join(" "));

  // Insertar EN MEDIO del numero, no solo al final: es donde un cursor mal
  // devuelto hace mas dano, porque el digito entra en el sitio equivocado.
  teclear(relAdn(), "1000");
  var medio = relAdn();
  medio.focus(); medio.setSelectionRange(1, 1);
  document.execCommand("insertText", false, "9");
  ok("insertar en medio respeta la posicion", relAdn().value === "19000",
     "campo='" + relAdn().value + "'");

  // Lo que el <input type=number> filtraba solo (letras, signos) ahora lo limpia
  // `limpiarNumero`, y sin mandar el cursor al final.
  teclear(relAdn(), "");
  var conLetras = relAdn();
  conLetras.focus();
  document.execCommand("insertText", false, "1a2");
  ok("las letras no entran en un campo de ADN", relAdn().value === "12",
     "campo='" + relAdn().value + "'");
  ok("y el valor limpio es el que se guarda", invDe(uuidIng).adn === 12,
     "guardado=" + invDe(uuidIng).adn);

  // --- escribir el NIVEL tambien ---
  var campoNivel = document.querySelector("[data-u='"+uuidIng+"'][data-campo='nivel']");
  teclear(campoNivel, "17");
  var g4 = INV[uuidIng];
  ok("el nivel escrito en el arbol se guarda", !!g4 && g4.nivel === 17, JSON.stringify(g4));

  // --- destildar 'Creada' ---
  var chk = document.querySelector("[data-u='"+uuidIng+"'][data-campo='creado']");
  ok("hay un checkbox 'Creada'", !!chk);
  var m2 = minLv(C[uuidIng][1]);
  chk.checked = false; ev(chk, "change");
  var g2 = INV[uuidIng];
  ok("destildar 'Creada' lo guarda como sin crear", !!g2 && g2.creado === false, JSON.stringify(g2));
  ok("sin crear, el nivel queda en 0", g2 && g2.nivel === 0);
  ok("el nodo avisa de 'sin crear'", /sin crear/.test(document.querySelector("#arbolCuerpo").innerText));
  var chk2 = document.querySelector("[data-u='"+uuidIng+"'][data-campo='creado']");
  chk2.checked = true; ev(chk2, "change");
  var g3 = INV[uuidIng];
  ok("al volver a crearla sube a su nivel de nacimiento (" + m2 + ")",
     !!g3 && g3.creado === true && g3.nivel === m2, JSON.stringify(g3));

  // --- guardado ---
  var json = localStorage.getItem("jwa322.inventario");
  ok("se escribio en localStorage", !!json && json.length > 20, (json||"").slice(0, 120));

  // --- Mis criaturas: SOLO lo que se guarda a proposito ---
  // Regla pedida por n30 (25-sep-2026): teclear en el arbol sirve para el calculo,
  // pero NO mete criaturas en la lista. Antes «Mis criaturas» era
  // `Object.keys(INV)`, asi que editar el ADN de los ingredientes dejaba guardado
  // el arbol genealogico entero, y pulsar «Guardar» no era la causa sino la
  // confirmacion. La lista es `MIS`, y solo la escriben Guardar, la × y la
  // importacion.
  pintarMios();
  var filas = document.querySelectorAll("#miosCuerpo tbody tr");
  var tocadas = Object.keys(INV).length;
  ok("teclear en el arbol NO mete nada en «Mis criaturas»", filas.length === 0,
     filas.length + " filas, con " + tocadas + " criaturas tocadas");
  ok("pero los datos SI quedan, para que el arbol calcule con ellos",
     tocadas > 0 && invDe(uuidIng).adn === 12,
     tocadas + " criaturas; el ingrediente con " + invDe(uuidIng).adn + " ADN");

  // Guardar mete UNA: la elegida.
  document.querySelector('nav button[data-t="calc"]').click();
  var btn = document.getElementById("btnGuardar");
  ok("existe el boton de guardar", !!btn);
  btn.click();
  pintarMios();
  var filas2 = document.querySelectorAll("#miosCuerpo tbody tr");
  var textoMios = document.querySelector("#miosCuerpo").innerText;
  ok("Guardar mete EXACTAMENTE la criatura elegida", filas2.length === 1, filas2.length + " filas");
  ok("y no cuela ningun ingrediente del arbol",
     textoMios.toLowerCase().indexOf(C[uuidIng][0].toLowerCase()) === -1,
     C[uuidIng][0] + (textoMios.toLowerCase().indexOf(C[uuidIng][0].toLowerCase()) === -1
                      ? " no aparece" : " SI aparece"));
  ok("Mis criaturas tiene columna de nivel maximo", /Nivel máx/i.test(textoMios));
  /* La columna de mejoras existe para que se VEA que los puntos se guardaron:
     sin ella, el dato solo se podria comprobar abriendo la ficha, y no habria
     forma de saber que sigue ahi. */
  var cabMios = Array.prototype.map.call(document.querySelectorAll("#miosCuerpo th"),
    function(t){ return t.textContent; }).join("|");
  ok("y una columna de mejoras, para que se vea que se guardaron",
     /Mejoras/.test(cabMios), cabMios);
  btn.click();
  var filas3 = document.querySelectorAll("#miosCuerpo tbody tr");
  ok("pulsar Guardar otra vez no duplica la fila", filas3.length === 1, filas3.length + " filas");

  // La lista guardada se persiste aparte de los datos.
  var guardadoMios = JSON.parse(localStorage.getItem("jwa322.mios") || "null");
  ok("la lista se guarda en su propia clave de localStorage",
     Array.isArray(guardadoMios) && guardadoMios.length === 1,
     JSON.stringify(guardadoMios));

  // --- 3) lo pedido por n30 el 25-sep: tira de fotos, «Lleva a» completo,
  //        informe sin columna «Rareza», y la zona en vez de «se recolecta» ---
  /* Nada de esto se juzga mirando una captura: se pulsa y se lee el DOM. Y cada
     comprobacion se hace contra el DATO del modelo o contra un calculo hecho
     aqui, nunca contra el HTML que acabamos de pintar: comparar el pintado
     con el pintado daria verde aunque las dos cosas estuvieran mal. */

  // (a) la tira de fotos, arriba de «Elige la criatura»
  var panel = document.getElementById("panelMisFotos");
  var tira  = document.getElementById("misFotos");
  MIS = ["indoraptor", "tyrannosaurus_rex"];
  pintarFotos();
  var fotos = tira.querySelectorAll("button[data-ir]");
  ok("la tira de fotos sale cuando hay criaturas guardadas",
     panel.style.display !== "none" && fotos.length === 2, fotos.length + " fotos");
  var nombresTira = [];
  var coloresTiraBien = true;
  Array.prototype.forEach.call(fotos, function(b){
    var nm = b.querySelector(".tira-nm");
    nombresTira.push(nm ? nm.textContent.trim() : "(sin nombre)");
    if (!nm || nm.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) coloresTiraBien = false;
  });
  ok("cada foto lleva el nombre de su criatura, con el color de su rareza",
     coloresTiraBien && nombresTira.length === 2, nombresTira.join(" | "));
  ok("y las fotos van ordenadas por nombre, igual que la tabla de la pestaña",
     nombresTira[0] === "Indoraptor" && nombresTira[1] === "Tyrannosaurus Rex",
     nombresTira.join(" | "));

  // el tope: con 12 guardadas solo se ensenan 10, y se dice cuantas hay
  MIS = Object.keys(C).slice(0, 12);
  pintarFotos();
  var n10 = tira.querySelectorAll("button[data-ir]").length;
  ok("la tira ensena como mucho 10 fotos", n10 === 10, n10 + " fotos de 12 guardadas");
  ok("y avisa de cuantas ensena de cuantas hay",
     /10 de 12/.test(document.getElementById("nMisFotos").textContent),
     document.getElementById("nMisFotos").textContent);

  // pulsar una foto abre ESA criatura, no la que estuviera abierta
  MIS = ["indoraptor", "tyrannosaurus_rex"];
  pintarFotos();
  elegir("indoraptor");
  tira.querySelector("button[data-ir='tyrannosaurus_rex']").click();
  ok("pulsar una foto abre esa criatura en la calculadora",
     elegido === "tyrannosaurus_rex" && document.getElementById("s-calc").classList.contains("on"),
     "elegido=" + elegido + ", pestaña calc=" +
     document.getElementById("s-calc").classList.contains("on"));

  // y sin criaturas guardadas el bloque no ocupa sitio
  MIS = []; pintarFotos();
  ok("sin criaturas guardadas la tira no ocupa sitio",
     panel.style.display === "none" && tira.querySelectorAll("button").length === 0,
     "display='" + panel.style.display + "'");

  // (b) «Lleva a»: TODA la rama superior, no solo los hijos directos
  /* El cierre transitivo se calcula AQUI, con codigo independiente del de la
     pagina. Si la ficha ensenara solo los hijos directos, los numeros no
     cuadrarian — y era exactamente el fallo: antes decia `c[6]`.
     Se usa Nundasuchus, que es el caso que lo distingue de verdad: 5 niveles y
     11 criaturas por encima, con solo 2 hijos directos. Con Indoraptor no se
     puede comprobar nada, porque su rama superior es un unico hijo y el numero
     sale igual por los dos caminos. */
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
  ok("«Lleva a» ensena TODA la rama superior, no solo los hijos directos",
     enLleva.length === espTotal,
     enLleva.length + " nombres; el cierre transitivo son " + espTotal +
     " en " + espNiv.length + " niveles");
  ok("y por eso son mas que los hijos directos", espTotal > hijosDirectos,
     espTotal + " vs " + hijosDirectos + " hijos directos");
  ok("y los agrupa por niveles, para que se vea que unas salen de otras",
     separadores === espNiv.length - 1,
     separadores + " separadores para " + espNiv.length + " niveles");
  var llevaMal = [], llevaU = [];
  Array.prototype.forEach.call(enLleva, function(b){
    llevaU.push(b.dataset.ir);
    if (b.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) llevaMal.push(C[b.dataset.ir][0]);
  });
  ok("cada nombre de «Lleva a» lleva el color de SU rareza", llevaMal.length === 0,
     enLleva.length + " nombres" + (llevaMal.length ? " | mal: " + llevaMal.join(", ") : ""));
  ok("y no hay ninguno repetido, aunque el grafo tenga diamantes",
     new Set(llevaU).size === llevaU.length, llevaU.length + " nombres, " +
     new Set(llevaU).size + " distintos");
  var destino = enLleva[enLleva.length - 1].dataset.ir;
  enLleva[enLleva.length - 1].click();
  ok("pulsar un nombre de «Lleva a» carga esa criatura en la calculadora",
     elegido === destino, "elegido=" + elegido + ", esperado " + destino);

  // (c) el informe del arbol: sin columna «Rareza», nombre pulsable y coloreado
  elegir("indoraptor");
  var inf = document.getElementById("informeArbol");
  var cab = [];
  Array.prototype.forEach.call(inf.querySelectorAll("thead th"), function(th){
    cab.push(th.textContent.trim());
  });
  ok("el informe ya no tiene columna «Rareza»", cab.indexOf("Rareza") === -1, cab.join(" | "));
  /* La de «Veces» se retiro el 25-sep-2026 por peticion de n30: «no da
     informacion util». Se comprueba que NO vuelve, igual que con «Rareza». */
  ok("ni la de «Veces», retirada por no dar informacion util",
     cab.indexOf("Veces") === -1, cab.join(" | "));
  ok("y la primera columna sigue siendo la criatura", cab[0] === "Criatura", cab[0]);
  /* La TABLA no puede llevar etiquetas: el color del nombre ya dice la rareza, y
     una etiqueta al lado seria decir lo mismo dos veces. El desglose «ADN que hay
     que ir a recolectar, por rareza» que va debajo SI las lleva, y es correcto:
     ahi la etiqueta es la clave de la cifra, no un adorno del nombre. */
  ok("la tabla del informe no pinta ninguna etiqueta de rareza",
     inf.querySelector("table").querySelectorAll(".tag").length === 0,
     inf.querySelector("table").querySelectorAll(".tag").length + " etiquetas en la tabla");
  var nomInf = inf.querySelectorAll("tbody tr button.ir");
  var infMal = [];
  Array.prototype.forEach.call(nomInf, function(b){
    if (b.className.indexOf("rc-" + CLASE[C[b.dataset.ir][1]]) === -1) infMal.push(C[b.dataset.ir][0]);
  });
  ok("cada nombre del informe lleva el color de la rareza de SU criatura",
     nomInf.length > 0 && infMal.length === 0,
     nomInf.length + " nombres" + (infMal.length ? " | mal: " + infMal.join(", ") : ""));
  var uInf = nomInf[1] ? nomInf[1].dataset.ir : null;
  nomInf[1].click();
  ok("pulsar el nombre en el informe carga esa criatura",
     !!uInf && elegido === uInf, "elegido=" + elegido + ", esperado " + uInf);

  // (d) «se recolecta» ya no existe: en su lugar, la zona real de cada criatura
  /* Se busca la PILDORA, no el texto: la prosa del informe dice «hasta las que
     se recolectan», y buscando la cadena suelta el fallo era de la prueba. */
  var pildorasRecolecta = 0;
  document.querySelectorAll(".pill").forEach(function(p){
    if (/^se recolecta$/i.test(p.textContent.trim())) pildorasRecolecta++;
  });
  ok("la pildora «se recolecta» ya no existe en ninguna parte",
     pildorasRecolecta === 0, pildorasRecolecta + " pildoras con ese texto");
  document.querySelector('nav button[data-t="arbol"]').click();
  pintarArbol();
  var nodosArb = document.querySelectorAll("#arbolCuerpo .nodo");
  var zonasVistas = [], zonaMal = null, nodosConZona = 0, fuera = [];
  /* Las etiquetas validas se sacan del MODELO, no de la pagina: si alguien
     escribiera un texto a mano («cerca de tu casa»), no estaria aqui y la prueba
     fallaria. Comparar contra `zonaDe` seria un espejo: el mismo malentendido
     pasaria en verde por los dos lados. */
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
    // (1) el texto tiene que ser el que da el modelo para ESA criatura
    if (t !== zonaDe(inp.dataset.u, true)) zonaMal = inp.dataset.u;
    // (2) y cada trozo tiene que ser una etiqueta del modelo, no texto inventado
    if (t !== "sin fuente en el mapa" && t !== "solo en santuario"){
      t.split(/\s*·\s*/).forEach(function(trozo){
        if (trozo === "combate") return;
        if (!etiquetasValidas[trozo]) fuera.push(inp.dataset.u + " -> '" + trozo + "'");
      });
    }
  });
  ok("los ingredientes del arbol ensenan su zona de recoleccion",
     nodosConZona > 0, nodosConZona + " nodos con zona: " + zonasVistas.slice(0, 3).join(" | "));
  ok("y la zona ensenada es la del modelo, criatura por criatura", !zonaMal,
     zonaMal ? zonaMal + " dice '" + zonaDe(zonaMal, true) + "'" : "todas coinciden");
  ok("y ningun trozo de la zona es texto inventado: todos salen del modelo",
     fuera.length === 0, fuera.length ? fuera.slice(0, 3).join(" ;; ")
                                      : "todos los trozos estan en el modelo");
  /* El dato crudo trae la franja horaria pegada («Local Area 3 | All Day») y en la
     pildora se quita: las siete zonas del mapa son las cuatro franjas, asi que
     «All Day» no distingue nada y alargaba la pildora hasta 49 caracteres. */
  ok("la pildora de la zona no arrastra la franja horaria redundante",
     !zonasVistas.some(function(t){ return /All Day/.test(t); }),
     zonasVistas.slice(0, 3).join(" | "));
  ok("la pildora de la zona va con el color de las pildoras de estado, no con uno de rareza",
     (function(){
       var z = document.querySelector("#arbolCuerpo .nodo:not(.raiz) .cab .pill");
       var r = document.querySelector("#arbolCuerpo .nodo.raiz .cab .pill");   // «raíz»
       if (!z || !r) return false;
       return getComputedStyle(z).color === getComputedStyle(r).color;
     })(), "comparada con la pildora «raíz» del nodo raíz");

  /* La ficha de la criatura elegida. La pildora de zona solo tiene que salir si
     dice algo: en un hibrido su fuente es `none` (248 de las 518) y «sin fuente en
     el mapa» es ruido — a un hibrido no se le busca, se fusiona. Se comprueba con
     el criterio independiente: ingredientes vacios, o fuente real en el modelo. */
  var faltan = [], sobran = [], nBase = 0, nHib = 0;
  Object.keys(C).forEach(function(u){
    elegir(u);
    var hay = !!document.querySelector("#elegida .pill.zona");
    var esBase = !(C[u][5] && C[u][5].length);
    var tieneFuente = (C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; });
    var deberia = esBase || tieneFuente;
    if (esBase) nBase++; else nHib++;
    if (deberia && !hay) faltan.push(u);
    if (!deberia && hay) sobran.push(u);
  });
  ok("la pildora de zona no falta en ninguna que deba llevarla", faltan.length === 0,
     faltan.length ? faltan.length + " sin pildora: " + faltan.slice(0, 6).join(", ") : "ninguna de " + nBase + " base");
  ok("y no sobra en ningun hibrido sin fuente", sobran.length === 0,
     sobran.length ? sobran.length + " con pildora de relleno: " + sobran.slice(0, 6).join(", ") : "ninguno de " + nHib + " hibridos");
  ok("las 518 se reparten entre 270 sin ingredientes y 248 hibridos", nBase === 270 && nHib === 248,
     nBase + " base + " + nHib + " hibridos = " + (nBase + nHib));
  /* El caso concreto que motiva la regla: un hibrido sin fuente no debe decir
     «sin fuente en el mapa». Se elige uno de verdad, no se supone. */
  var hibSinFuente = Object.keys(C).filter(function(u){
    return (C[u][5] && C[u][5].length) && !(C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; }); })[0];
  elegir(hibSinFuente);
  ok("un hibrido sin fuente (" + C[hibSinFuente][0] + ") no dice «sin fuente en el mapa»",
     document.querySelector("#elegida").textContent.indexOf("sin fuente en el mapa") === -1,
     "texto de la ficha buscado entero");
  var hibConFuente = Object.keys(C).filter(function(u){
    return (C[u][5] && C[u][5].length) && (C[u][7] || []).some(function(x){
      return M.locDardeo.indexOf(x) >= 0 || M.locCombate.indexOf(x) >= 0; }); });
  ok("y el hibrido que SI sale en el mapa conserva su pildora", hibConFuente.length >= 1,
     hibConFuente.length ? hibConFuente.map(function(u){ return C[u][0]; }).join(", ") : "ninguno");
  if (hibConFuente.length){
    elegir(hibConFuente[0]);
    var pz = document.querySelector("#elegida .pill.zona");
    ok("  (" + C[hibConFuente[0]][0] + " ensena «" + (pz ? pz.textContent.trim() : "nada") + "»)", !!pz,
       pz ? "con pildora" : "sin pildora");
  }

  // ======================================================================
  //  Los stats del dino, donde estaba «Filtrar por rareza»
  // ======================================================================
  ok("el filtro por rareza ya no esta en la pagina",
     !document.getElementById("fRar") &&
     document.body.innerText.indexOf("Filtrar por rareza") < 0, "");

  var panelS = document.getElementById("panelStats");
  var fichas = panelS ? panelS.querySelectorAll(".st") : [];
  ok("en su sitio hay un panel de stats con seis fichas", fichas.length === 6,
     fichas.length + " fichas");
  var nombresS = [], iconosS = [];
  fichas.forEach(function(f){
    nombresS.push(f.querySelector(".st-k").textContent);
    iconosS.push(f.querySelector("img").getAttribute("src"));
  });
  ok("las seis fichas llevan su nombre, entero y en orden",
     nombresS.join("|") === "Vida|Daño|Velocidad|Armadura|Crítico|Daño crít.",
     nombresS.join(" | "));
  ok("y su icono, distinto en cada una", new Set(iconosS).size === 6, iconosS.join(" "));
  ok("los iconos salen de la carpeta del proyecto, no de internet",
     iconosS.every(function(s){ return s.indexOf("img/stat/") === 0; }), iconosS.join(" "));

  /* Los valores a NIVEL 26 tienen que ser EXACTAMENTE los del dato: a ese nivel
     el multiplicador vale 1,000000 y no hay nada que escalar. Y los numeros de
     la comparacion estan escritos AQUI, no leidos del modelo: son los que
     paleo.gg ensena en su propia ficha cacheada de alacranix. Si la pagina se
     inventara una escala, esto lo caza. */
  function seis(){ return M.statsOrden.map(function(k){
    return document.getElementById("stV_" + k).textContent; }).join(" "); }
  /* Deja la criatura a un nivel concreto y a cero de todo. El nivel es un
     PARAMETRO y no una constante: dar por hecho un nivel fue el error de la
     primera version de estas pruebas, que daba por bueno el 30 despues de haber
     puesto el 26 y fallaba senalando al sitio equivocado. */
  function cero(u, niv){
    fijar(u, "nivel", niv); fijar(u, "adn", 0);
    ["bVida","bDano","bVel","mejora"].forEach(function(c){ fijar(u, c, 0); });
  }
  elegir("alacranix"); cero("alacranix", 26); pintarStats();
  var a26 = seis();
  ok("a nivel 26 los stats son los del dato, sin escala ninguna",
     a26 === "4,250 1,650 115 40% 15% 125%", a26);

  /* El nivel escala VIDA y DANO y nada mas. Es una comprobacion de ESTRUCTURA,
     no de la tabla: no depende de que el multiplicador sea el correcto. */
  fijar("alacranix", "nivel", 30); pintarStats();
  var a30 = seis().split(" ");
  var b26 = a26.split(" ");
  ok("subir de nivel sube la vida y el dano",
     a30[0] !== b26[0] && a30[1] !== b26[1],
     "nivel 26: " + b26[0] + "/" + b26[1] + "  ->  nivel 30: " + a30[0] + "/" + a30[1]);
  ok("y NO toca velocidad, armadura ni criticos",
     a30[2] === b26[2] && a30[3] === b26[3] && a30[4] === b26[4] && a30[5] === b26[5],
     a30.slice(2).join(" "));

  // --- los puntos de mejora: se guardan, suman y se acotan ---
  cero("alacranix", 30); pintarStats();
  var vel0 = Number(document.getElementById("stV_velocidad").textContent);
  var masV = document.querySelector('#panelStats [data-boost="bVel"][data-paso="1"]');
  var menV = document.querySelector('#panelStats [data-boost="bVel"][data-paso="-1"]');
  ok("con cero puntos, el mando de restar esta apagado y el de sumar no",
     menV.disabled === true && masV.disabled === false, "");
  for (var i1 = 0; i1 < 5; i1++) masV.click();
  ok("cinco puntos de velocidad suben la velocidad en 10 (2 por punto)",
     Number(document.getElementById("stV_velocidad").textContent) === vel0 + 10,
     vel0 + " -> " + document.getElementById("stV_velocidad").textContent);
  ok("y quedan guardados en el inventario, no solo en pantalla",
     INV["alacranix"] && INV["alacranix"].bVel === 5, JSON.stringify(INV["alacranix"]));
  ok("el contador ensena los puntos sobre el tope",
     /Puntos\s*5\s*de\s*30/.test(document.getElementById("stNota").innerText.replace(/\s+/g, " ")),
     document.getElementById("stNota").innerText.replace(/\s+/g, " "));
  menV.click();
  ok("y el mando de restar quita un punto de verdad", INV["alacranix"].bVel === 4,
     JSON.stringify(INV["alacranix"]));

  /* El tope es del CONJUNTO de los tres stats, no de cada uno: 20 por stat Y
     la suma sin pasar del tope. Se comprueba por el camino de la interfaz. */
  fijar("alacranix", "bVida", 20); pintarStats();
  ok("un stat solo no pasa de 20 puntos",
     document.querySelector('#panelStats [data-boost="bVida"][data-paso="1"]').disabled === true, "");
  /* El recorte del conjunto NO es alcanzable desde los mandos —el de sumar se
     apaga antes de pasarse—, asi que se prueba por donde si entra: una escritura
     directa, que es el camino de la IMPORTACION. */
  fijar("alacranix", "bDano", 20); fijar("alacranix", "bVel", 20); pintarStats();
  var mAl = mejDe("alacranix"), sumaAl = mAl.bVida + mAl.bDano + mAl.bVel;
  ok("una importacion que se pase del tope se recorta, y se guarda recortada",
     sumaAl === mAl.tope && sumaAl === 30, sumaAl + " de " + mAl.tope +
     "  " + JSON.stringify(INV["alacranix"]));

  /* La pista de mejoras. Y aqui esta lo que una SUPOSICION mia tenia mal: el
     orden de los pasos NO es el mismo en Unica y en Apex. En Apex el boost_max
     es el paso 3 y vale 2; en Unica es el paso 4 y vale 1. Estos dos casos se
     escribieron despues de verlo en una captura, porque el codigo los lee del
     dato y yo los habia dado por iguales. */
  elegir("alacranix"); cero("alacranix", 30); pintarStats();
  ok("sin pista puesta, el tope de puntos es el nivel", topePuntos("alacranix") === 30,
     "" + topePuntos("alacranix"));
  for (var i2 = 0; i2 < 3; i2++) cambiarMejora("alacranix", "mejora", 1);
  ok("en el Apex el paso 3 ya da +2 al tope (su boost_max vale 2)",
     topePuntos("alacranix") === 32, "" + topePuntos("alacranix"));
  /* Los iconos de los catalizadores y las monedas solo aparecen en la linea de
     coste, y esa linea solo existe con una pista y un paso por delante: se
     recogen AQUI para que la comprobacion de "todas las imagenes cargan" los
     cubra. Sin esto, los tres catalizadores no se comprobaban en ningun sitio. */
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
  ok("en la Unica el paso 3 NO toca el tope: su boost_max esta en el 4",
     topePuntos("indoraptor") === 30, "" + topePuntos("indoraptor"));
  cambiarMejora("indoraptor", "mejora", 1);
  ok("y el paso 4 da +1, no +2", topePuntos("indoraptor") === 31, "" + topePuntos("indoraptor"));

  /* La pista solo existe a partir del nivel 30, y al bajar se GUARDA a 0: lo que
     se ve tiene que ser lo que se guarda, o al recargar apareceria otra cosa. */
  fijar("indoraptor", "nivel", 29); pintarStats();
  ok("por debajo del nivel 30 el mando de mejoras esta apagado",
     document.querySelector('#panelStats [data-boost="mejora"][data-paso="1"]').disabled === true, "");
  ok("y la pista se recorta a 0 TAMBIEN en el inventario",
     INV["indoraptor"].mejora === 0 && document.getElementById("stP_mejora").textContent === "0",
     JSON.stringify(INV["indoraptor"]));
  ok("el tope de puntos vuelve a ser el nivel, sin bono",
     document.getElementById("stNota").innerText.indexOf("tope = nivel 29") > 0,
     document.getElementById("stNota").innerText.replace(/\s+/g, " "));

  /* Una criatura sin pista no debe ensenar el mando, ni dejar tocarlo. */
  elegir("tyrannosaurus_rex"); pintarStats();
  ok("una criatura sin pista no ensena el mando de mejoras",
     document.getElementById("stFilaMej").style.display === "none",
     "display=" + document.getElementById("stFilaMej").style.display);
  ok("y no se le puede poner una pista por mucho que se pulse",
     cambiarMejora("tyrannosaurus_rex", "mejora", 1) === false &&
     (INV["tyrannosaurus_rex"] || {}).mejora === undefined, "");

  // ======================================================================
  //  El tema, y el icono de la pestana
  // ======================================================================
  var selT = document.getElementById("tema");
  var opsT = selT ? Array.prototype.map.call(selT.options, function(o){ return o.value; }) : [];
  ok("hay un desplegable de tema con «default» y «yellow»",
     opsT.join(",") === "default,yellow", opsT.join(","));

  /* La prueba que de verdad importa: los colores de RAREZA no pueden cambiar
     entre temas. Si cambiaran, el tema nuevo seria exactamente la confusion que
     n30 pidio evitar. Se miran los valores COMPUTADOS, no el texto del CSS:
     leer el fichero solo demuestra que la linea esta escrita. */
  var raiz = document.documentElement;
  var claves = ["--r-comun","--r-rara","--r-epica","--r-legendaria","--r-unica",
                "--r-apex","--r-omega","--verde","--ambar","--rojo","--azul",
                "--pill","--st-acc"];
  function colores(){ var cs = getComputedStyle(raiz); return claves.map(function(k){
    return cs.getPropertyValue(k).trim(); }); }
  var colD = colores(), marcaD = getComputedStyle(raiz).getPropertyValue("--marca").trim();
  var bgD = getComputedStyle(document.body).backgroundColor;
  ponerTema("yellow");
  var colY = colores(), marcaY = getComputedStyle(raiz).getPropertyValue("--marca").trim();
  var bgY = getComputedStyle(document.body).backgroundColor;
  ok("el tema cambia el color de marca y el fondo",
     marcaD !== marcaY && bgD !== bgY, marcaD + " -> " + marcaY + " · " + bgD + " -> " + bgY);
  var distintas = [];
  claves.forEach(function(k, i){ if (colD[i] !== colY[i]) distintas.push(k); });
  ok("y NO toca ninguno de los colores de rareza ni los semanticos",
     distintas.length === 0,
     distintas.length ? "cambiarian: " + distintas.join(", ")
                      : "los " + claves.length + " intactos");
  ok("el tema se aplica como atributo en <html>",
     raiz.getAttribute("data-tema") === "yellow", "" + raiz.getAttribute("data-tema"));
  ok("y se guarda para la proxima vez",
     localStorage.getItem("jwa322.tema") === "yellow", "" + localStorage.getItem("jwa322.tema"));
  ponerTema("default");
  ok("volver a «default» quita el atributo, no lo deja en «default»",
     raiz.getAttribute("data-tema") === null, "" + raiz.getAttribute("data-tema"));
  ok("y el desplegable sigue al tema", selT.value === "default", selT.value);

  /* El icono de la pestana: lo unico que se ve cuando el foco esta en otra
     pestana. Que exista el <link> no prueba nada —que la imagen CARGUE, si. */
  var ico = document.querySelector('link[rel="icon"]');
  ok("hay un icono de pestana, y va en linea para no depender de un fichero",
     !!ico && ico.href.indexOf("data:image/svg+xml") === 0,
     ico ? ico.href.slice(0, 44) + "…" : "no hay <link rel=icon>");
  if (ico){
    var ci = new Image();
    ci.src = ico.href;
    ci.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
    document.body.appendChild(ci);
    CLONES.push({src: "(favicon de la pestana)", el: ci});
  }
  log("", "");

  // --- 2) clones ansiosos de cada imagen, para que bloqueen `load` ---
  var srcs = [];
  document.querySelectorAll("img").forEach(function(im){
    var s = im.getAttribute("src");
    if (s && srcs.indexOf(s) < 0) srcs.push(s);
  });
  log("imagenes distintas referenciadas", srcs.length);
  srcs.forEach(function(s){
    var c = new Image();
    c.src = s;
    c.style.cssText = "position:fixed;left:-9999px;top:0;width:1px;height:1px";
    document.body.appendChild(c);      // ansioso por defecto: bloquea load
    CLONES.push({src: s, el: c});
  });

  // --- el foco se comprueba en `load`, no aqui ---
  // La pagina recoloca el foco en el siguiente turno (setTimeout 0), asi que
  // comprobarlo en el mismo tick daria un falso fallo.
  // Y hay que VOLVER a la pestaña del arbol: el apartado anterior deja la
  // calculadora activa, y un campo dentro de una seccion en display:none no puede
  // recibir el foco — .focus() falla en silencio y activeElement se queda en BODY.
  /* Y hay que ELEGIR una criatura con ingredientes: el arbol solo tiene nodos
     hijos si la elegida se fusiona. Depender de la que dejo el bloque anterior
     hacia que esta prueba se cayera —con un `el is null`— en cuanto alguien
     tocara el orden de las comprobaciones. */
  elegir("indoraptor");
  document.querySelector('nav button[data-t="arbol"]').click();
  pintarArbol();
  var ingFoco = document.querySelector("#arbolCuerpo .nodo:not(.raiz) input[data-campo='adn']");
  FOCO_U = ingFoco ? ingFoco.dataset.u : null;
  teclear(ingFoco, "777");
  ok("el valor tecleado sobrevive al repintado",
     !!INV[FOCO_U] && INV[FOCO_U].adn === 777, JSON.stringify(INV[FOCO_U]));
} catch (e) {
  log("!! EXCEPCION", e.message + " @@ " + (e.stack || "").split("\n")[1]);
}

// --- 3) el informe, ya con las imagenes resueltas ---
window.addEventListener("load", function(){
  // el foco, ya con la recolocacion asincrona de la pagina hecha
  if (FOCO_U){
    var ae = document.activeElement;
    ok("el arbol se repinta sin perder el foco",
       ae && ae.dataset && ae.dataset.u === FOCO_U && ae.dataset.campo === "adn",
       "esperado u=" + FOCO_U + " campo=adn | real: " + (ae ? ae.tagName : "nada") +
       " u=" + (ae && ae.dataset ? ae.dataset.u : "?") +
       " campo=" + (ae && ae.dataset ? ae.dataset.campo : "?"));
  }

  var bien = 0, mal = [];
  CLONES.forEach(function(c){
    if (c.el.complete && c.el.naturalWidth > 0) bien++; else mal.push(c.src);
  });
  if (CLONES.length){
    ok("todos los ficheros de imagen cargan y decodifican", mal.length === 0,
       bien + "/" + CLONES.length + " ok" + (mal.length ? "  fallan: " + mal.slice(0,3).join(", ") : ""));
    var una = CLONES[0].el;
    log("ejemplo de imagen", una.naturalWidth + "x" + una.naturalHeight + "  " + una.src.split("/").pop());
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
# las imagenes se referencian como img/<uuid>.webp, relativas al HTML
enlace = os.path.join(DIR, "img")
if os.path.islink(enlace):
    if os.readlink(enlace) != IMG:
        os.unlink(enlace)          # os.remove lo intercepta el shim del sistema
elif os.path.isdir(enlace):
    shutil.rmtree(enlace, ignore_errors=True)
if not os.path.exists(enlace):
    os.symlink(IMG, enlace)

# Un cazador de errores ANTES del script principal: si el script revienta al
# cargar, todo lo que define deja de existir y el sintoma es "X is not defined",
# que no dice nada. Esto da el error de verdad.
CAZA = r"""
<script>
window.__errores = [];
window.addEventListener("error", function(e){
  window.__errores.push((e.message || "?") + "  @@ linea " + (e.lineno||"?") +
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
    raise SystemExit("no encuentro <head> para fijar el idioma")
html = html.replace("<head>", "<head>\n" + PIN, 1)
# El visor puede dejar atributos en <body> (data-page-node-id), asi que no
# vale buscar "<body>" a secas.
m = re.search(r"<body[^>]*>", html)
if not m:
    raise SystemExit("el HTML no tiene <body>")
html = html[:m.end()] + CAZA + html[m.end():]
# Antes de abrir el navegador: si el diagnostico no compila junto a la aplicacion
# —colision de nombres en el ambito global—, la prueba se quedaria sin correr y
# el sintoma seria «no entrego el informe», que no dice nada. Ver informe_browser.
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
print("informe:", TXT)
print("-" * 72)
print(informe)
print("-" * 72)
codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)


# ---------------------------------------------------------------------------
# SEGUNDA PASADA: la tira de fotos, en el ARRANQUE REAL.
#
# No cabe en la pasada de arriba, y no es un capricho: la de arriba pinta la
# tira DESDE DENTRO del evento `load`, asi que sus <img> se insertan cuando el
# evento ya paso y siempre salen a medio cargar. Medido: daba 0x0 con `lazy` y
# 0x0 tambien con `eager`, o sea que no distinguia nada.
#
# Aqui se siembra `localStorage` ANTES del script principal, de modo que el
# `pintarFotos()` del arranque ya encuentra la lista: ese es el camino del
# usuario. Y se mide lo que de verdad importa —que la imagen se vea—, no si el
# atributo dice `lazy` o `eager`.
#
# Este es el fallo que caza: con `loading="lazy"`, las fotos de la tira NO se
# cargaban nunca en el arranque (naturalWidth 0 en las tres), aunque los
# ficheros estuvieran bien — clones ansiosos de las MISMAS direcciones cargaban
# sin problema— y el texto alternativo salia en su lugar. Con `eager` cargan
# (207x250). Por eso la tira va ansiosa y el arbol sigue vago.
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
        raise SystemExit("no encuentro <head> para fijar el idioma")
    html = html.replace("<head>", "<head>\n" + PIN, 1)
    LISTA = '["indoraptor","tyrannosaurus_rex","velociraptor"]'
    SEMILLA = (
        "<script>\n"
        "/* ANTES del script principal: el pintado del arranque ya encuentra la lista. */\n"
        "try { localStorage.setItem('jwa322.mios', JSON.stringify(" + LISTA + ")); } catch(e){}\n"
        "</script>\n")
    marca = '<script>\n"use strict";'
    if marca not in html:
        raise SystemExit("no encuentro el script principal para sembrar antes")
    html = html.replace(marca, SEMILLA + marca, 1)

    srv2 = arrancar()
    diag = r"""
<script>
window.addEventListener("load", function(){
  var RES = [], FALLOS = 0;
  function ok(k, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + k + ": " + (d===undefined?"":d)); }
  try {
    var imgs = document.querySelectorAll("#misFotos img");
    ok("el arranque pinta la tira con la lista guardada", imgs.length === 3, imgs.length + " fotos");
    var malas = [], vistas = [];
    imgs.forEach(function(im){
      vistas.push(im.getAttribute("src") + " " + im.naturalWidth + "x" + im.naturalHeight);
      if (!(im.naturalWidth > 0)) malas.push(im.getAttribute("src"));
    });
    ok("y las fotos estan CARGADAS al terminar el arranque, no a medias",
       imgs.length > 0 && malas.length === 0,
       malas.length ? "sin cargar: " + malas.join(", ") : vistas.join(" | "));
    // y se ven de verdad: una imagen cargada pero con visibility:hidden no sirve
    var ocultas = 0;
    imgs.forEach(function(im){ if (getComputedStyle(im).visibility !== "visible") ocultas++; });
    ok("y ninguna esta oculta por un fallo de carga", ocultas === 0, ocultas + " ocultas");
    // el arbol si puede seguir siendo vago: 518 ficheros de golpe no
    var vagas = document.querySelectorAll('#arbolCuerpo img[loading="lazy"]').length;
    RES.push("   (informativo) imagenes vagas en el arbol: " + vagas);
  } catch(e){ RES.push("!! EXCEPCION " + e.message); FALLOS++; }
  /* El marcador no es decorativo: `veredicto()` da por buena la pasada SOLO si
     lo encuentra, y si no la declara fallida. Sin esta linea, la pasada salia
     con 0 fallos y el script terminaba en 1 igualmente. */
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
    _ok2, _msg2 = comprobar_scripts(html + diag, "probar_ui.py (la tira)")
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
    print("=== la tira de fotos, en el arranque real ===")
    print(info2)
    c2, lineas2 = veredicto(info2)
    for l in lineas2:
        print(l)
    return c2


raise SystemExit(codigo or pasada_tira())
