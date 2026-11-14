# Lesson 6: one-life story

Built 2026-11-14. Tested on fake match footage and a fake LM Studio server. It hasn't been used on a real match or a real Short yet.

## Why

The last Short was fast kills and a money counter. Only 25% of viewers stayed to watch. The channel's best watch time so far came from "10k one life": 0:37 long, 55% stayed, 59% average watched. That one had a reason to keep watching: one life, and the question of whether it would last.

So each Short now follows one match as a short story. The money total can sit small in a corner, but the story carries the Short.

## The format: 40 seconds at most

| Time | Part | What's on screen |
|---|---|---|
| 0 to 2 s | Hook | Frame one is a kill landing, with a story line like "ONE LIFE. NO ARMOR." No intro or title card. |
| 2 to 8 s | Setup | The plan or the constraint, in a few words. |
| 8 to 30 s | Rising beats | 3 or 4 moments in match order. Each one has a build-up, the kill and a reaction, and each gets a different edit. |
| about 25 to 32 s | Risky call | The one decision or shot the story turns on. |
| 32 to 38 s | Payoff | The best kill, in short slow-mo. |
| last 1.5 s | End card | @crazynando, twitch.tv/reydiant and a one-line "Next:" teaser. No subscribe ask. |

The edits you can give a beat:

- `hold`: stays on the empty moment right before the kill for half a second.
- `speed-ramp`: rushes the approach at 2x, then real speed for the fight.
- `freeze-rewind`: lesson 3. Freezes on the kill, rewinds, then plays through.
- `kinetic-text`: the caption slams in on the kill. For the full slam look, use lesson 5.
- `cut`: plain.
- `slowmo`: 1 second around the kill at half speed. The payoff always gets this one.

## Files

- `story_plan.py` turns your kills and beats into a timeline, checks it, exports files for the other lessons and renders a rough cut.
- `story_rules.py` holds every rule and number in one place. The LM Studio bridge uses it too, so the two can't disagree.
- `events.example.json` and `beats.example.json` are a filled-in example.
- `make_demo_match.py` makes a fake 70-second match recording to test with.
- `test_story_plan.py` breaks the example plan one rule at a time and makes sure each break is caught.

## What you write

**events.json** is the same file the other lessons use, with two additions. `t` is now the time of the kill in your match recording, not in the Short.

```json
{
  "clip": "match01.mp4",
  "labels": ["ONE LIFE. NO ARMOR.", "HOLD THE ZONE"],
  "events": [
    {"t": 14.20, "amount": 1350, "headshot": false, "dist_m": 34, "note": "first contact at the fence"}
  ]
}
```

- `labels` are true things about the match the footage shows: the constraint, the plan. Any word you want on screen has to be in a label or a kill's `note`.
- `note` is what happened in that kill, in plain words.

**beats.json** is your story. Kills are numbered 1, 2, 3 and so on, in match order.

```json
{
  "hook":   {"kill": 6, "text": "ONE LIFE. NO ARMOR."},
  "setup":  {"from": 2.0, "text": "HOLD THE ZONE"},
  "beats": [
    {"kill": 1, "label": "FIRST CONTACT",     "effect": "hold"},
    {"kill": 2, "label": "THROUGH THE SMOKE", "effect": "freeze-rewind"},
    {"kill": 4, "label": "106M ON THE RIDGE", "effect": "speed-ramp"}
  ],
  "risky":  {"kill": 5, "label": "PUSHED THE TRUCK ALONE", "effect": "kinetic-text"},
  "payoff": {"kill": 6, "label": "141M TO SAVE THE ZONE"},
  "next":   "Next: one life, pistol only"
}
```

- `setup.from` is where in the recording the setup footage starts. Add `"to"` to set where it ends.
- A beat can take `"build": 2.5` and `"react": 1.2` (seconds before and after the kill) if you don't like the automatic split.
- A risky call that isn't a kill takes `"from"` and `"to"` instead of `"kill"`.
- Kills you leave out of beats.json are cut. The kill counter and every number on screen only count the kills that are left.

## Run it

Open a terminal in `shorts-toolkit\lesson06-one-life-story`. On Windows, type `python`. On Mac or Linux, `python3`.

1. Build the plan. It prints the timeline and checks it right away.

       python story_plan.py build events.json beats.json --out plan.json

2. Check it against your footage. This also makes sure the recording is long enough.

       python story_plan.py check plan.json events.json --clip match01.mp4

3. Have Gemma draft the captions and titles in LM Studio. Load Gemma, start the server, then:

       python ..\lm-studio-bridge\lm_bridge.py events.json --plan plan.json --apply --model <gemma name from LM Studio>

   Captions that pass go into `plan.captioned.json`, and that plan gets the full check. The titles and description are in `events.<model>.text.json`. If you'd rather keep your own labels, skip this step and use `plan.json` below.

4. Export the inputs for the music and text lessons.

       python story_plan.py export plan.captioned.json events.json --out exports

5. Make the music. It's original and hits on every kill in the Short.

       python ..\lesson02-kill-synced-music\music_bed.py render exports\music_events.json --out exports --prefix story --mood dark

6. Render the Short.

       python story_plan.py render plan.captioned.json events.json --clip match01.mp4 --music exports\story_bed_under_game_-20LUFS.wav --out story_v1.mp4

   The render checks the plan first and won't start if it fails. It finishes with a QC report for size, fps, length, loudness and true peak.

7. Make it loop, then run QC again.

       python ..\lesson04-loop-ending\loop_ending.py make story_v1.mp4 --out story_v1_loop.mp4 --blend 0.3
       python story_plan.py qc story_v1_loop.mp4

Name each render with a new version number (v1, v2, and so on), so you never overwrite one.

`exports\commands.txt` has the lesson 3 and lesson 5 commands for this plan, in case you want to make those pieces by hand in your editor.

## What fails the check

- The Short is over 40 seconds.
- The first frame isn't the exact frame a kill lands.
- A number or word on screen isn't in events.json. Numbers from cut kills don't count either, so a cut kill's "18M" fails.
- The kill counter doesn't match the kills left after cuts, or its cash doesn't add up.
- A beat, the risky call or the payoff has under 2 seconds of footage a viewer can follow. Fast-forward and rewind don't count.
- Text a phone can't read: smaller than 64 px (40 px for the counter), more than 2 lines, too wide, in the area the Shorts buttons cover, or not on screen long enough to read (about 3 words a second, 0.8 s at least).
- The hook runs past 2 s, the setup past 8 s, or the end card isn't the last 1.5 s with both handles and a "Next:" line.
- Beats out of match order, the same edit twice in a row, or fewer than 3 kinds of edit across the beats.
- No slow-mo on the payoff kill.
- A banned word, a subscribe ask, or more than one Spanish word in a caption.

If the risky call or the payoff lands outside its time window, you get a warning, not a fail. Same if the payoff kill isn't the one that paid the most. The best moment isn't always the biggest reward.

## Tests

    python test_story_plan.py

    python make_demo_match.py events.example.json demo_match.mp4
    python story_plan.py build events.example.json beats.example.json --out plan.example.json
    python story_plan.py render plan.example.json events.example.json --clip demo_match.mp4 --out story_demo_v1.mp4

## Results on the fake match

Rendered from `plan.example.json` on the fake 70-second match, without music (the lesson 2 bed needs scipy, which the test machine didn't have):

- QC: 1080x1920, 60 fps, 40.00 s, -14.1 LUFS, true peak -2.6 dB. File size 120 MB (the fake footage is pure noise, so real footage should come out smaller).
- Frame one is the kill frame (the red flash at 1:01.300 in the recording), with "ONE LIFE. NO ARMOR." already on screen.
- Every kill lands on the frame the plan says. The kill counter reads 1 to 5 and the cash adds up to $10,800. Kill 3 was cut, and nothing on screen mentions it.
- The only frozen stretch is the end card, which is meant to hold still.
- 15 of 15 rule tests pass (`test_story_plan.py`), and 13 of 13 bridge checks pass (`../lm-studio-bridge/test_story_mode.py`).

What the first renders caught, now fixed:

- The first render ran 40.08 s, because AAC padding on each piece added up. Pieces now keep plain audio until the final encode.
- Loudness came out at -18.9 LUFS with peaks at +4.9 dB. ffmpeg's loudnorm can't reach -14 when gunshots peak that high. The render now sets the gain, limits peaks and measures the finished file until both numbers pass.
- The hook line faded in, so frame one had no text. Text that starts at 0 s is now fully there on frame one.

## Known gaps

- It hasn't run on real WARDOGS footage. Real recordings have muzzle flash, HUD clutter and camera shake, so look at frame one and every kill in the render.
- The rough cut's text fades in. The full slam-in look comes from lesson 5's overlay, added in your editor.
- The lesson 2 music bed ends about 2 seconds after the payoff kill. The end card plays over quiet game audio.
- I can't hear audio. Loudness and peaks are measured. How the mix sounds is your call.
- Kill times still come from you. A kill-feed reader could fill in events.json later.

Needs Python 3 and ffmpeg on the PATH. Pillow is optional: with it, text width is measured with the real font. Rendering the freeze-rewind beat uses lesson 3, which needs numpy and Pillow. Without them, the render uses its own simpler freeze and rewind.
