#!/usr/bin/env python3
"""
music_bed.py - original music for a WARDOGS Short, built from the kill list.

Everything is synthesized here (no samples, no copyrighted audio), so it meets
the "original music only" rule. It uses the same events.json as payoff_overlay.py.

What it builds
  - a dark A-minor bed (kick, sub bass, arp, pad, hats) that starts on a hit at
    frame one, with bass and pad ducked on each kick so it pumps
  - a kill stinger on every kill: sub boom + bright "coin" ping, one step higher each
    kill so a streak sounds like it is climbing; headshots get an extra ping
  - a riser into the last kill and a short silent beat right before it
  - the music ducks briefly on every kill so the game's gunshot and hit sound come through
  - a cut plan: how far each kill sits from the nearest 8th note, and how many
    milliseconds to trim or add to land it on the beat (standing rule 7)

Commands
  python3 music_bed.py render events.json --out outdir [--bpm auto|N] [--prefix name]
  python3 music_bed.py measure file            # loudness and true peak
  python3 music_bed.py master in out.wav       # normalize to -14 LUFS, true peak -1.5 dB

Needs Python 3, numpy, scipy and ffmpeg on the PATH.
"""
import argparse, json, math, os, re, subprocess, sys, wave
import numpy as np
from scipy.signal import butter, lfilter

SR = 48000

# A minor, one chord per bar: Am - F - C - G
ROOTS = [55.00, 43.65, 65.41, 49.00]
TRIADS = [[220.00, 261.63, 329.63], [174.61, 220.00, 261.63],
          [261.63, 329.63, 392.00], [196.00, 246.94, 293.66]]
COIN_STEPS = [0, 2, 4, 5, 7, 9, 11, 12]  # major scale steps, one per kill


def tt(n):
    return np.arange(n) / SR


def fade_out(sig, ms=15):
    n = min(len(sig), int(SR * ms / 1000))
    if n > 0:
        sig = sig.copy()
        sig[-n:] *= np.linspace(1, 0, n)
    return sig


def put(buf, start_s, sig, gain=1.0, pan=0.0):
    i0 = int(round(start_s * SR))
    if i0 >= len(buf) or i0 + len(sig) <= 0:
        return
    if i0 < 0:
        sig, i0 = sig[-i0:], 0
    n = min(len(sig), len(buf) - i0)
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i0:i0 + n, 0] += sig[:n] * gain * l
    buf[i0:i0 + n, 1] += sig[:n] * gain * r


# ------------------------------------------------------------- instruments
def kick(rng):
    n = int(0.30 * SR)
    t = tt(n)
    freq = 46 + 120 * np.exp(-t / 0.04)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.14)
    click = rng.standard_normal(n) * np.exp(-t / 0.003) * 0.15
    return fade_out(body + click)


def bass_note(freq, dur):
    n = int(dur * SR)
    t = tt(n)
    sig = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t)
    return fade_out(sig * np.minimum(1, t / 0.008) * np.exp(-t / (dur * 0.9)))


def pluck(freq, dur=0.28):
    n = int(dur * SR)
    t = tt(n)
    sig = np.zeros(n)
    for k in range(1, 12):
        if freq * k < 6000:
            sig += np.sin(2 * np.pi * freq * k * t) / k
    b, a = butter(2, 2200 / (SR / 2), "low")
    return fade_out(lfilter(b, a, sig) * np.exp(-t / 0.12) * np.minimum(1, t / 0.004))


def hat(rng, open_=False):
    n = int((0.16 if open_ else 0.07) * SR)
    t = tt(n)
    b, a = butter(2, 7000 / (SR / 2), "high")
    return fade_out(lfilter(b, a, rng.standard_normal(n)) * np.exp(-t / (0.06 if open_ else 0.02)))


def pad_chord(freqs, dur):
    n = int((dur + 0.3) * SR)
    t = tt(n)
    sig = np.zeros(n)
    for f in freqs:
        for d in (0.997, 1.003):
            sig += np.sin(2 * np.pi * f * d * t)
    env = np.minimum(1, t / 0.35) * np.minimum(1, (n / SR - t) / 0.3)
    b, a = butter(2, 1800 / (SR / 2), "low")
    return lfilter(b, a, sig * env) / 6


# ------------------------------------------------------------ kill sounds
def boom(rng, big=1.0):
    n = int(0.7 * SR)
    t = tt(n)
    freq = 36 + 70 * np.exp(-t / 0.07)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.28)
    b, a = butter(2, 900 / (SR / 2), "low")
    thud = lfilter(b, a, rng.standard_normal(n)) * np.exp(-t / 0.05) * 0.5
    return fade_out((body + thud) * big, 40)


def coin(step, headshot=False, big=1.0):
    f = 1046.5 * 2 ** (COIN_STEPS[step % len(COIN_STEPS)] / 12.0)
    n = int((0.9 if headshot else 0.45) * SR)
    t = tt(n)
    tail = 0.28 if headshot else 0.14
    sig = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.06)
           + 0.3 * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t / tail)
    if headshot:  # a second, higher ping a short beat later
        d = int(0.09 * SR)
        sig[d:] += 0.7 * np.sin(2 * np.pi * f * 2 * t[:-d]) * np.exp(-t[:-d] / 0.2)
    return fade_out(sig * np.minimum(1, t / 0.002) * big, 30)


def riser(rng, dur):
    n = int(dur * SR)
    t = tt(n)
    p = t / dur
    sweep_f = 180 * (2400 / 180) ** p
    sweep = np.sin(2 * np.pi * np.cumsum(sweep_f) / SR)
    b, a = butter(2, 3500 / (SR / 2), "high")
    noise = lfilter(b, a, rng.standard_normal(n))
    return (0.5 * sweep + 0.7 * noise) * (p ** 2.2) * 0.9


# ------------------------------------------------------------- planning
def snap_plan(times, bpm, grid=0.5):
    """Distance of each kill from the nearest grid point (grid = fraction of a beat)."""
    step = 60.0 / bpm * grid
    rows = []
    for k, t in enumerate(times):
        g = round(t / step) * step
        rows.append((k + 1, t, g, g - t))
    return rows


def best_bpm(times):
    best = None
    for b in np.arange(120, 152.01, 0.5):
        rows = snap_plan(times, b)
        cost = sum(abs(r[3]) for r in rows)
        if best is None or cost < best[0]:
            best = (cost, float(b))
    return best[1]


def cut_plan_text(times, bpm):
    rows = snap_plan(times, bpm)
    beat = 60.0 / bpm
    out = [f"BPM {bpm:.1f}. Kills should land on a beat or an 8th note ({beat/2*1000:.0f} ms apart).",
           "shift = how far the kill must move to hit the grid (+ later, - earlier).",
           "gap change = what to add (+) or trim (-) from the footage right before this kill,",
           "after the earlier kills have already been moved.", "",
           f"{'kill':>4} {'time s':>8} {'grid s':>8} {'shift ms':>9} {'gap change ms':>14}"]
    prev = 0.0
    for k, t, g, d in rows:
        out.append(f"{k:>4} {t:>8.3f} {g:>8.3f} {d*1000:>+9.0f} {(d-prev)*1000:>+14.0f}")
        prev = d
    worst = max(abs(r[3]) for r in rows) * 1000
    out.append("")
    out.append(f"Worst miss with no edits: {worst:.0f} ms. About 40 ms is 2 to 3 frames at 60 fps.")
    return "\n".join(out)


# ------------------------------------------------------------- render
def render(cfg, bpm, seed=7, tail=1.0):
    rng = np.random.default_rng(seed)
    events = sorted(cfg["events"], key=lambda e: e["t"])
    times = [e["t"] for e in events]
    D = max(times) + 1.15 + tail
    N = int(D * SR)
    beat = 60.0 / bpm
    bar = beat * 4

    music = np.zeros((N, 2))
    bed = np.zeros((N, 2))   # parts that get side-chained (bass, pad, arp)
    hits = np.zeros((N, 2))

    kick_s = kick(rng)
    n_beats = int(D / beat) + 1
    kick_times = [i * beat for i in range(n_beats)]
    for t in kick_times:
        put(music, t, kick_s, 0.95)

    # hats: off-beat 8ths, open hat on the "and" of 4
    for i in range(n_beats * 2):
        t = i * beat / 2
        if i % 2 == 1:
            put(music, t, hat(rng, open_=(i % 8 == 7)), 0.10, pan=0.25)
        elif i % 4 == 2:
            put(music, t + beat / 4, hat(rng), 0.04, pan=-0.2)

    # bass, arp, pad per bar
    for b in range(int(D / bar) + 1):
        ch = b % 4
        t0 = b * bar
        for i in range(8):
            f = ROOTS[ch] * (2 if i % 4 == 3 else 1)
            put(bed, t0 + i * beat / 2, bass_note(f, beat * 0.45), 0.75 if i % 2 == 0 else 0.5)
        tri = TRIADS[ch]
        order = [0, 1, 2, 1, 0, 1, 2, 1]
        for i in range(8):
            put(bed, t0 + i * beat / 2 + beat / 4, pluck(tri[order[i]] * 2), 0.11,
                pan=-0.3 if i % 2 == 0 else 0.3)
        put(bed, t0, pad_chord(tri, bar), 0.5)

    # side-chain: bass/pad duck on every kick
    sc = np.ones(N)
    seg = int(0.36 * SR)
    curve = 1 - 0.65 * np.exp(-np.arange(seg) / (0.1 * SR))
    for t in kick_times:
        i = int(t * SR)
        if i < N:
            m = min(seg, N - i)
            sc[i:i + m] = np.minimum(sc[i:i + m], curve[:m])
    music += bed * sc[:, None]

    # kill ducking so the game's own hit sound is not buried
    duck = np.ones(N)
    dseg = int(0.42 * SR)
    dcurve = 1 - 0.5 * np.exp(-np.arange(dseg) / (0.12 * SR))
    for t in times:
        i = int(t * SR)
        m = min(dseg, N - i)
        if m > 0:
            duck[i:i + m] = np.minimum(duck[i:i + m], dcurve[:m])

    # riser into the last kill, silent beat right before it
    t_last = times[-1]
    prev_t = times[-2] if len(times) > 1 else None
    gap = 0.12
    ride = min(1.8, (t_last - prev_t - 0.25)) if prev_t is not None else 0
    if ride >= 0.6:
        put(hits, t_last - gap - ride, riser(rng, ride), 0.38)
        a, b = int((t_last - gap - 0.02) * SR), int(t_last * SR)
        mask = np.ones(N)
        mask[a:b] = 0.0
        ramp = int(0.02 * SR)
        mask[a - ramp:a] = np.linspace(1, 0, ramp)
        duck *= mask
        kill_big = {len(times) - 1: 1.3}
    else:
        kill_big = {}
    music *= duck[:, None]

    for k, e in enumerate(events):
        big = kill_big.get(k, 1.0)
        put(hits, e["t"], boom(rng, big), 0.9)
        put(hits, e["t"], coin(k, e.get("headshot", False), big), 0.32,
            pan=-0.15 if k % 2 == 0 else 0.15)
        if big > 1:  # one echo on the final kill
            put(hits, e["t"] + 0.19, coin(k, True, 0.5), 0.2)

    mix = music * 0.8 + hits
    end = int(0.5 * SR)
    mix[-end:] *= np.linspace(1, 0, end)[:, None]
    peak = np.max(np.abs(mix))
    mix = mix / peak * 10 ** (-3 / 20)   # -3 dBFS before mastering
    return mix, D


def write_wav16(path, mix):
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ------------------------------------------------------------- loudness
def measure(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1))
    tp = re.search(r"True peak:\s*Peak:\s+(-?[\d.]+|-inf) dBFS", s)
    return lufs, float(tp.group(1)) if tp else float("nan")


def normalize(src, dst, lufs=-14.0, tp=-1.5):
    p1 = subprocess.run(["ffmpeg", "-nostats", "-i", src, "-af",
                         f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    j = json.loads(p1.stderr[p1.stderr.rfind("{"):p1.stderr.rfind("}") + 1])
    af = (f"loudnorm=I={lufs}:TP={tp}:LRA=11:measured_I={j['input_i']}:measured_LRA={j['input_lra']}"
          f":measured_TP={j['input_tp']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}"
          ":linear=true")
    tmp = dst + ".tmp.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", af, "-ar", str(SR),
                    "-c:a", "pcm_s24le", tmp], check=True)
    os.replace(tmp, dst)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("events")
    r.add_argument("--out", required=True)
    r.add_argument("--bpm", default="auto")
    r.add_argument("--prefix", default="short")
    r.add_argument("--seed", type=int, default=7)
    m = sub.add_parser("measure")
    m.add_argument("file")
    n = sub.add_parser("master")
    n.add_argument("src")
    n.add_argument("dst")
    n.add_argument("--lufs", type=float, default=-14.0)
    n.add_argument("--tp", type=float, default=-1.5)
    a = ap.parse_args()

    if a.cmd == "measure":
        l, tp = measure(a.file)
        print(f"{a.file}: {l:.1f} LUFS integrated, true peak {tp:.1f} dB")
        return
    if a.cmd == "master":
        normalize(a.src, a.dst, a.lufs, a.tp)
        l, tp = measure(a.dst)
        print(f"{a.dst}: {l:.1f} LUFS, true peak {tp:.1f} dB")
        return

    cfg = json.load(open(a.events))
    times = sorted(e["t"] for e in cfg["events"])
    bpm = best_bpm(times) if a.bpm == "auto" else float(a.bpm)
    os.makedirs(a.out, exist_ok=True)
    mix, D = render(cfg, bpm, a.seed)
    raw = os.path.join(a.out, f"{a.prefix}_raw.wav")
    write_wav16(raw, mix)
    full = os.path.join(a.out, f"{a.prefix}_bed_standalone_-14LUFS.wav")
    under = os.path.join(a.out, f"{a.prefix}_bed_under_game_-20LUFS.wav")
    normalize(raw, full, -14.0, -1.5)
    normalize(raw, under, -20.0, -1.5)
    os.remove(raw)
    plan = cut_plan_text(times, bpm)
    open(os.path.join(a.out, f"{a.prefix}_cut_plan.txt"), "w").write(plan + "\n")
    print(plan)
    for f in (full, under):
        l, tp = measure(f)
        print(f"{os.path.basename(f)}: {l:.1f} LUFS, true peak {tp:.1f} dB, {D:.2f}s")


if __name__ == "__main__":
    main()
