# LM Studio bridge

LM Studio drafts the text for a Short. Code checks it. Claude makes the final call.

LM Studio never sees footage and never touches the standing rules. It gets a facts block
(start, total, kill count, headshots, biggest kill, hook format) and returns titles, a description,
a pinned comment and caption lines. `lm_bridge.py` rejects anything that breaks the text rules and
asks the model to fix only what failed.

## Run it (on your PC)

1. In LM Studio, load a model and start the local server (default `http://localhost:1234`).
2. `python lm_bridge.py events.json`
3. Read `events.text.json`. Only titles listed under `passed_titles` passed.
4. After you post, run again with `--record` so the hook rotation remembers what you used.

Same `events.json` as lesson 1. Add an optional `"note"` and `"dist_m"` to a kill to give the model something specific to write about. Keep `lm_system_prompt.md` next to the script.

## What the code checks

- Every number is in the facts block (start, total, kills, headshots, biggest kill, distances), including spelled-out ones.
- Title: a number in the first four words ("Started with $0... ended with $81,090" passes), 70 characters or fewer, no emoji.
- Description: 1 or 2 lines, ends with `#wardogs #shorts #fps #gaming`, no headshot claim if the count is 0.
- Pinned comment: one question, 200 characters or fewer, and not a question the video already answers (kill count, total).
- Captions: 1 to 3 words.
- No "subscribe", no emoji. Hook format never repeats twice in a row.

## What it does not check

- Tone. Claude reads the passed options and picks.
- Whether the facts themselves are right. They come from your events.json, which must match the game.

Tested here against a fake LM Studio server only. Not run against a real model yet.
