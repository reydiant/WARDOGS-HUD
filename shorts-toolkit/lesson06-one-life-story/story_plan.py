#!/usr/bin/env python3
"""
story_plan.py - plan, check and rough-cut a one-life-story Short.

One match, told as a mini story in 40 seconds or less:

  hook     0-2 s     frame one is a kill landing, with a short story line ("ONE LIFE. NO ARMOR.")
  setup    2-8 s     the plan or constraint, in a few words
  beats    8-30 s    3 or 4 moments in match order, each with its own edit
  risky    25-32 s   the one decision or shot the story turns on
  payoff   32-38 s   the best kill, short slow-mo
  end      last 1.5 s  @crazynando, twitch, and a one-line "Next:" teaser

Commands:
  python story_plan.py build  events.json beats.json --out plan.json
  python story_plan.py check  plan.json events.json [--clip match.mp4]
  python story_plan.py export plan.json events.json --out exports
  python story_plan.py render plan.json events.json --clip match.mp4 --out short.mp4 [--music bed.wav]
  python story_plan.py qc     short.mp4

build needs nothing but Python 3. check uses Pillow to measure text if it's installed.
render and --clip need ffmpeg and ffprobe on the PATH. Everything else is in story_rules.py.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
import story_rules as R

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON03 = os.path.join(HERE, "..", "lesson03-freeze-rewind", "freeze_rewind.py")
ROUND = 4


# ---- pieces: the building blocks of every segment ---------------------------------------------
# play   : source footage from src_in to src_out at a speed (2.0 = twice as fast, 0.5 = slow-mo)
# freeze : one source frame held for dur seconds
# rewind : source footage src_in..src_out played backwards, squeezed into dur seconds
# card   : the end card, dur seconds
def play(a, b, speed=1.0):
    return {"type": "play", "src_in": round(a, ROUND), "src_out": round(b, ROUND), "speed": speed}


def piece_len(p):
    return (p["src_out"] - p["src_in"]) / p["speed"] if p["type"] == "play" else p["dur"]


def piece_readable(p):
    """Seconds of this piece a viewer can actually follow on a phone."""
    if p["type"] == "play":
        return piece_len(p) if p["speed"] <= R.READABLE_SPEED else 0.0
    return p["dur"] if p["type"] == "freeze" else 0.0


def effect_pieces(effect, k, b, r):
    """Pieces for one beat: b seconds of build-up before the kill at k, r seconds of reaction after."""
    if effect in ("cut", "kinetic-text"):
        return [play(k - b, k + r)]
    if effect == "hold":                  # linger on the empty moment right before the kill
        e = min(0.25, b / 2)
        return [play(k - b, k - e), {"type": "freeze", "at": round(k - e, ROUND), "dur": 0.5}, play(k - e, k + r)]
    if effect == "speed-ramp":            # rush through the approach, real speed for the fight
        return [play(k - b, k - 0.6, 2.0), play(k - 0.6, k + r)]
    if effect == "freeze-rewind":         # lesson 3: kill frame frozen, rewind, then play through
        return [{"type": "freeze", "at": round(k, ROUND), "dur": 0.3},
                {"type": "rewind", "src_in": round(k - b, ROUND), "src_out": round(k, ROUND), "dur": 0.3},
                play(k - b, k + r)]
    if effect == "slowmo":                # payoff: 1 s around the kill at half speed
        return [play(k - b, k - 0.3), play(k - 0.3, k + 0.7, 0.5), play(k + 0.7, k + r)]
    raise ValueError(f"unknown effect '{effect}'. Use one of: {', '.join(R.EFFECTS)}")


MIN_BUILD = {"speed-ramp": 1.0, "hold": 0.5, "slowmo": 0.4}
MIN_REACT = {"slowmo": 0.9}


def fit(effect, k, target, lo, hi, build=None, react=None):
    """Pick build-up and reaction lengths so the beat lasts about `target` seconds,
    without reaching back before `lo` or past `hi` in the source footage."""
    bmin, rmin = MIN_BUILD.get(effect, 0.3), MIN_REACT.get(effect, 0.3)

    def sizes(s):
        b = build if build is not None else min(max(0.6 * s, bmin), k - lo)
        r = react if react is not None else min(max(0.4 * s, rmin), hi - k)
        return max(b, 0.05), max(r, 0.05)

    def length(s):
        return sum(piece_len(p) for p in effect_pieces(effect, k, *sizes(s)))

    a, z = 0.0, 60.0
    for _ in range(50):
        m = (a + z) / 2
        a, z = (m, z) if length(m) < target else (a, m)
    b, r = sizes(a)
    return round(b * R.FPS) / R.FPS, round(r * R.FPS) / R.FPS     # whole frames, so kills land on a frame


# ---- build -------------------------------------------------------------------------------------
def default_label(e):
    note = (e.get("note") or "KILL").upper()
    words = note.split()
    if e.get("dist_m") and str(e["dist_m"]) not in note:
        words = [f"{e['dist_m']}M"] + words
    return " ".join(words[:R.MAX_CAPTION_WORDS])


def fit_text(text, size, at, dur, style, y, **extra):
    while len(R.wrap(text, size)) > R.MAX_LINES and size > R.MIN_TEXT_PX:
        size -= 4
    t = {"text": text, "at": round(at, 3), "dur": round(dur, 3), "size": size, "style": style, "y": y}
    t.update(extra)
    return t


def build(cfg, beats):
    ev = R.load_events(cfg)
    by_id = {e["id"]: e for e in ev}
    clip = beats.get("clip") or cfg.get("clip")

    def kill(spec, what):
        kid = spec.get("kill")
        if kid not in by_id:
            sys.exit(f"{what}: kill {kid} is not in events.json (kills are numbered 1 to {len(ev)} in match order)")
        return by_id[kid]

    story = [("beat", b) for b in beats["beats"]] + [("risky", beats["risky"]), ("payoff", beats["payoff"])]
    used = {kill(s, sec)["id"] for sec, s in story if "kill" in s} | {kill(beats["hook"], "hook")["id"]}
    unused = [e["t"] for e in ev if e["id"] not in used]

    segs = []
    # hook: starts on the exact frame the kill lands
    hk = kill(beats["hook"], "hook")
    hook_len = min(float(beats["hook"].get("len", 1.8)), R.HOOK_MAX)
    nxt = [e["t"] for e in ev if e["t"] > hk["t"]]
    hook_len = min(hook_len, (nxt[0] - hk["t"] - 0.1) if nxt else hook_len)
    hp = [play(hk["t"], hk["t"] + hook_len)]
    if beats["hook"].get("effect") == "freeze":
        hp = [{"type": "freeze", "at": hk["t"], "dur": 0.3}, play(hk["t"], hk["t"] + hook_len - 0.3)]
    segs.append({"section": "hook", "kill": hk["id"], "effect": beats["hook"].get("effect", "cut"), "pieces": hp,
                 "texts": [fit_text(beats["hook"]["text"], 96, 0.0, hook_len, "gold", 0.30)]})

    # setup: footage the owner picked, ending before the first story kill
    su = beats["setup"]
    first_k = min(kill(s, sec)["t"] for sec, s in story if "kill" in s)
    s_len = float(su.get("len", R.SETUP_END - 0.2 - hook_len))
    s_in = float(su.get("from", max(0.0, first_k - 3.0 - s_len)))
    s_out = min(float(su.get("to", s_in + s_len)), first_k - 1.0,
                min([u - 0.4 for u in unused if u > s_in] or [1e9]))
    segs.append({"section": "setup", "effect": "cut", "pieces": [play(s_in, s_out)],
                 "texts": [fit_text(su["text"], 84, 0.15, s_out - s_in - 0.3, "white", 0.30)]})

    # beats, risky, payoff: in match order, each one fitted to its share of the time
    n = len(beats["beats"])
    t_now = hook_len + (s_out - s_in)
    end_beats, end_risky, end_payoff = 25.0, 31.5, R.MAX_TOTAL - R.END_CARD
    lo = s_out
    story_kills = [kill(s, sec)["t"] if "kill" in s else None for sec, s in story]
    for i, (sec, spec) in enumerate(story):
        effect = spec.get("effect", "slowmo" if sec == "payoff" else "cut")
        if sec == "beat":
            target = (end_beats - t_now) / (n - i)
        elif sec == "risky":
            target = end_risky - t_now
        else:
            target = end_payoff - t_now
        if "kill" in spec:
            e = kill(spec, sec)
            k = e["t"]
            later = [t for t in story_kills[i + 1:] if t is not None]
            hi = min([u - 0.4 for u in unused if u > k] + [t - 1.0 for t in later] + [1e9])
            lo_k = max([lo] + [u + 0.4 for u in unused if u < k])
            b, r = fit(effect, k, target, lo_k, hi, spec.get("build"), spec.get("react"))
            pieces = effect_pieces(effect, k, b, r)
            label = spec.get("label") or default_label(e)
        else:                               # a risky call that isn't a kill: owner gives the footage
            pieces = [play(float(spec["from"]), float(spec["to"]))]
            label, e = spec["label"], None
        seg = {"section": sec, "effect": effect, "pieces": pieces, "texts": []}
        if e:
            seg["kill"] = e["id"]
        seg_len = sum(piece_len(p) for p in pieces)
        kill_at = kill_time_in(seg, e["t"]) if e else 0.0
        if effect == "kinetic-text":
            at = kill_at
            seg["texts"].append(fit_text(label, 92, at, max(seg_len - at - 0.1, 0.8), "slam", 0.62, kinetic=True))
        elif sec == "risky":
            seg["texts"].append(fit_text(label, 84, 0.1, seg_len - 0.2, "red", 0.30))
        else:
            need = R.reading_time(label)
            at = max(0.1, min(kill_at - 0.4, seg_len - 0.1 - need))
            seg["texts"].append(fit_text(label, 96 if sec == "payoff" else 84, at, seg_len - at - 0.1,
                                         "gold" if sec == "payoff" else "white", 0.30))
        segs.append(seg)
        t_now += seg_len
        lo = max(p.get("src_out", p.get("at", 0)) for p in pieces)

    nxt = beats.get("next", "").strip()
    if nxt and not nxt.lower().startswith("next"):
        nxt = "Next: " + nxt
    end_texts = [fit_text(R.HANDLE, 80, 0.0, R.END_CARD, "white", 0.40),
                 fit_text(R.TWITCH, 64, 0.0, R.END_CARD, "white", 0.47),
                 fit_text(nxt, 64, 0.0, R.END_CARD, "gold", 0.56)]
    last_src = max(p.get("src_out", p.get("at", 0)) for p in segs[-1]["pieces"])
    segs.append({"section": "end", "effect": "card",
                 "pieces": [{"type": "card", "dur": R.END_CARD, "bg_at": round(last_src - R.FRAME, ROUND)}],
                 "texts": end_texts})

    plan = {"version": 1, "format": R.HOOK_FORMAT, "fps": R.FPS, "size": [R.W, R.H], "clip": clip,
            "segments": segs,
            "counter": {"show": bool(beats.get("counter", True)), "cash": bool(beats.get("cash", True)),
                        "size": 44, "y": 0.085}}
    layout(plan)
    plan["counter"]["steps"] = counter_steps(plan, ev)
    return plan


def layout(plan):
    """Write out_start/out_end on every segment and make text times absolute."""
    t = 0.0
    for s in plan["segments"]:
        L = sum(piece_len(p) for p in s["pieces"])
        rel = s.get("_rel", True)
        s["out_start"], s["out_end"] = round(t, 3), round(t + L, 3)
        if rel:
            for x in s["texts"]:
                x["at"] = round(x["at"] + t, 3)
        s.pop("_rel", None)
        t += L
    plan["total"] = round(t, 3)


def layout_again(plan):
    """After editing pieces by hand: recompute segment times, keep each text at the same offset
    inside its segment. The kill counter is left alone, so check shows if it no longer matches."""
    t = 0.0
    for s in plan["segments"]:
        shift = t - s.get("out_start", t)
        for x in s["texts"]:
            x["at"] = round(x["at"] + shift, 3)
        L = sum(piece_len(p) for p in s["pieces"])
        s["out_start"], s["out_end"] = round(t, 3), round(t + L, 3)
        t += L
    plan["total"] = round(t, 3)


def kill_time_in(seg, t):
    """Seconds from the segment start to the first frame where the kill at source time t is shown."""
    pos = 0.0
    for p in seg["pieces"]:
        if p["type"] == "play" and p["src_in"] - R.FRAME / 2 <= t <= p["src_out"]:
            return pos + max(0.0, t - p["src_in"]) / p["speed"]
        if p["type"] == "freeze" and abs(p["at"] - t) <= R.FRAME:
            return pos
        pos += piece_len(p)
    return None


def shown_kills(plan, ev):
    """Every kill that is on screen after the cuts, with the Short time it first shows up.
    The hook is a flash-forward, so a kill there only counts if it never comes back later."""
    first, hook_only = {}, {}
    for s in plan["segments"]:
        if s["section"] == "end":
            continue
        start = s.get("out_start", 0.0)
        for e in ev:
            at = kill_time_in(s, e["t"])
            if at is None:
                continue
            if s["section"] == "hook":
                hook_only.setdefault(e["id"], start + at)
            else:
                first.setdefault(e["id"], (start + at, s["section"]))
    for kid, at in hook_only.items():
        first.setdefault(kid, (at, "hook"))
    return sorted(((kid, at, sec) for kid, (at, sec) in first.items()), key=lambda x: x[1])


def counter_steps(plan, ev):
    by_id = {e["id"]: e for e in ev}
    steps, cash = [], 0
    for i, (kid, at, _) in enumerate(shown_kills(plan, ev), 1):
        cash += by_id[kid].get("amount", 0)
        steps.append({"at": round(at, 3), "kill": kid, "kills": i, "cash": cash})
    return steps


# ---- check -------------------------------------------------------------------------------------
def check(plan, cfg, clip=None):
    """Return (fails, warns). A plan with any fail must not be rendered or posted."""
    F, Wn = [], []
    ev = R.load_events(cfg)
    by_id = {e["id"]: e for e in ev}
    segs = plan.get("segments", [])
    if plan.get("fps") != R.FPS or plan.get("size") != [R.W, R.H]:
        F.append(f"plan must be vertical {R.W}x{R.H} at {R.FPS} fps")

    # order of sections
    names = [s["section"] for s in segs]
    nb = names.count("beat")
    want = ["hook", "setup"] + ["beat"] * nb + ["risky", "payoff", "end"]
    if names != want:
        F.append(f"sections must run hook, setup, 3-4 beats, risky, payoff, end. Got: {', '.join(names)}")
    if not R.BEATS_MIN <= nb <= R.BEATS_MAX:
        F.append(f"{nb} rising beats; the format needs {R.BEATS_MIN} to {R.BEATS_MAX}")

    # times, recomputed from the pieces (never trust the stored numbers)
    t = 0.0
    for s in segs:
        L = sum(piece_len(p) for p in s["pieces"])
        for p in s["pieces"]:
            if p["type"] == "play" and p["src_out"] <= p["src_in"]:
                F.append(f"{s['section']}: a piece ends before it starts ({p['src_in']} -> {p['src_out']})")
        if abs(s.get("out_start", t) - t) > 2 * R.FRAME or abs(s.get("out_end", t + L) - (t + L)) > 2 * R.FRAME:
            F.append(f"{s['section']}: stored times {s.get('out_start')}-{s.get('out_end')} don't match the "
                     f"footage ({t:.3f}-{t + L:.3f}). Run build again after editing pieces.")
        s["_t0"], s["_t1"] = t, t + L
        t += L
    total = t
    if total > R.MAX_TOTAL + 1e-6:
        F.append(f"total length {total:.2f} s is over {R.MAX_TOTAL:.0f} s")
    if total < 30:
        Wn.append(f"total is only {total:.1f} s; the format is built for close to {R.MAX_TOTAL:.0f} s")

    # frame one is a kill landing
    if segs:
        p0 = segs[0]["pieces"][0]
        src0 = p0.get("src_in", p0.get("at"))
        if segs[0]["section"] != "hook" or p0["type"] not in ("play", "freeze") or \
                not any(abs(e["t"] - src0) <= R.FRAME for e in ev):
            F.append("the first frame is not a kill: the hook must start on the exact frame a kill in "
                     "events.json lands")

    sec = {n: [s for s in segs if s["section"] == n] for n in set(names)}
    # time windows
    if sec.get("hook") and sec["hook"][0]["_t1"] > R.HOOK_MAX + R.FRAME:
        F.append(f"hook runs to {sec['hook'][0]['_t1']:.2f} s; it must end by {R.HOOK_MAX:.0f} s")
    if sec.get("setup") and sec["setup"][0]["_t1"] > R.SETUP_END + R.FRAME:
        F.append(f"setup runs to {sec['setup'][0]['_t1']:.2f} s; it must end by {R.SETUP_END:.0f} s")
    if sec.get("risky"):
        r = sec["risky"][0]
        if r["_t1"] < R.RISKY_WINDOW[0] or r["_t0"] > R.RISKY_WINDOW[1]:
            Wn.append(f"risky call sits at {r['_t0']:.1f}-{r['_t1']:.1f} s; the format puts it around "
                      f"{R.RISKY_WINDOW[0]:.0f}-{R.RISKY_WINDOW[1]:.0f} s")
    if sec.get("payoff"):
        p = sec["payoff"][0]
        if p["_t0"] < R.PAYOFF_WINDOW[0] - 2.5 or p["_t1"] > R.PAYOFF_WINDOW[1] + 0.6:
            Wn.append(f"payoff sits at {p['_t0']:.1f}-{p['_t1']:.1f} s; the format puts it at "
                      f"{R.PAYOFF_WINDOW[0]:.0f}-{R.PAYOFF_WINDOW[1]:.0f} s")
        k = by_id.get(p.get("kill"))
        if not k or not any(q["type"] == "play" and q["speed"] < 1 and q["src_in"] <= k["t"] <= q["src_out"]
                            for q in p["pieces"]):
            F.append("payoff: the best kill must play in slow-mo")
        best = max(ev, key=lambda e: e.get("amount", 0))
        if k and k.get("amount", 0) < best.get("amount", 0):
            Wn.append(f"payoff uses kill {k['id']} (${k['amount']:,}), but kill {best['id']} paid more "
                      f"(${best['amount']:,}). Fine if it's the better moment.")

    # end card
    if segs and segs[-1]["section"] == "end":
        e = segs[-1]
        if abs((e["_t1"] - e["_t0"]) - R.END_CARD) > R.FRAME:
            F.append(f"end card must be the last {R.END_CARD} s")
        txt = " | ".join(x["text"] for x in e["texts"])
        if R.HANDLE not in txt:
            F.append(f"end card is missing {R.HANDLE}")
        if "reydiant" not in txt.lower() or "twitch" not in txt.lower():
            F.append("end card is missing the twitch handle")
        nxt = [x["text"] for x in e["texts"] if x["text"].lower().startswith("next")]
        if not nxt or len(nxt[0].split()) < 2:
            F.append("end card needs a one-line 'Next:' teaser")
        elif len(nxt[0].split()) > 8:
            F.append(f"'Next:' teaser is {len(nxt[0].split())} words; keep it to 8")
        for b in R.banned_in(txt):
            F.append(f"end card: banned '{b}' (no subscribe ask)")
    else:
        F.append("the last segment must be the end card")

    # every story section: its kill is in its footage, enough readable time, match order
    story = [s for s in segs if s["section"] in ("setup", "beat", "risky", "payoff")]
    prev_max, prev_name = None, None
    for s in story:
        srcs = [v for p in s["pieces"] for v in (p.get("src_in"), p.get("src_out"), p.get("at")) if v is not None]
        if prev_max is not None and min(srcs) < prev_max - 0.05:
            F.append(f"{s['section']} (kill {s.get('kill', '-')}) starts at {min(srcs):.2f} s in the match, before "
                     f"the {prev_name} ends ({prev_max:.2f} s). Beats must stay in match order.")
        prev_max, prev_name = max(srcs), s["section"]
        if s["section"] in ("beat", "risky", "payoff"):
            rd = sum(piece_readable(p) for p in s["pieces"])
            if rd < R.MIN_READABLE - 1e-6:
                F.append(f"{s['section']} (kill {s.get('kill', '-')}) has {rd:.2f} s of readable footage; "
                         f"needs {R.MIN_READABLE:.0f} s (fast-forward and rewind don't count)")
            if s.get("kill") is not None:
                k = by_id.get(s["kill"])
                if not k:
                    F.append(f"{s['section']}: kill {s['kill']} is not in events.json")
                elif kill_time_in(s, k["t"]) is None:
                    F.append(f"{s['section']}: kill {s['kill']} at {k['t']} s is not inside its footage")
        if s.get("effect") not in R.EFFECTS:
            F.append(f"{s['section']}: unknown effect '{s.get('effect')}'")

    # vary the editing
    fx = [s.get("effect") for s in segs if s["section"] in ("beat", "risky", "payoff")]
    for a, b, i in zip(fx, fx[1:], range(len(fx))):
        if a == b:
            F.append(f"two beats in a row use '{a}' (beats {i + 1} and {i + 2}). Vary the edit.")
    beat_fx = {s.get("effect") for s in segs if s["section"] == "beat"}
    if nb and len(beat_fx) < min(3, nb):
        F.append(f"rising beats use only {len(beat_fx)} kind(s) of edit; use at least 3")

    # kill counter matches the kills left after cuts
    shown = shown_kills(plan_with_times(segs, plan), ev)
    want_steps = counter_steps(plan_with_times(segs, plan), ev)
    steps = plan.get("counter", {}).get("steps", [])
    if [x["kill"] for x in steps] != [x["kill"] for x in want_steps]:
        F.append(f"kill counter lists kills {[x['kill'] for x in steps]} but the footage shows kills "
                 f"{[x['kill'] for x in want_steps]} after cuts")
    else:
        for a, b in zip(steps, want_steps):
            if a["kills"] != b["kills"] or a.get("cash") != b["cash"] or abs(a["at"] - b["at"]) > 2 * R.FRAME:
                F.append(f"kill counter step for kill {a['kill']} says {a['kills']} kills / ${a.get('cash', 0):,} "
                         f"at {a['at']:.2f} s; the footage gives {b['kills']} / ${b['cash']:,} at {b['at']:.2f} s")
    story_ids = {s.get("kill") for s in segs}
    for kid, at, where in shown:
        if kid not in story_ids:
            Wn.append(f"kill {kid} is visible in the {where} footage at {at:.2f} s without being that "
                      f"section's story kill. It counts on the counter.")

    # on-screen text: true to events.json, readable on a phone
    ids = {x[0] for x in shown}
    vocab, ok_nums = R.vocabulary(cfg), R.allowed_numbers(cfg, ids)
    for s in segs:
        for x in s["texts"]:
            where = f"{s['section']} text '{x['text']}'"
            if s["section"] != "end":
                for why in R.text_problems(x["text"], vocab, ok_nums):
                    F.append(f"{where}: {why}")
            F.extend(f"{where}: {why}" for why in text_readability(x, s))
    c = plan.get("counter", {})
    if c.get("show") and c.get("size", 0) < R.MIN_SMALL_PX:
        F.append(f"kill counter text is {c.get('size')} px; {R.MIN_SMALL_PX} px is the smallest that reads")

    # source footage
    if clip:
        info = probe(clip)
        if not info:
            F.append(f"can't read {clip} with ffprobe")
        else:
            last = max(v for s in segs for p in s["pieces"] for v in (p.get("src_out"), p.get("at"), p.get("bg_at"))
                       if v is not None)
            if last > info["dur"] + R.FRAME:
                F.append(f"plan uses footage up to {last:.2f} s but {clip} is {info['dur']:.2f} s long")
            if info["fps"] < 59:
                Wn.append(f"{clip} is {info['fps']:.0f} fps. Slow-mo and the 60 fps export look best from 60 fps footage.")
    for s in segs:
        s.pop("_t0", None), s.pop("_t1", None)
    return F, Wn


def plan_with_times(segs, plan):
    tmp = {"segments": [dict(s, out_start=s["_t0"]) for s in segs]}
    return tmp


def text_readability(x, s):
    why = []
    small = x.get("style") == "small"
    if x["size"] < (R.MIN_SMALL_PX if small else R.MIN_TEXT_PX):
        why.append(f"{x['size']} px is too small for a phone (min {R.MIN_TEXT_PX})")
    lines = R.wrap(x["text"], x["size"])
    if len(lines) > R.MAX_LINES:
        why.append(f"needs {len(lines)} lines at {x['size']} px; max {R.MAX_LINES}")
    for ln in lines:
        if R.text_width(ln, x["size"]) > R.SAFE_X1 - R.SAFE_X0:
            why.append(f"'{ln}' is wider than the safe area")
    block = len(lines) * x["size"] * 1.15
    top, bot = x["y"] * R.H - block / 2, x["y"] * R.H + block / 2
    if top < R.SAFE_Y0 or bot > R.SAFE_Y1:
        why.append(f"sits at {top:.0f}-{bot:.0f} px, outside the area the Shorts buttons don't cover "
                   f"({R.SAFE_Y0}-{R.SAFE_Y1})")
    need = R.reading_time(x["text"]) if s["section"] != "end" else 1.2
    if x["dur"] + 1e-6 < need:
        why.append(f"on screen {x['dur']:.2f} s; needs {need:.2f} s to read")
    if x["at"] < s["_t0"] - R.FRAME or x["at"] + x["dur"] > s["_t1"] + R.FRAME:
        why.append(f"runs outside its section ({s['_t0']:.2f}-{s['_t1']:.2f} s)")
    return why


# ---- ffmpeg helpers ----------------------------------------------------------------------------
def probe(path):
    if not os.path.exists(path) or not shutil.which("ffprobe"):
        return None

    def run(args):
        return subprocess.run(["ffprobe", "-v", "error"] + args + [path], capture_output=True, text=True).stdout.strip()
    try:
        num, den = run(["-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0"]).split("/")
        dur = float(run(["-show_entries", "format=duration", "-of", "csv=p=0"]))
        aud = bool(run(["-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0"]))
        return {"fps": float(num) / float(den), "dur": dur, "audio": aud}
    except ValueError:
        return None


def ff(args, cwd=None):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args, cwd=cwd,
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed:\n" + " ".join(args) + "\n" + r.stderr[-2000:])
    return r


def atempo(speed):
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.5f}")
    return ",".join(parts)


VF = f"scale={R.W}:{R.H}:force_original_aspect_ratio=increase,crop={R.W}:{R.H},fps={R.FPS},setsar=1,format=yuv420p"
# Pieces keep their audio as plain PCM in .mov files. AAC adds padding to every piece, and over
# ten pieces that drifted the sound 0.08 s and made the Short too long. AAC is applied once, at the end.
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(R.FPS),
       "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]


def render_piece(p, clip, has_audio, out, tmp):
    d = piece_len(p)
    sil = ["-f", "lavfi", "-t", f"{d:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]
    if p["type"] == "play":
        a, s = p["src_in"], p["speed"]
        src = ["-ss", f"{a:.4f}", "-t", f"{p['src_out'] - a:.4f}", "-i", clip]
        vf = f"[0:v]setpts=(PTS-STARTPTS)/{s},{VF}[v]"
        af = f"[0:a]asetpts=PTS-STARTPTS,{atempo(s)},aresample=48000[a]" if has_audio else "[1:a]anull[a]"
    elif p["type"] == "freeze":
        src = ["-ss", f"{p['at']:.4f}", "-t", f"{p['dur']:.4f}", "-i", clip]
        vf = f"[0:v]trim=end_frame=1,{VF},tpad=stop_mode=clone:stop_duration={d:.4f},setpts=PTS-STARTPTS[v]"
        af = (f"[0:a]asetpts=PTS-STARTPTS,volume=0.4,afade=t=out:st={max(0, d - 0.1):.3f}:d=0.1,"
              f"aresample=48000,apad[a]") if has_audio else "[1:a]anull[a]"
    elif p["type"] == "rewind":
        a, b = p["src_in"], p["src_out"]
        s = (b - a) / d
        src = ["-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-i", clip]
        vf = f"[0:v]reverse,setpts=(PTS-STARTPTS)/{s:.5f},{VF},eq=saturation=0.6[v]"
        af = (f"[0:a]asetpts=PTS-STARTPTS,areverse,{atempo(s)},volume=0.35,aresample=48000[a]"
              if has_audio else "[1:a]anull[a]")
    else:                                   # end card: the last frame of the payoff, darkened and blurred
        src = ["-ss", f"{max(0, p['bg_at']):.4f}", "-t", "0.1", "-i", clip]
        vf = (f"[0:v]trim=end_frame=1,{VF},gblur=sigma=18,eq=brightness=-0.32:saturation=0.5,"
              f"tpad=stop_mode=clone:stop_duration={d:.4f},setpts=PTS-STARTPTS[v]")
        af = "[1:a]anull[a]"
    ff(src + sil + ["-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]", "-t", f"{d:.4f}"] + ENC + [out])


def render_freeze_rewind(seg, clip, out, tmp):
    """Use lesson 3's freeze-rewind look for the whole beat, then normalise it to match the other pieces."""
    fr, rw, pl = seg["pieces"]
    tail = pl["src_out"] - fr["at"]
    lead = fr["at"] - pl["src_in"]
    raw = os.path.join(tmp, "l03_" + os.path.basename(out))
    r = subprocess.run([sys.executable, LESSON03, clip, "--hit", f"{fr['at']:.4f}", "--out", raw,
                        "--lead", f"{lead:.4f}", "--freeze", str(fr["dur"]), "--rewind", str(rw["dur"]),
                        "--tail", f"{tail:.4f}"], capture_output=True, text=True)
    if r.returncode or not os.path.exists(raw):
        return False
    d = sum(piece_len(p) for p in seg["pieces"])
    has_a = probe(raw)["audio"]
    sil = ["-f", "lavfi", "-t", f"{d:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]
    ff(["-i", raw] + sil + ["-filter_complex", f"[0:v]{VF},tpad=stop_mode=clone:stop_duration=1[v];"
        + ("[0:a]aresample=48000,apad[a]" if has_a else "[1:a]anull[a]"),
        "-map", "[v]", "-map", "[a]", "-t", f"{d:.4f}"] + ENC + [out])
    return True


def esc_path(p):
    return p.replace("\\", "/").replace(":", "\\:")


def drawtexts(plan, tmp):
    """drawtext filters for every caption plus the kill counter. Text goes through files so
    colons, quotes and dollar signs need no escaping."""
    font = os.path.join(tmp, "font.ttf")
    shutil.copy(R.FONT, font)
    colors = {"white": "0xF2EFE8", "gold": "0xF5B93A", "red": "0xFF4646", "slam": "0xFFFFFF", "small": "0xE8E4DA"}
    out, n = [], 0

    def one(text, size, x_expr, y_px, color, a, b, fade=0.12):
        nonlocal n
        n += 1
        tf = os.path.join(tmp, f"t{n:03d}.txt")
        open(tf, "w", encoding="utf-8").write(text)
        alpha = f"if(lt(t,{a + fade:.3f}),(t-{a:.3f})/{fade},if(gt(t,{b - 0.08:.3f}),({b:.3f}-t)/0.08,1))"
        out.append(f"drawtext=fontfile='{esc_path(font)}':textfile='{esc_path(tf)}':fontsize={size}:"
                   f"fontcolor={color}:borderw={max(3, size // 12)}:bordercolor=0x0B0A10:shadowx=0:shadowy=6:"
                   f"shadowcolor=0x000000@0.6:x={x_expr}:y={y_px:.0f}:alpha='{alpha}':"
                   f"enable='between(t,{a:.3f},{b:.3f})'")

    for s in plan["segments"]:
        for x in s["texts"]:
            lines = R.wrap(x["text"], x["size"])
            lh = x["size"] * 1.15
            top = x["y"] * R.H - len(lines) * lh / 2
            for i, ln in enumerate(lines):
                one(ln, x["size"], "(w-text_w)/2", top + i * lh, colors.get(x["style"], "0xFFFFFF"),
                    x["at"], x["at"] + x["dur"], 0.05 if x.get("kinetic") else 0.12)
    c = plan.get("counter", {})
    if c.get("show") and c.get("steps"):
        end = plan["segments"][-1]["out_start"]
        st = c["steps"]
        for i, step in enumerate(st):
            b = st[i + 1]["at"] if i + 1 < len(st) else end
            txt = f"KILLS {step['kills']}" + (f"   ${step['cash']:,}" if c.get("cash") else "")
            one(txt, c["size"], str(R.SAFE_X0 + 20), c["y"] * R.H, colors["small"], step["at"], b, 0.01)
    return out


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1]
    return json.loads(j)


def master(src, out, total, tmp, target=-14.0, tp_max=-1.2):
    """Mux the video with audio at -14 LUFS and true peak under -1 dB, measured on the finished
    AAC file. A gain, then a limiter running at 4x the sample rate (it catches peaks between
    samples). AAC can push peaks up by a few dB on noisy sounds like gunshots, so the loop measures
    the real output and lowers the limiter or fixes the gain until both numbers pass (up to 6 tries)."""
    gain, ceiling = target - float(loudness(src)["input_i"]), -2.0
    wav = os.path.join(tmp, "master.wav")
    for _ in range(6):
        ff(["-i", src, "-vn", "-af", f"volume={gain:.2f}dB,aresample=192000,"
            f"alimiter=limit={10 ** (ceiling / 20):.4f}:attack=1:release=60:level=false,aresample=48000",
            "-c:a", "pcm_s16le", wav])
        ff(["-i", src, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-ar", "48000", "-t", f"{total:.3f}", "-movflags", "+faststart", out])
        m = loudness(out)
        I, TP = float(m["input_i"]), float(m["input_tp"])
        if abs(I - target) <= 0.5 and TP <= tp_max:
            return
        if TP > tp_max:
            ceiling -= TP - tp_max + 0.3
        gain += target - I


def render(plan, cfg, clip, out, music=None, music_db=-6.0, keep=False):
    F, Wn = check(plan, cfg, clip)
    if F:
        print_report(F, Wn)
        sys.exit("Not rendering: the plan fails its checks.")
    info = probe(clip)
    tmp = tempfile.mkdtemp(prefix="story_", dir=os.path.dirname(os.path.abspath(out)) or ".")
    parts = []
    for i, s in enumerate(plan["segments"]):
        if s["effect"] == "freeze-rewind" and os.path.exists(LESSON03):
            p = os.path.join(tmp, f"seg{i:02d}.mov")
            if render_freeze_rewind(s, clip, p, tmp):
                parts.append(p)
                print(f"  {s['section']:<6} freeze-rewind (lesson 3)")
                continue
        for j, pc in enumerate(s["pieces"]):
            p = os.path.join(tmp, f"seg{i:02d}_{j}.mov")
            render_piece(pc, clip, info["audio"], p, tmp)
            parts.append(p)
        print(f"  {s['section']:<6} {s['effect']}")
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(p)}'\n" for p in parts))
    joined = os.path.join(tmp, "joined.mov")
    ff(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mov"], cwd=tmp)

    vf = ",".join(drawtexts(plan, tmp)) or "null"
    total = plan["total"]
    ins = ["-i", joined]
    if music:
        ins += ["-i", music]
        af = (f"[1:a]volume={music_db}dB,apad,atrim=0:{total:.3f}[m];"
              f"[0:a][m]amix=inputs=2:normalize=0:duration=first[mix]")
    else:
        af = "[0:a]anull[mix]"
    pre = os.path.join(tmp, "pre.mov")
    final_v = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "24M", "-bufsize", "48M",
               "-pix_fmt", "yuv420p", "-r", str(R.FPS), "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
    ff(ins + ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[mix]", "-t", f"{total:.3f}"]
       + final_v + [pre])                   # capped at 24 Mbps, inside YouTube's range for 1080p60
    master(pre, out, total, tmp)            # -14 LUFS, true peak under -1 dB, measured on the final file
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
    if not qc(out):
        sys.exit("QC failed: see the FAIL lines above. Don't post this version.")


def qc(path):
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,r_frame_rate", "-show_entries", "format=duration", "-of", "json", path],
                        capture_output=True, text=True)
    j = json.loads(pr.stdout)
    v, d = j["streams"][0], float(j["format"]["duration"])
    num, den = v["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    m = loudness(path)
    I, TP = float(m["input_i"]), float(m["input_tp"])
    rows = [("size", f"{v['width']}x{v['height']}", (v["width"], v["height"]) == (R.W, R.H)),
            ("fps", f"{fps:g}", abs(fps - R.FPS) < 0.01),
            ("length", f"{d:.2f} s", d <= R.MAX_TOTAL + 0.05),
            ("loudness", f"{I:.1f} LUFS", abs(I + 14) <= 1.0),
            ("true peak", f"{TP:.1f} dBTP", TP < -1.0)]
    print(f"\nQC {path}")
    for name, val, ok in rows:
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<10} {val}")
    return all(ok for *_, ok in rows)


# ---- export for the other lessons --------------------------------------------------------------
def export(plan, cfg, outdir):
    os.makedirs(outdir, exist_ok=True)
    ev = {e["id"]: e for e in R.load_events(cfg)}
    steps = plan["counter"]["steps"]
    music = {"events": [{"t": s["at"], "amount": ev[s["kill"]].get("amount", 0),
                         "headshot": bool(ev[s["kill"]].get("headshot"))} for s in steps]}
    json.dump(music, open(os.path.join(outdir, "music_events.json"), "w"), indent=2)
    style = {"white": "slam", "slam": "slam", "gold": "gold", "red": "red"}
    words = {"bpm": 120, "fps": R.FPS, "duration": plan["total"],
             "words": [{"text": x["text"], "t": x["at"], "dur": x["dur"], "style": style.get(x["style"], "slam"),
                        "y": x["y"]} for s in plan["segments"] if s["section"] != "end" for x in s["texts"]]}
    json.dump(words, open(os.path.join(outdir, "kinetic_words.json"), "w"), indent=2)
    clip = plan.get("clip") or "match.mp4"
    lines = ["# Commands for the other lessons, made from this plan. Run them from shorts-toolkit/.", "",
             "# Lesson 2: original music that hits on every kill in the Short (dark mood fits the channel).",
             f"python lesson02-kill-synced-music/music_bed.py render {outdir}/music_events.json --out {outdir} "
             f"--prefix story --mood dark",
             "# Then use story_bed_under_game_-20LUFS.wav as --music for story_plan.py render.", "",
             "# Lesson 5: slam-in text. Set bpm in kinetic_words.json to the bpm music_bed.py printed first.",
             f"python lesson05-kinetic-text/kinetic_text.py {outdir}/kinetic_words.json --out {outdir}/kinetic", ""]
    for s in plan["segments"]:
        if s["effect"] == "freeze-rewind":
            fr, rw, pl = s["pieces"]
            lines += [f"# Lesson 3: {s['section']} kill {s.get('kill')} (render does this for you)",
                      f"python lesson03-freeze-rewind/freeze_rewind.py {clip} --hit {fr['at']} "
                      f"--lead {fr['at'] - pl['src_in']:.3f} --tail {pl['src_out'] - fr['at']:.3f} "
                      f"--out {outdir}/kill{s.get('kill')}_freeze_rewind.mp4", ""]
    lines += ["# Lesson 4: blend the end card back into frame one so the replay is seamless.",
              "python lesson04-loop-ending/loop_ending.py make short.mp4 --out short_loop.mp4 --blend 0.3",
              "python lesson04-loop-ending/loop_ending.py check short_loop.mp4"]
    open(os.path.join(outdir, "commands.txt"), "w").write("\n".join(lines) + "\n")
    print("wrote", ", ".join(os.path.join(outdir, f) for f in ("music_events.json", "kinetic_words.json", "commands.txt")))


# ---- reporting ----------------------------------------------------------------------------------
def timeline(plan, cfg):
    ev = {e["id"]: e for e in R.load_events(cfg)}
    print(f"\n{'time':<13}{'section':<8}{'edit':<14}{'source':<17}text")
    for s in plan["segments"]:
        srcs = [v for p in s["pieces"] for v in (p.get("src_in"), p.get("src_out"), p.get("at")) if v is not None]
        src = f"{min(srcs):6.2f}-{max(srcs):6.2f}" if s["section"] != "end" else "card"
        txt = " / ".join(x["text"] for x in s["texts"])
        k = f" [kill {s['kill']}]" if s.get("kill") else ""
        print(f"{s['out_start']:5.2f}-{s['out_end']:5.2f}  {s['section']:<8}{s['effect']:<14}{src:<17}{txt}{k}")
    st = plan["counter"]["steps"]
    if st:
        order = ", ".join("#%d at %.2fs" % (x["kill"], x["at"]) for x in st)
        print(f"\nkill counter: {len(st)} kills, ${st[-1]['cash']:,} ({order})")
    print(f"total: {plan['total']:.2f} s")


def print_report(F, Wn):
    for w in Wn:
        print("  warn ", w)
    for f in F:
        print("  FAIL ", f)
    print(f"\nSTATUS: {'PLAN PASSES' if not F else f'PLAN FAILS ({len(F)} problem(s))'}")


def main():
    ap = argparse.ArgumentParser(description="Plan, check and render a one-life-story Short.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="events.json + beats.json -> plan.json")
    b.add_argument("events"); b.add_argument("beats"); b.add_argument("--out", required=True)
    c = sub.add_parser("check", help="fail the plan if it breaks a rule")
    c.add_argument("plan"); c.add_argument("events"); c.add_argument("--clip")
    e = sub.add_parser("export", help="input files for lessons 2, 3, 4 and 5")
    e.add_argument("plan"); e.add_argument("events"); e.add_argument("--out", required=True)
    r = sub.add_parser("render", help="rough cut with captions, counter, end card, -14 LUFS")
    r.add_argument("plan"); r.add_argument("events"); r.add_argument("--clip"); r.add_argument("--out", required=True)
    r.add_argument("--music", help="music bed from lesson 2 (the _under_game_ file)")
    r.add_argument("--music-db", type=float, default=0.0, help="music level change in dB (default 0)")
    r.add_argument("--keep", action="store_true", help="keep the temp folder for debugging")
    q = sub.add_parser("qc", help="size, fps, length, loudness and true peak of a finished video")
    q.add_argument("video")
    a = ap.parse_args()

    if a.cmd == "qc":
        sys.exit(0 if qc(a.video) else 1)
    cfg = json.load(open(a.events, encoding="utf-8"))
    if a.cmd == "build":
        plan = build(cfg, json.load(open(a.beats, encoding="utf-8")))
        json.dump(plan, open(a.out, "w", encoding="utf-8"), indent=2)
        timeline(plan, cfg)
        F, Wn = check(plan, cfg)
        print_report(F, Wn)
        print("wrote", a.out)
        sys.exit(1 if F else 0)
    plan = json.load(open(a.plan, encoding="utf-8"))
    if a.cmd == "check":
        timeline(plan, cfg)
        F, Wn = check(plan, cfg, a.clip)
        print_report(F, Wn)
        sys.exit(1 if F else 0)
    if a.cmd == "export":
        export(plan, cfg, a.out)
    if a.cmd == "render":
        clip = a.clip or plan.get("clip")
        if not clip or not os.path.exists(clip):
            sys.exit(f"footage not found: {clip}. Pass --clip match.mp4")
        render(plan, cfg, clip, a.out, a.music, a.music_db, a.keep)


if __name__ == "__main__":
    main()
