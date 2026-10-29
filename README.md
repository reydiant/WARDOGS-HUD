# WARDOGS HUD

A live stats HUD for WARDOGS that runs from one HTML file. Open it in Chrome or Edge on a second monitor while you play.

## Features
- **Career stats** from the WARDOGS Tracker API: XP, level, roles, cash, rank, with a Refresh button and a Sync career shortcut
- **Kill feed reader**: share your game screen and it counts kills and deaths from the on-screen feed, including team kills (read from the team badge icons)
- **Match tracking**: reads the three team scores under the minimap, warns at match point, and logs the winner
- **Cash tracking**: reads the top-right money display for earned, spent and net per session, with a breakdown by reward type
- **K/D history** by day, week and month, with records, rivals and CSV / JSON backup
- **Wins by team color** (green, blue, red) and your team's win-loss record
- **Coach**: built-in analysis, plus an optional breakdown from Claude if you add your own API key

## How to use
1. Download `wardogs-hud.html` and open it in Chrome or Edge.
2. Enter your SteamID64 (sign in at wardogstracker.gg first so your stats sync).
3. Press **Start screen capture**, pick the screen your game is on, then draw boxes around the kill feed, team scores and cash display.
4. Run the game in borderless or windowed mode. Exclusive fullscreen can capture as black.

## Privacy
Screen capture is read in your browser and nothing is uploaded. The HUD only calls the WARDOGS Tracker API for your stats, and the Claude API only if you add a key.

## Notes
Unofficial. Not affiliated with Bulkhead, Team17 or WARDOGS Tracker. Needs a desktop Chromium browser for screen capture.
