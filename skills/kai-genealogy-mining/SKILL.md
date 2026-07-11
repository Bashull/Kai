---
name: kai-genealogy-mining
description: Use when tracing historical versions, ZIP snapshots, copied files, forks, ancestors, descendants, placeholders, or functional evolution across Kai artifacts.
---

# Kai Genealogy Mining

## Overview

Reconstruct technical lineage from evidence instead of nostalgia, filenames or dates alone.

Primary tool: `kai_genealogy_miner.py`.

Core rule: **timestamps alone never prove ancestry**.

## When to use

Use this skill when:

- two files may be copies, variants, ancestors or descendants;
- a ZIP snapshot must be compared with a later extraction or repository;
- historical scripts may have evolved into renamed modern modules;
- a zero-byte or corrupted file may have a recoverable non-empty counterpart;
- the user asks which version came first, which was superseded, or what capability survived.

## Evidence contract

Collect:

- SHA-256 for exact-copy claims;
- file size and path;
- source provenance;
- Python functions, classes and imports when applicable;
- structural overlap;
- parse failures;
- timestamps as secondary context only;
- additional source evidence needed to establish direction.

## Safety contract

- Never execute historical code simply to classify lineage.
- Never claim `EXACT_COPY` without SHA-256 equality.
- Never infer ancestry from timestamp order alone.
- Never hide syntax or parse errors; preserve them as evidence.
- Never assume newer means better or older means canonical.
- Preserve source provenance and distinguish exact copies from functional descendants.

## Workflow

1. Ground the exact left and right artifacts.
2. Run `kai_genealogy_miner.py`.
3. Check SHA-256 equality first.
4. Check zero-byte placeholders and corruption signals.
5. For Python, compare functions, classes, imports and structural overlap.
6. Use timestamps only after structural relationship exists, and only as a directional hint.
7. Search additional provenance before upgrading a candidate relationship into demonstrated ancestry.
8. Record useful capability survival separately from historical lineage.
9. Route reusable discoveries to `kai-continuous-improvement-forge`.

## Decision labels

- `EXACT_COPY`: identical SHA-256.
- `CORRUPTED_PLACEHOLDER`: zero-byte or equivalent placeholder beside a non-empty variant.
- `FUNCTIONAL_ANCESTOR_CANDIDATE`: strong structural overlap suggests lineage, but direction still requires supporting provenance.
- `DIVERGED_BRANCH`: partial shared structure indicates a branch or common ancestry candidate.
- `UNRELATED_OR_UNKNOWN`: current evidence is insufficient for a stronger relationship.

A genealogy result can be useful without being canonical. Preserve uncertainty honestly.
