---
name: shorts-audio
description: Use whenever making or finishing a Short or any video with music. Generates the music with ACE-Step and masters the final audio with master_me.
---

# Shorts audio: ACE-Step + master_me

## Where the tools are
- **ACE-Step** (music generation): https://github.com/ACE-Step/ACE-Step-1.5, UI: https://github.com/fspecii/ace-step-ui
- **master_me** (automatic mastering plugin): https://github.com/trummerschlunk/master_me, installers: its Releases page.

## Environment limits (be honest about these)
- The user is on **Windows with an AMD GPU**. ACE-Step runs there via ROCm 7.2 and **Python 3.12 only**, in a separate `venv_rocm`, started with `start_gradio_ui_rocm.bat` or `start_api_server_rocm.bat`. Never use `uv sync` or `uv run acestep` (installs NVIDIA PyTorch and breaks the AMD setup). Support depends on the exact Radeon card; CPU mode is a slow fallback.
- Cloud sessions have **no GPU**, so ACE-Step cannot generate music there. In a cloud session, write the music prompt and settings for the user to run locally, or ask for the generated file.
- master_me is CPU-only and light. For local use, use the Windows VST3/CLAP from Releases. The Linux build can run headless in a cloud session only if one is built.

## Workflow
1. **Music prompt**: write an ACE-Step prompt (genre, mood, tempo/BPM, instruments, instrumental unless the user wants vocals). Match the Short's length (usually 15 to 60 s) and keep it free of vocals that fight game audio and voice.
2. **Generate** with ACE-Step; keep 2 to 3 takes and let the user pick.
3. **Mix**: music sits well under game audio and any voice; duck it during callouts and kills.
4. **Master** the final mix with master_me (not just the music). Target about -14 LUFS integrated, true peak at or below -1 dBTP.
5. **Verify** with the `shorts-review-gates-qc` loudness check before sign-off.

## Rules
- Never claim a track was generated or mastered unless it actually was. Report which step ran, which was skipped and why.
- Only use music the user has the rights to; ACE-Step output is fine, but don't mix in copyrighted tracks.
