#!/usr/bin/env python3
"""
Muestra las siete etiquetas de rareza juntas, y COMPRUEBA que el navegador las
pinta del color que dice el CSS.

El CSS no se copia: se extrae del HTML entregable, igual que los verificadores
extraen el motor. Lo que se ve aqui es literalmente lo que vera el usuario.

La comprobacion no se queda en leer el fichero: se lee el color **calculado**
(`getComputedStyle`) de cada etiqueta en el navegador y se compara con el valor
declarado en `--r-*`. Leer el fichero solo demuestra que el texto esta escrito;
leer el color calculado demuestra que el navegador lo aplica.

Y el informe viaja por XHR sincrono (ver informe_browser.py), no dentro de un
PNG: si una etiqueta sale sin color, el script falla con codigo de salida 1.

Genera /tmp/jwa-rareza/rareza.png

Uso:
    python3 probar_rareza.py            # comprueba los colores calculados
    python3 probar_rareza.py --visual   # solo la muestra, sin el informe encima
                                        # (el informe es un <pre> fijo a pantalla
                                        #  completa: si se pinta, tapa la muestra
                                        #  y no se puede juzgar el tono a ojo)
"""
import os, re, subprocess, sys

from informe_browser import arrancar, comprobar_scripts, veredicto

VISUAL = "--visual" in sys.argv

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "calculadora-jwa-3.22.html")
DIR = "/tmp/jwa-rareza"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "rareza.html")
SHOT = os.path.join(DIR, "rareza.png")

ORDEN = ["common", "rare", "epic", "legendary", "unique", "apex", "omega"]
# lo que pidio n30, en palabras
PEDIDO = {"common": "blanco", "rare": "azul", "epic": "amarillo", "legendary": "rojo",
          "unique": "verde", "apex": "morado", "omega": "(no lo pidio: fucsia, para no "
                                                    "chocar con el morado del apex)"}

srv = arrancar()

html = open(HTML, encoding="utf-8").read()

# 1) el bloque :root. Se vuelve a envolver en el selector: el grupo es solo las
#    declaraciones, y pegarlas sueltas en la hoja las deja sin dueno -> var()
#    no resuelve y todo sale en blanco. (Paso, y por eso ahora hay comprobacion.)
m = re.search(r":root\s*\{(.*?)\}", html, re.S)
if not m:
    raise SystemExit("no encuentro el bloque :root en el entregable")
raiz = ":root{" + m.group(1) + "}"

# 2) las reglas de la etiqueta y de los colores de rareza
reglas = []
for patron in (r"\.tag\s*\{[^}]*\}", r"\.rc-[a-z]+\s*\{[^}]*\}"):
    reglas += re.findall(patron, html)
if not any("rc-apex" in r for r in reglas):
    raise SystemExit("no encuentro las clases .rc-* en el entregable")

# 3) nombres, clases y valores declarados, sacados del propio entregable
mm = re.search(r"const RAREZAS\s*=\s*\{(.*?)\}", html, re.S)
mc = re.search(r"const CLASE\s*=\s*\{(.*?)\}", html, re.S)
if not (mm and mc):
    raise SystemExit("no encuentro RAREZAS/CLASE en el entregable")
rareza = dict(re.findall(r'(\w+)\s*:\s*"([^"]+)"', mm.group(1)))
clase = dict(re.findall(r'(\w+)\s*:\s*"([^"]+)"', mc.group(1)))
declarado = dict(re.findall(r"--r-([a-z]+)\s*:\s*(#[0-9a-fA-F]{6})", raiz))

faltan = [r for r in ORDEN if r not in rareza or r not in clase or clase[r] not in declarado]
if faltan:
    raise SystemExit("faltan rarezas en el entregable: %s" % faltan)

# el color de las pildoras de estado, que NO puede estar en la paleta de rarezas
m_pill = re.search(r"--pill\s*:\s*(#[0-9a-fA-F]{6})", raiz)
if not m_pill:
    raise SystemExit("no encuentro --pill en el entregable")
pill = m_pill.group(1)
if pill.lower() in [v.lower() for v in declarado.values()]:
    raise SystemExit("--pill (%s) coincide con un color de rareza: %s"
                     % (pill, [k for k, v in declarado.items() if v.lower() == pill.lower()]))

# Las variables semanticas del interfaz (verde = "todo bien", ambar = "falta",
# rojo = "mal", azul = "informacion"). Se comparan con la paleta de rarezas para
# saber QUE hex estan haciendo doble trabajo. No es un error en si: es una
# colision que hay que ver, no que esconder.
sem = dict(re.findall(r"--(verde|ambar|rojo|azul|violeta|pill)\s*:\s*(#[0-9a-fA-F]{6})", raiz))
choques = {}
for r in ORDEN:
    h = declarado[clase[r]].lower()
    iguales = sorted(k for k, v in sem.items() if v.lower() == h)
    if iguales:
        choques[h] = iguales

filas = "".join(
    '<tr><td class="nom">%s</td><td><span class="tag rc-%s">%s</span></td>'
    '<td><code>--r-%s: %s</code></td></tr>'
    % (rareza[r], clase[r], rareza[r], clase[r], declarado[clase[r]])
    for r in ORDEN
)
tira = " ".join('<span class="tag rc-%s">%s</span>' % (clase[r], rareza[r]) for r in ORDEN)

# 4) el arnes: lee el color CALCULADO de cada etiqueta y lo manda.
#    Las claves van con el prefijo `rc-`, que es la clase que se busca en el DOM.
esperado_js = "{" + ",".join('"rc-%s":"%s"' % (clase[r], declarado[clase[r]]) for r in ORDEN) + "}"
nombres_js = "{" + ",".join('"rc-%s":"%s"' % (clase[r], rareza[r]) for r in ORDEN) + "}"
arnes = """
<script>
(function(){
  var RES = [], FALLOS = 0;
  function ok(k, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + k + ": " + (d===undefined?"":d)); }
  var ESPERADO = %(esperado)s;
  var NOMBRE = %(nombres)s;
  function aHex(rgb){
    var m = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/.exec(rgb);
    if (!m) return rgb;
    return "#" + [1,2,3].map(function(i){
      return ("0" + Number(m[i]).toString(16)).slice(-2);
    }).join("");
  }
  var vistos = {};
  document.querySelectorAll(".tag").forEach(function(t){
    var cls = Array.prototype.filter.call(t.classList, function(c){ return /^rc-/.test(c); })[0];
    if (!cls || vistos[cls]) return;
    vistos[cls] = true;
    var cs = getComputedStyle(t);
    var real = aHex(cs.color);
    var esperado = ESPERADO[cls];
    ok("la etiqueta " + NOMBRE[cls] + " se pinta de " + esperado,
       real === esperado, "calculado " + real + " (" + cs.color + ") vs declarado " + esperado);
    ok("y lleva borde, no es texto suelto " + NOMBRE[cls],
       cs.borderTopStyle === "solid" && cs.borderTopWidth !== "0px",
       cs.borderTopWidth + " " + cs.borderTopStyle);
  });
  ok("estan las siete etiquetas", Object.keys(vistos).length === 7,
     Object.keys(vistos).length + " de 7");
  // el color de fondo del panel tiene que resolver, o la muestra mentiria
  var caja = document.querySelector(".caja");
  ok("las variables de color resuelven (el panel no sale blanco)",
     getComputedStyle(caja).backgroundColor === "rgb(23, 26, 35)",
     getComputedStyle(caja).backgroundColor);
  RES.push("");
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var d = document.createElement("pre"); d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:14px/1.5 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\\n");
  document.body.appendChild(d);
%(entrega)s
})();
</script>
""" % {"esperado": esperado_js, "nombres": nombres_js, "entrega": srv.js("__diag")}

pagina = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Etiquetas de rareza</title><style>
%(raiz)s
%(reglas)s
body{padding:22px;font-family:ui-sans-serif,system-ui,sans-serif;background:var(--bg)}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.7px;color:#8b93a7;margin:0 0 10px}
.caja{background:var(--panel);border:1px solid var(--borde);border-radius:9px;padding:16px;margin-bottom:18px}
.caja.p2{background:var(--panel2)}
.caja.bg{background:var(--bg)}
table{border-collapse:collapse;width:100%%}
td{padding:7px 10px;vertical-align:middle;border-bottom:1px solid #272c3a}
td.nom{color:#e6e9ef;font-size:14px;width:150px}
code{color:#5f6879;font-size:12px}
.grande .tag{font-size:16px;padding:4px 12px}
.grande p{margin:0;line-height:2.8}
</style></head><body>
<div class="caja"><h2>Fondo de panel &mdash; #171a23</h2><table>%(filas)s</table></div>
<div class="caja p2"><h2>Fondo de cifra &mdash; #1d212c</h2><table>%(filas)s</table></div>
<div class="caja bg"><h2>Fondo del cuerpo &mdash; #0f1117</h2><table>%(filas)s</table></div>
<div class="caja grande"><h2>Al doble de tamano, para juzgar el tono</h2><p>%(tira)s</p></div>
%(arnes)s
</body></html>""" % {"raiz": raiz, "reglas": "\n".join(reglas), "filas": filas,
                     "tira": tira, "arnes": "" if VISUAL else arnes}

os.makedirs(DIR, exist_ok=True)
os.makedirs(PERFIL, exist_ok=True)
open(FUERA, "w", encoding="utf-8").write(pagina)

env = dict(os.environ)
env.update({"DBUS_SESSION_BUS_ADDRESS": "disabled:", "NO_AT_BRIDGE": "1",
            "MOZ_HEADLESS": "1", "MOZ_DISABLE_CONTENT_SANDBOX": "1", "HOME": DIR})
subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                "--window-size", "760,1560", "--screenshot", SHOT, "file://" + FUERA],
               env=env, capture_output=True, text=True, timeout=180)
srv.parar()

print("png:", SHOT, os.path.getsize(SHOT) if os.path.exists(SHOT) else "NO")
if VISUAL:
    print("modo visual: sin informe, la muestra se mira a ojo")
    raise SystemExit(0)

print()
print("=== paleta declarada en el entregable ===")
for r in ORDEN:
    print("  %-12s %-12s %s   (pedido: %s)" % (r, rareza[r], declarado[clase[r]], PEDIDO[r]))
print()
print("=== lo que dice el navegador ===")
print("-" * 72)
informe = srv.texto().strip()
print(informe)
print("-" * 72)
codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)

# ---------------------------------------------------------------------------
# 4b) EL MARCO DE LAS FOTOS: LO TRAE LA IMAGEN, NO EL CSS.
#
# En una captura del arbol parece que cada foto lleva un borde del color de su
# rareza. La auditoria de mas abajo dice que el borde CALCULADO de `.arbol .foto`
# es neutro (`#272c3a`), y es verdad: el CSS no pinta nada. Pero la captura
# tampoco mentia. Lo que faltaba era MEDIR LA IMAGEN, no el estilo.
#
# Las fotos de paleo.gg traen un marco de color YA DIBUJADO dentro del WebP, y
# ese color SI depende de la rareza. Asi que hay dos capas: la del CSS (neutra) y
# la del fichero (de color). Mirar solo la primera lleva a escribir en el LEEME
# una frase falsa: "las fotos no llevan el color de la rareza".
#
# Se mide el anillo exterior de cada imagen, se agrupa por rareza y se exige:
#   a) que las imagenes de una misma rareza COMPARTAN el color del marco. Si no,
#      el marco no puede leerse como "esto es de tal rareza" y hay que saberlo;
#   b) que el marco no CONTRADIGA la etiqueta. Un marco verde en una criatura
#      rara, o azul en una unica, seria una mentira visible en la misma fila.
# ---------------------------------------------------------------------------
import colorsys, collections, json
try:
    from PIL import Image
except ImportError:
    print()
    print("!! falta Pillow: sin el no se puede medir el marco de las fotos, y este")
    print("   paso NO se salta en silencio. Instala python-pillow.")
    raise SystemExit(1)

FOTO = os.path.join(RAIZ, "img")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")
ES = {"common": "común", "rare": "rara", "epic": "épica", "legendary": "legendaria",
      "unique": "única", "apex": "apex", "omega": "omega"}

def anillo(f, inset=1):
    """El perimetro interior de la imagen, que es donde vive el marco."""
    im = Image.open(f).convert("RGB")
    w, h = im.size
    px = []
    for x in range(inset, w - inset, 3):
        px.append(im.getpixel((x, inset)))
        px.append(im.getpixel((x, h - 1 - inset)))
    for y in range(inset, h - inset, 3):
        px.append(im.getpixel((inset, y)))
        px.append(im.getpixel((w - 1 - inset, y)))
    return px

def modal(px, cubo=32):
    """El color mas repetido del anillo, cuantizado para no partir por un pixel."""
    q = collections.Counter(tuple(v // cubo * cubo for v in p) for p in px)
    c, n = q.most_common(1)[0]
    return c, n / len(px)

def hsl(rgb):
    r, g, b = [v / 255 for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l

def saturacion(rgb):
    """Saturacion en HSV, no en HLS.

    Con HLS, un gris casi blanco como `#c0e0e0` sale con saturacion 0,34 y hue
    180° (cian), y el paso lo tomaba por un marco de color que "contradecia" el
    fucsia del omega. En HSV ese mismo color da 0,14: es un blanco sucio, y su
    tono no significa nada. Para decidir "esto es de color o es neutro" manda la
    saturacion HSV, que es la que no se dispara en los extremos de luminosidad.
    """
    r, g, b = [v / 255 for v in rgb]
    mx = max(r, g, b)
    return 0 if mx == 0 else (mx - min(r, g, b)) / mx

def familia(rgb):
    """(etiqueta de la familia, tono o None).

    Dos grises distintos (`#404040`, `#202020`) son la MISMA familia, y dos
    naranjas de distinta luminosidad (`#802000`, `#804000`) tambien. Agrupar por
    el hex exacto obligaba a exigir un 100% imposible: lo que importa es que el
    marco sea funcion de la rareza, y eso se lee por TONO.
    """
    s = saturacion(rgb)
    if s < 0.25:
        return "neutro", None
    h = hsl(rgb)[0]
    return "%d-%d°" % (int(h) // 30 * 30, int(h) // 30 * 30 + 30), h

def hexs(rgb):
    return "#%02x%02x%02x" % rgb

fallosMarco = 0
print()
print("=== el marco de las fotos: lo trae el WebP, no el CSS ===")
print("-" * 72)

if not os.path.exists(DATOS):
    print("!! no encuentro %s: sin el no hay rarezas que comparar" % DATOS)
    fallosMarco += 1
else:
    cr = json.load(open(DATOS, encoding="utf-8"))["criaturas"]
    print("%-11s %4s  %-22s %-8s %-9s %-9s %s" %
          ("rareza", "n", "marco modal de la imagen", "familia", "etiqueta", "tonos", "veredicto"))
    for r in ORDEN:
        us = [u for u, v in cr.items()
              if v.get("rareza") == r and os.path.exists(os.path.join(FOTO, u + ".webp"))]
        if not us:
            print("%-11s %4d  (sin imagenes)" % (ES[r], 0))
            fallosMarco += 1
            continue
        cnt = collections.Counter()
        fam = collections.Counter()
        for u in us:
            c, _ = modal(anillo(os.path.join(FOTO, u + ".webp")))
            cnt[c] += 1
            fam[familia(c)[0]] += 1
        (top, veces), = cnt.most_common(1)
        (famTop, famVeces), = fam.most_common(1)
        frac = famVeces / len(us)

        # el tono del marco y el de la etiqueta, comparados
        fm, hm = familia(top)
        he = hsl(tuple(int(declarado[clase[r]][i:i + 2], 16) for i in (1, 3, 5)))[0]
        if fm == "neutro" or saturacion(tuple(int(declarado[clase[r]][i:i + 2], 16)
                                              for i in (1, 3, 5))) < 0.25:
            d = None
            txt = "sin choque: " + ("marco neutro" if fm == "neutro" else "etiqueta neutra")
        else:
            d = min(abs(hm - he), 360 - abs(hm - he))
            txt = ("%d°" % round(d)) + ("" if d <= 60 else "  <-- SE CONTRADICEN")

        print("%-11s %4d  %-22s %-8s %-9s %-9s %s" %
              (ES[r], len(us), hexs(top), famTop, declarado[clase[r]],
               "-" if d is None else "%d°" % round(d), txt))

        # (a) el marco tiene que ser funcion de la rareza, no azar
        if frac < 0.6:
            print("      !! solo el %d%% de las %d imagenes comparte familia de marco: "
                  "ya no se puede leer como rareza" % (round(frac * 100), len(us)))
            fallosMarco += 1
        # (b) y no puede contradecir a la etiqueta
        if d is not None and d > 60:
            print("      !! el marco es %s (%d°) y la etiqueta %s (%d°): la misma fila "
                  "dice dos rarezas distintas" % (hexs(top), round(hm),
                                                  declarado[clase[r]], round(he)))
            fallosMarco += 1

    print("-" * 72)
    print("El borde del CSS es neutro en las tres vistas (lo comprueba la auditoria de")
    print("abajo). El color que se ve en las fotos viene del fichero de paleo.gg y sigue")
    print("las rarezas del JUEGO, que en tono coinciden con las que pidio n30. Apex y")
    print("omega no: sus imagenes traen marco negro y casi blanco, asi que la unica senal")
    print("de su rareza es la etiqueta.")

# ---------------------------------------------------------------------------
# 5) AUDITORIA sobre la pagina real.
#
# El paso anterior demuestra que las etiquetas se pintan bien en una pagina
# hecha a mano. Este comprueba que en la HERRAMIENTA no hay ningun otro sitio
# que se haya quedado con la paleta vieja: se abre el entregable, se recorren
# todos los elementos y se listan los que llevan alguno de los siete colores,
# agrupados por selector. Asi no hay que fiarse de mirar una captura.
# ---------------------------------------------------------------------------
srv2 = arrancar()

# Selectores que usan un color de rareza SIN ser una etiqueta de rareza. No es una
# lista de la compra: es la DECLARACION de una colision conocida. `--verde` y
# `--r-unica` son el mismo hex, y tambien `--ambar`/`--r-epica`, `--azul`/`--r-rara`
# y `--rojo`/`--r-legendaria`. Todo lo que este aqui significa "esta pintado con el
# color de una rareza, pero no habla de una rareza".
#
# Si aparece un selector nuevo que no este en esta lista, la prueba FALLA. Asi el
# dia que alguien pinte algo con --verde, sale aqui en vez de esconderse.
SEMANTICOS = [
    "nav button.on",      # pestana activa
    "h1 .v",              # version en la cabecera
    ".maxnivel .t",       # titulo del bloque de nivel maximo
    ".cifra .v",          # cifras grandes de los paneles (al/wa/ro)
    ".informe h3",        # titulo del informe
    ".aviso",             # borde izquierdo de los avisos
    "b", "td", "span.v",  # estilos en linea dentro del informe y las tablas
]

# Selectores cuyo color ES la rareza de la criatura que nombran. No son una
# colision: son la rareza dicha con el color en vez de con la etiqueta. Desde el
# 25-sep hay tres sitios asi (los nombres del informe, los de «Lleva a» y los de
# la tira de fotos), y se anaden a proposito porque el color ahorra la columna.
#
# Pero NO se dan por buenos: se comprueba, elemento a elemento, que el color
# calculado sea exactamente el de la rareza de la criatura a la que ese elemento
# lleva. Un nombre pintado del color de OTRA rareza es peor que una colision:
# afirma algo falso sobre la criatura.
NOMBRES = [".ir", ".tira-nm"]

auditoria_js = """
<script>
(function(){
  var COLORES = %(colores)s;              // hex -> nombre de la rareza
  var PILL = %(pill)s;                    // el color que deben tener las pildoras
  var SEMANTICOS = %(semanticos)s;        // selectores declarados como colision
  var NOMBRES = %(nombres)s;              // selectores cuyo color ES la rareza
  var HEX_CLASE = %(porClase)s;           // "rc-unica" -> el hex declarado en --r-unica
  var nombresBien = 0, nombresMal = [];
  var CHOQUES = %(choques)s;              // hex de rareza -> variables semanticas iguales
  var RES = [], FALLOS = 0;
  function ok(k, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + k + ": " + (d===undefined?"":d)); }
  function aHex(c){
    var m = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/.exec(c);
    if (!m) return null;
    return "#" + [1,2,3].map(function(i){ return ("0"+Number(m[i]).toString(16)).slice(-2); }).join("");
  }
  function sel(el){
    var s = el.tagName.toLowerCase();
    if (el.className && typeof el.className === "string")
      s += "." + el.className.trim().split(/\\s+/).join(".");
    return s;
  }
  try {
    /* Estado de partida propio: el perfil de Firefox conserva localStorage entre
       pasadas, y aqui hace falta que «Mis criaturas» tenga contenido para que la
       tira de fotos se pinte. Sin esto la tira no existe y sus nombres —que
       llevan el color de la rareza— no se auditan: la comprobacion pasaria sin
       mirar nada. */
    MIS = ["indoraptor", "tyrannosaurus_rex", "velociraptor"];
    pintarFotos();

    // un escenario que ensene etiquetas: hibrido con ingredientes de varias rarezas
    elegir("indoraptor");
    var na = document.getElementById("nivelAct"), at = document.getElementById("adnTengo");
    na.value = "21"; at.value = "0";
    na.dispatchEvent(new Event("input", {bubbles:true}));
    at.dispatchEvent(new Event("input", {bubbles:true}));
    var no = document.getElementById("nivelObj"); no.value = 30;
    no.dispatchEvent(new Event("input", {bubbles:true}));
    document.querySelector('nav button[data-t="arbol"]').click();
    pintarArbol();

    var cuenta = {}, etiquetas = 0, porSelector = {};
    var sinClasificar = [], porHex = {};
    document.querySelectorAll("*").forEach(function(el){
      var cs = getComputedStyle(el);
      var esEtiqueta = /(^|\\s)tag(\\s|$)/.test(el.className || "");
      /* Las CUATRO caras del borde, no solo la de arriba: el aviso pinta su borde
         IZQUIERDO, y mirando solo borderTopColor no aparecia nunca. */
      var lados = [["color", cs.color], ["borde-sup", cs.borderTopColor],
                   ["borde-der", cs.borderRightColor], ["borde-inf", cs.borderBottomColor],
                   ["borde-izq", cs.borderLeftColor]];
      var hexes = {};
      lados.forEach(function(par){
        var h = aHex(par[1]);
        if (!h || !COLORES[h]) return;
        hexes[h] = true;
        var k = sel(el) + "  [" + par[0] + " = " + COLORES[h] + "]";
        porSelector[k] = (porSelector[k] || 0) + 1;
      });
      var suyos = Object.keys(hexes);
      if (!suyos.length) return;
      if (esEtiqueta){ etiquetas++; return; }
      /* No es una etiqueta, pero lleva el color de una rareza. O esta declarado
         como colision conocida, o es un sitio nuevo que se ha colado: eso falla.
         Se cuenta el ELEMENTO una vez, no cada cara del borde: si no, un solo
         `td` sumaria cinco. Y se recogen TODOS los selectores que casan, no el
         primero: un elemento puede casar con `h1 .v` y con `span.v`, y quedarse
         con el primero haria que el otro figurase como "sin uso". */
      var quien = [];
      for (var i = 0; i < SEMANTICOS.length; i++){
        try { if (el.matches(SEMANTICOS[i])) quien.push(SEMANTICOS[i]); } catch(e){}
      }
      /* ¿Es un NOMBRE pintado con la rareza de su criatura? Entonces el color no
         es una colision: es la rareza dicha de otra forma. Y no se da por bueno:
         se comprueba contra la rareza REAL de la criatura a la que apunta. */
      var esNombre = false;
      for (var j = 0; j < NOMBRES.length; j++){
        try { if (el.matches(NOMBRES[j])) { esNombre = true; break; } } catch(e){}
      }
      if (esNombre){
        var ancla = el.closest("[data-ir]");
        var uu = ancla ? ancla.dataset.ir : null;
        var cr = uu ? C[uu] : null;
        var esp = cr ? HEX_CLASE["rc-" + CLASE[cr[1]]] : null;
        suyos.forEach(function(h){
          if (esp && h === esp) nombresBien++;
          else nombresMal.push(sel(el) + " " + h + " para " + (cr ? cr[0] + " (" + cr[1] + ", " + esp + ")" : "sin criatura"));
        });
        return;
      }
      suyos.forEach(function(h){
        var d = porHex[h] || (porHex[h] = {sel:{}, n:0});
        d.n++;
        if (quien.length) quien.forEach(function(s){ d.sel[s] = (d.sel[s] || 0) + 1; });
      });
      if (!quien.length) sinClasificar.push(sel(el) + "  [" + COLORES[suyos[0]] + "]" +
                                            "  <" + el.tagName.toLowerCase() +
                                            " class='" + (el.className||"") + "'>");
    });
    var claves = Object.keys(porSelector).sort();
    RES.push("--- elementos con un color de rareza, agrupados ---");
    claves.forEach(function(k){ RES.push("   " + porSelector[k] + " x  " + k); });

    /* Esta lista es la prueba de que la auditoria no se tapa a si misma: son los
       sitios que usan el color de una rareza para decir OTRA cosa. */
    RES.push("");
    RES.push("--- donde un color de rareza significa otra cosa (colision conocida) ---");
    if (!Object.keys(CHOQUES).length){
      RES.push("   ninguna: la paleta de rarezas no comparte hex con nada");
    } else {
      Object.keys(CHOQUES).sort().forEach(function(h){
        var d = porHex[h] || {sel:{}, n:0};
        var usos = Object.keys(d.sel).sort().map(function(s){ return s + " x" + d.sel[s]; });
        RES.push("   " + h + "  " + COLORES[h] + "  = " +
                 CHOQUES[h].map(function(v){ return "--" + v; }).join(", "));
        RES.push("        " + d.n + " elementos que no son etiquetas: " +
                 (usos.length ? usos.join(", ") : "ninguno en esta pantalla"));
      });
    }
    var noVistos = SEMANTICOS.filter(function(s){
      return !Object.keys(porHex).some(function(h){ return porHex[h].sel[s]; });
    });
    if (noVistos.length)
      RES.push("   (declarados que no salen en esta pantalla, no es un fallo: " +
               noVistos.join(", ") + ")");

    ok("hay etiquetas de rareza pintadas", etiquetas > 0, etiquetas + " etiquetas");
    /* Los nombres son el otro sitio donde el color dice la rareza. Se comprueba
       que cada uno lleve el de SU criatura, no solo que sea de la paleta. */
    RES.push("");
    RES.push("--- nombres pintados con el color de SU rareza ---");
    RES.push("   " + nombresBien + " nombres correctos" +
             (nombresMal.length ? " | MAL: " + nombresMal.slice(0,4).join(" ;; ") : ""));
    ok("hay nombres con el color de su rareza (informe, «Lleva a» y la tira)",
       nombresBien > 0, nombresBien + " nombres");
    ok("y todos llevan el color de la rareza de SU criatura, no de otra",
       nombresMal.length === 0,
       nombresMal.length ? nombresMal.slice(0,4).join(" ;; ") : "ninguno mal pintado");
    /* La tira de fotos tiene que estar en pantalla: si «Mis criaturas» estuviera
       vacia, sus nombres no existirian y la comprobacion de arriba pasaria sin
       mirar nada. */
    var tiraN = document.querySelectorAll("#misFotos .tira-nm").length;
    ok("la tira de fotos de «Mis criaturas» sale en esta pantalla", tiraN > 0,
       tiraN + " fotos con nombre");
    ok("no hay ningun elemento con color de rareza sin declarar",
       sinClasificar.length === 0,
       sinClasificar.length ? sinClasificar.slice(0,6).join(" ;; ")
                            : "ninguno fuera de la lista declarada");
    // Si algun sitio se quedo con la paleta vieja, saldria aqui con un color que
    // ya no esta en la lista, asi que no apareceria: por eso ademas se comprueba
    // que no quede NINGUNA etiqueta sin color de la paleta nueva.
    var sinColor = 0;
    document.querySelectorAll(".tag").forEach(function(t){
      var h = aHex(getComputedStyle(t).color);
      if (!h || !COLORES[h]) sinColor++;
    });
    ok("todas las etiquetas llevan un color de la paleta nueva", sinColor === 0,
       sinColor + " etiquetas con un color de fuera de la paleta");
    // El color de rareza no debe usarse como borde de nodo: los nodos van con el
    // borde neutro, o el arbol pareceria un semaforo.
    var nodosRaros = 0;
    document.querySelectorAll(".arbol .nodo").forEach(function(n){
      var h = aHex(getComputedStyle(n).borderTopColor);
      if (h && COLORES[h]) nodosRaros++;
    });
    ok("el borde del CSS de los nodos no usa el color de rareza", nodosRaros === 0,
       nodosRaros + " nodos con borde de color de rareza");
    /* Las fotos son el otro borde del arbol. OJO con lo que demuestra esto: mira el
       borde CALCULADO, es decir el CSS. Y el CSS es neutro. Pero en una captura se
       ve un marco de color, y es real: lo trae dibujado el WebP de origen. Aqui se
       demuestra solo la mitad de la historia; la otra mitad (que el marco del
       fichero sigue la rareza y no contradice a la etiqueta) la mide el paso 4b,
       sobre las imagenes. Las dos frases juntas son la verdad; cualquiera de las
       dos sola es una mentira util. */
    var fotos = document.querySelectorAll(".arbol .foto");
    var fotosRaras = 0, coloresFoto = {};
    fotos.forEach(function(f){
      var h = aHex(getComputedStyle(f).borderTopColor);
      coloresFoto[h] = (coloresFoto[h] || 0) + 1;
      if (h && COLORES[h]) fotosRaras++;
    });
    ok("hay fotos en el arbol", fotos.length > 0, fotos.length + " fotos");
    ok("el borde del CSS de las fotos no usa el color de rareza (el marco que se ve lo trae el WebP: paso 4b)",
       fotosRaras === 0,
       fotosRaras + " fotos con borde de color de rareza; medidos: " +
       Object.keys(coloresFoto).map(function(h){ return h + " x" + coloresFoto[h]; }).join(" | "));

    /* Las pildoras de estado son el otro sitio donde aparecia el verde y el ambar
       que ahora son de Unica y Epica. Tienen que usar un color propio: si alguna
       cae en la paleta de rarezas, vuelve el problema que se vino a arreglar. */
    var pildoras = document.querySelectorAll(".pill");
    var pillRara = [], coloresPill = {};
    pildoras.forEach(function(p){
      var h = aHex(getComputedStyle(p).color);
      if (h && COLORES[h]) pillRara.push(p.textContent.trim() + "=" + COLORES[h]);
      coloresPill[h] = (coloresPill[h] || 0) + 1;
    });
    ok("hay pildoras de estado pintadas", pildoras.length > 0, pildoras.length + " pildoras");
    ok("ninguna pildora usa un color de la paleta de rarezas", pillRara.length === 0,
       pillRara.length ? pillRara.slice(0,4).join(", ") : "ninguna");
    var distintos = Object.keys(coloresPill);
    ok("todas las pildoras comparten un unico color", distintos.length === 1,
       distintos.map(function(h){ return h + " x" + coloresPill[h]; }).join(" | "));
    ok("y es el color declarado en --pill", distintos.length === 1 && distintos[0] === PILL,
       (distintos[0] || "?") + " vs " + PILL);

    /* Las etiquetas llevan un fondo del 12%% de su propio color. Ese tinte sube la
       luminosidad JUSTO debajo del texto, asi que baja el contraste: hay que medirlo, no
       suponerlo. Se compone el fondo translucido sobre el primer ancestro opaco y se
       calcula el contraste WCAG real. Sin esto, el 12%% seria un numero puesto a ojo. */
    function lum(rgb){
      var c = rgb.map(function(v){ v /= 255;
        return v <= 0.04045 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
      return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
    }
    function parse(c){
      var m = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/.exec(c);
      if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
      /* Firefox serializa el resultado de color-mix() como `color(srgb r g b / a)`, con
         los canales en 0..1 y NO como rgba(). Sin esta rama, el fondo del tinte se leia
         como "sin fondo" y la prueba acusaba a la pagina de un fallo que era suyo. */
      var k = /color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?\\)/.exec(c);
      if (k) return [+k[1]*255, +k[2]*255, +k[3]*255, k[4] === undefined ? 1 : +k[4]];
      return null;
    }
    function fondoOpaco(el){
      var n = el;
      while (n && n !== document.documentElement){
        var b = parse(getComputedStyle(n).backgroundColor);
        if (b && b[3] >= 0.999) return b;
        n = n.parentElement;
      }
      return [15, 17, 23, 1];
    }
    var sinTinte = 0, peor = 99, peorDato = "", medidas = 0;
    document.querySelectorAll(".tag").forEach(function(t){
      var cs = getComputedStyle(t);
      var fg = parse(cs.color), bg = parse(cs.backgroundColor);
      if (!fg) return;
      if (!bg || bg[3] < 0.05){ sinTinte++; return; }
      var base = fondoOpaco(t.parentElement || t);
      var comp = [0,1,2].map(function(i){ return bg[i]*bg[3] + base[i]*(1-bg[3]); });
      var lf = lum(fg), lc = lum(comp);
      var c = (Math.max(lf,lc) + 0.05) / (Math.min(lf,lc) + 0.05);
      medidas++;
      if (c < peor){
        peor = c;
        peorDato = t.textContent.trim() + " " + cs.color +
                   " sobre rgb(" + comp.map(Math.round).join(",") + ")";
      }
    });
    ok("todas las etiquetas llevan el fondo de tinte", sinTinte === 0,
       sinTinte + " etiquetas sin fondo");
    ok("y el tinte no baja el contraste por debajo de AA (4,5:1)", peor >= 4.5,
       medidas ? "peor " + peor.toFixed(2) + ":1 en " + peorDato : "no se midio ninguna");
  } catch (e) {
    RES.push("!! EXCEPCION " + e.message + " @@ " + (e.stack||"").split("\\n")[1]);
    FALLOS++;
  }
  RES.push("");
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var d = document.createElement("pre"); d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:13px/1.45 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\\n");
  document.body.appendChild(d);
%(entrega)s
})();
</script>
""" % {"colores": "{" + ",".join('"%s":"%s"' % (declarado[clase[r]], rareza[r]) for r in ORDEN) + "}",
       "pill": '"%s"' % pill,
       "semanticos": "[" + ",".join('"%s"' % s for s in SEMANTICOS) + "]",
       "nombres": "[" + ",".join('"%s"' % s for s in NOMBRES) + "]",
       "porClase": esperado_js,
       "choques": "{" + ",".join(
           '"%s":[' % h + ",".join('"%s"' % v for v in vs) + "]"
           for h, vs in sorted(choques.items())) + "}",
       "entrega": srv2.js("__diag")}

# el entregable necesita img/ al lado
enlace = os.path.join(DIR, "img")
IMGDIR = os.path.join(RAIZ, "img")
if os.path.islink(enlace):
    if os.readlink(enlace) != IMGDIR:
        os.unlink(enlace)
elif os.path.isdir(enlace):
    import shutil
    shutil.rmtree(enlace, ignore_errors=True)
if not os.path.exists(enlace):
    os.symlink(IMGDIR, enlace)

AUD = os.path.join(DIR, "auditoria.html")
# Antes de abrir el navegador: si la auditoria no compila junto a la aplicacion
# —colision de nombres en el ambito global—, se quedaria sin correr y el sintoma
# seria «no entrego el informe», que no dice nada. Ver informe_browser.
_ok_scripts, _msg_scripts = comprobar_scripts(html + auditoria_js, "probar_rareza.py")
print(_msg_scripts)
if not _ok_scripts:
    raise SystemExit("!! " + _msg_scripts)
open(AUD, "w", encoding="utf-8").write(html + auditoria_js)
subprocess.run(["/usr/lib/firefox/firefox", "--headless", "--profile", PERFIL,
                "--window-size", "1400,2000",
                "--screenshot", os.path.join(DIR, "auditoria.png"), "file://" + AUD],
               env=env, capture_output=True, text=True, timeout=180)
srv2.parar()

print()
print("=== auditoria sobre la herramienta real ===")
print("-" * 72)
aud = srv2.texto().strip()
print(aud)
print("-" * 72)
codigo2, lineas2 = veredicto(aud)
for l in lineas2:
    print(l)
raise SystemExit(codigo or codigo2 or (1 if fallosMarco else 0))

