#!/usr/bin/env python3
"""
lm_bridge.py - draft Short text with LM Studio, checked by code.

Runs on your Windows PC next to LM Studio. Python 3 only, no installs.

  1. Start the LM Studio local server (Developer tab, port 1234) and load a model.
  2. python lm_bridge.py events.json
  3. Pick from the titles that passed. Nothing that fails a check is shown as ready.

events.json is the same file lesson 1 uses:
  {"events": [{"t": 0.0, "amount": 2100, "headshot": false}, ...]}
Optional keys: "start": 0, "series": "Blood Money #3".

Options:
  --url http://localhost:1234/v1   LM Studio server
  --model NAME                     default: the first model LM Studio reports
  --hook FORMAT                    payoff-first | question | challenge | personality | series
                                   default: next one in rotation, never the same twice in a row
  --record                         write the chosen hook to hook_log.json (do this after you post)
  --tries 3                        how many times to ask the model to fix its own failures
"""
import argparse, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = ["payoff-first", "question", "challenge", "personality", "series"]
TAGS = "#wardogs #shorts #fps #gaming"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
BANNED = ("subscribe", "like and", "link in bio", "insane", "epic")


def facts_from(path, hook):
    cfg = json.load(open(path, encoding="utf-8"))
    ev = cfg["events"]
    total = sum(e["amount"] for e in ev)
    head = sum(1 for e in ev if e.get("headshot"))
    big = max(ev, key=lambda e: e["amount"])
    return {
        "start_amount": cfg.get("start", 0),
        "final_total": total,
        "kill_count": len(ev),
        "headshot_count": head,
        "biggest_kill_amount": big["amount"],
        "biggest_kill_was_headshot": bool(big.get("headshot")),
        "longest_shot_m": max([e["dist_m"] for e in ev if e.get("dist_m")] or [None]),
        "highlights": [{"what": e["note"], "distance_m": e.get("dist_m"), "headshot": bool(e.get("headshot")),
                        "reward": e["amount"]} for e in ev if e.get("note")],
        "hook_format": hook,
        "series": cfg.get("series"),
    }


def next_hook(requested):
    log = os.path.join(HERE, "hook_log.json")
    last = None
    if os.path.exists(log):
        h = json.load(open(log, encoding="utf-8"))
        last = h[-1] if h else None
    if requested:
        if requested == last:
            print(f"note: '{requested}' was also the last Short's hook. Rule: never twice in a row.")
        return requested
    if last in HOOKS:
        return HOOKS[(HOOKS.index(last) + 1) % len(HOOKS)]
    return HOOKS[0]


def allowed_numbers(f):
    vals = {f["start_amount"], f["final_total"], f["kill_count"], f["headshot_count"],
            f["biggest_kill_amount"], f.get("longest_shot_m")}
    for h in f.get("highlights", []):
        vals.update([h.get("distance_m"), h.get("reward")])
    vals.discard(None)
    out = set()
    for v in vals:
        out.add(str(v))
        out.add(f"{v:,}")
    if f["series"]:
        out.update(re.findall(r"\d+", f["series"]))
    return out


UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
MULT = {"hundred": 100, "thousand": 1000, "grand": 1000}
COUNTED = ("headshot", "headshots", "kill", "kills", "shot", "shots")


def spelled_numbers(text):
    """Number words as digit strings, e.g. 'thirty five grand' -> '35000'. Bare 'one' is ignored
    unless it counts something ('one headshot'), so 'one life' is not flagged."""
    toks = re.findall(r"[a-z]+", text.lower())
    out, i = [], 0
    while i < len(toks):
        w = toks[i]
        if w in UNITS or w in TENS:
            if w == "one" and (i + 1 >= len(toks) or toks[i + 1] not in COUNTED):
                i += 1
                continue
            val = 0
            while i < len(toks) and (toks[i] in UNITS or toks[i] in TENS):
                val += UNITS.get(toks[i], 0) + TENS.get(toks[i], 0)
                i += 1
            if i < len(toks) and toks[i] in MULT:
                val *= MULT[toks[i]]
                i += 1
            out.append(str(val))
        else:
            i += 1
    return out


def numbers_in(text):
    digits = [n.replace("$", "") for n in re.findall(r"\$?\d[\d,]*(?:\.\d+)?", text)]
    return digits + spelled_numbers(text)


def check(draft, f):
    """Return a list of reasons the draft fails. Empty list means it passes."""
    bad = {}
    ok_nums = allowed_numbers(f)

    def num_problems(text):
        return [n for n in numbers_in(text) if n.rstrip(",") not in ok_nums and n.replace(",", "") not in {x.replace(",", "") for x in ok_nums}]

    titles = draft.get("titles") or []
    if not titles:
        bad["titles"] = ["no titles"]
    good_titles = []
    for t in titles:
        why = []
        if len(t) > 70:
            why.append("over 70 characters")
        if not re.search(r"[\$\d]", " ".join(t.split()[:4])) and not (f["series"] and t.startswith(f["series"])):
            why.append("number must be in the first 4 words")
        for n in num_problems(t):
            why.append(f"number {n} is not in the facts")
        if EMOJI.search(t):
            why.append("emoji")
        if any(b in t.lower() for b in BANNED):
            why.append("banned word")
        (bad.setdefault("title: " + t, why) if why else good_titles.append(t))
    desc = draft.get("description", "")
    d = []
    lines = [x for x in desc.strip().splitlines() if x.strip()]
    if not desc.strip().endswith(TAGS):
        d.append(f"must end with exactly: {TAGS}")
    body = desc.replace(TAGS, "").strip()
    if len(body.splitlines()) > 2 or len(body) < 10:
        d.append("body must be 1 or 2 short lines")
    for n in num_problems(body):
        d.append(f"number {n} is not in the facts")
    if re.search(r"\bheadshots?\b", body, re.I) and f["headshot_count"] == 0:
        d.append("mentions headshots but the facts say 0")
    if EMOJI.search(desc) or any(b in desc.lower() for b in BANNED):
        d.append("emoji or banned word")
    if d:
        bad["description"] = d
    pc = draft.get("pinned_comment", "")
    p = []
    if not pc.strip().endswith("?"):
        p.append("must end with a question")
    if len(pc) > 200:
        p.append("over 200 characters")
    if re.search(r"kill count|how many (kills|headshots)|final total|how much|what was the (total|final)", pc, re.I):
        p.append("the video already answers this; ask viewers to pick or argue about a specific kill")
    p += [f"number {n} is not in the facts" for n in num_problems(pc)]
    if EMOJI.search(pc) or any(b in pc.lower() for b in BANNED):
        p.append("emoji or banned word")
    if p:
        bad["pinned_comment"] = p
    caps = draft.get("captions") or []
    c = []
    if len(caps) < 1:
        c.append("no captions")
    for cap in caps:
        if not 1 <= len(cap.split()) <= 3:
            c.append(f"'{cap}' is not 1 to 3 words")
        c += [f"number {n} is not in the facts" for n in num_problems(cap)]
    if c:
        bad["captions"] = c
    return good_titles, bad


def ask(url, model, system, user):
    body = json.dumps({"model": model, "temperature": 0.7, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(url + "/chat/completions", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in the model's reply")
    return json.loads(m.group(0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events")
    ap.add_argument("--url", default="http://localhost:1234/v1")
    ap.add_argument("--model")
    ap.add_argument("--hook", choices=HOOKS)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--tries", type=int, default=3)
    a = ap.parse_args()

    hook = next_hook(a.hook)
    f = facts_from(a.events, hook)
    system = open(os.path.join(HERE, "lm_system_prompt.md"), encoding="utf-8").read()
    try:
        ids = [m["id"] for m in json.load(urllib.request.urlopen(a.url + "/models", timeout=10))["data"]]
        chat = [i for i in ids if "embed" not in i.lower()]   # embedding models cannot chat
        model = a.model or chat[0]
    except (urllib.error.URLError, KeyError, IndexError) as e:
        sys.exit(f"Can't reach LM Studio at {a.url} ({e}). Start the local server and load a model.")
    print(f"model: {model}   hook: {hook}\nfacts: {json.dumps(f)}")

    user = "Facts:\n" + json.dumps(f, indent=2)
    draft, titles, bad = None, [], {}
    for i in range(a.tries):
        try:
            draft = ask(a.url, model, system, user)
        except (ValueError, json.JSONDecodeError) as e:
            user += f"\n\nYour last reply was not valid JSON ({e}). Return only the JSON object."
            continue
        titles, bad = check(draft, f)
        if not bad:
            break
        user = ("Facts:\n" + json.dumps(f, indent=2) + "\n\nYour last draft failed these checks. Fix only these:\n"
                + json.dumps(bad, indent=2) + "\n\nLast draft:\n" + json.dumps(draft, indent=2))
        print(f"try {i + 1}: {len(bad)} problem(s), asking for a fix")
    if draft is None:
        sys.exit("The model never returned usable JSON.")

    out = {"model": model, "tries_used": min(i + 1, a.tries) if draft is not None else 0, "hook_format": hook, "facts": f, "passed_titles": titles, "description": draft.get("description"),
           "pinned_comment": draft.get("pinned_comment"), "captions": draft.get("captions"),
           "failed_checks": bad}
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model)          # one output file per model, so runs can be compared
    path = os.path.splitext(a.events)[0] + "." + safe + ".text.json"
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)
    print(f"\nSTATUS: {'ALL CHECKS PASSED' if not bad else 'SOME CHECKS FAILED - fix by hand or rerun'}")
    for t in titles:
        print("  title ok:", t)
    for k, v in bad.items():
        print("  FAIL", k, "->", "; ".join(v))
    print("wrote", path)
    if a.record:
        log = os.path.join(HERE, "hook_log.json")
        h = json.load(open(log)) if os.path.exists(log) else []
        h.append(hook)
        json.dump(h, open(log, "w"))
        print("recorded hook:", hook)


if __name__ == "__main__":
    main()
