---
name: gpt-long-term-memory
description: Use when a task depends on prior chats, earlier decisions, user preferences, project state, artifact locations, previous improvements, unresolved work, or continuity across sessions.
---

# GPT Long-Term Memory

## Overview

Use durable external memory as evidence-backed continuity across chats. The model's current context is not proof of long-term recall; load persisted records before making claims about previous work.

Core principle: **source before story, continuity without invention**.

## When to use

Use this skill when the user says or implies:

- â€œcontinueâ€, â€œas we did beforeâ€, â€œremember what we madeâ€, or â€œwhere did we leave it?â€
- a new chat must recover project state, paths, versions, decisions, improvements or pending work;
- exact historical context matters for code, Drive, GitHub, Android, ZIPs, prompts, protocols or lore;
- substantial work has just been completed and future chats should inherit it.

do not invent continuity when durable memory is unavailable. Say what is missing and use connected sources or current evidence instead.

## Memory loading contract

1. Look for the newest canonical `boot_packet.md` or `boot_packet.json` in the available local runtime or connected private source.
2. Load the boot packet before asserting what happened in earlier chats or sessions.
3. Search deeper ledger records when exact paths, hashes, versions, provenance, supersession chains or historical decisions matter.
4. Prefer ACTIVE records. Treat SUPERSEDED records as history, not current truth.
5. Reconcile current-chat evidence with durable memory; newer explicit evidence may supersede older records, but never silently.

Default local runtime paths:

- Windows: `%USERPROFILE%\.kai_memory`
- Other systems: `~/.kai_memory`
- Override: `KAI_MEMORY_HOME`

Primary tool: `kai_memory_ledger.py`.

Useful commands:

```bash
python kai_memory_ledger.py search --query "memory terms"
python kai_memory_ledger.py boot --project kai --max-chars 12000
python kai_memory_ledger.py doctor
```

## Memory writing contract

After material work, preserve a session closure containing:

- objective;
- actions actually performed;
- artifacts and exact locations;
- decisions and precedence changes;
- improvements gained;
- unresolved items;
- next recommended step;
- provenance when available.

Use `session-close` with a JSON session summary. Do not save private reasoning or hidden chain-of-thought; save concise outcomes, evidence, decisions and externally useful context.

## Evidence and confidence

Every durable claim uses one confidence label:

- `EXPLICIT` â€” directly stated or deliberately decided by the user.
- `EVIDENCED` â€” supported by files, hashes, tool output, connected sources or verified execution.
- `INFERRED` â€” reasoned from evidence but not directly confirmed.
- `UNKNOWN` â€” context is incomplete; do not guess.

Preserve provenance for important records: source type, path or URL, document/file ID, hash when useful, and capture time when available.

Never upgrade `INFERRED` to `EVIDENCED` merely because an inference was repeated many times.

## Safety contract

- Never store or emit raw API keys, OAuth secrets, passwords, tokens, cookies or private-key material.
- Redact sensitive values before hashing, persistence, event logging, boot generation or export.
- Do not copy a private memory database into a public repository.
- Do not erase superseded memory just because it is outdated; preserve history unless the user explicitly requests deletion under an appropriate policy.
- Do not treat generated first-person prose as factual memory without evidence and provenance.
- Do not claim automatic recall in a new chat unless this skill and a readable memory source are actually available.

## New-chat boot sequence

1. Resolve the canonical memory source.
2. Read `boot_packet.md` or `boot_packet.json`.
3. Check memory health when a doctor command is available.
4. Identify identity/directives, preferences, current project state, validated decisions, recent work, artifacts, improvements and pending work.
5. Search deeper records only for details needed by the current task.
6. Continue from evidence; do not restart solved work unnecessarily.
7. When material work ends, create a new session closure and regenerate the boot packet.

## Decision labels

- `ACTIVE`: current durable memory.
- `SUPERSEDED`: historical record replaced by a newer explicit or evidenced record.
- `ARCHIVED`: retained but outside active recall.
- `QUARANTINED`: excluded from boot/search defaults because of sensitivity, corruption or unresolved trust.
- `SKIP_EXACT_DUPLICATE`: identical stable record already exists.
- `INSERTED`: new durable record accepted.

The boot packet is a compact entry point, not the entire memory. Search the ledger when precision matters.
