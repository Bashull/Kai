---
name: kai-minecraft-skill-forge
description: Generar skills de Codex para Minecraft o Sóloland desde capacidades contrastadas, sin duplicarlas ni instalarlas automáticamente; crear manifiesto candidato y preparar pruebas.
---

# Kai Minecraft Skill Forge

**Estado:** CANDIDATE / GENERADOR LOCAL TESTEABLE / NO PROMOTED.

Propósito: transformar una capacidad estudiada (por ejemplo control de chat, estado de combate, captura del cliente) en una nueva skill de Codex con trigger, propósito, dependencias, política de permisos, pruebas, recuperación y genealogía; **no** suponer que una skill generada ejecuta esa capacidad.

1. Recuperar la wiki/runbook y el CURRENT del proyecto; inventariar donors reales (repositorios propios, código antiguo, proyectos externos). REUSE → ADAPT → COMPOSE → ACQUIRE → BUILD. Registrar Capability DNA y Transfer×3.
2. Determinar primero la interfaz real (cliente GUI, servidor Java RCON, mod/plugin, API de voz) y sus límites; no resolver ausencia de APIs generando afirmaciones falsas.
3. Crear carpeta STAGING manualmente fuera de la raíz `.agents/skills`, por ejemplo `mkdir staging-mc-skills`.
4. `python .agents/skills/kai-minecraft-skill-forge/scripts/forge_skill.py minecraft-npc-dialogue --purpose 'Narrar combates de arena' --trigger 'Cuando se pida narrar combates en Minecraft' --staging staging-mc-skills`.
5. El generador valida nombre, produce `SKILL.md` y `manifest.json` y se niega a sobrescribir; queda CANDIDATE/NOT_TESTED. Implementar scripts, tests y probes medibles ANTES de mover el candidato a `.agents/skills`.
6. Separar `COMPREHENSION_PROOF`, `RECONSTRUCTION_PROOF` y `PROOF_OF_COMPLETENESS`; ninguna prueba local equivale a cliente controlado o servidor integrado. Registrar errores, rollback, contratos de autorización y secretos por punteros. No incluir valores secretos.
7. Promover a CANONICAL solo después de evaluación y aprobación; sincronizar GitHub como fuente de código, Drive CURRENT/wiki como fuente documental.

Código: `scripts/forge_skill.py`. Pruebas: `tests/test_skills.py`. Las skills de Codex siguen el formato `.agents/skills/<nombre>/SKILL.md` respaldado por documentación oficial.
