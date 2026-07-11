---
name: kai-discovery-to-capability
description: Use when one concrete newly found artifact must be inspected, classified, compared, and turned into a traceable capability candidate without executing it blindly.
---

# Kai Discovery to Capability

## Overview

Transform one concrete discovery into an evidence-backed candidate decision. The default path is static inspection first, not execution.

Primary tool: `kai_capability_scanner.py`.

Core rule: **do not execute discovered code** during classification.

## When to use

Use this skill for a newly found:

- code file or script;
- protocol, prompt, directive or document;
- package manifest or library definition;
- infrastructure, connector or tunnel configuration;
- historical artifact that may contain reusable capability DNA.

Use the broader `kai-continuous-improvement-forge` skill when multiple candidates, promotion decisions or lifecycle governance are involved.

## Evidence contract

Collect, when available:

- exact path or source URL;
- SHA-256;
- size and type;
- Python functions, classes and imports when applicable;
- inferred capability labels;
- secret-signal labels with values omitted;
- provenance;
- known exact-hash matches;
- relationship to existing tools, skills or canon.

## Safety contract

- do not execute discovered code merely to understand or classify it.
- Never reproduce a detected secret value in reports, memory, prompts or manifests.
- Exact duplicate status requires SHA-256 equality.
- A filename match, timestamp or similar size is supporting context only.
- Preserve parse failures, unreadable files and missing provenance honestly.
- Use `QUARANTINED` when sensitive signals make ordinary promotion unsafe.

## Workflow

1. Ground the exact artifact.
2. Run `kai_capability_scanner.py` statically.
3. Review artifact type, SHA-256, capabilities, secret signals, structure and provenance.
4. If `DUPLICATE`, link to the verified exact-hash source instead of creating another copy.
5. If `QUARANTINED`, isolate from ordinary promotion and do not expose values.
6. Compare against existing capabilities.
7. Register only a traceable candidate, not an automatic promotion.
8. Route historical version questions to `kai-genealogy-mining`.
9. Route multi-candidate promotion work to `kai-continuous-improvement-forge`.

## Decision labels

- `TOOL_CANDIDATE`: executable capability worth testing.
- `SKILL_CANDIDATE`: reusable workflow or operating contract.
- `PROTOCOL_CANDIDATE`: governance, restoration, safety or operating procedure.
- `LIBRARY_CANDIDATE`: package or reusable dependency candidate.
- `INFRASTRUCTURE_CANDIDATE`: connector, relay, endpoint or environment capability.
- `MEMORY_CANDIDATE`: evidence that may belong in durable memory after review.
- `DUPLICATE`: exact SHA-256 already known.
- `QUARANTINED`: sensitive or unsafe for ordinary promotion.
- `NEEDS_RESEARCH`: evidence is insufficient for a stronger conclusion.
