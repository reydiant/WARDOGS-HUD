#!/usr/bin/env python3
"""
kinetic_text.py - words that slam in on the beat (backlog #5).

Renders short phone-readable words as a transparent 1080x1920 60 fps overlay.
Each word slams in with an overshoot, shakes for a moment, pulses on every beat
while it is on screen, then exits fast.

  python3 kinetic_text.py words.json --out outdir

words.json:
  {
    "bpm": 128,                 // from music_bed.py (use the same bpm as the music)
    "fps": 60,
    "duration": 6.0,            // seconds; default = last word end
    "words": [
      {"text": "$0",        "beat": 0,   "len_beats": 1,   "style": "slam"},
      {"text": "ONE LIFE",  "beat": 2,   "len_beats": 2,   "style": "gold"},
      {"text": "+$81,090",  "t": 5.0,    "dur": 0.9,       "style": "red"}
    ]
  }
A word is placed with "beat" (beat number from 0) or "t" (seconds). Length is
"len_beats" or "dur" (seconds). Styles: slam (white), gold, red. "y" (0 top to 1
bottom, default 0.62) moves it up or down. Keep words to 1 to 3 short words (rule 15).

Output: overlay.webm (VP9 with alpha) and overlay.mov (ProRes 4444 with alpha).
Drop either on the track above the footage.
Needs Python 3, numpy, Pillow and ffmpeg on the PATH.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_CANDIDATES = [os.path.join(HERE, "..", "lesson01-payoff-counter", "fonts", "Poppins-Bold.ttf"),
                   os.path.join(HERE, "fonts", "Poppins-Bold.ttf")]
STYLES = {                       # fill, outline, glow
    "slam": ((255, 255, 255), (12, 8, 20), (139, 92, 246)),
    "gold": ((245, 185, 58), (30, 14, 4), (255, 140, 30)),
    "red":  ((255, 70, 70), (24, 4, 8), (255, 30, 60)),
}
MAX_W = 940                      # keep clear of the screen edges and the Shorts UI


def find_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("Poppins-Bold.ttf not found (expected in lesson01-payoff-counter/fonts)")


def render_word(text, style, font_path):
    fill, outline, glow = STYLES[style]
    size = 240
    while size > 60:
        font = ImageFont.truetype(font_path, size)
        l, t, r, b = font.getbbox(text, stroke_width=10)
        if r - l <= MAX_W:
            break
        size -= 8
    pad = 70
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad - l, pad - t), text, font=font, fill=fill + (255,),
           stroke_width=10, stroke_fill=outline + (255,))
    mask = img.split()[3]
    g = Image.new("RGBA", img.size, glow + (0,))
    g.putalpha(mask.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.7)))
    g.alpha_composite(img)
    return g


def back_out(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def make_frames(words, bpm, fps, duration):
    beat = 60.0 / bpm
    font_path = find_font()
    items = []
    for w in words:
        t0 = w["beat"] * beat if "beat" in w else float(w["t"])
        dur = w["len_beats"] * beat if "len_beats" in w else float(w.get("dur", 2 * beat))
        items.append(dict(img=render_word(w["text"], w.get("style", "slam"), font_path),
                          t0=t0, t1=t0 + dur, y=float(w.get("y", 0.62))))
    n = int(round(duration * fps))
    rng = np.random.default_rng(5)
    for i in range(n):
        t = i / fps
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for it in items:
            if not (it["t0"] <= t < it["t1"]):
                continue
            age, left = t - it["t0"], it["t1"] - t
            slam = min(1.0, age / 0.14)
            scale = 2.4 - 1.4 * back_out(slam)           # 2.4x down to 1.0x with overshoot
            scale = max(scale, 0.0)
            pulse = 1 + 0.05 * np.exp(-((t % beat) / beat) * 6)   # beat pulse
            if age > 0.14:
                scale = pulse
            alpha = min(1.0, age / 0.05)
            if left < 0.10:                               # fast exit: shrink and fade
                k = left / 0.10
                scale *= 0.85 + 0.15 * k
                alpha *= k
            shake = 14 * max(0.0, 1 - age / 0.12) ** 2
            dx, dy = rng.uniform(-shake, shake), rng.uniform(-shake, shake)
            im = it["img"]
            sw, sh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
            im = im.resize((sw, sh), Image.BILINEAR)
            if alpha < 1.0:
                im.putalpha(im.split()[3].point(lambda v, a=alpha: int(v * a)))
            x = int(W / 2 - sw / 2 + dx)
            y = int(it["y"] * H - sh / 2 + dy)
            canvas.alpha_composite(im, (max(x, -sw), max(y, -sh))) if x >= 0 and y >= 0 else \
                canvas.paste(im, (x, y), im)
        yield np.asarray(canvas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.words))
    bpm = float(cfg.get("bpm", 128))
    fps = float(cfg.get("fps", 60))
    beat = 60.0 / bpm
    ends = [(w["beat"] * beat if "beat" in w else w["t"]) +
            (w["len_beats"] * beat if "len_beats" in w else w.get("dur", 2 * beat))
            for w in cfg["words"]]
    duration = float(cfg.get("duration", max(ends)))
    os.makedirs(a.out, exist_ok=True)
    webm, mov = os.path.join(a.out, "overlay.webm"), os.path.join(a.out, "overlay.mov")
    common = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
              "-s", f"{W}x{H}", "-framerate", f"{fps:g}", "-i", "-"]
    e = subprocess.Popen(common + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
                                   "-crf", "24", "-auto-alt-ref", "0", "-row-mt", "1", webm],
                         stdin=subprocess.PIPE)
    p = subprocess.Popen(common + ["-c:v", "prores_ks", "-profile:v", "4444",
                                   "-pix_fmt", "yuva444p10le", mov], stdin=subprocess.PIPE)
    n = 0
    for fr in make_frames(cfg["words"], bpm, fps, duration):
        b = np.ascontiguousarray(fr).tobytes()
        e.stdin.write(b); p.stdin.write(b); n += 1
    for pr in (e, p):
        pr.stdin.close(); pr.wait()
    print(f"done: {n} frames, {n / fps:.2f}s at {fps:g} fps, bpm {bpm:g} -> {webm}, {mov}")


if __name__ == "__main__":
    main()
