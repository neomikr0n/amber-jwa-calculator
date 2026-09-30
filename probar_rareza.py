#!/usr/bin/env python3
"""
Shows the seven rarity tags together, and CHECKS that the browser paints them
the color the CSS says.

The CSS is not copied: it is extracted from the deliverable HTML, just like the checkers
extract the engine. What is seen here is literally what the user will see.

The check does not stop at reading the file: the **computed** color is read
(`getComputedStyle`) of each tag in the browser and compared with the value
declared in `--r-*`. Reading the file only proves the text is written;
reading the computed color proves the browser applies it.

And the report travels over synchronous XHR (see informe_browser.py), not inside a
PNG: if a tag comes out with no color, the script fails with exit code 1.

Generates /tmp/jwa-rareza/rareza.png

Usage:
    python3 probar_rareza.py            # checks the computed colors
    python3 probar_rareza.py --visual   # only the sample, without the report on top
                                        # (the report is a <pre> fixed to the full
                                        #  screen: if it is painted, it covers the sample
                                        #  and the shade cannot be judged by eye)
"""
import os, re, subprocess, sys

from informe_browser import arrancar, comprobar_scripts, veredicto

VISUAL = "--visual" in sys.argv

RAIZ = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(RAIZ, "amber-jwa-3.23.html")
DIR = "/tmp/jwa-rareza"
PERFIL = os.path.join(DIR, "perfil")
FUERA = os.path.join(DIR, "rareza.html")
SHOT = os.path.join(DIR, "rareza.png")

ORDEN = ["common", "rare", "epic", "legendary", "unique", "apex", "omega"]
# what n30 asked for, in words
PEDIDO = {"common": "white", "rare": "blue", "epic": "yellow", "legendary": "red",
          "unique": "green", "apex": "purple", "omega": "(not requested: fuchsia, to no "
                                                          "clash with the purple of the apex)"}

srv = arrancar()

html = open(HTML, encoding="utf-8").read()
# Pin the language for this run: the audit reads the Spanish rendering, and the
# app now boots in English. It goes in the <head> because that is where the app
# resolves the language.
PIN = ('<script>window.__lang = "es";'
       'try { localStorage.removeItem("jwa322.idioma"); } catch (e) {}</script>\n')
if "<head>" not in html:
    raise SystemExit("cannot find <head> to pin the language")
html = html.replace("<head>", "<head>\n" + PIN, 1)

# 1) the :root block. It is wrapped again in the selector: the group is only the
#    declarations, and pasting them loose into the sheet leaves them ownerless -> var()
#    does not resolve and everything comes out white. (It happened, and that is why there is a check now.)
m = re.search(r":root\s*\{(.*?)\}", html, re.S)
if not m:
    raise SystemExit("cannot find the :root block in the deliverable")
raiz = ":root{" + m.group(1) + "}"

# 2) the tag rules and the rarity color rules
reglas = []
for patron in (r"\.tag\s*\{[^}]*\}", r"\.rc-[a-z]+\s*\{[^}]*\}"):
    reglas += re.findall(patron, html)
if not any("rc-apex" in r for r in reglas):
    raise SystemExit("cannot find the .rc-* classes in the deliverable")

# 3) names, classes and declared values, taken from the deliverable itself
mm = re.search(r"const RAREZAS\s*=\s*\{(.*?)\}", html, re.S)
mc = re.search(r"const CLASE\s*=\s*\{(.*?)\}", html, re.S)
if not (mm and mc):
    raise SystemExit("cannot find RAREZAS/CLASE in the deliverable")
# The label may be a literal ("Apex") or an i18n() call, now that the interface
# is bilingual: i18n("Common"). What is being checked is the mapping key -> label
# and key -> CSS class, so the wrapper is optional here.
VAL = r'(\w+)\s*:\s*(?:i18n\(\s*)?"([^"]+)"'
rareza = dict(re.findall(VAL, mm.group(1)))
clase = dict(re.findall(r'(\w+)\s*:\s*"([^"]+)"', mc.group(1)))
declarado = dict(re.findall(r"--r-([a-z]+)\s*:\s*(#[0-9a-fA-F]{6})", raiz))

faltan = [r for r in ORDEN if r not in rareza or r not in clase or clase[r] not in declarado]
if faltan:
    raise SystemExit("missing rarities in the deliverable: %s" % faltan)

# the color of the status pills, which must NOT be in the rarity palette
m_pill = re.search(r"--pill\s*:\s*(#[0-9a-fA-F]{6})", raiz)
if not m_pill:
    raise SystemExit("cannot find --pill in the deliverable")
pill = m_pill.group(1)
if pill.lower() in [v.lower() for v in declarado.values()]:
    raise SystemExit("--pill (%s) matches a rarity color: %s"
                     % (pill, [k for k, v in declarado.items() if v.lower() == pill.lower()]))

# The semantic variables of the interface (green = "all good", amber = "missing",
# red = "bad", blue = "information"). They are compared with the rarity palette to
# know WHICH hexes are doing double duty. It is not an error in itself: it is a
# collision that must be seen, not hidden.
sem = dict(re.findall(r"--(verde|ambar|rojo|azul|violeta|pill)\s*:\s*(#[0-9a-fA-F]{6})", raiz))
choques = {}
for r in ORDEN:
    h = declarado[clase[r]].lower()
    iguales = sorted(k for k, v in sem.items() if v.lower() == h)
    if iguales:
        choques[h] = iguales

# The alternative theme, pasted under a class so that both palettes can live on
# the same page. It matters here for a measured reason: the tag tint is
# translucent, so its contrast depends on the background, and the two themes no
# longer share backgrounds (the default is deep black now). Measuring only the
# default would stop covering the lightest panel, which is «boring»'s.
m_b = re.search(r':root\[data-tema="boring"\]\s*\{(.*?)\}', html, re.S)
if not m_b:
    raise SystemExit("cannot find the [data-tema=boring] block in the deliverable")
BLOQUE_BORING = m_b.group(1)

def hex_var(bloque, nombre):
    mm = re.search(r"--%s\s*:\s*(#[0-9a-fA-F]{6})" % nombre, bloque)
    if not mm:
        raise SystemExit("cannot find --%s in a theme block" % nombre)
    return mm.group(1)

def rgb_de(h):
    h = h.lstrip("#")
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# The default theme is the one in `:root`; «boring» is the other block.
PANEL_DEF, PANEL_BOR = rgb_de(hex_var(m.group(1), "panel")), rgb_de(hex_var(BLOQUE_BORING, "panel"))
BG_DEF = rgb_de(hex_var(m.group(1), "bg"))
BG_DEF_ARR = "[" + BG_DEF.replace("rgb(", "").replace(")", "") + ",1]"

filas = "".join(
    '<tr><td class="nom">%s</td><td><span class="tag rc-%s">%s</span></td>'
    '<td><code>--r-%s: %s</code></td></tr>'
    % (rareza[r], clase[r], rareza[r], clase[r], declarado[clase[r]])
    for r in ORDEN
)
tira = " ".join('<span class="tag rc-%s">%s</span>' % (clase[r], rareza[r]) for r in ORDEN)

# 4) the harness: it reads the COMPUTED color of each tag and sends it.
#    The keys carry the `rc-` prefix, which is the class looked up in the DOM.
esperado_js = "{" + ",".join('"rc-%s":"%s"' % (clase[r], declarado[clase[r]]) for r in ORDEN) + "}"
nombres_js = "{" + ",".join('"rc-%s":"%s"' % (clase[r], rareza[r]) for r in ORDEN) + "}"
arnes = """
<script>
(function(){
  var RES = [], FALLOS = 0;
  function ok(k, c, d){ if (!c) FALLOS++; RES.push((c ? "OK   " : "FALLO") + " " + k + ": " + (d===undefined?"":d)); }
  var ESPERADO = %(esperado)s;
  var NOMBRE = %(nombres)s;
  var BG_DEF = %(bg_def_arr)s;   // the default theme's --bg, as [r,g,b,a]
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
    ok("the tag " + NOMBRE[cls] + " is painted " + esperado,
       real === esperado, "computed " + real + " (" + cs.color + ") vs declared " + esperado);
    ok("and it has a border, it is not loose text " + NOMBRE[cls],
       cs.borderTopStyle === "solid" && cs.borderTopWidth !== "0px",
       cs.borderTopWidth + " " + cs.borderTopStyle);
  });
  ok("the seven tags are present", Object.keys(vistos).length === 7,
     Object.keys(vistos).length + " of 7");
  // The panel background of EACH theme must resolve, or the sample would lie.
  var caja = document.querySelector(".caja");
  var cajaB = document.querySelector(".tema-boring .caja");
  ok("the DEFAULT theme's panel resolves (it does not come out white)",
     !!caja && getComputedStyle(caja).backgroundColor === "%(panel_def)s",
     caja ? getComputedStyle(caja).backgroundColor : "(no caja)");
  ok("and the «boring» theme's panel resolves as well",
     !!cajaB && getComputedStyle(cajaB).backgroundColor === "%(panel_bor)s",
     cajaB ? getComputedStyle(cajaB).backgroundColor : "(no boring section)");
  RES.push("");
  RES.push(FALLOS ? ("=== FALLOS: " + FALLOS + " ===") : "=== TODO OK ===");
  var d = document.createElement("pre"); d.id = "__diag";
  d.style.cssText = "position:fixed;inset:0;z-index:999999;background:#fff;color:#000;font:14px/1.5 monospace;padding:14px;margin:0;overflow:auto;white-space:pre-wrap";
  d.textContent = RES.join("\\n");
  document.body.appendChild(d);
%(entrega)s
})();
</script>
""" % {"esperado": esperado_js, "nombres": nombres_js,
       "panel_def": PANEL_DEF, "panel_bor": PANEL_BOR, "bg_def_arr": BG_DEF_ARR,
       "entrega": srv.js("__diag")}

# The same sample twice, once per theme. The second block hangs from
# `.tema-boring`, which is the alternative theme's variables under a class.
def cajas_de(nombre, bloque):
    p, p2, bg = (hex_var(bloque, n) for n in ("panel", "panel2", "bg"))
    return (
        '<div class="caja"><h2>%s panel &mdash; %s</h2><table>%s</table></div>'
        '<div class="caja p2"><h2>%s figure &mdash; %s</h2><table>%s</table></div>'
        '<div class="caja bg"><h2>%s body &mdash; %s</h2><table>%s</table></div>'
        '<div class="caja grande"><h2>%s &middot; at double size, to judge the shade</h2><p>%s</p></div>'
        % (nombre, p, filas, nombre, p2, filas, nombre, bg, filas, nombre, tira)
    )

CAJAS = (cajas_de("Default", m.group(1)) + "\n" +
         '<div class="tema-boring">' + cajas_de("Boring", BLOQUE_BORING) + "</div>")

pagina = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Rarity tags</title><style>
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
%(cajas)s
%(arnes)s
</body></html>""" % {"raiz": raiz + "\n.tema-boring{" + BLOQUE_BORING + "}",
                     "reglas": "\n".join(reglas), "cajas": CAJAS,
                     "arnes": "" if VISUAL else arnes}

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
    print("visual mode: no report, the sample is judged by eye")
    raise SystemExit(0)

print()
print("=== palette declared in the deliverable ===")
for r in ORDEN:
    print("  %-12s %-12s %s   (asked for: %s)" % (r, rareza[r], declarado[clase[r]], PEDIDO[r]))
print()
print("=== what the browser says ===")
print("-" * 72)
informe = srv.texto().strip()
print(informe)
print("-" * 72)
codigo, lineas = veredicto(informe)
for l in lineas:
    print(l)

# ---------------------------------------------------------------------------
# 4b) THE PHOTO FRAME: IT COMES FROM THE IMAGE, NOT THE CSS.
#
# In a screenshot of the tree it looks like each photo has a border of the color of its
# rarity. The audit further below says that the COMPUTED border of `.arbol .foto`
# is neutral (`#272c3a`), and that is true: the CSS paints nothing. But the screenshot
# was not lying either. What was missing was MEASURING THE IMAGE, not the style.
#
# The paleo.gg photos carry a color frame ALREADY DRAWN inside the WebP, and
# that color DOES depend on the rarity. So there are two layers: the CSS one (neutral) and
# the file one (colored). Looking only at the first leads to writing in the README
# a false sentence: "the photos do not carry the rarity color".
#
# The outer ring of each image is measured, grouped by rarity, and it is required:
#   a) that the images of the same rarity SHARE the frame color. If not,
#      the frame cannot be read as "this is of such rarity" and that must be known;
#   b) that the frame does not CONTRADICT the tag. A green frame on a rare
#      creature, or blue on a unique one, would be a lie visible in the same row.
# ---------------------------------------------------------------------------
import colorsys, collections, json
try:
    from PIL import Image
except ImportError:
    print()
    print("!! Pillow is missing: without it the photo frame cannot be measured, and this")
    print("   step is NOT skipped silently. Install python-pillow.")
    raise SystemExit(1)

FOTO = os.path.join(RAIZ, "img")
DATOS = os.path.join(RAIZ, "data", "jwa-3.23.json")
ES = {"common": "common", "rare": "rare", "epic": "epic", "legendary": "legendary",
      "unique": "unique", "apex": "apex", "omega": "omega"}

def anillo(f, inset=1):
    """The inner perimeter of the image, which is where the frame lives."""
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
    """The most repeated color of the ring, quantized so as not to split on a single pixel."""
    q = collections.Counter(tuple(v // cubo * cubo for v in p) for p in px)
    c, n = q.most_common(1)[0]
    return c, n / len(px)

def hsl(rgb):
    r, g, b = [v / 255 for v in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l

def saturacion(rgb):
    """Saturation in HSV, not in HLS.

    With HLS, an almost white gray such as `#c0e0e0` comes out with saturation 0.34 and hue
    180° (cyan), and the step took it for a color frame that "contradicted" the
    fuchsia of the omega. In HSV that same color gives 0.14: it is a dirty white, and its
    hue means nothing. To decide "this is colored or neutral" the HSV
    saturation rules, which is the one that does not spike at the extremes of luminosity.
    """
    r, g, b = [v / 255 for v in rgb]
    mx = max(r, g, b)
    return 0 if mx == 0 else (mx - min(r, g, b)) / mx

def familia(rgb):
    """(family label, hue or None).

    Two different grays (`#404040`, `#202020`) are the SAME family, and two
    oranges of different luminosity (`#802000`, `#804000`) as well. Grouping by
    the exact hex forced an impossible 100% requirement: what matters is that the
    frame be a function of the rarity, and that is read by HUE.
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
print("=== the photo frame: it comes from the WebP, not the CSS ===")
print("-" * 72)

if not os.path.exists(DATOS):
    print("!! %s not found: without it there are no rarities to compare" % DATOS)
    fallosMarco += 1
else:
    cr = json.load(open(DATOS, encoding="utf-8"))["criaturas"]
    print("%-11s %4s  %-22s %-8s %-9s %-9s %s" %
          ("rarity", "n", "modal frame of the image", "family", "tag", "hues", "verdict"))
    for r in ORDEN:
        us = [u for u, v in cr.items()
              if v.get("rareza") == r and os.path.exists(os.path.join(FOTO, u + ".webp"))]
        if not us:
            print("%-11s %4d  (no images)" % (ES[r], 0))
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

        # the frame hue and the tag hue, compared
        fm, hm = familia(top)
        he = hsl(tuple(int(declarado[clase[r]][i:i + 2], 16) for i in (1, 3, 5)))[0]
        if fm == "neutro" or saturacion(tuple(int(declarado[clase[r]][i:i + 2], 16)
                                              for i in (1, 3, 5))) < 0.25:
            d = None
            txt = "no clash: " + ("neutral frame" if fm == "neutro" else "neutral tag")
        else:
            d = min(abs(hm - he), 360 - abs(hm - he))
            txt = ("%d°" % round(d)) + ("" if d <= 60 else "  <-- THEY CONTRADICT EACH OTHER")

        print("%-11s %4d  %-22s %-8s %-9s %-9s %s" %
              (ES[r], len(us), hexs(top), famTop, declarado[clase[r]],
               "-" if d is None else "%d°" % round(d), txt))

        # (a) the frame must be a function of the rarity, not chance
        if frac < 0.6:
            print("      !! only %d%% of the %d images share a frame family: "
                  "it can no longer be read as rarity" % (round(frac * 100), len(us)))
            fallosMarco += 1
        # (b) and it cannot contradict the tag
        if d is not None and d > 60:
            print("      !! the frame is %s (%d°) and the tag %s (%d°): the same row "
                  "says two different rarities" % (hexs(top), round(hm),
                                                  declarado[clase[r]], round(he)))
            fallosMarco += 1

    print("-" * 72)
    print("The CSS border is neutral in the three views (the audit below checks")
    print("it). The color seen in the photos comes from the paleo.gg file and follows")
    print("the GAME rarities, which in hue match those n30 asked for. Apex and")
    print("omega do not: their images carry a black and almost white frame, so the only signal")
    print("of their rarity is the tag.")

# ---------------------------------------------------------------------------
# 5) AUDIT on the real page.
#
# The previous step proves that the tags are painted correctly on a
# hand-made page. This one checks that in the TOOL there is no other place
# that kept the old palette: the deliverable is opened, all the elements are
# walked and the ones carrying any of the seven colors are listed,
# grouped by selector. That way there is no need to trust looking at a screenshot.
# ---------------------------------------------------------------------------
srv2 = arrancar()

# Selectors that use a rarity color WITHOUT being a rarity tag. It is not a
# shopping list: it is the DECLARATION of a known collision. `--verde` and
# `--r-unica` are the same hex, and so are `--ambar`/`--r-epica`, `--azul`/`--r-rara`
# and `--rojo`/`--r-legendaria`. Everything here means "it is painted with the
# color of a rarity, but it does not talk about a rarity".
#
# If a new selector appears that is not in this list, the test FAILS. That way
# the day someone paints something with --verde, it shows up here instead of hiding.
SEMANTICOS = [
    "nav button.on",      # active tab
    "h1 .v",              # version in the header
    ".maxnivel .t",       # title of the max level block
    ".cifra .v",          # large panel figures (al/wa/ro)
    ".informe h3",        # report title
    ".aviso",             # left border of the notices
    "b", "td", "span.v",  # inline styles inside the report and the tables
]

# Selectors whose color IS the rarity of the creature they name. They are not a
# collision: they are the rarity said with color instead of with the tag. Since
# 25-sep there are three such places (the report names, those of «Lleva a» and those of
# the photo strip), and they are added on purpose because the color saves the column.
#
# But they are NOT taken for granted: it is checked, element by element, that the
# computed color be exactly that of the rarity of the creature that element
# links to. A name painted with the color of ANOTHER rarity is worse than a collision:
# it states something false about the creature.
NOMBRES = [".ir", ".tira-nm"]

auditoria_js = """
<script>
(function(){
  var COLORES = %(colores)s;              // hex -> rarity name
  var PILL = %(pill)s;                    // the color the pills must have
  var SEMANTICOS = %(semanticos)s;        // selectors declared as collision
  var NOMBRES = %(nombres)s;              // selectors whose color IS the rarity
  var HEX_CLASE = %(porClase)s;           // "rc-unica" -> the hex declared in --r-unica
  var nombresBien = 0, nombresMal = [];
  var CHOQUES = %(choques)s;              // rarity hex -> equal semantic variables
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
    /* Its own starting state: the Firefox profile keeps localStorage between
       runs, and here «Mis criaturas» needs content for the
       photo strip to be painted. Without this the strip does not exist and its names —which
       carry the rarity color— are not audited: the check would pass without
       looking at anything. */
    MIS = ["indoraptor", "tyrannosaurus_rex", "velociraptor"];
    pintarFotos();

    // a scenario that shows tags: hybrid with ingredients of several rarities
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
      /* The FOUR sides of the border, not only the top one: the notice paints its
         LEFT border, and looking only at borderTopColor it never appeared. */
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
      /* It is not a tag, but it carries a rarity color. Either it is declared
         as a known collision, or it is a new place that slipped in: that fails.
         The ELEMENT is counted once, not each border side: otherwise a single
         `td` would add five. And ALL matching selectors are collected, not the
         first one: an element can match `h1 .v` and `span.v`, and keeping
         the first would make the other show up as "unused". */
      var quien = [];
      for (var i = 0; i < SEMANTICOS.length; i++){
        try { if (el.matches(SEMANTICOS[i])) quien.push(SEMANTICOS[i]); } catch(e){}
      }
      /* Is it a NAME painted with the rarity of its creature? Then the color is not
         a collision: it is the rarity said another way. And it is not taken for granted:
         it is checked against the REAL rarity of the creature it points to. */
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
          else nombresMal.push(sel(el) + " " + h + " for " + (cr ? cr[0] + " (" + cr[1] + ", " + esp + ")" : "no creature"));
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
    RES.push("--- elements with a rarity color, grouped ---");
    claves.forEach(function(k){ RES.push("   " + porSelector[k] + " x  " + k); });

    /* This list is the proof that the audit does not cover itself up: they are the
       places that use the color of a rarity to say ANOTHER thing. */
    RES.push("");
    RES.push("--- where a rarity color means something else (known collision) ---");
    if (!Object.keys(CHOQUES).length){
      RES.push("   none: the rarity palette does not share a hex with anything");
    } else {
      Object.keys(CHOQUES).sort().forEach(function(h){
        var d = porHex[h] || {sel:{}, n:0};
        var usos = Object.keys(d.sel).sort().map(function(s){ return s + " x" + d.sel[s]; });
        RES.push("   " + h + "  " + COLORES[h] + "  = " +
                 CHOQUES[h].map(function(v){ return "--" + v; }).join(", "));
        RES.push("        " + d.n + " elements that are not tags: " +
                 (usos.length ? usos.join(", ") : "none on this screen"));
      });
    }
    var noVistos = SEMANTICOS.filter(function(s){
      return !Object.keys(porHex).some(function(h){ return porHex[h].sel[s]; });
    });
    if (noVistos.length)
      RES.push("   (declared ones that do not appear on this screen, not a failure: " +
               noVistos.join(", ") + ")");

    ok("there are painted rarity tags", etiquetas > 0, etiquetas + " tags");
    /* The names are the other place where the color says the rarity. It is checked
       that each one carries that of ITS creature, not just that it is from the palette. */
    RES.push("");
    RES.push("--- names painted with the color of THEIR rarity ---");
    RES.push("   " + nombresBien + " correct names" +
             (nombresMal.length ? " | BAD: " + nombresMal.slice(0,4).join(" ;; ") : ""));
    ok("there are names with the color of their rarity (report, «Lleva a» and the strip)",
       nombresBien > 0, nombresBien + " names");
    ok("and all of them carry the color of the rarity of THEIR creature, not another",
       nombresMal.length === 0,
       nombresMal.length ? nombresMal.slice(0,4).join(" ;; ") : "none badly painted");
    /* The photo strip must be on screen: if «Mis criaturas» were
       empty, its names would not exist and the check above would pass without
       looking at anything. */
    var tiraN = document.querySelectorAll("#misFotos .tira-nm").length;
    ok("the photo strip of «Mis criaturas» appears on this screen", tiraN > 0,
       tiraN + " photos with a name");
    ok("there is no element with an undeclared rarity color",
       sinClasificar.length === 0,
       sinClasificar.length ? sinClasificar.slice(0,6).join(" ;; ")
                            : "none outside the declared list");
    // If some place kept the old palette, it would show up here with a color that
    // is no longer in the list, so it would not appear: that is also why it is checked
    // that NO tag is left without a color from the new palette.
    var sinColor = 0;
    document.querySelectorAll(".tag").forEach(function(t){
      var h = aHex(getComputedStyle(t).color);
      if (!h || !COLORES[h]) sinColor++;
    });
    ok("all tags carry a color from the new palette", sinColor === 0,
       sinColor + " tags with a color from outside the palette");
    // The rarity color must not be used as a node border: the nodes go with the
    // neutral border, or the tree would look like a traffic light.
    var nodosRaros = 0;
    document.querySelectorAll(".arbol .nodo").forEach(function(n){
      var h = aHex(getComputedStyle(n).borderTopColor);
      if (h && COLORES[h]) nodosRaros++;
    });
    ok("the CSS border of the nodes does not use the rarity color", nodosRaros === 0,
       nodosRaros + " nodes with a rarity-colored border");
    /* The photos are the other border of the tree. CAREFUL with what this proves: it looks at the
       COMPUTED border, that is, the CSS. And the CSS is neutral. But in a screenshot
       a color frame is seen, and it is real: the source WebP brings it drawn. Here
       only half the story is proven; the other half (that the frame of the
       file follows the rarity and does not contradict the tag) is measured by step 4b,
       on the images. The two sentences together are the truth; either of the
       two alone is a useful lie. */
    var fotos = document.querySelectorAll(".arbol .foto");
    var fotosRaras = 0, coloresFoto = {};
    fotos.forEach(function(f){
      var h = aHex(getComputedStyle(f).borderTopColor);
      coloresFoto[h] = (coloresFoto[h] || 0) + 1;
      if (h && COLORES[h]) fotosRaras++;
    });
    ok("there are photos in the tree", fotos.length > 0, fotos.length + " photos");
    ok("the CSS border of the photos does not use the rarity color (the frame that is seen comes from the WebP: step 4b)",
       fotosRaras === 0,
       fotosRaras + " photos with a rarity-colored border; measured: " +
       Object.keys(coloresFoto).map(function(h){ return h + " x" + coloresFoto[h]; }).join(" | "));

    /* The status pills are the other place where the green and amber appeared
       that now belong to Unique and Epic. They must use their own color: if any
       falls into the rarity palette, the problem that was being fixed comes back. */
    var pildoras = document.querySelectorAll(".pill");
    var pillRara = [], coloresPill = {};
    pildoras.forEach(function(p){
      var h = aHex(getComputedStyle(p).color);
      if (h && COLORES[h]) pillRara.push(p.textContent.trim() + "=" + COLORES[h]);
      coloresPill[h] = (coloresPill[h] || 0) + 1;
    });
    ok("there are painted status pills", pildoras.length > 0, pildoras.length + " pills");
    ok("no pill uses a color from the rarity palette", pillRara.length === 0,
       pillRara.length ? pillRara.slice(0,4).join(", ") : "none");
    var distintos = Object.keys(coloresPill);
    ok("all pills share a single color", distintos.length === 1,
       distintos.map(function(h){ return h + " x" + coloresPill[h]; }).join(" | "));
    ok("and it is the color declared in --pill", distintos.length === 1 && distintos[0] === PILL,
       (distintos[0] || "?") + " vs " + PILL);

    /* The tags carry a 12%% background of their own color. That tint raises the
       luminosity RIGHT under the text, so it lowers the contrast: it must be measured, not
       assumed. The translucent background is composited over the first opaque ancestor and the
       real WCAG contrast is computed. Without this, the 12%% would be a number picked by eye. */
    function lum(rgb){
      var c = rgb.map(function(v){ v /= 255;
        return v <= 0.04045 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); });
      return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2];
    }
    function parse(c){
      var m = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/.exec(c);
      if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
      /* Firefox serializes the result of color-mix() as `color(srgb r g b / a)`, with
         the channels in 0..1 and NOT as rgba(). Without this branch, the tint background was read
         as "no background" and the test blamed the page for a fault that was its own. */
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
      return BG_DEF;
    }
    /* The tint is translucent, so its contrast depends on the panel behind it.
       The two themes no longer share backgrounds (the default is deep black
       now), and the lighter panel —the one that lowers the contrast— is
       «boring»'s. Measuring only the theme that happens to be painted would
       stop covering it, so BOTH are measured on the real tool: the theme is
       switched, the same tags are measured again, and the default is restored. */
    function tinteDe(){
      var sinTinte = 0, peor = 99, peorDato = "", n = 0;
      document.querySelectorAll(".tag").forEach(function(t){
        var cs = getComputedStyle(t);
        var fg = parse(cs.color), bg = parse(cs.backgroundColor);
        if (!fg) return;
        if (!bg || bg[3] < 0.05){ sinTinte++; return; }
        var base = fondoOpaco(t.parentElement || t);
        var comp = [0,1,2].map(function(i){ return bg[i]*bg[3] + base[i]*(1-bg[3]); });
        var lf = lum(fg), lc = lum(comp);
        var c = (Math.max(lf,lc) + 0.05) / (Math.min(lf,lc) + 0.05);
        n++;
        if (c < peor){
          peor = c;
          peorDato = t.textContent.trim() + " " + cs.color +
                     " sobre rgb(" + comp.map(Math.round).join(",") + ")";
        }
      });
      return {sinTinte: sinTinte, peor: peor, peorDato: peorDato, n: n};
    }
    ponerTema("yellow");
    var tinteDef = tinteDe();
    ponerTema("boring");
    var tinteBor = tinteDe();
    /* Back to the default: the screenshot of this run is the theme the user
       gets out of the box. */
    ponerTema("yellow");
    ok("all tags carry the tint background in both themes",
       tinteDef.sinTinte === 0 && tinteBor.sinTinte === 0,
       "Default " + tinteDef.sinTinte + ", Boring " + tinteBor.sinTinte + " without background");
    ok("both themes were measured, not only one",
       tinteDef.n > 0 && tinteBor.n > 0,
       "Default " + tinteDef.n + " tags, Boring " + tinteBor.n);
    ok("and the tint does not lower the contrast below AA (4.5:1) in the DEFAULT theme",
       tinteDef.peor >= 4.5,
       tinteDef.n ? "worst " + tinteDef.peor.toFixed(2) + ":1 in " + tinteDef.peorDato
                  : "none was measured");
    ok("nor in the «boring» theme", tinteBor.peor >= 4.5,
       tinteBor.n ? "worst " + tinteBor.peor.toFixed(2) + ":1 in " + tinteBor.peorDato
                  : "none was measured");
  } catch (e) {
    RES.push("!! EXCEPTION " + e.message + " @@ " + (e.stack||"").split("\\n")[1]);
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

# the deliverable needs img/ next to it
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
# Before opening the browser: if the audit does not compile alongside the application
# —name collision in the global scope—, it would not run and the symptom
# would be «it did not deliver the report», which says nothing. See informe_browser.
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
print("=== audit on the real tool ===")
print("-" * 72)
aud = srv2.texto().strip()
print(aud)
print("-" * 72)
codigo2, lineas2 = veredicto(aud)
for l in lineas2:
    print(l)
raise SystemExit(codigo or codigo2 or (1 if fallosMarco else 0))

