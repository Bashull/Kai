---
name: kai-skill-doctor
description: Audit active Termux agent skill directories for format, hashes, symlinks and portable SEP-2640 manifest candidates without running or installing any skill.
---

# KAI Skill Doctor

When auditing installed skills, diagnosing a missing SKILL.md, checking metadata and path safety, or preparing an offline MCP Skills manifest, run `kai-skill-doctor`.

Modes: `kai-skill-doctor` is an offline human summary; `kai-skill-doctor --json` prints a redacted JSON report; `kai-skill-doctor --root ~/.agents/skills --sep-preview broken-zip-salvage` prepares a candidate SEP-2640 entry for one verified skill.

It never installs or invokes other skills, never modifies existing files, never connects to the network, and never approves activation. A READY_FOR_REVIEW result does not mean it works on another machine. LINK_REFERENCE indicates a symlink not automatically followed. Do not change symlinks blindly.

Operational documentation: `~/tools/kai-skill-doctor/README.md`. Code: `~/tools/kai-skill-doctor/skill_doctor.py`. For failures inspect the exit status, original target path and README rollback procedure. Do not expose secret values in logs.
