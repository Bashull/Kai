# KAI Minecraft · Codex skills candidate (2026-10-10)

Repository-local Codex Skills: `.agents/skills/`.

- `kai-minecraft-pc`: local GUI and RCON adapter, dry-run by default.
- `kai-minecraft-skill-forge`: generates new **uninstalled draft** skills from a purpose/trigger.
- `kai-sololand-commentator`: offline commentator samples, not an in-game live bot.

Use on authorized PC after code review, in isolated worktree; first `python -m unittest discover -s tests -v`, then `python .agents/skills/kai-minecraft-pc/scripts/mc_operator.py doctor`.

**NO deployment, no live Sóloland access, no credentials in this bundle.** Full installation, risk register and genealogy: `docs/KAI_MINECRAFT_CODEX_RUNBOOK.md`.

## Edición cruzada y evidencia (extensión offline)

- `kai-minecraft-cross-edition`: produce un **plan únicamente** para Java, Bedrock nativo o Java+Geyser. No inicia sesiones de juego.
- `docs/minecraft/donor-ledger.json`: catálogo de 18 donantes con commit fijo, papel, licencia y política de estudio/posible adaptación.
- `docs/minecraft/validate_donors.py`: comprueba la trazabilidad y rechaza copia implícita de licencias desconocidas/copyleft; sin red.
- `kai-sololand-commentator/scripts/event_bridge.py`: puente **offline** de eventos simulados; no valida criptográficamente el origen y **no debe conectarse directamente** a un feed público sin un verificador de identidad externo.

Comandos sin conexión desde la raíz del repo:

```sh
python -m unittest discover -s tests -v
python docs/minecraft/validate_donors.py docs/minecraft/donor-ledger.json
python .agents/skills/kai-minecraft-cross-edition/scripts/route_mc.py --edition unknown --server unknown --intent observe
```

La prueba en el PC y un servidor staging es una fase distinta; consulta `docs/plans/2026-10-10-kai-minecraft-java-bedrock.md`.


## Android S24 live vision/control · 2026-10-11

- `relay/kai_minecraft_live.py` is the verified local-only Bedrock vision/control bridge for the authorized S24 Ultra.
- It uses official scrcpy capture, one H.264 encoder, an MKV FIFO, FFmpeg in-memory JPEG frames, sequence-aware action observation and automatic portrait/landscape capture recovery.
- All HTTP endpoints are localhost-only and token-protected. The saved Minecraft server-address privacy confirmation is not bypassed.
- This path is client control only; it does not imply Sóloland server administration or RCON access.
- Full evidence, launch contract, timings and limits are in `docs/KAI_MINECRAFT_CODEX_RUNBOOK.md`.


## Termux Balanced profile

The S24 runtime is now organized as a profile-driven deployment. See:

- `docs/minecraft/TERMUX_UNIFIED_EVOLUTION_PLAN.md` — phased architecture and gates.
- `docs/minecraft/KAI_TERMUX_BALANCED_PROFILE.md` — active Balanced settings, evidence and limits.
- `relay/profiles/balanced.env` — portable runtime defaults.
- `relay/kai-profile` — health-checked profile switcher with rollback.
- `relay/kai_balanced_probe.py` — soak/health benchmark.
- `relay/kai-codex-balanced` — Android guard; Codex agent execution stays blocked until external containment is proven.
