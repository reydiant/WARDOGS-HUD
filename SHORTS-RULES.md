# WARDOGS Shorts rules (v2)

These are the standing rules for every WARDOGS YouTube Short. They come before the hook-title and QC skills. Update this file when the stats say a rule is wrong, and record why in the changelog at the bottom.

## Why v2

The last Short was fast kills with a money counter and almost no editing. Only **25% stayed to watch**, so 3 in 4 viewers swiped away in the first second or two. Counting money only means something to people who already play. A stranger needs a reason to care before the first kill lands.

## Rule 1: 40 seconds is the hard limit

Plan the whole Short against this timeline. Every second needs a job.

| Time | Job | What goes on screen |
|---|---|---|
| 0.0–1.5 s | **Hook.** Stop the swipe. | Open on the strongest frame: the payoff kill, the near-death or the enemy in the scope. No intro card, logo, name or menu. Hook text of 6 words or fewer from the first frame. |
| 1.5–5 s | **Stakes.** Why should I care? | One line saying what's at risk: "This guy killed me 4 times", "Last one alive, enemy at 95". |
| 5–30 s | **Escalation.** Keep it moving. | Each beat is 4 s or less. Cut every run, loot, menu and respawn. Something changes on screen at least every 2 s: a cut, a zoom, a text pop or a sound hit. |
| 30–38 s | **Payoff.** | The moment the hook promised: slow-mo or freeze on the kill, punch-in zoom, the big number or line. |
| 38–40 s | **Loop.** | Cut straight back so the last frame flows into the first. No end card, stats card or "subscribe" outro. Loops count as rewatches. |

If the footage doesn't fill 40 seconds with good beats, make it shorter. A tight 25-second Short beats a padded 40-second one.

## Rule 2: Every Short needs a story, and money is only a prop

Pick the angle before cutting. Money, K/D and kill counts can sit small in a corner, but they're never the story.

Angles, in the order to try them (the HUD already has the data for each):

1. **Nemesis / revenge.** The HUD's Rivals list shows who keeps killing you. "This player killed me 5 times. Watch." Open on the revenge kill, then show the deaths that set it up. It's a series format ("Nemesis #1, #2…") and it gives people a reason to come back for the next one.
2. **Clutch at match point.** The team score hits 95 and you're the last one on the zone. The score box shows the stakes on screen.
3. **Mistake → fix (coach).** "Why I keep dying here", made from the why-you-died review. Show the death, freeze, give the tip in one line, then show it working. Viewers stay to learn something.
4. **Impossible shot.** A 100 m+ headshot. Show the distance before the shot, then replay it from the scope.
5. **Chaos / fails.** Vehicle crashes, team kills, getting run over. Comedy keeps people watching even with no kill.

Plain fast-kill compilations, money-counter Shorts and montages with an intro card are **retired** unless the stats show one doing well again.

## Rule 3: Editing minimums (fast kills with no editing isn't enough)

Every Short has all of these:

- **Captions** that say what's happening, readable on a phone with the sound off. They sit in the middle third of the frame, clear of the YouTube UI at the top and bottom.
- **Punch-in zoom** (about 115–130%) on every kill and on the payoff.
- **Speed ramps:** fast through travel, normal for the fight, slow-mo for the payoff.
- **Sound design:** keep the game audio and add a hit or bass drop on the payoff. Background music sits under the gunfire, never over it. Mute Discord voice.
- **One pattern interrupt** in the middle (12–22 s): a freeze frame, a "wait for it", a rewind or a replay from another angle.
- **No dead air.** No more than 1.5 s without action or new text.

## Rule 4: Hooks and titles

Use the hook-title skill for the package (hook text, title, description, hashtags, pinned comment). Also:

- The hook text promises something the Short delivers before 38 s.
- The title states the story, not the stat. Use "He killed me 5 times. Then this happened", not "$12,400 in 9 kills".
- Never use the same hook format twice in a row.

## Rule 5: Stats decide what comes next

Before building any Short:

1. Read `shorts-log.csv`.
2. Fill in the stats the user has posted for earlier Shorts. Ask once if they're missing, and if the user is away, go with the last known data.
3. Use this table to pick the change for the next Short:

| Stat (YouTube Studio → Short → Analytics) | Target | If it misses |
|---|---|---|
| **Stayed to watch** (viewed vs. swiped away) | 70%+ (red flag under 50%) | Fix the first 1.5 s: stronger opening frame, shorter hook text, start mid-action. |
| **Average % viewed** | 80%+ (over 100% means people rewatch) | Fix the middle: cut more, shorter beats, add a pattern interrupt, move the payoff earlier. |
| **Average view duration** | 30 s+ on a 40 s Short | Same as above, or make the Short shorter. |
| **Likes per 100 views** | 4+ | The payoff isn't strong enough, or the title over-promised. |
| **Subscribers gained** | Any, and it should rise across a series | Turn the best-performing angle into a numbered series. |

4. **Change one thing per Short** (angle, hook format, length or an editing technique) so the stats show what worked. Write the change in the log's `test` column.
5. **Mix:** about 70% of Shorts use the best angle so far, 20% test the next angle on the list in Rule 2, and 10% are wild experiments.
6. Two Shorts in a row from one angle that finish under 50% stayed-to-watch: drop the angle and move down the list.
7. When an angle clears 70% stayed-to-watch, make it a series and move it to the top of Rule 2.

## Rule 6: Build and hand-over

- Follow the QC skill gates (brief → hook frames → rough cut → final), and run its ffmpeg checks against a **40 s** limit.
- The brief lists the angle, the hook text, the payoff timestamp, the one thing being tested and what the log said last time.
- After posting, add a row to `shorts-log.csv` (stats columns left blank) so the next session can fill them in.
- When the user is away, make the call and say which call was made and why.

## Changelog

- **v2 (2026-11-14):** 40 s limit with a timeline per second. Money counting and plain kill compilations retired in favour of story angles (Nemesis first). Added editing minimums and a stats loop with targets. Reason: the money-counter Short with fast kills got 25% stayed-to-watch.
