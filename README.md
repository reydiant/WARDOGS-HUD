# WARDOGS HUD

A live stats heads-up display for **WARDOGS**, built as a single HTML file. Put it on your second monitor and it tracks your career, your current session, your kills and deaths, your cash, and who is about to win the match. It also has a built-in coach and an optional AI coach.

No install, no server, no build step. Open `wardogs-hud.html` in Chrome or Edge.

> **Unofficial fan project.** Not affiliated with the WARDOGS developers or WARDOGS Tracker. Your data stays in your own browser.



---

## What it does

### Career and session tracking
- **Service Record** pulled from the WARDOGS Tracker API: rank, XP, K/D, roles and rank ladder.
- **This session** panel with live kills, deaths, K/D, streaks and time played.
- **Live XP** for the session, read from the XP lines on your screen. It is shown as `~+N` and swapped for the exact figure once the tracker syncs.
- **Refresh** button and a **Sync career** popup, so you never have to reload the page after syncing on wardogstracker.gg. The HUD picks up new data on its own and warns you when the tracker data is stale.

### Kill feed reader (screen capture)
- Reads the kill feed from a box you draw on your game, using screen capture and OCR (Tesseract.js). Nothing is sent anywhere.
- Counts your kills and deaths, with weapon and name matching (Strict / Normal / Loose).
- **Team kill detection** using the team badge icons, plus your own list of team kill words.
- **Why-you-died reviews** (optional) with a screenshot of each kill and death.
- Clean player names, undo for miscounts, and a "swap kills and deaths" switch if your feed is read the other way around.

### Team score box and match winners
- Reads the three team scores under the minimap (first to 100 wins).
- Shows the match pace and which team is about to win.
- Logs the **winning team color** (green, blue or red) at the end of each match, and tracks your wins per team color in K/D history.
- Uses a small box and a slow read rate instead of scanning the whole screen, so it costs far less CPU.

### Cash tracking
- Reads your wallet from the top-right money display.
- Tracks **cash earned, spent and net per session**.
- Reads the small reward lines under it (kills, revives, assists, control zone, revenge kills and more) and totals them by type.
- Reads the **KILL CONFIRMED** display in the middle of the screen and adds any kills the feed missed.
- Reward-line XP feeds the live session XP.

### History
- K/D by **day, week and month** (24H / 30D / ALL views).
- Wins by team color, cash per session, and session history.
- Export to **CSV**, plus **Backup** and **Restore backup** for all your data.

### Coach
- **Built-in coach** with rule-based feedback: what you're doing right, habits to fix and what to improve next.
- **Cash management** advice: break-even goals, overspending and where your money came from.
- **Session goals** and a K/D goal.
- **Optional Claude AI coach**: add your own Anthropic API key and the HUD sends a short stats packet for a deeper breakdown. Pick Sonnet 5.5 (deeper) or Haiku 5.5 (faster, cheaper). **Copy for Claude** copies the same packet if you'd rather paste it into a chat yourself.
- Rough-patch alert when you're on a bad streak.

---

## Getting started

1. **Sign in on the tracker.** Go to [wardogstracker.gg](https://wardogstracker.gg), sign in with Steam and sync your career. Keep your profile public.
2. **Open the HUD.** Open `wardogs-hud.html` in Chrome or Edge, ideally on your second monitor.
3. **Add your ID.** In **Settings**, enter your SteamID64 (the 17-digit number in your profile URL, or paste the profile link) or your Discord user ID, plus your in-game name.
4. **Start screen capture.** Click **Start screen capture** and pick your game screen or window.
5. **Draw the boxes.** Open **Adjust area** and draw each box over the matching part of your game:
   - **Kill feed box**
   - **Team score box** (under the minimap)
   - **Cash box** (top right)
   - **Kill confirm box** (middle of the screen)
6. **Play.** Use **Show reader** to see what the HUD is reading if a box needs tuning.

> With no ID entered, the HUD shows example data so you can look around first.

> **Opening it on iPhone:** screen capture only works on a desktop browser. On a phone you can view the Service Record, but the readers won't run.

---

## Settings worth knowing

| Setting | What it does |
|---|---|
| **Screen reader load** | **Low impact** (best game FPS, about 1 s slower), **Balanced**, or **Max speed** (fastest, most CPU). |
| **End-of-game winner** | **Read the team score box** (recommended, lowest CPU), scan the whole screen, or off. |
| **Screenshot on each kill and death** | **Kill feed area only** is lighter than full screen. |
| **Why-you-died reviews** | Off, or on with Haiku 5.5 or Sonnet 5.5 (needs an API key). |
| **Name matching** | Strict, Normal or Loose, for short or unusual names. |
| **Kill feed order** | Killer on the left or on the right. |
| **Refresh every** | How often the HUD checks the tracker for new data. |
| **Keep screen awake** | Stops your second monitor from sleeping. |

---

## Performance

The HUD shares your CPU with the game, so it has a small but real cost. It is built to keep that low:

- Screen capture is capped at 5, 8 or 15 frames a second depending on your load setting.
- Every reader only runs OCR when its box has visibly changed. A quick pixel check decides that, and it costs a fraction of a millisecond.
- The team score box is read every few seconds, not constantly.
- The cash and kill confirm boxes are only read when their text changes.
- Winner detection uses the small score box. It does not scan the whole screen unless you turn that on.

To keep the impact as low as possible:
- Use **Low impact**.
- Keep your boxes small.
- Set screenshots to **Kill feed area only**.
- Keep the winner setting on **Read the team score box**.
- Keep **Show reader** closed while you play.
- Turn on hardware acceleration in Chrome (Settings, System).
- Run the HUD on a second monitor.

You can check the cost yourself in Chrome's Task Manager (Shift+Esc) while you play.

---

## Privacy

- Everything is stored in your browser's local storage on your computer.
- Screen capture and OCR run locally in the page. Video frames are never uploaded.
- The HUD only connects to `wardogstracker.gg` for your stats and, if you turn it on, to the Anthropic API for AI coaching and reviews. The API key stays in your browser.
- Use **Backup** to keep a copy of your data and **Restore backup** to move it to another browser.

---

## Limits

- The WARDOGS Tracker API is read-only. Your career data only changes when you sync on wardogstracker.gg, so the HUD can't force a sync. It opens the sync page for you and then checks for the update.
- The readers depend on your game's UI, resolution and brightness. If a box misreads, redraw it tighter and check it with **Show reader**.
- Live XP and cash from the screen are estimates until the tracker syncs.
- Works best in borderless windowed mode, so the screen can be captured.

---

## Built with

- A single HTML file with plain JavaScript and CSS
- [Tesseract.js](https://github.com/naptha/tesseract.js) for OCR
- The browser's screen capture API
- The WARDOGS Tracker API
- Optional: the Anthropic API

---

## Disclaimer

This is an unofficial community tool. WARDOGS and WARDOGS Tracker belong to their respective owners. The HUD only reads what is shown on your own screen and public tracker data. It doesn't read game memory or modify the game, but check the game's rules if you're unsure.

## License



<img width="1207" height="2383" alt="Image" src="https://github.com/user-attachments/assets/b3f83031-4d65-4829-b72f-e03386648730" />
<img width="1320" height="2130" alt="Image" src="https://github.com/user-attachments/assets/80a79348-7e0e-40f4-ab64-735ef62351e9" />
<img width="1320" height="2460" alt="Image" src="https://github.com/user-attachments/assets/3dc254c5-310d-485b-a8a1-58f995909620" />
<img width="1320" height="2442" alt="Image" src="https://github.com/user-attachments/assets/7d0d2add-73be-4f98-a763-8178a92584ad" />
<img width="1320" height="2460" alt="Image" src="https://github.com/user-attachments/assets/0171f9be-42fd-414c-88f5-b8e99669148d" />
<img width="1320" height="2460" alt="Image" src="https://github.com/user-attachments/assets/ef62ad0c-c58a-4bbf-b57b-4168c4717a07" />
<img width="1320" height="2682" alt="Image" src="https://github.com/user-attachments/assets/58e1c723-3f6e-4f60-a1ba-e5cd99450960" />
<img width="1320" height="2460" alt="Image" src="https://github.com/user-attachments/assets/8798fb04-3bf2-4ac6-8c0a-ae790fa1ecb7" />
<img width="1320" height="2077" alt="Image" src="https://github.com/user-attachments/assets/a03de656-c2b9-4a71-8b74-a0f1e70944bc" />
