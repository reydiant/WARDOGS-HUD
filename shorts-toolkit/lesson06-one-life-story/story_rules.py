"""
story_rules.py - the rules for one-life-story Shorts, in one place.

story_plan.py (build and check) and ../lm-studio-bridge/lm_bridge.py both import this file,
so the plan checker and the caption checker can't drift apart. Plain Python 3, no installs.
Pillow is used to measure text width if it is installed. Without it, a safe estimate is used.
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "lesson01-payoff-counter", "fonts", "Poppins-Bold.ttf")

# ---- video ---------------------------------------------------------------------------------
W, H, FPS = 1080, 1920, 60
FRAME = 1.0 / FPS
MAX_TOTAL = 40.0                 # hard limit, seconds
END_CARD = 1.5                   # the end card is the last 1.5 s
HOOK_MAX = 2.0                   # hook is 0 to 2 s
SETUP_END = 8.0                  # setup runs 2 to 8 s
RISKY_WINDOW = (25.0, 32.0)      # the risky call happens around 25 to 32 s
PAYOFF_WINDOW = (32.0, 38.0)     # payoff, best kill, short slow-mo
BEATS_MIN, BEATS_MAX = 3, 4
MIN_READABLE = 2.0               # every beat needs 2 s of footage a viewer can follow
READABLE_SPEED = 1.25            # footage faster than this is a blur on a phone, so it doesn't count

# Shorts UI covers the top ~130 px, the bottom ~420 px and the right ~130 px (same as lesson 1).
SAFE_X0, SAFE_X1 = 60, 950
SAFE_Y0, SAFE_Y1 = 130, 1500
MIN_TEXT_PX = 64                 # story text: smallest size that reads on a phone held upright
MIN_SMALL_PX = 40                # the small kill counter / cash element
MAX_LINES = 2
MAX_CAPTION_WORDS = 5            # "ONE LIFE. NO ARMOR." is 4

HANDLE = "@crazynando"
TWITCH = "twitch.tv/reydiant"

EFFECTS = ("cut", "hold", "speed-ramp", "freeze-rewind", "kinetic-text", "slowmo")
HOOK_FORMAT = "one-life-story"

# ---- words ---------------------------------------------------------------------------------
# Hype words and internal labels. Never on screen, in a title, a description or a comment.
BANNED = ("subscribe", "like and", "link in bio", "smash that", "hit the bell", "follow for more",
          "insane", "epic", "unreal", "legendary", "godlike", "goated", "cracked", "crazy shot",
          "you won't believe", "wait till the end", "wait for the end", "must watch", "no way",
          "payoff first", "payoff-first", "question hook", "hook format", "personality pov",
          "series entry", "one-life-story", "one life story", "story format", "rising beat",
          "risky call", "story beat")

# Words that join a caption together but claim nothing about the match. Every other word on
# screen has to come from events.json (a label the owner wrote, or a kill's note).
NEUTRAL = set("""A AN THE AND BUT OR SO THEN NOW STILL JUST ONLY HERE THERE THIS THAT IT IS WAS
I ME MY HE HIM HIS THEY THEM TO FOR IN ON AT OF WITH FROM UP OUT OFF NO NOT ALL ONE
WAIT WATCH LOOK NEXT KILL KILLS M K""".split())

# Puerto Rican / Spanish words the model may use. Voice rule from lm_system_prompt.md:
# a Spanish word can show up if it fits, never forced, no catchphrase. Code caps it at one per
# piece of text and two in a whole Short package, and the same word can't be used twice.
# Interjections only, so a Spanish word can never sneak in a claim the footage doesn't show.
SPANISH = set("""DALE WEPA ACHO CHACHO MANO PANA MIRA DIANTRE DIABLO AY BENDITO VAMOS BRUTAL TRANQUI""".split())
SPANISH_PER_PIECE = 1
SPANISH_PER_PACKAGE = 2

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                     "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
MULT = {"hundred": 100, "thousand": 1000, "grand": 1000, "k": 1000}
COUNTED = ("headshot", "headshots", "kill", "kills", "shot", "shots")


def words(text):
    """Upper-case words, with numbers and units split off: '106M' -> ['106', 'M']."""
    out = []
    for tok in re.findall(r"\$?\d[\d,]*(?:\.\d+)?|[A-Za-zÀ-ÿ']+", text):
        out.append(tok.upper().strip("'"))
    return [w for w in out if w]


def numbers(text):
    """Every number in the text as a plain digit string. '$5,400' -> '5400', '106m' -> '106',
    '10k' -> '10000', 'thirty five grand' -> '35000'. Bare 'one' is skipped unless it counts
    something ('one headshot'), so 'one life' is not a number."""
    out = []
    for m in re.finditer(r"\$?(\d[\d,]*(?:\.\d+)?)(?:\s*([kK])(?![A-Za-z]))?", text):
        v = m.group(1).replace(",", "")
        if m.group(2):
            v = str(int(float(v) * 1000))
        out.append(v)
    toks = re.findall(r"[a-z]+", text.lower())
    i = 0
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
            if i < len(toks) and toks[i] in MULT and toks[i] != "k":
                val *= MULT[toks[i]]
                i += 1
            out.append(str(val))
        else:
            i += 1
    return out


def banned_in(text):
    low = text.lower()
    return [b for b in BANNED if re.search(r"(?<![a-z])" + re.escape(b) + r"(?![a-z])", low)]


def spanish_in(text):
    return [w for w in words(text) if w in SPANISH]


# ---- facts from events.json ------------------------------------------------------------------
def load_events(cfg):
    """Kills sorted by time, each with an 'id' (1-based, in match order)."""
    ev = sorted(cfg["events"], key=lambda e: e["t"])
    for i, e in enumerate(ev, 1):
        e.setdefault("id", i)
    return ev


def vocabulary(cfg):
    """Words allowed on screen: the owner's labels, every kill note, plus neutral joining words."""
    vocab = set(NEUTRAL)
    for lab in cfg.get("labels", []):
        vocab.update(w for w in words(lab) if not w[0].isdigit() and not w.startswith("$"))
    for e in cfg["events"]:
        vocab.update(w for w in words(e.get("note", "")) if not w[0].isdigit() and not w.startswith("$"))
        if e.get("headshot"):
            vocab.update({"HEADSHOT", "HEADSHOTS"})
    return vocab


def allowed_numbers(cfg, shown_ids=None):
    """Numbers that may be on screen. Only kills that stay in the Short count (shown_ids)."""
    ev = load_events(cfg)
    kept = [e for e in ev if shown_ids is None or e["id"] in shown_ids]
    vals = set()
    run = 0
    for i, e in enumerate(kept, 1):
        run += e.get("amount", 0)
        vals.update({e.get("amount"), e.get("dist_m"), run, i})
        vals.update(numbers(e.get("note", "")))
    vals.add(sum(1 for e in kept if e.get("headshot")))
    vals.add(cfg.get("start", 0))
    for lab in cfg.get("labels", []):
        vals.update(numbers(lab))
    vals.discard(None)
    return {str(v) for v in vals}


def text_problems(text, vocab, ok_numbers, max_words=MAX_CAPTION_WORDS):
    """Why an on-screen line breaks the facts rules. Empty list = fine."""
    why = []
    for n in numbers(text):
        if n not in ok_numbers:
            why.append(f"number {n} is not in events.json for the kills in this Short")
    for w in words(text):
        if w[0].isdigit() or w.startswith("$"):
            continue
        if w not in vocab and w not in SPANISH:
            why.append(f"word '{w}' is not in events.json (labels or kill notes)")
    if len(spanish_in(text)) > SPANISH_PER_PIECE:
        why.append(f"more than {SPANISH_PER_PIECE} Spanish word (never force it)")
    n_words = len(text.split())
    if n_words > max_words:
        why.append(f"{n_words} words, max {max_words} on a phone")
    for b in banned_in(text):
        why.append(f"banned: '{b}'")
    return why


# ---- reading on a phone ----------------------------------------------------------------------
_font_cache = {}


def text_width(text, size):
    try:
        from PIL import ImageFont
        if size not in _font_cache:
            _font_cache[size] = ImageFont.truetype(FONT, size)
        l, t, r, b = _font_cache[size].getbbox(text, stroke_width=max(2, size // 14))
        return r - l
    except Exception:                       # no Pillow or no font: Poppins Bold caps run about 0.68 em
        return int(len(text) * size * 0.68) + size // 7


def wrap(text, size, max_w=SAFE_X1 - SAFE_X0):
    """Split into lines that fit the safe width. Returns the lines (may still be too wide).
    If the text is two short sentences ("ONE LIFE. NO ARMOR.") and it needs two lines, it breaks
    between the sentences."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(parts) == 2 and text_width(text, size) > max_w and all(text_width(p, size) <= max_w for p in parts):
        return parts
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if cur and text_width(trial, size) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def reading_time(text):
    """Seconds a viewer needs to read a line: about 3 words a second, 0.8 s at least."""
    return max(0.8, 0.3 + len(text.split()) / 3.0)
