# Kai Continuous Improvement Forge + GPT Long-Term Memory Design

**Date:** 2026-07-11
**Status:** Approved by Asier.

## Goal

Create a governed improvement layer for Kai that turns useful discoveries into reusable skills and tools, plus a persistent memory system that can reconstruct context across new chats from durable external records.

## Architecture

The design has two connected subsystems:

1. **Kai Continuous Improvement Forge** — discovers capabilities in code, documents, prompts, protocols, libraries, tunnels and architectures; classifies them; compares them with existing capabilities; and promotes validated candidates.
2. **GPT Long-Term Memory Bridge** — stores durable memories outside chat, generates compact boot packets, records session closures, preserves provenance and supports future-chat reconstruction.

Both subsystems are evidence-first. Inferred narrative is never promoted as fact.

## Canonical principles

- Truth over brilliance.
- Source before story.
- No promotion without provenance.
- No destructive action without explicit intent, dry-run where applicable and rollback when practical.
- Exact duplicates use hashes, not filenames alone.
- Sensitive credentials are redacted and excluded from memory packets.
- Historical code is source material, not automatic canon.
- Newer code is not automatically superior; precedence is decided by canon, tests, safety and explicit decisions.

## Persistent memory data model

A memory record contains:

- `memory_id`: stable SHA-256-derived identifier.
- `created_at` and `updated_at`: UTC ISO-8601 timestamps.
- `kind`: `CORE_IDENTITY`, `PREFERENCE`, `PROJECT_STATE`, `DECISION`, `ACTION`, `ARTIFACT`, `IMPROVEMENT`, `LESSON`, `PENDING`, `CONTEXT` or `SESSION`.
- `scope`: `global`, `project`, `chat`, `entity` or a named project scope.
- `title` and `content`.
- `status`: `ACTIVE`, `SUPERSEDED`, `ARCHIVED` or `QUARANTINED`.
- `priority`: integer 0–100.
- `confidence`: `EXPLICIT`, `EVIDENCED`, `INFERRED` or `UNKNOWN`.
- `tags`: normalized keywords.
- `provenance`: source path/URL/document ID, optional SHA-256, source type and captured timestamp.
- `supersedes`: optional previous memory IDs.

## Storage and durability

The tool uses Python standard library only.

Default memory home: `%USERPROFILE%\.kai_memory` on Windows or `~/.kai_memory` elsewhere, overrideable with `KAI_MEMORY_HOME`.

Files:

- `memory.sqlite3` — canonical structured index.
- `events.jsonl` — append-only audit event log.
- `boot_packet.md` — compact human-readable context for a new chat.
- `boot_packet.json` — machine-readable equivalent.
- `sessions/<session_id>.json` — immutable session closure snapshots.
- `exports/` — explicit user-requested exports only.

Actual private memory data is never committed to the public repository. Only code, schemas, tests and synthetic fixtures are versioned.

## New-chat continuity contract

At the start of a Kai-related chat, the `gpt-long-term-memory` skill should:

1. Look for a canonical boot packet in available connected sources or local runtime.
2. Load it before making project claims.
3. Distinguish durable records from current-chat statements and inferred context.
4. State when memory is unavailable instead of inventing continuity.
5. Search deeper records when the current task depends on past decisions, paths, versions or pending work.

At the end of material work, the skill should create or update session memory with: objective, actions, artifacts, decisions, improvements, unresolved items, source references and next recommended step.

## Boot packet selection

The boot packet is not a raw dump. It selects active memories using priority, recency, confidence, scope and explicit project relevance. It must include:

- identity/directives;
- user preferences relevant to collaboration;
- current project state;
- validated decisions and precedence rules;
- latest completed work and artifact locations;
- active improvements/capabilities;
- pending work and next recommended step;
- memory health metadata.

The packet has a configurable character budget and never silently drops critical identity or active pending items.

## Continuous improvement forge

Every discovery is classified as one of:

`SKILL_CANDIDATE`, `TOOL_CANDIDATE`, `LIBRARY_CANDIDATE`, `PROTOCOL_CANDIDATE`, `CANON_CANDIDATE`, `MEMORY_CANDIDATE`, `INFRASTRUCTURE_CANDIDATE`, `HISTORICAL_ONLY`, `SUPERSEDED`, `DANGEROUS`, `DUPLICATE`, `NEEDS_RESEARCH`.

Promotion states are:

`DISCOVERED` → `CLASSIFIED` → `CANDIDATE` → `TESTING` → `VALIDATED` → `PROMOTED` → `CANONICAL`.

Alternative terminal states: `QUARANTINED`, `SUPERSEDED`, `REJECTED`.

No artifact reaches `PROMOTED` without source, provenance, comparison against existing capability, risk assessment and tests appropriate to its behavior.

## Initial skills

Create these skills first:

1. `gpt-long-term-memory` — use when continuity across chats, prior decisions, project state, past work, pending work or personal collaboration context matters.
2. `kai-continuous-improvement-forge` — use when new artifacts may improve Kai's capabilities.
3. `kai-discovery-to-capability` — use when a concrete discovery must be classified and turned into a candidate capability.
4. `kai-genealogy-mining` — use when tracing historical versions, forks, ZIP snapshots, code ancestry or functional descendants.

## Initial tools

- `tools/kai_memory_ledger.py` — persistent memory store and CLI.
- `tools/kai_capability_scanner.py` — static classification of discovered artifacts into capability candidates.
- `tools/kai_genealogy_miner.py` — hash/name/AST comparison for historical Python ancestry.

## Testing strategy

- Python `unittest`; standard library only.
- Test-first for production behavior.
- Contract tests for every skill: required frontmatter, trigger wording, safety/evidence sections and decision labels.
- Memory tests cover idempotency, search, supersession, boot selection, session closure, secret redaction and deterministic exports.
- Forge tests cover classification, duplicate detection and promotion prerequisites.
- Genealogy tests cover exact hash match, functional ancestry hints, parse failures and non-Python fallback.

## Promotion and deployment

Implementation happens in isolated branch `feature/kai-continuous-memory-forge`.

After tests pass:

1. Commit code/spec/plan to the isolated branch.
2. Copy validated skills and tools into `_KAI_BRIDGE\skills` and `_KAI_BRIDGE\agent_tools` without overwriting unrelated originals.
3. Initialize private runtime memory outside Git.
4. Seed memory only from explicit or evidenced records.
5. Generate the first boot packet.
6. Mirror the current boot packet and memory manifest to a private Google Drive folder for future-chat recovery.

## Success criteria

- A fresh process can store a memory, restart, search it and generate the same boot context.
- A session closure records what was done, where, why, what changed, what improved and what remains.
- A new chat can recover context from the boot packet without relying on the current conversation transcript.
- No credential value is present in emitted memory files.
- All skill contract tests and tool tests pass.
- The existing inherited `scripts/test-memory-system.cjs` is documented as incomplete legacy intent rather than falsely treated as proof of a finished system.
