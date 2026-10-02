#!/usr/bin/env python3
"""
Generates the three SVGs the README shows: the «Amber» wordmark in two variants
and the light-background copy of the hexagon mark.

WHY THE TEXT IS OUTLINED, AND NOT `<text>`
------------------------------------------
An SVG referenced from a README is painted with the fonts the VISITOR has. This
machine has neither Helvetica nor Arial, so the wordmark would be rendered in
whatever the reader's system falls back to — and on a machine with none of them,
in something else again. The glyphs are therefore converted to paths with
fontTools, using Liberation Sans Bold, which is metric-compatible with Arial and
is what the lockup was drawn with.

WHY THERE ARE TWO VARIANTS
--------------------------
The bright amber of the app is illegible on white: its lightest stop, `#ffe7b3`,
measures 1.21:1 against white. And a dark ramp disappears on GitHub's dark
background. GitHub allows choosing with `<picture>` + `prefers-color-scheme`, and
that survives its renderer (measured with `gh api --method POST /markdown`). The
colours of each ramp are CHOSEN BY MEASURING CONTRAST, not by eye: the light ramp
is the same amber brought down in luminance until all three stops pass 3:1 on
white, which is the threshold for large text.

THE LIGHT LOGO IS DERIVED, NOT REDRAWN
--------------------------------------
`logo-claro.svg` is `img/logo.svg` with its gradient stops rewritten. Deriving it
means the shape cannot drift: if the mark ever changes, running this again brings
the light copy with it.

THIS IS NOT PART OF THE BUILD OR OF THE TESTS
---------------------------------------------
It needs `fontTools`, which is a third-party dependency, and this project has
none anywhere else: `build.py` and the fourteen tests run on a bare Python 3.
This script is run by hand, and only when the README artwork has to change. The
three SVGs it writes are committed, so a clone does not need it.

    pip install fonttools          # only for this script
    python3 img/readme/generar-titulo.py [output_dir] [path_to_img/logo.svg]
"""
import os
import re
import sys

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FONT = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
TEXT = "Amber"
WHITE = (255, 255, 255)     # GitHub, light theme
DARK = (13, 17, 23)         # GitHub, dark theme (#0d1117)

# The two ramps, both running the same way as the app's logo (light at the top).
RAMPS = {
    # dark theme: the app's own amber, as it is
    "oscuro": [("0", "#ffe7b3"), (".42", "#ffb738"), ("1", "#ef6a10")],
    # light theme: the same amber brought down in luminance until all THREE
    # stops pass 3:1 on white (measured: 3.09 / 4.61 / 6.19)
    "claro": [("0", "#d97b06"), (".42", "#b35f04"), ("1", "#9c4a05")],
}


def luminance(rgb):
    def channel(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def glyphs(font, text):
    """Places the glyphs and returns (paths in font units, bounding box)."""
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    kern = {}
    if "kern" in font:
        for st in font["kern"].kernTables:
            kern.update(st.kernTable)

    placed, x, previous = [], 0, None
    for ch in text:
        gn = cmap[ord(ch)]
        if previous is not None:
            x += kern.get((previous, gn), 0)
        placed.append((gn, x))
        x += gs[gn].width
        previous = gn

    x0 = y0 = 10 ** 9
    x1 = y1 = -10 ** 9
    for gn, dx in placed:
        bp = BoundsPen(gs)
        gs[gn].draw(bp)
        if bp.bounds:
            bx0, by0, bx1, by1 = bp.bounds
            x0, y0 = min(x0, bx0 + dx), min(y0, by0)
            x1, y1 = max(x1, bx1 + dx), max(y1, by1)

    # SVG has Y pointing down: the glyph is flipped and placed where it belongs.
    paths = []
    for gn, dx in placed:
        pen = SVGPathPen(gs)
        gs[gn].draw(TransformPen(pen, Transform(1, 0, 0, -1, dx, 0)))
        d = pen.getCommands()
        if d:
            paths.append(d)
    return paths, (x0, -y1, x1 - x0, y1 - y0)


def svg(paths, box, stops, name):
    x, y, w, h = box
    stops_xml = "".join(
        '<stop offset="%s" stop-color="%s"/>' % (o, c) for o, c in stops)
    gradient = (
        '<linearGradient id="%s" gradientUnits="userSpaceOnUse" '
        'x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>'
        % (name, x, y, x, y + h, stops_xml))
    body = "".join('<path d="%s"/>' % d for d in paths)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s" '
        'role="img" aria-label="%s"><defs>%s</defs>'
        '<g fill="url(#%s)">%s</g></svg>\n'
        % (x, y, w, h, TEXT, gradient, name, body))


def light_logo(source, stops):
    """The app's hexagon with the light ramp, for a white background."""
    with open(source, encoding="utf-8") as fh:
        s = fh.read()
    colours = [c for _, c in stops]
    done = []

    def swap(m):
        # If the SVG carries more stops than the ramp has colours, this has to
        # stop HERE: further down it is too late, and the failure comes out as an
        # IndexError that explains nothing.
        if len(done) >= len(colours):
            raise SystemExit(
                "%s has more gradient stops than the ramp has colours (%d)"
                % (source, len(colours)))
        colour = colours[len(done)]
        done.append(colour)
        return 'stop-color="%s"' % colour

    # One stop per colour of the ramp, IN ORDER. Counting the substitutions and
    # demanding there are exactly three is what stops this passing in a vacuum:
    # the first version rewrote the same stop three times and left the gradient
    # broken, and the light logo came out with the colours run together.
    s = re.sub(r'stop-color="[^"]*"', swap, s)
    if len(done) != len(colours):
        raise SystemExit(
            "%s has %d stops and the ramp brings %d: they do not match"
            % (source, len(done), len(colours)))
    return s


def main():
    destination = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "img", "readme")
    source = (sys.argv[2] if len(sys.argv) > 2
              else os.path.join(RAIZ, "img", "logo.svg"))
    if not os.path.exists(FONT):
        raise SystemExit("the font is not there: %s" % FONT)
    if not os.path.exists(source):
        raise SystemExit("the logo is not there: %s" % source)

    font = TTFont(FONT)
    paths, box = glyphs(font, TEXT)
    print("wordmark box (font units): %s" % (box,))

    print()
    print("contrast of every stop (target: >=3 on white, for large text)")
    print("%-10s %-9s %8s %8s" % ("variant", "colour", "vs white", "vs dark"))
    for variant, stops in RAMPS.items():
        for _, colour in stops:
            rgb = hex_to_rgb(colour)
            print("%-10s %-9s %8.2f %8.2f"
                  % (variant, colour, contrast(rgb, WHITE), contrast(rgb, DARK)))

    print()
    for variant, stops in RAMPS.items():
        path = os.path.join(destination, "titulo-%s.svg" % variant)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg(paths, box, stops, "ambar" + variant.capitalize()))
        print("wrote %s" % path)

    path = os.path.join(destination, "logo-claro.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(light_logo(source, RAMPS["claro"]))
    print("wrote %s (derived from %s)" % (path, source))


if __name__ == "__main__":
    main()
