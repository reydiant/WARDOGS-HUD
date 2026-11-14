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

## One-life story mode

For a one-life-story Short (lesson 6), pass the plan:

    python lm_bridge.py events.json --plan plan.json --apply --model <gemma name from LM Studio>

- The facts only hold the kills left in the plan, so a title can't quote a cut kill's numbers.
- The model gets `lm_story_prompt.md` added after `lm_system_prompt.md`, so the voice rules and banned words still apply.
- It writes one caption per story slot (hook, setup, each beat, risky, payoff). Code checks each caption the same way the plan checker does: every word has to come from a label or kill note in events.json, every number from a kill that's still in the Short, 5 words at most, no banned words.
- Spanish: at most one word in a caption, two in the whole Short, and never the same word twice.
- `--apply` puts the captions that passed into `plan.captioned.json` and runs the full plan check on it.
- The hook format is `one-life-story`. If the last Short you recorded was one too, the run is marked failed, because the rule is never the same format twice in a row.

Test it without a model:

    python test_story_mode.py

## What the code checks

- Every number is in the facts block (start, total, kills, headshots, biggest kill, distances), including spelled-out ones.
- Title: a number in the first four words ("Started with $0... ended with $81,090" passes), 70 characters or fewer, no emoji.
- Description: 1 or 2 lines, ends with `#wardogs #shorts #fps #gaming`, no headshot claim if the count is 0.
- Pinned comment: one question, 200 characters or fewer, and not a question the video already answers (kill count, total).
- Captions: 1 to 3 words.
- No "subscribe", no emoji, no hype words (the list is in `../lesson06-one-life-story/story_rules.py`). Hook format never repeats twice in a row. The rotation is payoff-first, question, challenge, personality, series, one-life-story.

## What it does not check

- Tone. Claude reads the passed options and picks.
- Whether the facts themselves are right. They come from your events.json, which must match the game.

Tested here against a fake LM Studio server only. Not run against a real model yet. Keep the `lesson06-one-life-story` folder next to this one: the banned words and the story checks live there.
