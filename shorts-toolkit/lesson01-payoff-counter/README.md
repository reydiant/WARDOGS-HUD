# Lesson 1: payoff counter and kill pops

Built 2026-11-09. Not used on a real Short yet, so nothing here is proven.

## What it does

Reads a kill list and renders a transparent 1080x1920, 60 fps overlay:

- The payoff text ("$0 -> $23,750") is on screen from frame one, with a small punch-in.
- It hands over to a running cash counter at the top that climbs with every kill.
- Each kill gets a "+$X" pop near the crosshair. Headshots get a tag and a pink-violet color.
- The payoff total and the counter come from the same kill list, so they always add up.
  Cut a kill from the list and every number updates.

Colors are the channel look: near-black, gold to violet. Text has a dark outline
and shadow so it reads on bright footage. Everything stays out of the Shorts UI
zones (top 130 px, bottom 420 px, right 130 px).

Targets standing rules 1, 3, 8, 9, 11 and 12. The metric to watch is the share of
viewers who stay past the first second.

## Use it

1. Copy `events.example.json` and fill in one row per kill: `t` is seconds from the
   start of the Short, `amount` is the reward the game shows, `headshot` is true or false.
   Put the best kill at `t: 0` so it lands on frame one.
2. Run:

       python3 payoff_overlay.py events.json --out out --prefix short01

3. Put `short01_overlay_webm.webm` (small) or the ProRes file on a track above the
   footage. If your editor won't read the webm, add `--codec prores` or `--codec qtrle`.
   ProRes is about 340 MB for 12 seconds, so use it only if you need it.

To see it on a test background first, make one with `make_demo_bg.py` and pass `--bg`.
That also writes a `_demo_composite.mp4` you can watch on your phone.

Needs Python 3, Pillow, numpy and ffmpeg on the PATH. Poppins is in `fonts/`.

## Settings you will probably touch

- `"payoff": "28 KILLS"` in the JSON replaces the automatic "$0 -> $total" text.
- `"hold": 1.5` is how long the big payoff text stays before the counter takes over.
- Positions and sizes are plain numbers near the top of `Overlay.render`.

## Known gaps

- Drift's support for alpha video is untested. The webm is the first thing to try.
- The kill times have to be entered by hand for now. A kill-feed reader could fill them in.
