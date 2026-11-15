# KAI Skill Doctor v0.1.0 · Runtime Termux

## Status
LOCAL_DEPLOYED_AND_SMOKE_TESTED; NOT_CANONICAL; NO_REMOTE_MCP_PUBLISHED.
Origin: capability forge / read-only auditor adapted for live skill roots. All changes reversible. Owner: Asier.

## L0/L1 / What & why
Read-only installed-skill inspector and SEP-2640 manifest PREVIEW. Complements existing KAI Skills Forge (offline ZIP/catalog auditor); does not create a second registry, install skills, certify runtime or activate them.

## L2-L4 / Role, trigger and operation
Trigger: checking current Termux skill folders or preparing one skills/URI manifest.
CLI: `kai-skill-doctor`, `kai-skill-doctor --json`, `kai-skill-doctor --root ~/.agents/skills --sep-preview broken-zip-salvage`.
States: READY_FOR_REVIEW means format/hash check only; LINK_REFERENCE is a symlink not followed; BLOCKED indicates broken frontmatter, file type, dangerous path, or bounds. Duplicate-name count tracks occurrences, not independent executable capabilities.

## L5 / Dependencies, provenance, paths, permissions
Runtime Python >=3.10 + PyYAML (Termux observed 3.14.8 / 6.0.3). No network, provider tokens, pip install or daemon. Code: `~/tools/kai-skill-doctor/skill_doctor.py`; wrapper `~/.local/bin/kai-skill-doctor`; active instruction `~/.codex/skills/kai-skill-doctor/SKILL.md`. All local to mobile; PC untested/offline.
Read-only skill roots: `~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills`. Hashes raw resource bytes with 16MiB/resource and 512 resources/skill boundaries, blocks symlinks and sensitive paths. A malicious concurrent filesystem actor and hardlink edge cases are not fully mitigated; do not use on untrusted writable trees. No endpoint or OAuth.
SEP preview is a candidate JSON entry only, not a running MCP server, host activation or conformance certification. URI includes server ID + skill name; raw file bodies not printed. Server ID must be pinned before publication.

## L6 / Failure and rollback
If the wrapper fails: invoke `python -B ~/tools/kai-skill-doctor/skill_doctor.py`; run tests via `PYTHONPATH=~/tools/kai-skill-doctor python -B -m unittest discover -s ~/tools/kai-skill-doctor/tests -v`. Do not interpret a missing root as empty inventory. Disable tool by removing ONLY the new wrapper (backup under pilot lab). Remove only newly created code/skill after explicit verification; never delete original KAI skills or historical evidence. Separate one-off rollback for frontmatter repair: `python -B ~/KAI_RUNTIME_LAB/KAI_SKILLS_DOCTOR_PILOT_20261115/repair_frontmatter.py --rollback` (only if hashes still match).

## L7 / Rationale/genealogy
REUSE: old KAI Skills Forge archive auditor's integrity and route constraints; ADAPT: live root observation + raw SHA + safe YAML reading; COMPOSE: SEP-2640 preview with existing naming. No new catalog/dispatcher or agent loop. Not a replacement for Source Federation or global Capability Registry. Names/sha/receipts are evidence, not deployment certificates. Do not promote across devices without Windows/Termux tests and owner acceptance.

## Device-test receipt
2026-11-15 Termux: 16/16 unittest PASS; real 55 entries before/after targeted repair 34 to 36 READY_FOR_REVIEW, 19 LINK_REFERENCE; remaining BLOCKED=0 in inspected roots; historical 847/5229 not reaudited.
