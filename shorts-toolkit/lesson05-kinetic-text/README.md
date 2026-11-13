# Lesson 5: kinetic text on the beat

Rebuilt 2026-11-13 (the Nov 12 original never reached GitHub). Tested on demo input only.

Words slam in with an overshoot and a shake, pulse on every beat while on screen, and exit fast.
Output is a transparent 1080x1920 60 fps overlay: overlay.webm (VP9 alpha) and overlay.mov (ProRes 4444).

    python3 kinetic_text.py words.example.json --out out

Words go on a beat number or a time in seconds. Styles: slam (white), gold, red. Use the same
bpm as music_bed.py so the words and music line up. Keep to 1 to 3 short words (rule 15).
Font: Poppins Bold from lesson01.

Demo (3 words, 3.28 s): 197 frames, both files decode with alpha. About 47 s to render.
Frames were extracted and alpha confirmed; I have not looked at them on real footage.
Needs Python 3, numpy, Pillow, ffmpeg.
