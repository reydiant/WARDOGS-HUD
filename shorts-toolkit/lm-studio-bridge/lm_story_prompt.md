# One-life story mode

This Short follows one match as a short story. The money is a small number in the corner now. The story is the point.

The facts block has a `story` section:

- `labels`: lines the owner wrote about the match, like the constraint ("ONE LIFE. NO ARMOR.").
- `beats`: the moments in the order they happened. Each one has a slot name, the edit, the owner's text and the kill it shows.
- `story_words`: the only words you may use in on-screen captions, besides small joining words (the, and, then, wait, now, one, no).
- `spanish_ok`: Spanish words you may use, if one fits.

## Extra field to return

Add this to the JSON:

"beat_captions": {"hook": "...", "setup": "...", "beat1": "...", "beat2": "...", "beat3": "...", "risky": "...", "payoff": "..."}

Write one caption for every slot listed in `beats`, and no others.

## Caption rules (code checks these)

1. 1 to 5 words. Each one is read in about a second on a phone.
2. Only words from `story_words`, small joining words, and numbers from the facts. If a word isn't in the list, don't use it. The footage has to show everything a caption says.
3. The hook caption is the story line: the constraint or the stakes. It goes on frame one, over a kill.
4. The setup caption says the plan or the constraint in a few words.
5. Each beat caption names what happened in that moment. The risky caption names the decision the story turns on. The payoff caption names the best kill.
6. Read in order, the captions tell the match from start to finish.

## Titles in this mode

Tell the story of the match: the constraint, then what it cost or what it got. Keep every title rule from above. Put a number in the first four words, and only numbers from the facts. Never call it a "one life story" or write any other internal label.

## Voice

The voice rules above still apply: dark, gritty, plain, no hype words. Use a Spanish word only when it fits the moment. At most two in the whole Short, never the same one twice, and never more than one in a caption. Most Shorts need none.
