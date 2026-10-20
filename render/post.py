"""Acabado fotografico: vineteo de objetivo y grano de pelicula."""
import sys
from PIL import Image, ImageChops
import random, math

def finish(src, dst, vignette=0.26, grain=3.0, seed=11):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = im.load()

    # vineteo: caida radial suave, como la de un objetivo real a f/3.5
    cx, cy = w / 2.0, h / 2.0
    mx = math.hypot(cx, cy)
    for y in range(h):
        dy2 = (y - cy) ** 2
        for x in range(w):
            r = math.sqrt((x - cx) ** 2 + dy2) / mx
            f = 1.0 - vignette * (r ** 2.4)
            p = px[x, y]
            px[x, y] = (int(p[0] * f), int(p[1] * f), int(p[2] * f))

    # grano monocromo fino
    random.seed(seed)
    noise = Image.new("L", (w, h))
    npx = noise.load()
    for y in range(h):
        for x in range(w):
            npx[x, y] = max(0, min(255, 128 + int(random.gauss(0, grain))))
    im = ImageChops.overlay(im, Image.merge("RGB", (noise, noise, noise)))
    im.save(dst, quality=96)
    print("acabado ->", dst, im.size)

if __name__ == "__main__":
    finish(sys.argv[1], sys.argv[2],
           float(sys.argv[3]) if len(sys.argv) > 3 else 0.26)
