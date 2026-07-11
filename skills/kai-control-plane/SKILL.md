---
name: kai-control-plane
description: Use when a Kai chat, terminal session, Termux node, PC agent, or automation needs continuity, memory access, capability operations, artifact placement, health checks, or governed creation and updates.
---

# Kai Control Plane

## Overview

Use `kai_control_plane.py` as the single operational entrypoint over memory, boot, capability registry, placement policy, evidence, authoring and promoted parallel capabilities. It orchestrates proven tools; it must not duplicate their logic or bypass guardrails.

## When to use

Use for new-chat recovery, remembering previous work, closing or absorbing sessions, creating or updating skills/tools, locating destinations, writing evidence, inspecting capability state or running a global doctor.

## Commands

Conversational aliases and CLI equivalents:
- `/despierta` -> `wake`
- `/recuerda` -> `remember`
- `/absorbe` -> `absorb-chat`
- `/cierra` -> `close-session`
- `/crea-skill` -> `create-skill`
- `/crea-herramienta` -> `create-tool`
- `/actualiza-skill` -> `update-skill`
- `/actualiza-herramienta` -> `update-tool`
- `/donde-va` -> `where`
- `/promueve` -> `promote`
- `/organiza` -> `organize`
- `/checkpoint` -> `checkpoint`
- `/evidencia` -> `evidence`
- `/doctor-global` -> `doctor`
- `/integraciones` -> `integrations`
- `/doctor-integraciones` -> `integration-doctor`
- `/usa-capacidad` -> `integration-call`

## Placement contract

Before writing any artifact, load `kai_location_policy.json` or call `/donde-va`. Skills and tools are created in source first, evidence goes to the lab, and runtime deployment happens only after validation and promotion.

## Integration contract

The Control Plane integrates only curated, registry-backed capabilities. Current promoted targets include `storage-commander`, `termux-bridge-planner`, `backup-manifest`, `file-indexer` and `local-knowledge-vault`.

- `/integraciones` lists normalized integration records.
- `/doctor-integraciones` runs safe probes and reports degraded or blocked external state.
- `/usa-capacidad` may invoke only adapter-allowlisted operations.
- `storage-commander execute` is not exposed by this skill.
- Arbitrary registry artifacts are never executed just because they exist.

## Memory contract

New work that changes state, creates artifacts, fixes bugs, updates capabilities or leaves pending work must end with a checkpoint or session close. Regenerate the boot packet and verify memory health.

## Safety contract

- do not bypass guardrails
- Do not write secrets into general memory, prompts, evidence or boot packets.
- Do not overwrite existing skills or tools without a snapshot before replace.
- Do not claim deployment, promotion or canonical status without evidence.
- Do not move unknown material before classification.

## Decision labels

Use `DISCOVERED`, `CLASSIFIED`, `CANDIDATE`, `TESTING`, `VALIDATED`, `PROMOTED`, `CANONICAL`, `SUPERSEDED`, `QUARANTINED` and `REJECTED` according to the capability registry.
