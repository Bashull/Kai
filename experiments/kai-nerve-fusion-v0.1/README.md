# KAI NERVE Fusion v0.1 — CANDIDATE

Estado: CANDIDATE / NO DESPLEGADO / NO ARMADO.

Consolidación clean-room de los 22 donors de Drive para Termux + GPT. No añade otro bridge Bedrock y no toca el mundo principal.

## P0
Corregir frescura/provenance y demostrar:
Minecraft Bedrock real -> transporte seleccionado -> normalización -> SQLite/WorldBus
con session_id, source_seq y freshness verificables.

## Fail closed
- armed=false por defecto.
- stale/unknown/replay nunca autorizan movimiento.
- un único control owner mediante lease.
- driver físico y sensor Bedrock permanecen candidatos hasta pruebas en mundo de ensayo.

## Artefacto completo
Drive: KAI_NERVE_Fusion_v0.1_CANDIDATE.zip
SHA-256: 5fc7881fa30ced1870b92c158bbd024090bc134adcfdffbe443a0680b5797ba2

El ZIP contiene núcleo Python, tests, GPT SKILL, sensor Bedrock, donor matrix, runbook y manifiesto SHA-256 de cada archivo interno de los 22 ZIP.
