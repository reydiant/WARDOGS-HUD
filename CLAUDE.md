# WARDOGS-HUD project rules

## Making a YouTube Short (always)

Whenever making, planning or checking a Short:

1. Use the `shorts-hook-title-pack` skill for the hook, title, description, hashtags and pinned comment.
2. Use the `shorts-review-gates-qc` skill for the staged build, approval gates and ffmpeg checks.
3. Use the `shorts-audio` skill (`.claude/skills/shorts-audio/SKILL.md`) for music and mastering:
   - **ACE-Step** generates the music bed.
   - **master_me** masters the final mix.

Do not skip step 3 because the music "is already there". If a tool can't run in the current environment, say so and ask; don't silently skip it or fake the result.
