#!/usr/bin/env python3
"""Fake match recording for testing story_plan.py: 1920x1080, 60 fps, dark, with a red flash, a
time stamp and a gunshot on every kill time in events.json. It is not gameplay.

  python make_demo_match.py events.example.json demo_match.mp4 [--dur 70]
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "lesson01-payoff-counter", "fonts", "Poppins-Bold.ttf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=70.0)
    a = ap.parse_args()
    kills = [e["t"] for e in json.load(open(a.events, encoding="utf-8"))["events"]]
    font = os.path.relpath(FONT).replace("\\", "/").replace(":", "\\:")
    boxes = ",".join(f"drawbox=x=760:y=340:w=400:h=400:color=red@0.85:t=fill:enable='between(t,{k},{k + 0.12})'"
                     for k in kills)
    vf = (f"noise=alls=14:allf=t,drawgrid=w=160:h=160:t=2:c=0x2a2f36,"
          f"drawbox=x=0:y=760:w=1920:h=320:color=0x2b2722:t=fill,"
          f"drawbox=x='mod(t*140,1920)':y=600:w=60:h=160:color=0x0e0f12:t=fill,{boxes},"
          f"drawtext=fontfile='{font}':text='%{{pts\\:hms}}':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=880")
    shots = "+".join(f"0.9*(random(0)*2-1)*exp(-max(t-{k},0)/0.05)*gte(t,{k})" for k in kills)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", f"color=c=0x1b1e23:s=1920x1080:r=60:d={a.dur}",
           "-f", "lavfi", "-i", f"aevalsrc='0.03*sin(2*PI*70*t)+{shots}':s=48000:d={a.dur}",
           "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", a.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-1500:])
    print("wrote", a.out)


if __name__ == "__main__":
    main()
