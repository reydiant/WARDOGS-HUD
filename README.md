WARDOGS Live HUD

A live stats and coaching screen for WARDOGS, built to sit on your second monitor while you play. It reads your kill feed, team scores and money straight off your screen, tracks your session, coaches you between lives, and turns your best kill streaks into YouTube Shorts.

Everything runs in one HTML file in your browser. Screen reading happens on your PC. See Privacy for the few things that go online.

Contents

	•	What you need
	•	Quick start
	•	Drawing the boxes
	•	Combat panel
	•	Coach
	•	Highlights and YouTube Shorts
	•	K/D history
	•	Fixing a wrong count
	•	Settings
	•	Keyboard shortcuts
	•	Troubleshooting
	•	Privacy
	•	What's new

What you need

	•	Chrome or Edge on your PC. Other browsers can't capture the screen this way.
	•	WARDOGS in borderless or windowed mode. Exclusive fullscreen shows up black in a screen share.
	•	Internet the first time capture starts, to load the text reader. After that it runs locally.
	•	A second monitor is recommended. Keep the HUD visible there; a hidden or minimized tab gets slowed down by the browser.
	•	Optional: an Anthropic API key for the Claude coach and why-you-died reviews.

Quick start

	1.	Open wardogs-hud-v18.html in Chrome or Edge.
	2.	In Settings, enter your SteamID64 or wardogstracker.gg profile link. This pulls your level, role XP, rank and cash from the tracker.
	3.	In the Combat panel, press Start screen capture and pick the screen WARDOGS is on, not the HUD monitor. To record game audio for clips, tick Also share system audio.
	4.	In the window that opens, draw the boxes (see below), enter your in-game name, and press Save.
	5.	Play. The status pill at the top of Combat should say Reading kill feed with a read count that keeps climbing.

When you switch to a new HTML version, start screen capture again. Your settings, boxes and history carry over.

Drawing the boxes

The capture window shows a frame of your screen. Pick a box type at the top and drag a rectangle.

Box	Draw it around	Used for
Kill feed box	The kill feed lines, including the team icons at both ends of each line	Kills, deaths, headshots, team kills
Team score box	The three team scores under the minimap (the numbers that race to 100)	Match score, match point warning, wins and losses
Cash box	Your money in the top-right corner, plus the reward lines under it ("KILL +$1,350")	Earned, spent, rewards by type
Kill confirm box (optional)	The area just under your crosshair where "KILL CONFIRMED" and "86M // NAME" appear	Kills the feed misses, team kill fines

Tips:

	•	Make the cash box wide enough on the left that reward names aren't cut off ("ONTROL ZONE" means the C is outside the box).
	•	Make the kill confirm box tall enough to include fine lines like "TEAM KILL -$1,800".
	•	If a box isn't reading, open Show reader. It shows exactly what each box captures and what was read.

Combat panel

Kill feed

Every line with your name is counted as a kill or a death within about half a second, flashed on screen and screenshotted.

	•	Kills, deaths, K/D, streak, best streak, multi-kills, kills per minute, last kill
	•	Kill range: longest and average, from the "[34m]" tags in the feed
	•	Headshots: count and percentage. A kill is a headshot when the feed line shows the skull icon between the gun and the victim, or a "HEADSHOT KILL" reward line appears within 10 seconds. A few may be missed, so treat the percentage as a minimum and tap HS when you know one was missed.
	•	Team kills and Team killed by others, from words like "TEAMKILL", the team icons, or name colors
	•	Deaths with no killer named: a vehicle crash (even one a teammate was flying), a fall or a suicide shows as "no killer named". Tap TK if it was a teammate's crash.
	•	Duplicate protection: a line that stays on screen counts once, and a second death within 10 seconds is treated as the same death read differently.

Scoreboard (exact numbers)

Open the in-game scoreboard for a couple of seconds now and then. The HUD finds your highlighted row and reads your exact kills, assists, deaths, revives and cash earned. These show as Scoreboard · exact and are trusted over the kill feed counts, which can miss a kill or two when lines scroll by fast.

Team scores and wins

The team score box is read every few seconds, slower if it keeps failing. You get a match point warning when a team reaches 95, and the winner is logged when a team reaches 100. If the box can't be read, the HUD checks the whole screen for the VICTORY or DEFEAT banner every 12 seconds or so, but never right after kill feed activity. You can also log a winner by hand in K/D history.

Cash

Your wallet is the source of truth. Earned and Spent add up its increases and decreases, Net is wallet now minus wallet at the start. Reward chips show where the money came from (Control Zone Presence, Kill, Headshot Kill, and so on).

Misreads are filtered out. A wallet value that jumps and comes back within 2 minutes is cancelled, jumps of $20,000 or more need three matching reads, and an amount far off a reward's usual value is corrected.

Show reader

Shows what each box captures, the text read, and What it did with each line: counted, skipped and why. Send this when something isn't counting right.

Coach

The Coach panel has two views: Built-in (instant, free, rule-based) and Claude (a written breakdown; needs an API key, or use Copy for Claude and paste into the Claude app).

Coaching styles

Pick a style in the Coach header. It changes what gets praised and flagged, the session goals, and the Claude coach's personality.

Style	Coach voice	Judges you on
All-round	Experienced coach	Fighting, team play and cash evenly
Lone wolf	Veteran solo operator	Clean exits after kills, crossing open ground, close-range ambushes, headshot rate, earning alone. Never nags about squads or revives.
Squad mate	Squad leader	Assists, revives, trading kills for teammates
Medic	Combat medic instructor	Revives, staying alive to revive, Medic XP
Logistics runner	Logistics sergeant	Transport, resupply, building, Support and Driver XP
Recon	Marksman mentor	Kill range, moving after shots, getting flanked, headshot rate, long lives
Zone pusher	Frontline sergeant	Zone presence and captures, kills per life
Driver / Pilot	Vehicle instructor	Vehicle kills, transport, Driver and Pilot XP

Why-you-died reviews

With an API key and Why-you-died reviews turned on in Settings, Claude looks at frames from the last few seconds before each death and writes the cause and a tip. On Haiku that's about 0.05¢ per death; on Sonnet about 1¢ per death, with sharper answers.

Highlights and YouTube Shorts

How clips are made

	1.	While capture is on, the HUD keeps the last 90 seconds of your screen at 30 fps. Older footage is thrown away unless a streak needs it.
	2.	A run is a series of kills with no more than 25 seconds between them. It ends when you die or go 25 seconds without a kill.
	3.	The run is scored on kills, double and triple kills, headshots, shots of 100 m or more, and streak milestones. Runs worth posting are saved and labelled worthy, great or post this, and a "Highlight saved" pop-up appears.

Saving a clip only keeps footage that was already recorded. Nothing is edited during play.

Making a Short

Press Make Short on a clip, after you're done playing. The editor:

	•	frames it vertically at 1080×1920, under 60 seconds
	•	puts the streak title and your name at the top
	•	pops up a call-out on each kill, like "HEADSHOT · 107 m · paulcorel012" or "DOUBLE KILL"
	•	fills a kill counter along the bottom (red dots are headshots)
	•	ends on a stats card

Rendering plays through in real time (a 30-second Short takes about 30 seconds), so keep the tab open. When it's done, press Save video and copy the ready-made title and hashtags. Upload at youtube.com/upload or in the YouTube app; vertical videos this short are posted as Shorts.

Montages

Make montage joins your best clips that fit in one Short, in the order they happened, with an intro card, flash cuts between clips and a session stats card at the end.

Clip settings

In the capture settings window (Adjust area):

	•	Highlight clips: worthy streaks (default), only great ones, every run of 2+ kills, or off
	•	Shorts layout: crop to the middle of the screen to fill the phone (default), or the whole screen with a blurred background
	•	Game audio in clips: on or off. System audio includes everything your PC plays, like Discord voice and music, so mute those before playing if you plan to post.

Your 30 newest clips are kept in this browser, so you can make a montage at the end of a session. Recording is the only extra work during play. If the game stutters, set Highlight clips to off; kill feed tracking keeps working.

K/D history

Every session is saved when it ends (press N to end one; it also rolls over after 10 hours).

	•	Tiles for today, this week, this month and all time, with headshot percentages
	•	K/D per day, week or month chart, with your K/D goal line if set
	•	By-period table with K/D change, headshot %, best streak, team kills, wins and cash
	•	Records: best day, most kills in a day, best streak, best multi-kill, longest kill, most headshots in a session, best headshot day, longest session
	•	Rivals: your head-to-head record against players you keep meeting
	•	Wins by team color and your own win-loss record
	•	Export CSV (includes headshots), Backup and Restore backup
	•	Sessions and Match results lists, where you can remove a bad entry

Fixing a wrong count

Each row under Last counted has buttons:

	•	Undo: remove a kill or death that shouldn't have counted
	•	TK / Not TK: mark or unmark a team kill
	•	HS / Not HS: mark or unmark a headshot
	•	Swap kills ↔ deaths: use this if every kill shows as a death. It flips the kill feed order setting.

For exact totals, open the scoreboard; those numbers override the kill feed.

Settings

Settings (press S):

Setting	What it does
Your ID	SteamID64 or wardogstracker.gg profile link
Community server for kill stats	Optional; only for community servers with their kill feed connected
Refresh every	How often tracker data is fetched
Keep screen awake	Stops the HUD monitor from sleeping
Anthropic API key	Enables the Claude coach and why-you-died reviews
Claude model	Sonnet 5.5 (deeper) or Haiku 5.5 (faster, cheaper) for the coaching breakdown
Screen reader load	Low impact (best game FPS), Balanced, or Max speed
Why-you-died reviews	Off, Haiku 5.5 or Sonnet 5.5
K/D goal	Shown on the history chart and used for coach goals
Rough-patch alert	Warns you after three deaths for one kill or fewer in eight minutes

Capture settings (the window that opens with Start screen capture or Adjust area):

Setting	What it does
Your in-game name	Leave out your clan tag. Add other names you play under, separated by commas.
Name matching	Strict, Normal, or Loose (for short or unusual names). Looser catches more misread names but may count the wrong line.
Kill feed order	Killer on the left or on the right
Screenshot on each kill and death	Full screen, or the kill feed area only
Skip lines containing	Words from feed lines that aren't kills (revives, joins, captures)
Teammate name color	Fallback for team kill detection if the team icons can't be read
Team kill words	Words that mark a line as a team kill
End-of-game winner	Team score box (recommended), whole-screen scanning, or off
Team names on the winner screen	Only needed if the game names teams instead of showing Green, Blue and Red
Highlight clips, Shorts layout, Game audio	See Clip settings

Keyboard shortcuts

These work when you're not typing in a field.

Key	Action
K	Start or stop the kill feed reader
N	End this session and start a new one
S	Open Settings
F	Fullscreen
C	Compact view
R	Refresh tracker data now
Esc	Close the open window

Troubleshooting

Nothing is counting.
Check the status pill at the top of Combat. "Screen capture off" means capture isn't running; press Start screen capture and pick the game's screen. If the read count isn't climbing, the HUD tab may be hidden or minimized. If the capture shows black, switch the game to borderless or windowed.

My kills show as deaths.
Press Swap kills ↔ deaths.

A kill or death was counted twice, or not at all.
Use Undo, or open the scoreboard for exact numbers. If it keeps happening, open Show reader right after and look at What it did with each line: it shows how the line was read and why it was counted or skipped. A misread name usually means the kill feed box needs adjusting, or you should add the misread spelling to your in-game name list.

Team scores say "not readable".
Open Show reader and look under Team score box. The color image should show the three scores. If it shows the wrong area, redraw the box from a fresh frame. Scores and match results only read while the score row is on screen (not while dead or on the map).

Cash numbers look wrong.
Start a new session (N) to reset the totals, and make sure the cash box isn't cutting off the left side of the reward lines.

The game stutters.
Set Screen reader load to Low impact, and set Highlight clips to off.

Highlights say "no game audio".
Start capture again and tick Also share system audio in Chrome's share window.

Privacy

	•	Screen reading is local. The kill feed, scores and cash are read on your PC, and your screen isn't uploaded anywhere.
	•	Tracker data comes from wardogstracker.gg using the ID you enter.
	•	Claude is only used if you add an API key. Coaching breakdowns send your stats; why-you-died reviews send a few frames from just before each death.
	•	Clips stay in your browser until you save them. Nothing is posted for you.
	•	Your history, settings and clips are stored in this browser on this PC. Use Backup to keep a copy of your history.

What's new

v18: Highlights and YouTube Shorts. Automatic kill streak clips scored for how post-worthy they are, a vertical Shorts editor with kill call-outs, and montages. Rendering only happens when you press the button.

v17: Reliability.

	•	The kill feed always gets read first. In earlier versions, the score backup and winner-banner checks could crowd it out and kills went missing.
	•	New team score reader that handles dim leading zeros and team-tinted digits.

v16: Crash deaths. Deaths with no killer named (crashes, falls, suicides) now count.

v15: Headshots. Headshot tracking from the kill feed skull icon and reward lines, shown across Combat, history, records, CSV export, kill screenshots and the coach.

v14: Coaching styles. Eight playstyles that change the built-in coach, goals and the Claude coach's personality.

v13: Wins without the score box. Wins and losses are logged from the end-of-match banner when the team score box can't be read.

v12: Scoreboard reader. Finds your highlighted row more reliably, and still reads kills, assists, deaths and revives when the cash amount is misread.

v11: Cash accuracy.

	•	Wallet misreads no longer inflate Earned and Spent.
	•	Cut-off reward names are merged.
	•	"+$180" read as "+5180" is fixed.

v10: Fixes. Backup team score reader, and no more double-counted deaths.
