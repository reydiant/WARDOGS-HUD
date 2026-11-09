# Lesson 2: kill-synced original music

Built 2026-11-09. I can't listen to audio, so I checked it with measurements
(loudness, peaks, timing, spectrogram). How it sounds is for you to judge.
Not used on a real Short yet.

## What it does

Builds an original music bed for a Short from the same `events.json` as lesson 1.
Everything is synthesized in code, so there are no samples and no copyright problem
(standing rule 16).

- The music starts on a hit at frame one. No intro.
- Every kill gets a low boom and a bright ping. The ping goes up a step with each
  kill, so a streak sounds like it is climbing. Headshots get a second, higher ping.
- A riser builds into the last kill, then there is a short silent beat right before it.
- The music dips for a moment on each kill so the game's gunshot and hit sound come through (rule 17).
- It prints a cut plan: how far each kill is from the nearest 8th note, and how many
  milliseconds to trim or add before it to land it on the beat (rule 7).
- Loudness comes out at -14 LUFS with true peak under -1 dB (rule 18).

## Use it

    python3 music_bed.py render events.json --out out --prefix short01

You get two files:

- `short01_bed_standalone_-14LUFS.wav`, the bed on its own at final loudness.
- `short01_bed_under_game_-20LUFS.wav`, quieter, to sit under the game audio. Mix it
  with the footage, then check the full export (below).

Check or fix the final export's audio:

    python3 music_bed.py measure final.mp4
    python3 music_bed.py master final_audio.wav final_audio_-14.wav

`--bpm 140` forces a tempo. The default picks the tempo in 120 to 152 where your
kills land closest to the beat.

Needs Python 3, numpy, scipy and ffmpeg on the PATH.

## What I measured on the demo

- Kill hits start within 2 to 4 ms of each kill time.
- Silence of -88 dBFS in the 100 ms before the last kill.
- Standalone bed: -14.0 LUFS, true peak -1.5 dB. After AAC encoding: -14.0 LUFS, -1.4 dB.

## Known gaps

- Taste is untested. If the bed feels too busy under your game audio, use the -20 LUFS file
  or lower the `music * 0.8` mix line.
- One key and one chord loop (A minor) for now.
