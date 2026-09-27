#!/usr/bin/env python3
"""
Downloads the images of the 518 creatures from the paleo.gg CDN and converts
them to high quality WebP.

Why WebP: the original PNG is 207x250 RGBA and weighs ~48 KB, badly compressed
(optipng gets nothing out of it, pngquant leaves it at 24 KB). In WebP q90 it
drops to ~16 KB with no visible difference at this size. 518 x 16 KB = ~8 MB,
which is manageable.

There is NO higher resolution available: @2x, /large/ and .webp were tried on
the CDN and all three return 403. 207x250 is the ceiling.

Usage:  python3 descargar_imagenes.py [--refetch]
"""
import json, os, sys, time, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(RAIZ, "img")
DATOS = os.path.join(RAIZ, "data", "jwa-3.22.json")
CDN = "https://cdn.paleo.gg/games/jwa/images/creature/%s.png"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")

CALIDAD = 90


def bajar(uuid, refetch=False):
    """Returns (status, source_bytes)."""
    salida = os.path.join(DEST, uuid + ".webp")
    if os.path.exists(salida) and not refetch and os.path.getsize(salida) > 0:
        return "cached", os.path.getsize(salida)
    req = urllib.request.Request(CDN % uuid, headers={"User-Agent": UA,
                                                      "Referer": "https://www.paleo.gg/"})
    with urllib.request.urlopen(req, timeout=45) as r:
        crudo = r.read()
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(crudo)).convert("RGBA")
    im.save(salida, "WEBP", quality=CALIDAD, method=6)
    return "new", os.path.getsize(salida)


def main():
    refetch = "--refetch" in sys.argv
    os.makedirs(DEST, exist_ok=True)
    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]
    uuids = sorted(cri.keys())
    print("creatures: %d -> %s" % (len(uuids), DEST))

    fallos, nuevos, cacheados, total = [], 0, 0, 0
    for i, u in enumerate(uuids, 1):
        try:
            est, n = bajar(u, refetch)
            total += n
            if est == "new":
                nuevos += 1
            else:
                cacheados += 1
        except Exception as e:
            fallos.append((u, str(e)[:90]))
        if i % 50 == 0 or i == len(uuids):
            print("  %3d/%d  new=%d cached=%d failed=%d  %.1f MB"
                  % (i, len(uuids), nuevos, cacheados, len(fallos), total / 1e6))
        if not refetch and est == "new":
            time.sleep(0.05)   # courtesy towards the CDN

    print()
    print("Total on disk: %.1f MB" % (total / 1e6))
    if fallos:
        print("FALLOS (%d):" % len(fallos))
        for u, e in fallos[:20]:
            print("  ", u, e)
        return 1
    print("No failures: the %d images are in img/." % len(uuids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
