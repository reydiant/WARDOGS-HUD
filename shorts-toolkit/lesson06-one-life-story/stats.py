#!/usr/bin/env python3
"""
stats.py - the Shorts evolution log: what each Short tested, how it did, keep or drop.

  python stats.py show
  python stats.py ship    --short story_v1 --plan plan.json [--length 40]
  python stats.py numbers --short story_v1 --at 24h --stayed 38 --avg-watch 51 [--views 900 --likes 40 --subs 3]
  python stats.py numbers --short story_v1 --at 7d  --stayed 44 --avg-watch 56 [--views 4200 ...]

ship    after you post. Logs the format, the hook format, the new technique and the hypothesis, and
        records the hook format in the LM Studio bridge's rotation. Refuses a technique already used.
numbers the YouTube Studio numbers at 24 hours and 7 days. The 7-day numbers set the verdict:
          keep    stayed >= 45% and average watched >= 50% (close to "10k one life": 55% / 59%)
          drop    stayed <= 30% (no better than the 25% money-counter Short)
          retest  anything in between
        The 24-hour numbers only give an early read.

The log lives in ../shorts-evolution.json, and ../shorts-evolution.md is rewritten from it every time.
The .md is the repo copy of /areas/shorts-evolution.md from Claude's memory. Paste it there to sync.
Plain Python 3, no installs.
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "..", "shorts-evolution.json")
MD = os.path.join(HERE, "..", "shorts-evolution.md")
HOOK_LOG = os.path.join(HERE, "..", "lm-studio-bridge", "hook_log.json")
HYPOTHESIS = "A story with a stake keeps more viewers past the first second and to the end than a counter does."
KEEP = {"stayed": 45, "avg_watch": 50}
DROP_STAYED = 30
TARGET = {"stayed": 70, "avg_watch": 80}          # SHORTS-RULES.md Rule 5

SEED = {
    "hypothesis": HYPOTHESIS,
    "shorts": [
        {"short": "10k one life", "format": "one life (before the story format)", "length_s": 37,
         "stats": {"reported": {"stayed": 55, "avg_watch": 59}}, "verdict": "keep",
         "note": "Best watch time on the channel. Why the owner picked the one-life-story niche."},
        {"short": "latest money Short", "format": "money counter + fast kills", "length_s": None,
         "stats": {"reported": {"stayed": 25}}, "verdict": "drop",
         "note": "Fast kills with little editing. Money counting alone isn't a strong enough niche."},
    ],
}


def load():
    if not os.path.exists(LOG):
        return json.loads(json.dumps(SEED))
    return json.load(open(LOG, encoding="utf-8"))


def save(log):
    json.dump(log, open(LOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(MD, "w", encoding="utf-8").write(markdown(log))


def used_techniques(log):
    return {s["technique"].strip().lower(): s["short"] for s in log["shorts"] if s.get("technique")}


def verdict(st):
    stayed, avg = st.get("stayed"), st.get("avg_watch")
    if stayed is None:
        return None
    if stayed <= DROP_STAYED:
        return "drop"
    if stayed >= KEEP["stayed"] and (avg or 0) >= KEEP["avg_watch"]:
        return "keep"
    return "retest"


def weakest(log):
    """The number furthest below its target in the most recent Short that has numbers."""
    for s in reversed(log["shorts"]):
        st = s["stats"].get("7d") or s["stats"].get("24h") or s["stats"].get("reported")
        if st:
            gaps = {k: TARGET[k] - st[k] for k in TARGET if st.get(k) is not None}
            if gaps:
                k = max(gaps, key=gaps.get)
                name = {"stayed": "stayed-to-watch %", "avg_watch": "average % watched"}[k]
                return f"{name}: {st[k]:g}% on \"{s['short']}\" (target {TARGET[k]}%)"
    return "no numbers yet"


def markdown(log):
    rows = []
    for s in log["shorts"]:
        def cell(stage):
            st = s["stats"].get(stage)
            if not st:
                return ""
            return " / ".join(f"{st[k]:g}%" if st.get(k) is not None else "-" for k in ("stayed", "avg_watch"))
        rows.append(f"| {s['short']} | {s.get('posted') or ''} | {s['format']} | {s.get('hook_format') or ''} | "
                    f"{s.get('technique') or ''} | {s.get('length_s') or ''} | {cell('24h') or cell('reported')} | "
                    f"{cell('7d')} | {s.get('verdict') or 'waiting'} |")
    return "\n".join([
        "# Shorts evolution log",
        "",
        "Repo copy of `/areas/shorts-evolution.md`. `stats.py` rewrites this file, so edit through it, not by hand.",
        "",
        f"**Hypothesis:** {log['hypothesis']}",
        "",
        f"**Weakest number right now:** {weakest(log)}",
        "",
        "| Short | Posted | Format | Hook format | New technique | Length (s) | 24 h stayed / avg watched | "
        "7 d stayed / avg watched | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        f"Verdict at 7 days: keep if stayed is {KEEP['stayed']}% or more and average watched is {KEEP['avg_watch']}% "
        f"or more. Drop if stayed is {DROP_STAYED}% or less. Anything else, retest. The \"10k one life\" and latest "
        f"money Short numbers came from the owner, without a 24 h or 7 d label.",
        "",
    ])


def main():
    ap = argparse.ArgumentParser(description="Shorts evolution log")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    s = sub.add_parser("ship")
    s.add_argument("--short", required=True, help="the version name, like story_v1")
    s.add_argument("--plan", required=True)
    s.add_argument("--length", type=float)
    n = sub.add_parser("numbers")
    n.add_argument("--short", required=True)
    n.add_argument("--at", required=True, choices=["24h", "7d"])
    n.add_argument("--stayed", type=float, required=True, help="stayed to watch, percent")
    n.add_argument("--avg-watch", type=float, required=True, help="average percentage viewed")
    for k in ("views", "likes", "subs"):
        n.add_argument("--" + k, type=int)
    a = ap.parse_args()
    log = load()

    if a.cmd == "ship":
        if any(x["short"] == a.short for x in log["shorts"]):
            sys.exit(f"'{a.short}' is already in the log. Use a new version name.")
        plan = json.load(open(a.plan, encoding="utf-8"))
        tech = (plan.get("new_technique") or "").strip()
        if not tech:
            sys.exit("The plan has no new_technique. Every Short tests one new technique; add it to beats.json and build again.")
        if tech.lower() in used_techniques(log):
            sys.exit(f"'{tech}' was already tested in {used_techniques(log)[tech.lower()]}. Pick a new technique.")
        hook = plan.get("format", "one-life-story")
        log["shorts"].append({"short": a.short, "posted": datetime.date.today().isoformat(), "format": "one-life story",
                              "hook_format": hook, "technique": tech, "length_s": round(a.length or plan.get("total") or 0, 1) or None,
                              "hypothesis": log["hypothesis"], "stats": {}, "verdict": None})
        h = json.load(open(HOOK_LOG, encoding="utf-8")) if os.path.exists(HOOK_LOG) else []
        h.append(hook)
        json.dump(h, open(HOOK_LOG, "w"))
        save(log)
        print(f"logged {a.short}: technique '{tech}', hook format '{hook}' (also recorded in the hook rotation)")
        print("Next: run 'stats.py numbers' with the Studio numbers at 24 hours and at 7 days.")
    elif a.cmd == "numbers":
        hit = [x for x in log["shorts"] if x["short"] == a.short]
        if not hit:
            sys.exit(f"'{a.short}' isn't in the log. Run 'stats.py ship' for it first.")
        x = hit[0]
        st = {"stayed": a.stayed, "avg_watch": a.avg_watch}
        st.update({k: getattr(a, k) for k in ("views", "likes", "subs") if getattr(a, k) is not None})
        x["stats"][a.at] = st
        v = verdict(st)
        if a.at == "7d":
            x["verdict"] = v
            print(f"{a.short} at 7 days: {a.stayed:g}% stayed, {a.avg_watch:g}% watched -> {v.upper()}")
        else:
            print(f"{a.short} at 24 hours: {a.stayed:g}% stayed, {a.avg_watch:g}% watched. Early read: {v}. "
                  f"The verdict waits for the 7-day numbers.")
        save(log)
    else:
        if not os.path.exists(LOG):
            save(log)
        print(markdown(log))


if __name__ == "__main__":
    main()
