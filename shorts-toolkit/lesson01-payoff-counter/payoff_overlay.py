#!/usr/bin/env python3
"""
payoff_overlay.py - animated payoff text, running cash counter and "+$X" pops
for WARDOGS Shorts (Reydiant / @crazynando).

Input : a JSON file with the kill list (time in seconds, reward, headshot or not).
Output: a transparent 1080x1920 60 fps overlay (ProRes 4444 with alpha) to drop
        on top of the footage in an editor, plus an optional demo composite.

The payoff total and the counter are both computed from the same kill list, so
the numbers on screen always add up. Cut a kill from the JSON and every number
updates (standing rules 9, 11 and 12).

Usage:
  python3 payoff_overlay.py events.json --out outdir [--bg bg.png] [--prefix name]
                            [--codec prores|qtrle] [--limit SECONDS]
                            [--previews 0,0.25,1.0,2.2]

events.json:
  {"events": [{"t": 0.0, "amount": 2100, "headshot": false}, ...],
   "payoff": "auto",     # or any text, e.g. "28 KILLS"
   "hold": 1.5}          # seconds the big payoff text stays on screen
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 60

# Channel look: near-black with gold-to-violet.
GOLD = (245, 185, 58)
GOLD_LIGHT = (255, 226, 140)
VIOLET = (139, 92, 246)
VIOLET_LIGHT = (176, 132, 255)
ROSE = (246, 112, 178)
SILVER = (230, 230, 250)
INK = (8, 6, 14)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_font(name):
    """Poppins ships in ./fonts next to this script. SHORTS_FONT_DIR overrides it."""
    for d in (os.environ.get("SHORTS_FONT_DIR", ""), os.path.join(_HERE, "fonts"),
              "/usr/share/fonts/truetype/google-fonts"):
        if d and os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    sys.exit(f"font {name} not found: put it in {os.path.join(_HERE, 'fonts')} or set SHORTS_FONT_DIR")


FONT_BOLD = _find_font("Poppins-Bold.ttf")
FONT_MED = _find_font("Poppins-Medium.ttf")

# Shorts UI covers the top ~130 px, the bottom ~420 px and the right ~130 px.
SAFE_X0, SAFE_X1 = 60, 950
SAFE_Y0, SAFE_Y1 = 130, 1500


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


_fonts = {}


def font(path, size):
    key = (path, int(size))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, int(size))
    return _fonts[key]


# ---------------------------------------------------------------- sprites
def layout(parts, fnt):
    """parts: list of ('t', text) or ('arrow', None). Returns items and total width."""
    S = fnt.size
    gap, aw = int(0.20 * S), int(0.80 * S)
    x, items = 0.0, []
    for kind, val in parts:
        if kind == "t":
            w = fnt.getlength(val)
            items.append((kind, val, x, w))
            x += w
        else:
            x += gap
            items.append((kind, None, x, aw))
            x += aw + gap
    return items, x


def draw_parts(draw, items, fnt, pad, mode, stroke):
    S = fnt.size
    b = fnt.getbbox("0")
    cy = pad + (b[1] + b[3]) / 2.0
    for kind, val, x, w in items:
        if kind == "t":
            if mode == "fill":
                draw.text((pad + x, pad), val, font=fnt, fill=255)
            else:
                draw.text((pad + x, pad), val, font=fnt, fill=255,
                          stroke_width=stroke, stroke_fill=255)
        else:
            ax = pad + x
            th, hl, hh = 0.13 * S, 0.34 * S, 0.26 * S
            shaft = [ax, cy - th / 2, ax + w - hl + 2, cy + th / 2]
            head = [(ax + w - hl, cy - hh), (ax + w, cy), (ax + w - hl, cy + hh)]
            if mode == "fill":
                draw.rectangle(shaft, fill=255)
                draw.polygon(head, fill=255)
            else:
                draw.rectangle([shaft[0] - stroke, shaft[1] - stroke,
                                shaft[2] + stroke, shaft[3] + stroke], fill=255)
                draw.polygon(head, fill=255, outline=255, width=stroke * 2)


def make_sprite(parts, fnt, c0, c1, stroke=6, glow=16, glow_color=VIOLET):
    items, tw = layout(parts, fnt)
    asc, desc = fnt.getmetrics()
    pad = glow * 2 + stroke + 14
    w, h = int(tw) + pad * 2, asc + desc + pad * 2
    fill = Image.new("L", (w, h), 0)
    out = Image.new("L", (w, h), 0)
    draw_parts(ImageDraw.Draw(fill), items, fnt, pad, "fill", stroke)
    draw_parts(ImageDraw.Draw(out), items, fnt, pad, "out", stroke)

    layers = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # soft dark drop shadow so the text reads on bright footage
    sh = Image.new("L", (w, h), 0)
    sh.paste(out, (0, 6))
    sh = sh.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.65))
    s_layer = Image.new("RGBA", (w, h), INK + (0,))
    s_layer.putalpha(sh)
    layers = Image.alpha_composite(layers, s_layer)

    # glow
    gl = out.filter(ImageFilter.GaussianBlur(glow / 2.0)).point(lambda v: min(255, int(v * 1.1)))
    g_layer = Image.new("RGBA", (w, h), glow_color + (0,))
    g_layer.putalpha(gl)
    layers = Image.alpha_composite(layers, g_layer)

    # dark outline
    o_layer = Image.new("RGBA", (w, h), INK + (0,))
    o_layer.putalpha(out)
    layers = Image.alpha_composite(layers, o_layer)

    # gradient fill, left to right, slightly brighter at the top.
    # c0 may be a list of colors (evenly spaced stops); a plain gold-to-violet
    # blend goes muddy grey in the middle, so the payoff uses a rose mid stop.
    stops = list(c0) if isinstance(c0[0], (tuple, list)) else [c0, c1]
    pos = np.linspace(0, 1, len(stops))
    xline = np.linspace(0, 1, w, dtype=np.float32)
    cols = np.stack([np.interp(xline, pos, [s[k] for s in stops]) for k in range(3)], -1)
    ys = np.linspace(1.0, 0.86, h, dtype=np.float32)[:, None, None]
    grad = cols[None, :, :] * ys
    f_layer = Image.fromarray(np.clip(grad, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    f_layer.putalpha(fill)
    return Image.alpha_composite(layers, f_layer)


def blit(canvas, spr, cx, cy, scale=1.0, opacity=1.0):
    if opacity <= 0.003 or scale <= 0.01:
        return
    if abs(scale - 1.0) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))),
                         Image.BILINEAR)
    if opacity < 0.999:
        a = spr.getchannel("A").point(lambda v: int(v * opacity))
        spr = spr.copy()
        spr.putalpha(a)
    x, y = int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + spr.width), min(H, y + spr.height)
    if x1 <= x0 or y1 <= y0:
        return
    crop = spr.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    region = Image.alpha_composite(canvas.crop((x0, y0, x1, y1)), crop)
    canvas.paste(region, (x0, y0))


# ---------------------------------------------------------------- timeline
class Overlay:
    def __init__(self, cfg):
        self.events = sorted(cfg["events"], key=lambda e: e["t"])
        self.total = sum(e["amount"] for e in self.events)
        self.hold = float(cfg.get("hold", 1.5))
        self.payoff_text = cfg.get("payoff", "auto")
        self.pop_life = 1.15
        self.cache = {}
        self.payoff_sprite = self._make_payoff()
        self.offsets = [-70, 60, -30, 80, -60, 40, -20, 70]

    def duration(self):
        last = self.events[-1]["t"] if self.events else 0
        return max(self.hold + 0.6, last + self.pop_life) + 0.8

    def _make_payoff(self):
        if self.payoff_text == "auto":
            parts = [("t", "$0"), ("arrow", None), ("t", f"${self.total:,}")]
        else:
            parts = [("t", str(self.payoff_text))]
        for size in range(170, 60, -4):
            fnt = font(FONT_BOLD, size)
            _, tw = layout(parts, fnt)
            if tw <= 770:  # leaves room for the 12% punch-in on frame one
                break
        return make_sprite(parts, fnt, [GOLD_LIGHT, GOLD, ROSE, VIOLET_LIGHT], None,
                           stroke=8, glow=22)

    def counter_sprite(self, value):
        key = ("c", value)
        if key not in self.cache:
            if len(self.cache) > 400:
                self.cache.clear()
            self.cache[key] = make_sprite([("t", f"${value:,}")], font(FONT_BOLD, 112),
                                          GOLD_LIGHT, GOLD, stroke=7, glow=16)
        return self.cache[key]

    def label_sprite(self, n):
        key = ("l", n)
        if key not in self.cache:
            self.cache[key] = make_sprite([("t", f"KILL {n}" if n else "KILLS 0")],
                                          font(FONT_MED, 40), SILVER, SILVER,
                                          stroke=4, glow=8)
        return self.cache[key]

    def pop_sprites(self, i):
        key = ("p", i)
        if key not in self.cache:
            e = self.events[i]
            hs = e.get("headshot", False)
            main = make_sprite([("t", f"+${e['amount']:,}")], font(FONT_BOLD, 120),
                               GOLD_LIGHT if not hs else [GOLD_LIGHT, ROSE, VIOLET_LIGHT],
                               GOLD if not hs else None, stroke=8, glow=20)
            tag = make_sprite([("t", "HEADSHOT")], font(FONT_BOLD, 46), SILVER, VIOLET_LIGHT,
                               stroke=5, glow=12) if hs else None
            self.cache[key] = (main, tag)
        return self.cache[key]

    def render(self, t):
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # 1. payoff text, readable on frame one, then it hands over to the counter
        leave = ease_in_out((t - self.hold) / 0.30)
        if leave < 1:
            pop = 1.0 + 0.12 * (1 - ease_out_cubic(t / 0.30))
            sc = pop * (1 - 0.22 * leave)
            cy = 330 - 40 * leave
            blit(canvas, self.payoff_sprite, W / 2 - 20, cy, sc, 1 - leave)

        # 2. running cash counter
        vis = ease_in_out((t - self.hold - 0.12) / 0.35)
        if vis > 0:
            value, kills, bump = 0, 0, 0.0
            for e in self.events:
                dt = t - e["t"]
                if dt >= 0:
                    value += e["amount"] * ease_out_cubic(dt / 0.35)
                    kills += 1
                    if dt < 0.28:
                        bump = max(bump, math.sin(math.pi * dt / 0.28))
            value = int(round(value))
            sc = (0.88 + 0.12 * vis) * (1 + 0.14 * bump)
            blit(canvas, self.counter_sprite(value), W / 2 - 20, 205, sc, vis)
            blit(canvas, self.label_sprite(kills), W / 2 - 20, 295, 1.0, vis * 0.9)

        # 3. "+$X" pops at the crosshair
        for i, e in enumerate(self.events):
            age = t - e["t"]
            if age < 0 or age > self.pop_life:
                continue
            main, tag = self.pop_sprites(i)
            if age < 0.14:
                sc = 0.8 + (1.22 - 0.8) * ease_out_cubic(age / 0.14)
            elif age < 0.30:
                sc = 1.22 - 0.22 * ease_in_out((age - 0.14) / 0.16)
            else:
                sc = 1.0
            op = 1.0  # fully visible on frame one: the kill must land on the first frame
            rise = 0.0
            if age > 0.75:
                k = ease_in_out((age - 0.75) / 0.40)
                op *= 1 - k
                rise = 90 * k
            cx = W / 2 - 20 + self.offsets[i % len(self.offsets)]
            cy = 770 - rise
            for j in range(i + 1, len(self.events)):  # newer pops push older ones up
                dtj = t - self.events[j]["t"]
                if dtj > 0:
                    cy -= 115 * ease_out_cubic(dtj / 0.2)
            blit(canvas, main, cx, cy, sc, op)
            if tag is not None:
                blit(canvas, tag, cx, cy + 92 * sc, sc, op)
        return canvas


# ---------------------------------------------------------------- render
def encode_args(codec):
    if codec == "qtrle":
        return ["-c:v", "qtrle", "-pix_fmt", "argb"]
    if codec == "webm":  # tiny file, good for previews and editors that read VP9 alpha
        return ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28",
                "-deadline", "realtime", "-cpu-used", "6", "-auto-alt-ref", "0"]
    return ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
            "-vendor", "apl0"]


EXT = {"prores": "mov", "qtrle": "mov", "webm": "webm"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bg")
    ap.add_argument("--prefix", default="shorts")
    ap.add_argument("--codec", default="webm,prores",
                    help="comma list of alpha outputs: webm (tiny), prores (editor standard, big), qtrle")
    ap.add_argument("--limit", type=float)
    ap.add_argument("--previews", default="")
    a = ap.parse_args()

    cfg = json.load(open(a.events))
    ov = Overlay(cfg)
    dur = ov.duration()
    if a.limit:
        dur = min(dur, a.limit)
    n = int(round(dur * FPS))
    os.makedirs(a.out, exist_ok=True)
    codecs = [c.strip() for c in a.codec.split(",") if c.strip()]
    tmp_comp = os.path.join(a.out, "tmp_comp.mp4")
    tmp_alpha = {c: os.path.join(a.out, f"tmp_alpha_{c}.{EXT[c]}") for c in codecs}

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    src = "0:v"
    if a.bg:
        cmd += ["-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", a.bg]
        src = "1:v"
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-"]
    branches = [f"a{i}" for i in range(len(codecs))] + (["b"] if a.bg else [])
    fc = f"[{src}]split={len(branches)}" + "".join(f"[{b}]" for b in branches)
    if a.bg:
        fc += ";[0:v][b]overlay=format=auto,format=yuv420p[comp]"
    cmd += ["-filter_complex", fc]
    for i, c in enumerate(codecs):
        cmd += ["-map", f"[a{i}]", "-r", str(FPS)] + encode_args(c) + [tmp_alpha[c]]
    if a.bg:
        cmd += ["-map", "[comp]", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "18", "-pix_fmt", "yuv420p", tmp_comp]

    prev_times = [float(x) for x in a.previews.split(",") if x.strip()]
    prev_frames = {int(round(t * FPS)): t for t in prev_times}
    bg_img = Image.open(a.bg).convert("RGBA") if a.bg else Image.new("RGBA", (W, H), (20, 18, 28, 255))

    err = open(os.path.join(a.out, "ffmpeg.log"), "w")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
    for f in range(n):
        t = f / FPS
        frame = ov.render(t)
        if f in prev_frames:
            Image.alpha_composite(bg_img, frame).convert("RGB").save(
                os.path.join(a.out, f"{a.prefix}_preview_{prev_frames[f]:05.2f}s.png"))
        p.stdin.write(frame.tobytes())
        if f % 120 == 0:
            print(f"frame {f}/{n}", flush=True)
    p.stdin.close()
    rc = p.wait()
    err.close()
    if rc != 0:
        print("ffmpeg failed, see ffmpeg.log", file=sys.stderr)
        sys.exit(rc)
    for c in codecs:
        os.replace(tmp_alpha[c], os.path.join(a.out, f"{a.prefix}_overlay_{c}.{EXT[c]}"))
    if a.bg:
        os.replace(tmp_comp, os.path.join(a.out, f"{a.prefix}_demo_composite.mp4"))
    print(f"done: {n} frames, {dur:.2f}s, total ${ov.total:,}, kills {len(ov.events)}")


if __name__ == "__main__":
    main()
