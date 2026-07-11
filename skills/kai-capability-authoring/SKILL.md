---
name: kai-capability-authoring
description: Use when creating a new Kai skill or tool, changing behavior in an existing one, replacing an implementation, or deciding whether a discovered capability should become reusable code or process guidance.
---

# Kai Capability Authoring

## Overview

Create or update skills and tools through the Control Plane, never by scattering files across arbitrary folders. Use `writing-skills` for skill design and `test-driven-development` for executable behavior.

## When to use

Use for `/crea-skill`, `/crea-herramienta`, `/actualiza-skill`, `/actualiza-herramienta`, or any equivalent request to build, refine, repair or replace a reusable Kai capability.

## Creation workflow

1. Classify the desired capability as skill, tool, protocol, library or mixed system.
2. Resolve storage through `kai_location_policy.json`.
3. Use `create-skill` or `create-tool` to create source in the validated worktree.
4. Write tests or contract checks before production behavior.
5. Keep state at `CANDIDATE` until evidence exists.
6. Record provenance, hashes and test evidence before promotion.

## Update workflow

1. Inspect the existing source and current runtime version.
2. Compare behavior and identify the exact change.
3. snapshot before replace.
4. Use `update-skill` or `update-tool` against the source copy.
5. Re-run focused tests and the relevant regression suite.
6. Deploy only the verified source; confirm source/runtime hashes when promoted.

## Storage contract

source before runtime is mandatory. Candidate skills belong under the worktree `skills/`; candidate tools under `tools/`; snapshots under capability state storage; evidence in the lab; runtime copies only after validation and promotion. Unknown material goes through `80_INBOX_UNCLASSIFIED`; sensitive material never enters general canon.

## Test and promotion contract

The normal lifecycle is `DISCOVERED -> CLASSIFIED -> CANDIDATE -> TESTING -> VALIDATED -> PROMOTED -> CANONICAL`.

- `TESTING` requires focused evaluation.
- `VALIDATED` requires passing tests and provenance.
- `PROMOTED` requires verified deployment evidence.
- `CANONICAL` requires explicit approval.

Never jump states because an idea is exciting or newer.

## Safety contract

- Never execute discovered historical code merely to inspect it.
- Never overwrite a source without a recoverable snapshot.
- Never deploy directly to runtime before tests.
- Never copy secrets into prompts, memory, evidence or public Drive documents.
- Never call a candidate promoted or canonical without registry evidence.
