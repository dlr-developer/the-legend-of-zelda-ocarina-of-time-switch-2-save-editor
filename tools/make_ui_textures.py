"""Make the pause view's UI textures (our own procedural art): a seamless carved-wood panel, the top bar strip
with a scrolled lower edge, and the pause-menu button icon.

usage: python tools/make_ui_textures.py [out_dir]   (default: assets/switch2_ui)
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                          "assets", "switch2_ui")
random.seed(1311)


def periodic_noise(w, h, octaves=((4, 1.0), (9, 0.5), (23, 0.25)), stretch=(1.0, 6.0)):
    """Seamless value pattern from sums of sines with integer frequencies (tiles in both directions)."""
    phases = [(random.uniform(0, 6.28), random.uniform(0, 6.28), random.randint(1, 3)) for _ in octaves]
    img = Image.new("L", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = 0.0
            for (f, amp), (p1, p2, k) in zip(octaves, phases):
                fx = f / stretch[0]
                fy = max(1, round(f / stretch[1]))
                v += amp * math.sin(2 * math.pi * (fy * y / h) + p1 + 1.7 * math.sin(2 * math.pi * k * x / w + p2)) \
                    * math.cos(2 * math.pi * round(fx) * x / w * 0.0 + p2)
            px[x, y] = int(max(0, min(255, 128 + 60 * v)))
    return img


def wood(w, h, dark, light, rings=7):
    """Seamless wood grain running horizontally."""
    g = Image.new("RGB", (w, h))
    px = g.load()
    ph = [random.uniform(0, 6.28) for _ in range(4)]
    for y in range(h):
        for x in range(w):
            t = (rings * y / h
                 + 0.10 * math.sin(2 * math.pi * 2 * x / w + ph[0])
                 + 0.05 * math.sin(2 * math.pi * 5 * x / w + ph[1])
                 + 0.03 * math.sin(2 * math.pi * 13 * x / w + 3 * y / h * 2 * math.pi + ph[2]))
            v = 0.5 + 0.5 * math.sin(2 * math.pi * t)
            v = v ** 1.8
            fine = 0.5 + 0.5 * math.sin(2 * math.pi * (31 * y / h + 0.6 * math.sin(2 * math.pi * 3 * x / w + ph[3])))
            m = 0.75 * v + 0.25 * fine
            px[x, y] = tuple(int(dark[i] + (light[i] - dark[i]) * m) for i in range(3))
    return g


def carve(img, paths, width, alpha=70):
    """Emboss curves into an image: a dark groove with a light rim below/right (light from the top left)."""
    w, h = img.size
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for pts in paths:
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                p = [(x + ox, y + oy) for x, y in pts]
                d.line([(x + 2, y + 2) for x, y in p], fill=(255, 225, 180, alpha), width=width)
                d.line(p, fill=(10, 5, 2, alpha + 40), width=width)
    shade = shade.filter(ImageFilter.GaussianBlur(1.2))
    out = img.convert("RGBA")
    out.alpha_composite(shade)
    return out


def scroll_curve(cx, cy, r, turns=1.6, start=0.0, sign=1, n=80):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = start + sign * t * turns * 2 * math.pi
        rr = r * (1 - 0.82 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def panel(size=512):
    base = wood(size, size, dark=(40, 28, 17), light=(62, 44, 28), rings=11)
    paths = []
    # Pairs of facing scrolls joined by a wave, repeated so the tile stays seamless.
    for cx, cy in ((128, 128), (384, 384)):
        paths.append(scroll_curve(cx - 52, cy, 46, start=0.0, sign=1))
        paths.append(scroll_curve(cx + 52, cy, 46, start=math.pi, sign=-1))
        paths.append([(cx - 52 + 46 * math.cos(a / 20 * math.pi), cy - 46 - 10 * math.sin(a / 20 * math.pi * 2))
                      for a in range(0, 21)])
    for cx, cy in ((384, 128), (128, 384)):
        paths.append([(cx + 70 * math.cos(2 * math.pi * i / 48), cy + 70 * math.sin(2 * math.pi * i / 48)) for i in range(49)])
        paths.append(scroll_curve(cx, cy, 40, turns=1.2, start=math.pi / 2, sign=1))
    return carve(base, paths, 7, alpha=55)


def topbar(w=1920, h=120):
    band = wood(w, h, dark=(95, 64, 36), light=(150, 108, 64), rings=3).convert("RGBA")
    # Darken towards the bottom of the band.
    grad = Image.new("L", (1, h))
    for y in range(h):
        grad.putpixel((0, y), int(70 * (y / h) ** 1.5))
    shade = Image.new("RGBA", (w, h), (20, 10, 4, 255))
    shade.putalpha(grad.resize((w, h)))
    band.alpha_composite(shade)
    # Scrolled lower edge: the band ends in a wave with curls; everything below is transparent.
    edge_y = 92
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    poly = [(0, 0), (w, 0)]
    period = 160
    for x in range(w, -1, -4):
        y = edge_y + 9 * math.sin(2 * math.pi * x / period)
        poly.append((x, y))
    md.polygon(poly, fill=255)
    for cx in range(period // 4, w, period):
        md.ellipse((cx - 16, edge_y - 4, cx + 16, edge_y + 26), fill=255)
    band.putalpha(mask)
    d = ImageDraw.Draw(band)
    for cx in range(period // 4, w, period):
        curl = scroll_curve(cx, edge_y + 11, 12, turns=1.3, start=-math.pi / 2, sign=1, n=40)
        d.line(curl, fill=(40, 22, 10, 230), width=3)
    rim = [(x, edge_y + 9 * math.sin(2 * math.pi * x / period) - 3) for x in range(0, w + 1, 4)]
    d.line(rim, fill=(200, 160, 105, 160), width=2)
    return band


def button_icon(size=24):
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = s // 10
    d.rounded_rectangle((pad, pad + s // 12, s - pad, s - pad - s // 12), radius=s // 7, outline=(255, 255, 255, 255),
                        width=s // 12)
    bw = s // 9
    for x in (s // 2 - bw - s // 14, s // 2 + s // 14):
        d.rounded_rectangle((x, s // 3, x + bw, s - s // 3), radius=bw // 3, fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    panel().save(os.path.join(OUT, "ui_panel_wood.png"))
    topbar().save(os.path.join(OUT, "ui_topbar.png"))
    button_icon().save(os.path.join(OUT, "ui_button_pause.png"))
    print("wrote ui_panel_wood.png, ui_topbar.png, ui_button_pause.png to", OUT)


if __name__ == "__main__":
    main()
