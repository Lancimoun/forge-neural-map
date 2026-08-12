#!/usr/bin/env python3
"""Generate a 1200x630 social share card (og.png) for the FORGE Neural Map."""
import math, random, colorsys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

random.seed(11)
W, H = 1200, 630
img = Image.new("RGB", (W, H), (2, 3, 10))
draw = ImageDraw.Draw(img, "RGBA")

# ---- faint starfield ----
for _ in range(520):
    x, y = random.randint(0, W), random.randint(0, H)
    b = random.randint(40, 170)
    r = random.choice([1, 1, 1, 2])
    draw.ellipse([x, y, x + r, y + r], fill=(b, b, int(b * 1.15), 255))

# ---- glowing orbs (galaxy clusters) drawn on a separate layer + blur ----
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
orbs = [
    (250, 250, 150, 0.07),   # orange-ish (hue,sat handled below by index)
    (980, 180, 120, 0.55),
    (1040, 470, 160, 0.80),
    (170, 470, 110, 0.33),
    (640, 360, 90, 0.95),
    (760, 120, 70, 0.16),
    (430, 520, 80, 0.62),
]
for (cx, cy, rad, hue) in orbs:
    r0, g0, b0 = [int(c * 255) for c in colorsys.hls_to_rgb(hue, 0.6, 0.95)]
    steps = 26
    for i in range(steps, 0, -1):
        rr = rad * i / steps
        a = int(120 * (1 - i / steps) ** 1.6)
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(r0, g0, b0, a))
    # bright core
    gd.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(255, 255, 255, 230))
glow = glow.filter(ImageFilter.GaussianBlur(7))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
draw = ImageDraw.Draw(img, "RGBA")

# ---- fonts ----
def font(path_options, size):
    for p in path_options:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

BOLD = ["C:/Windows/Fonts/arialbd.ttf", "arialbd.ttf"]
BLACK = ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf"]
REG = ["C:/Windows/Fonts/arial.ttf", "arial.ttf"]
f_brand = font(BOLD, 26)
f_title = font(BLACK, 92)
f_sub = font(REG, 34)
f_foot = font(BOLD, 24)

# ---- gradient title via mask ----
title = "The mind of Maxima"
# measure
tb = draw.textbbox((0, 0), title, font=f_title)
tw, th = tb[2] - tb[0], tb[3] - tb[1]
mask = Image.new("L", (tw + 20, th + 40), 0)
ImageDraw.Draw(mask).text((10 - tb[0], 10 - tb[1]), title, font=f_title, fill=255)
grad = Image.new("RGB", (tw + 20, th + 40))
gp = grad.load()
c1 = (245, 166, 35)   # orange
c2 = (214, 41, 118)   # pink
for x in range(grad.width):
    t = x / grad.width
    gp_col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    for y in range(grad.height):
        gp[x, y] = gp_col
tx, ty = 78, 250
img.paste(grad, (tx, ty), mask)
draw = ImageDraw.Draw(img, "RGBA")

# ---- brand line ----
draw.text((80, 70), "FORGE", font=f_brand, fill=(255, 255, 255, 240))
bb = draw.textbbox((0, 0), "FORGE", font=f_brand)
draw.text((80 + (bb[2] - bb[0]) + 10, 70), "·  NEURAL MAP", font=f_brand, fill=(232, 92, 47, 235))

# ---- subtitle ----
draw.text((82, 378), "2,778 nodes  ·  7,295 connections  ·  157 systems", font=f_sub, fill=(220, 222, 235, 255))
draw.text((82, 420), "Maxima's entire mind, mapped in 3D.", font=f_sub, fill=(150, 156, 180, 255))

# ---- footer ----
draw.text((82, 540), "forge-neural-map.up.railway.app", font=f_foot, fill=(232, 92, 47, 255))

img.save("og.png", "PNG")
import os
print("og.png:", round(os.path.getsize("og.png") / 1024, 1), "KB", img.size)
