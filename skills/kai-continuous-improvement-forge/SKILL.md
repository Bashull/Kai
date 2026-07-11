---
name: kai-continuous-improvement-forge
description: Use when newly discovered code, documents, prompts, protocols, libraries, infrastructure, archives, tools, or patterns may improve Kai and need governed evaluation, testing, registration, or promotion.
---

# Kai Continuous Improvement Forge

## Overview

Turn verified discoveries into reusable capabilities without blindly absorbing code, secrets, duplicates, obsolete patterns or unsupported claims.

Core rule: **No promotion without provenance**.

Use `kai_capability_scanner.py` for static evidence extraction and `kai_capability_registry.py` for governed lifecycle state. When historical lineage matters, route to `kai-genealogy-mining`. After material changes, record durable outcomes through `gpt-long-term-memory`.

## When to use

Use this skill when:

- a new script, document, protocol, prompt, library, tunnel, connector, model, architecture or workflow appears;
- the user asks whether Kai can learn from, reuse, absorb, modernize or improve itself using a discovery;
- a historical component may contain capability DNA worth rescuing;
- a validated tool or skill may be ready for promotion.

## Evidence contract

Every candidate must identify:

- source and provenance;
- SHA-256 when the source is a stable file;
- artifact type and extracted capabilities;
- secret, corruption and execution-risk signals;
- existing equivalent or related capability when known;
- test evidence before validation;
- explicit approval before canonization.

The lifecycle is:

`DISCOVERED` → `CLASSIFIED` → `CANDIDATE` → `TESTING` → `VALIDATED` → `PROMOTED` → `CANONICAL`.

Alternative states include `QUARANTINED`, `SUPERSEDED` and `REJECTED`.

## Safety contract

- Never execute discovered code merely to classify it.
- Never propagate raw credentials or secret values.
- Never call two files duplicates from name or size alone; exact duplicate claims require SHA-256 equality.
- Never promote historical code because it is old, emotionally important or large.
- Never promote new code merely because it is newer.
- Prefer dry-run, reversible actions, explicit conflicts and rollback for mutating tools.
- Preserve source evidence even when a candidate is rejected or superseded.

## Workflow

1. Discover the artifact and preserve source identity.
2. Run `kai_capability_scanner.py` statically.
3. If secret signals exist, classify as `QUARANTINED`; do not reproduce values.
4. Compare SHA-256 against known artifacts and registry entries.
5. Search for existing capabilities before creating a duplicate tool or skill.
6. Register the candidate in `kai_capability_registry.py`.
7. Build focused tests appropriate to the capability.
8. Move to `VALIDATED` only with passing test evidence and provenance.
9. Move to `PROMOTED` only after deployment verification.
10. Move to `CANONICAL` only with explicit approval evidence.
11. Store durable outcomes, paths, improvements and pending work through `gpt-long-term-memory`.

## Decision labels

Artifact decisions include `TOOL_CANDIDATE`, `SKILL_CANDIDATE`, `PROTOCOL_CANDIDATE`, `LIBRARY_CANDIDATE`, `INFRASTRUCTURE_CANDIDATE`, `MEMORY_CANDIDATE`, `DUPLICATE`, `QUARANTINED` and `NEEDS_RESEARCH`.

Registry lifecycle decisions use `DISCOVERED`, `CLASSIFIED`, `CANDIDATE`, `TESTING`, `VALIDATED`, `PROMOTED`, `CANONICAL`, `QUARANTINED`, `SUPERSEDED` and `REJECTED`.

A discovery is not a capability merely because it exists. A capability becomes live only after evidence, testing and controlled promotion.
