#!/usr/bin/env python3
"""Synthetic FPS-looking test clip (vertical, 60 fps, with a gunshot) for testing edit tools.
Not real gameplay. The kill lands at --hit seconds.

  python3 make_demo_footage.py out.mp4 [--hit 2.0] [--dur 4.0]
"""
import argparse, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw

W, H, FPS = 1080, 1920, 60


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--hit", type=float, default=2.0)
    ap.add_argument("--dur", type=float, default=4.0)
    a = ap.parse_args()
    n = int(a.dur * FPS)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-", "-c:v", "libx264",
                            "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "tmp_video.mp4"],
                           stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        sky = np.stack([40 + 50 * (yy / H), 55 + 60 * (yy / H), 80 + 70 * (yy / H)], -1)
        stripes = 12 * np.sin((xx + 120 * t) / 70.0)[..., None]       # slow sideways drift
        img = Image.fromarray(np.clip(sky + stripes, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 1250, W, H], fill=(48, 44, 40))                 # ground
        ex = int(300 + 480 * (t / a.dur))                               # enemy walks across
        ey = 1000
        d.rectangle([ex - 55, ey, ex + 55, ey + 260], fill=(25, 25, 30))  # body
        d.ellipse([ex - 38, ey - 80, ex + 38, ey - 4], fill=(30, 30, 36))  # head
        cx, cy = W // 2, H // 2
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:               # crosshair
            d.line([(cx + dx * 16, cy + dy * 16), (cx + dx * 56, cy + dy * 56)], fill=(240, 240, 240), width=4)
        if abs(t - a.hit) < 0.5 / FPS or (0 <= t - a.hit < 0.12):        # kill lands: hit marker + flash
            k = 1 - (t - a.hit) / 0.12 if t >= a.hit else 1
            d.line([(cx - 30, cy - 30), (cx + 30, cy + 30)], fill=(255, 60, 60), width=8)
            d.line([(cx - 30, cy + 30), (cx + 30, cy - 30)], fill=(255, 60, 60), width=8)
            d.ellipse([cx - 160, cy + 380, cx + 160, cy + 700], fill=(255, int(180 * k + 40), 60))
        enc.stdin.write(np.asarray(img).tobytes())
    enc.stdin.close()
    enc.wait()

    sr = 48000
    t = np.arange(int(a.dur * sr)) / sr
    audio = 0.05 * np.sin(2 * np.pi * 70 * t) + 0.02 * np.random.default_rng(1).standard_normal(len(t))
    i0 = int(a.hit * sr)
    k = np.arange(int(0.3 * sr)) / sr
    shot = np.random.default_rng(2).standard_normal(len(k)) * np.exp(-k / 0.04) * 0.8
    audio[i0:i0 + len(k)] += shot[:len(audio) - i0]
    with wave.open("tmp_audio.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "tmp_video.mp4", "-i", "tmp_audio.wav",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", a.out], check=True)
    os.remove("tmp_video.mp4"); os.remove("tmp_audio.wav")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
