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
  --model NAME                     exact name from LM Studio's list. Default: the first chat model it
                                   reports, which may not be the one you loaded; the script warns
  --hook FORMAT                    payoff-first | question | challenge | personality | series | one-life-story
                                   default: next one in rotation, never the same twice in a row
  --plan plan.json                 one-life-story mode: facts come from the kills left in the plan, and the
                                   model also drafts a caption for each beat (hook, setup, beats, risky, payoff)
  --apply                          with --plan: put the captions that passed into plan.captioned.json and
                                   run the full plan check on it
  --record                         write the chosen hook to hook_log.json (do this after you post)
  --tries 3                        how many times to ask the model to fix its own failures
"""
import argparse, copy, json, os, re, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
STORY_DIR = os.path.join(HERE, "..", "lesson06-one-life-story")
sys.path.insert(0, STORY_DIR)
import story_rules as R                    # one list of banned words and voice rules for every check

HOOKS = ["payoff-first", "question", "challenge", "personality", "series", R.HOOK_FORMAT]
TAGS = "#wardogs #shorts #fps #gaming"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
BANNED = R.BANNED                          # includes the old list plus the new hype words and labels


def facts_from(path, hook, keep_ids=None):
    """Facts for the model. keep_ids limits them to the kills left in a story plan, so the
    titles can only quote numbers the Short actually shows."""
    cfg = json.load(open(path, encoding="utf-8"))
    ev = R.load_events(cfg)
    if keep_ids is not None:
        ev = [e for e in ev if e["id"] in keep_ids]
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

    def money_format(text):
        """Numbers of 1,000 or more must be written like $35,000 (dollar sign, comma)."""
        return [m for m in re.findall(r"(?<![\d,$])\d{4,}(?![\d,])|(?<![\d,])\$\d{4,}(?![\d,])", text)]

    def num_problems(text):
        money = money_format(text)
        if money:
            return [f"write {n} as ${int(n.replace('$', '')):,} (dollar sign and comma)" for n in money]
        return [f"number {n} is not in the facts" for n in numbers_in(text)
                if n.rstrip(",") not in ok_nums and n.replace(",", "") not in {x.replace(",", "") for x in ok_nums}]

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
            why.append(f"{n}")
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
        d.append(f"{n}")
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
    p += [f"{n}" for n in num_problems(pc)]
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
        c += [f"{n}" for n in num_problems(cap)]
        if EMOJI.search(cap) or any(b in cap.lower() for b in BANNED):
            c.append(f"'{cap}' is an internal label, an emoji or a banned word")
    if c:
        bad["captions"] = c
    return good_titles, bad


SLOTS = {"hook": "hook", "setup": "setup", "risky": "risky", "payoff": "payoff"}


def story_slots(plan):
    """Caption slots in plan order: hook, setup, beat1..beat4, risky, payoff."""
    out, n = [], 0
    for i, s in enumerate(plan["segments"]):
        if s["section"] == "beat":
            n += 1
            out.append((f"beat{n}", i))
        elif s["section"] in SLOTS:
            out.append((s["section"], i))
    return out


def story_facts(cfg, plan):
    ev = {e["id"]: e for e in R.load_events(cfg)}
    beats = []
    for slot, i in story_slots(plan):
        s = plan["segments"][i]
        e = ev.get(s.get("kill"))
        beats.append({"slot": slot, "edit": s["effect"], "owner_text": s["texts"][0]["text"] if s["texts"] else "",
                      "kill": {"what": e.get("note"), "distance_m": e.get("dist_m"), "headshot": bool(e.get("headshot")),
                               "reward": e.get("amount")} if e else None})
    vocab = sorted(R.vocabulary(cfg) - R.NEUTRAL)
    return {"labels": cfg.get("labels", []), "beats": beats, "story_words": vocab,
            "spanish_ok": sorted(R.SPANISH), "max_caption_words": R.MAX_CAPTION_WORDS}


def check_story(draft, f, cfg, plan, last_hook):
    """Extra checks in one-life-story mode. Returns {slot: [reasons]} for anything that fails."""
    bad = {}
    keep = {x["kill"] for x in plan["counter"]["steps"]}
    vocab, ok = R.vocabulary(cfg), R.allowed_numbers(cfg, keep)
    caps = draft.get("beat_captions") or {}
    for slot, _ in story_slots(plan):
        text = (caps.get(slot) or "").strip()
        why = ["missing"] if not text else R.text_problems(text, vocab, ok)
        if text and EMOJI.search(text):
            why.append("emoji")
        if why:
            bad[f"beat_captions.{slot}: {text}"] = why
    # voice: a Spanish word only where it fits. One per piece, two in the whole package, never the same one twice
    pieces = list(draft.get("titles") or []) + [draft.get("description", ""), draft.get("pinned_comment", "")] \
        + list(draft.get("captions") or []) + list(caps.values())
    found = [w for p in pieces for w in R.spanish_in(p or "")]
    if len(found) > R.SPANISH_PER_PACKAGE or len(set(found)) < len(found):
        bad["voice"] = [f"Spanish words used: {', '.join(found)}. At most {R.SPANISH_PER_PACKAGE} in the whole "
                        f"Short and never the same one twice. Don't force it."]
    for p in pieces:
        if len(R.spanish_in(p or "")) > R.SPANISH_PER_PIECE:
            bad.setdefault("voice", []).append(f"'{p}' has more than one Spanish word")
    if last_hook == R.HOOK_FORMAT:
        bad["hook_format"] = [f"the last Short was also {R.HOOK_FORMAT}. Rule: never the same hook format twice in a row. "
                              f"Post a different format first, or decide to break the rule on purpose."]
    return bad


def apply_captions(draft, cfg, plan):
    """Copy the beat captions into a new plan and run the full plan check on it."""
    import story_plan as SP
    p = copy.deepcopy(plan)
    caps = draft.get("beat_captions") or {}
    for slot, i in story_slots(p):
        if caps.get(slot) and p["segments"][i]["texts"]:
            x = p["segments"][i]["texts"][0]
            x["text"] = caps[slot].strip()
            while len(R.wrap(x["text"], x["size"])) > R.MAX_LINES and x["size"] > R.MIN_TEXT_PX:
                x["size"] -= 4
    F, Wn = SP.check(p, cfg)
    return p, F, Wn


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
    ap.add_argument("--plan")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    system = open(os.path.join(HERE, "lm_system_prompt.md"), encoding="utf-8").read()
    plan = cfg = None
    if a.plan:                               # one-life-story mode
        cfg = json.load(open(a.events, encoding="utf-8"))
        plan = json.load(open(a.plan, encoding="utf-8"))
        log = os.path.join(HERE, "hook_log.json")
        hist = json.load(open(log, encoding="utf-8")) if os.path.exists(log) else []
        last_hook = hist[-1] if hist else None
        hook = R.HOOK_FORMAT
        f = facts_from(a.events, hook, {x["kill"] for x in plan["counter"]["steps"]})
        f["story"] = story_facts(cfg, plan)
        system += "\n\n" + open(os.path.join(HERE, "lm_story_prompt.md"), encoding="utf-8").read()
    else:
        hook = next_hook(a.hook)
        f = facts_from(a.events, hook)
    try:
        ids = [m["id"] for m in json.load(urllib.request.urlopen(a.url + "/models", timeout=10))["data"]]
        chat = [i for i in ids if "embed" not in i.lower()]   # embedding models cannot chat
        model = a.model or chat[0]
        if a.model and a.model not in ids:
            sys.exit(f"Model '{a.model}' is not in LM Studio's list. Available: {', '.join(ids)}")
        if not a.model and len(chat) > 1:
            print(f"WARNING: {len(chat)} chat models are listed ({', '.join(chat)}). Using the first: {model}.\n"
                  f"         To pick one, run again with --model <name> from that list.")
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
        if plan:
            bad.update(check_story(draft, f, cfg, plan, last_hook))
        if not bad or set(bad) == {"hook_format"}:   # the model can't fix the rotation; stop asking
            break
        user = ("Facts:\n" + json.dumps(f, indent=2) + "\n\nYour last draft failed these checks. Fix only these:\n"
                + json.dumps(bad, indent=2) + "\n\nLast draft:\n" + json.dumps(draft, indent=2))
        print(f"try {i + 1}: {len(bad)} problem(s), asking for a fix")
    if draft is None:
        sys.exit("The model never returned usable JSON.")

    out = {"model": model, "tries_used": min(i + 1, a.tries) if draft is not None else 0, "hook_format": hook, "facts": f, "passed_titles": titles, "description": draft.get("description"),
           "pinned_comment": draft.get("pinned_comment"), "captions": draft.get("captions"),
           "beat_captions": draft.get("beat_captions"), "failed_checks": bad}
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", model)          # one output file per model, so runs can be compared
    path = os.path.splitext(a.events)[0] + "." + safe + ".text.json"
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)
    print(f"\nSTATUS: {'ALL CHECKS PASSED' if not bad else 'SOME CHECKS FAILED - fix by hand or rerun'}")
    for t in titles:
        print("  title ok:", t)
    for k, v in bad.items():
        print("  FAIL", k, "->", "; ".join(v))
    print("wrote", path)
    if plan and a.apply:
        caption_bad = [k for k in bad if k.startswith("beat_captions") or k == "voice"]
        if caption_bad:
            print("Not applying: some beat captions failed. Fix them by hand in the text file or rerun.")
        else:
            newplan, F, Wn = apply_captions(draft, cfg, plan)
            dst = os.path.splitext(a.plan)[0] + ".captioned.json"
            json.dump(newplan, open(dst, "w", encoding="utf-8"), indent=2)
            for w in Wn:
                print("  plan warn", w)
            for x in F:
                print("  plan FAIL", x)
            print(f"wrote {dst} - plan check {'PASSES' if not F else 'FAILS'}")
    if a.record:
        log = os.path.join(HERE, "hook_log.json")
        h = json.load(open(log)) if os.path.exists(log) else []
        h.append(hook)
        json.dump(h, open(log, "w"))
        print("recorded hook:", hook)


if __name__ == "__main__":
    main()
