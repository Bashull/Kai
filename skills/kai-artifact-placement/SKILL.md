---
name: kai-artifact-placement
description: Use when creating, receiving, moving, classifying, archiving, staging, promoting, or recovering any Kai artifact and its correct storage destination is unclear or consequential.
---

# Kai Artifact Placement

## Overview

Apply the machine-readable `kai_location_policy.json` before saving or moving anything. Storage is part of provenance: the destination must reflect function, sensitivity, lifecycle and authority.

## When to use

Use for documents, code, skills, tools, prompts, protocols, reports, evidence, project assets, AI workspace outputs, snapshots, historical sources, unknown files and sensitive material.

## Canonical Drive zones

- `00_KAI_CORE`: identity, memory, governance, bootstrap, current indexes and canonical navigation.
- `10_KAI_LAB_INGESTION_FORENSICS`: audits, extraction, candidates, test evidence, migration logs and staging.
- `20_PROJECTS`: creative and technical projects with their own identity.
- `30_AI_WORKSPACES`: AI Studio, Hugging Face and other external AI environments.
- `40_LIBRARY_REFERENCE`: research, documentation and external references.
- `80_INBOX_UNCLASSIFIED`: unknown material goes to 80_INBOX_UNCLASSIFIED.
- `90_ARCHIVE_HISTORICAL`: snapshots, ancestors, superseded and historical material.
- `99_PRIVATE_SENSITIVE`: sensitive material goes to 99_PRIVATE_SENSITIVE.

## Local source and runtime rules

Skills live first in the validated worktree under `skills/<name>/SKILL.md`. Tools live first under `tools/<name>.py`. Runtime deployment targets are `_KAI_BRIDGE/skills/...` and `_KAI_BRIDGE/agent_tools/...`, but source before runtime is mandatory.

## Placement workflow

1. Identify artifact kind and sensitivity.
2. Call `/donde-va` or `kai_control_plane.py where --kind <kind>`.
3. Preserve current path, source, hash when available and incoming references.
4. Write or move only after destination is explicit.
5. Verify destination and unchanged identity after movement.
6. Record material changes in memory and migration evidence.

## Safety contract

Unknown material must not be guessed into canon. Secrets and personal data stay outside general memory. Historical artifacts are preserved before replacement. Movement must never be confused with promotion.

## Decision rule

A correct destination does not make an artifact canonical. Placement, validation, deployment and canon are separate decisions.
