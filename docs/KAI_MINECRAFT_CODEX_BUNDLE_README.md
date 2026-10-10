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
