# KAI Minecraft · Codex skills candidate (2026-10-10)

Repository-local Codex Skills: `.agents/skills/`.

- `kai-minecraft-pc`: local GUI and RCON adapter, dry-run by default.
- `kai-minecraft-skill-forge`: generates new **uninstalled draft** skills from a purpose/trigger.
- `kai-sololand-commentator`: offline commentator samples, not an in-game live bot.

Use on authorized PC after code review, in isolated worktree; first `python -m unittest discover -s tests -v`, then `python .agents/skills/kai-minecraft-pc/scripts/mc_operator.py doctor`.

**NO deployment, no live Sóloland access, no credentials in this bundle.** Full installation, risk register and genealogy: `docs/KAI_MINECRAFT_CODEX_RUNBOOK.md`.
