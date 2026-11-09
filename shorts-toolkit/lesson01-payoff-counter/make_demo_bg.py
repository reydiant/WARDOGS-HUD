#!/usr/bin/env python3
"""Placeholder footage frame for testing overlays: dark gradient, vignette, crosshair."""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H = 1080, 1920
out = sys.argv[1]
y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
x = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
base = np.stack([14 + 20 * y, 16 + 18 * y, 28 + 30 * y], -1) * np.ones((H, W, 1), np.float32)
# a few bright patches so we can check text readability on busy / light footage
yy, xx = np.mgrid[0:H, 0:W]
for cx, cy, r, c in [(220, 330, 260, (210, 200, 170)), (840, 760, 220, (120, 150, 200)), (540, 1100, 320, (180, 120, 90))]:
    m = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1)[..., None] ** 1.5
    base = base * (1 - m) + np.array(c, np.float32) * m
vig = 1 - 0.55 * (x ** 2 + ((y - 0.5) * 1.6) ** 2)
img = Image.fromarray(np.clip(base * vig[..., None] if vig.ndim == 2 else base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
cx, cy = W // 2, H // 2
for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
    d.line([(cx + dx * 18, cy + dy * 18), (cx + dx * 60, cy + dy * 60)], fill=(240, 240, 240), width=4)
d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(240, 60, 60))
f = ImageFont.truetype(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "fonts", "Poppins-Medium.ttf"), 30)
d.text((60, 1660), "DEMO BACKGROUND - numbers are placeholders", font=f, fill=(200, 200, 215))
img.save(out)
