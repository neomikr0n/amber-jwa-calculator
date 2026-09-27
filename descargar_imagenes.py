#!/usr/bin/env python3
"""
Descarga las imagenes de las 518 criaturas desde el CDN de paleo.gg y las
convierte a WebP de alta calidad.

Por que WebP: el PNG original es de 207x250 RGBA y pesa ~48 KB, mal comprimido
(optipng no le saca nada, pngquant lo deja en 24 KB). En WebP q90 baja a ~16 KB
sin diferencia visible a este tamano. 518 x 16 KB = ~8 MB, que es manejable.

NO hay resolucion mayor disponible: se probaron @2x, /large/ y .webp en el CDN
y las tres devuelven 403. 207x250 es el techo.

Uso:  python3 descargar_imagenes.py [--refetch]
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
    """Devuelve (estado, bytes_origen)."""
    salida = os.path.join(DEST, uuid + ".webp")
    if os.path.exists(salida) and not refetch and os.path.getsize(salida) > 0:
        return "cache", os.path.getsize(salida)
    req = urllib.request.Request(CDN % uuid, headers={"User-Agent": UA,
                                                      "Referer": "https://www.paleo.gg/"})
    with urllib.request.urlopen(req, timeout=45) as r:
        crudo = r.read()
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(crudo)).convert("RGBA")
    im.save(salida, "WEBP", quality=CALIDAD, method=6)
    return "nuevo", os.path.getsize(salida)


def main():
    refetch = "--refetch" in sys.argv
    os.makedirs(DEST, exist_ok=True)
    cri = json.load(open(DATOS, encoding="utf-8"))["criaturas"]
    uuids = sorted(cri.keys())
    print("criaturas: %d -> %s" % (len(uuids), DEST))

    fallos, nuevos, cacheados, total = [], 0, 0, 0
    for i, u in enumerate(uuids, 1):
        try:
            est, n = bajar(u, refetch)
            total += n
            if est == "nuevo":
                nuevos += 1
            else:
                cacheados += 1
        except Exception as e:
            fallos.append((u, str(e)[:90]))
        if i % 50 == 0 or i == len(uuids):
            print("  %3d/%d  nuevos=%d cacheados=%d fallos=%d  %.1f MB"
                  % (i, len(uuids), nuevos, cacheados, len(fallos), total / 1e6))
        if not refetch and est == "nuevo":
            time.sleep(0.05)   # cortesia con el CDN

    print()
    print("Total en disco: %.1f MB" % (total / 1e6))
    if fallos:
        print("FALLOS (%d):" % len(fallos))
        for u, e in fallos[:20]:
            print("  ", u, e)
        return 1
    print("Sin fallos: las %d imagenes estan en img/." % len(uuids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
