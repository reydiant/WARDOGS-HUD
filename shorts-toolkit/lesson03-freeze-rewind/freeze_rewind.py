#!/usr/bin/env python3
"""
freeze_rewind.py - impact-freeze opener for WARDOGS Shorts.

Frame one is the kill landing (standing rules 1 and 2). The hit frame is held for
a beat with a zoom punch, a flash and a gold vignette, then the footage rewinds
with a violet tint and plays forward normally, so the viewer sees the kill again
in full. It costs about 0.6 seconds of runtime.

  frame one .. 0.30 s   hit frame frozen: zoom punch, shake, white-gold flash, gold vignette
  next 0.30 s           rewind through the lead-up, violet tint, small color split
  after                 normal play from the start of the lead-up, through the hit, to the end

Layer the lesson 1 payoff text and the lesson 2 music on top of the result.
The audio is rebuilt the same way: the gunshot at the hit plays under the freeze, a
sped-up reversed "tape" sound plays during the rewind, then the original audio.

Usage:
  python3 freeze_rewind.py clip.mp4 --hit 12.40 --out opener.mp4
      [--lead 0.9] [--freeze 0.3] [--rewind 0.3] [--tail SECONDS_AFTER_HIT]

--hit is the time in seconds, in the source clip, of the frame where the kill lands.
The output is cropped to 1080x1920 from the center of the picture (rule 14).
Needs Python 3, numpy, Pillow and ffmpeg on the PATH.
"""
import argparse, os, subprocess, sys
import numpy as np
from PIL import Image

W, H = 1080, 1920
GOLD = np.array([245, 185, 58], np.float32)
VIOLET = np.array([139, 92, 246], np.float32)
FLASH = np.array([255, 240, 205], np.float32)


def ease_out_cubic(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def probe(path):
    def run(args):
        return subprocess.run(["ffprobe", "-v", "error"] + args + [path],
                              capture_output=True, text=True).stdout.strip()
    num, den = run(["-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                    "-of", "csv=p=0"]).split("/")
    fps = float(num) / float(den)
    has_audio = bool(run(["-select_streams", "a:0", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0"]))
    dur = float(run(["-show_entries", "format=duration", "-of", "csv=p=0"]))
    return fps, has_audio, dur


def vignette_alpha():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / 1.414
    return (np.clip((r - 0.35) / 0.65, 0, 1) ** 1.6)[..., None]


VIG = vignette_alpha()


def blend(frame, color, alpha):
    return frame * (1 - alpha) + color * alpha


def punch(frame_u8, scale, dx, dy):
    """Zoom in around the center, then shake by (dx, dy) pixels."""
    im = Image.fromarray(frame_u8)
    w, h = int(round(W * scale)), int(round(H * scale))
    im = im.resize((w, h), Image.BILINEAR)
    x0 = (w - W) // 2 - dx
    y0 = (h - H) // 2 - dy
    x0 = min(max(x0, 0), w - W)
    y0 = min(max(y0, 0), h - H)
    return np.asarray(im.crop((x0, y0, x0 + W, y0 + H)))


def freeze_frame(hit, i, n, fps, rng):
    p = i / max(1, n - 1)
    scale = 1.0 + 0.14 * (1 - ease_out_cubic(p))
    shake = 10 * (1 - p) ** 2
    dx, dy = int(rng.uniform(-shake, shake)), int(rng.uniform(-shake, shake))
    f = punch(hit, scale, dx, dy).astype(np.float32)
    f = blend(f, GOLD, VIG * (0.55 - 0.25 * p))
    flash = max(0.0, 1 - i / max(1.0, 0.10 * fps)) * 0.32
    if flash > 0:
        f = blend(f, FLASH, flash)
    return np.clip(f, 0, 255).astype(np.uint8)


def rewind_frame(src, j, n):
    strength = 0.35 + 0.65 * np.sin(np.pi * (j + 0.5) / n)
    f = src.astype(np.float32) * (1 - 0.25 * strength)
    f = blend(f, VIOLET, 0.28 * strength + VIG * 0.45 * strength)
    shift = int(round(7 * strength))
    out = f.copy()
    out[..., 0] = np.roll(f[..., 0], shift, axis=1)   # red one way, blue the other
    out[..., 2] = np.roll(f[..., 2], -shift, axis=1)
    return np.clip(out, 0, 255).astype(np.uint8)


def atempo_chain(speed):
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    parts.append(f"atempo={speed:.4f}")
    return ",".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--hit", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lead", type=float, default=0.9)
    ap.add_argument("--freeze", type=float, default=0.3)
    ap.add_argument("--rewind", type=float, default=0.3)
    ap.add_argument("--tail", type=float, default=None)
    a = ap.parse_args()

    fps, has_audio, src_dur = probe(a.clip)
    fps = min(fps, 60.0)
    lead = min(a.lead, a.hit)
    lead_n = int(round(lead * fps))
    freeze_n = int(round(a.freeze * fps))
    rewind_n = int(round(a.rewind * fps))
    start = a.hit - lead_n / fps
    rng = np.random.default_rng(3)

    dec = ["ffmpeg", "-loglevel", "error", "-ss", f"{start:.4f}", "-i", a.clip]
    if a.tail is not None:
        dec += ["-t", f"{lead_n / fps + a.tail:.4f}"]
    dec += ["-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps}",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    d = subprocess.Popen(dec, stdout=subprocess.PIPE)
    fsize = W * H * 3

    def read():
        b = d.stdout.read(fsize)
        return np.frombuffer(b, np.uint8).reshape(H, W, 3) if len(b) == fsize else None

    buf = []
    for _ in range(lead_n + 1):
        f = read()
        if f is None:
            break
        buf.append(f)
    if len(buf) < lead_n + 1:
        sys.exit("clip ends before the hit time; check --hit")
    hit_frame = buf[-1]

    tmp = a.out + ".video.tmp.mp4"
    enc = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-framerate", f"{fps}", "-i", "-", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", tmp]
    e = subprocess.Popen(enc, stdin=subprocess.PIPE)

    def emit(frame):
        e.stdin.write(np.ascontiguousarray(frame).tobytes())

    for i in range(freeze_n):
        emit(freeze_frame(hit_frame, i, freeze_n, fps, rng))
    for j in range(rewind_n):
        idx = max(0, lead_n - int(round((j + 1) * lead_n / rewind_n)))
        emit(rewind_frame(buf[idx], j, rewind_n))
    for f in buf:
        emit(f)
    n_rest = 0
    while True:
        f = read()
        if f is None:
            break
        emit(f)
        n_rest += 1
    e.stdin.close()
    e.wait()
    d.wait()
    total = freeze_n + rewind_n + len(buf) + n_rest
    vid_dur = total / fps

    if has_audio:
        speed = lead / (rewind_n / fps)
        hs = a.hit
        fc = (f"[1:a]atrim=start={max(0, hs - 0.05):.4f}:end={hs - 0.05 + freeze_n / fps:.4f},"
              f"asetpts=PTS-STARTPTS[a1];"
              f"[1:a]atrim=start={hs - lead:.4f}:end={hs:.4f},asetpts=PTS-STARTPTS,areverse,"
              f"{atempo_chain(speed)},volume=0.5[a2];"
              f"[1:a]atrim=start={hs - lead:.4f},asetpts=PTS-STARTPTS[a3];"
              f"[a1][a2][a3]concat=n=3:v=0:a=1[a]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", a.clip,
                        "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-t", f"{vid_dur:.4f}", a.out + ".tmp.mp4"],
                       check=True)
        os.remove(tmp)
        os.replace(a.out + ".tmp.mp4", a.out)
    else:
        os.replace(tmp, a.out)
    print(f"done: {total} frames, {vid_dur:.2f}s at {fps:g} fps. The kill lands on frame one and "
          f"again at {(freeze_n + rewind_n) / fps + lead:.2f}s. Added {(freeze_n + rewind_n) / fps:.2f}s.")


if __name__ == "__main__":
    main()
