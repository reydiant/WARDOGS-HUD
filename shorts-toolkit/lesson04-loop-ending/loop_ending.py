#!/usr/bin/env python3
"""
loop_ending.py - make a Short loop seamlessly (backlog #8).

The last 0.4 s whips sideways (motion blur plus a small zoom) and dissolves into
frame one, so when YouTube replays the Short the cut back to the start is invisible.
Replays raise average watch %.

  python3 loop_ending.py make short.mp4 --out short_loop.mp4 [--blend 0.4]
  python3 loop_ending.py check short_loop.mp4

make:  the video is left alone until the last --blend seconds. In that window each
       frame is blurred along x, zoomed slightly, and mixed toward frame one. The
       final frame IS frame one. Audio gets a 30 ms fade at both ends so the loop
       point has no click.
check: prints the seam score, the mean absolute pixel difference (0 to 255) between
       the last frame and the first frame. Under about 2 means the loop is invisible.
       Run it on the original Short to see the "before" number.

Keep the end card on screen about 1.2 s before the blend starts (rule 10), then blend.
Needs Python 3, numpy, Pillow and ffmpeg on the PATH.
"""
import argparse, os, subprocess, sys
import numpy as np

W, H = 1080, 1920


def probe(path):
    def run(args):
        return subprocess.run(["ffprobe", "-v", "error"] + args + [path],
                              capture_output=True, text=True).stdout.strip()
    num, den = run(["-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                    "-of", "csv=p=0"]).split("/")
    fps = float(num) / float(den)
    w, h = run(["-select_streams", "v:0", "-show_entries", "stream=width,height",
                "-of", "csv=p=0:s=x"]).split("x")
    has_audio = bool(run(["-select_streams", "a:0", "-show_entries", "stream=codec_type",
                          "-of", "csv=p=0"]))
    dur = float(run(["-show_entries", "format=duration", "-of", "csv=p=0"]))
    return fps, int(w), int(h), has_audio, dur


def grab(path, t, w, h):
    """One frame at time t (seconds) as an HxWx3 uint8 array. Negative t counts from the end."""
    args = ["ffmpeg", "-loglevel", "error"]
    args += (["-sseof", f"{t:.4f}"] if t < 0 else ["-ss", f"{t:.4f}"])
    args += ["-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    b = subprocess.run(args, capture_output=True).stdout
    if len(b) != w * h * 3:
        sys.exit("could not read a frame")
    return np.frombuffer(b, np.uint8).reshape(h, w, 3)


def last_frame(path, fps, w, h):
    # the last frame is the one whose timestamp is just before the end
    return grab(path, -1.5 / fps, w, h)


def seam_score(path):
    fps, w, h, _, _ = probe(path)
    a = last_frame(path, fps, w, h).astype(np.float32)
    b = grab(path, 0.0, w, h).astype(np.float32)
    return float(np.abs(a - b).mean())


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def whip(frame, strength):
    """Horizontal motion blur plus a small zoom toward the center."""
    f = frame.astype(np.float32)
    k = int(round(70 * strength))
    if k >= 2:
        acc = np.zeros_like(f)
        shifts = np.linspace(-k, k, 9).astype(int)
        for s in shifts:
            acc += np.roll(f, s, axis=1)
        f = acc / len(shifts)
    z = 1.0 + 0.06 * strength
    if z > 1.001:
        from PIL import Image
        im = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
        w2, h2 = int(round(w_ := f.shape[1] * z)), int(round(f.shape[0] * z))
        im = im.resize((w2, h2), Image.BILINEAR)
        x0, y0 = (w2 - f.shape[1]) // 2, (h2 - f.shape[0]) // 2
        f = np.asarray(im.crop((x0, y0, x0 + f.shape[1], y0 + f.shape[0]))).astype(np.float32)
    return f


def make(a):
    fps, w, h, has_audio, dur = probe(a.clip)
    n_blend = max(2, int(round(a.blend * fps)))
    total = int(round(dur * fps))
    n_head = total - n_blend
    if n_head < 1:
        sys.exit("clip is shorter than the blend")
    t_split = n_head / fps
    first = grab(a.clip, 0.0, w, h)
    tmp_head, tmp_tail = a.out + ".head.mp4", a.out + ".tail.mp4"
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
           "-r", f"{fps}"]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.clip, "-t", f"{t_split:.5f}",
                    "-an"] + enc + [tmp_head], check=True)
    dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{t_split:.5f}", "-i", a.clip,
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    e = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{w}x{h}", "-framerate", f"{fps}", "-i", "-"] + enc + [tmp_tail],
                         stdin=subprocess.PIPE)
    fsize = w * h * 3
    ff = first.astype(np.float32)
    for i in range(n_blend):
        b = dec.stdout.read(fsize)
        if len(b) != fsize:
            break
        src = np.frombuffer(b, np.uint8).reshape(h, w, 3)
        p = (i + 1) / n_blend                      # 1/n .. 1.0
        strength = np.sin(np.pi * min(1.0, p * 0.9 + 0.05)) ** 0.8   # whip peaks mid-blend
        mix = smooth((p - 0.15) / 0.85)            # reaches 1.0 on the last frame
        f = whip(src, strength) * (1 - mix) + ff * mix
        if i == n_blend - 1:
            f = ff                                  # last frame is exactly frame one
        e.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
    e.stdin.close(); e.wait(); dec.stdout.close(); dec.wait()
    lst = a.out + ".list.txt"
    with open(lst, "w") as fh:
        fh.write(f"file '{os.path.abspath(tmp_head)}'\nfile '{os.path.abspath(tmp_tail)}'\n")
    vtmp = a.out + ".v.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", vtmp], check=True)
    if has_audio:
        vid_dur = total / fps
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vtmp, "-i", a.clip,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", f"afade=t=in:d=0.03,afade=t=out:st={vid_dur - 0.03:.4f}:d=0.03",
                        "-c:a", "aac", "-b:a", "192k", "-t", f"{vid_dur:.4f}", a.out], check=True)
    else:
        os.replace(vtmp, a.out)
    for p in (tmp_head, tmp_tail, lst, vtmp):
        if os.path.exists(p):
            os.remove(p)
    before = float(np.abs(last_frame(a.clip, fps, w, h).astype(np.float32) - ff).mean())
    after = seam_score(a.out)
    print(f"done: {a.out}  seam score {before:.1f} -> {after:.1f} (under ~2 is invisible)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("clip"); m.add_argument("--out", required=True)
    m.add_argument("--blend", type=float, default=0.4)
    c = sub.add_parser("check"); c.add_argument("clip")
    a = ap.parse_args()
    if a.cmd == "make":
        make(a)
    else:
        print(f"seam score {seam_score(a.clip):.1f} (mean pixel difference, last frame vs first)")


if __name__ == "__main__":
    main()
