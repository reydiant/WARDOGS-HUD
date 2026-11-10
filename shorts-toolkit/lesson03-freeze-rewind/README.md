# Lesson 3: impact freeze, then rewind into the kill

Built 2026-11-10 (rebuilt the same day after the overnight run couldn't reach GitHub).
Tested on synthetic footage only, not on real gameplay and not in a real Short yet.

## What it does

Frame one is the kill landing, which is standing rules 1 and 2. The tool then
shows the kill again from the lead-up so the viewer sees how it happened.

- **0 to 0.3 s:** the hit frame is frozen. It punches in, shakes, gets a short flash and a gold vignette.
  The gunshot at the hit plays under it.
- **0.3 to 0.6 s:** a fast rewind through the lead-up, with a violet tint and a small color split.
  The audio is the same stretch reversed and sped up, quiet, like a tape rewind.
- **After that:** normal play from the start of the lead-up, through the hit, to the end.

It adds 0.6 seconds, so keep that in mind against the 40 second limit.
The target is the 51% who swipe away in the first second. Layer the lesson 1 payoff text
and the lesson 2 music on top.

## Use it

    python3 freeze_rewind.py clip.mp4 --hit 12.40 --out opener.mp4

`--hit` is the time in seconds, in your clip, of the exact frame where the kill lands.
Other settings: `--lead 0.9` (seconds shown in the rewind), `--freeze 0.3`, `--rewind 0.3`,
`--tail 4` (stop 4 seconds after the hit). The output is 1080x1920, cropped from the center.

Try it first on fake footage: `python3 make_demo_footage.py demo.mp4 --hit 2.0`.

Needs Python 3, numpy, Pillow and ffmpeg on the PATH.

## Checks on the demo

- Output length is the source from the lead-up start plus 0.6 s, and audio and video lengths match.
- The kill frame at 1.50 s matches the source hit frame (PSNR 45 dB), so the normal-play part is untouched.
- Audio: gunshot at -17 dBFS under the freeze, rewind at -34 dBFS, second gunshot at -16 dBFS.
- My first version washed out frame one with the flash, so I cut the flash strength from 0.55 to 0.32.

## Known gaps

- Real footage may have a muzzle flash or screen shake that fights the punch-in. Look at frame one.
- If the clip is very bright, the gold vignette may need to be weaker.
- You still have to find the hit time yourself. A kill-feed reader could supply it.
