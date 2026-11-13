# Lesson 4: loop ending

Rebuilt 2026-11-13 (the Nov 11 original never reached GitHub). Tested on synthetic footage only.

The last 0.4 s whips sideways (motion blur and a small zoom) and dissolves into frame one,
so the replay looks continuous. Target: average watch % through replays.

    python3 loop_ending.py make short.mp4 --out short_loop.mp4 [--blend 0.4]
    python3 loop_ending.py check short_loop.mp4

`check` prints the seam score: mean pixel difference between the last and first frame
(0 to 255). Under about 2 is invisible. Keep the end card on screen about 1.2 s before the blend.

Demo result: seam score 4.3 to 1.1, same length (4.00 s), same 240 frames, audio kept (30 ms fades at both ends).
The demo's start and end already looked alike, so real footage will start from a much worse number.
Needs Python 3, numpy, Pillow, ffmpeg.
