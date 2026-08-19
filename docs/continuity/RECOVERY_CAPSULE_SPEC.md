# Kai Recovery Capsule — Public-Safe Spec

Status: DRAFT / public-safe recovery layer

Purpose: provide enough non-sensitive metadata to reconstruct the Kai ecosystem when one or more nodes are unavailable, without storing private memories, credentials, tokens, personal data, or secret configuration.

## Core rule

**One authority per object. Multiple recovery replicas. No single indispensable node.**

## Capsule contents

A generated capsule should contain only pointers, hashes, state summaries, and recovery instructions:

- `RESTORE.md` — recovery order and bootstrap steps.
- `LAST_STATE.md` — last material state summary safe for this repo.
- `ACTIVE_CHECKPOINTS.json` — IDs, names, status, and authority pointers; no private content.
- `PROJECT_MAP.json` — project -> authority -> canonical path/URL.
- `CAPABILITY_MAP.json` — capability -> implementation -> consumers.
- `NODE_MAP.json` — node IDs, role, last verified sync, and coverage status.
- `INVENTORY_SUMMARY.json` — counts only when scope is labelled `PARTIAL`, `VERIFIED_SCOPE`, or `FULL_INVENTORY`.
- `PROTOCOL_POINTERS.json` — names/IDs/URLs/SHAs of CURRENT protocols.
- `MANIFEST.sha256` — integrity hashes.
- `VERSION.txt` — capsule schema version and generation timestamp.

## Prohibited content

Do not commit:

- API keys, tokens, passwords, `.env` contents, recovery codes, or credentials.
- private diary entries or personal long-term memory content.
- private images or biometric references.
- raw private chat exports.
- encrypted private bundles unless explicitly approved for this repository and threat-modelled first.

## Node roles

- **ChatGPT:** orchestration and writeback; never sole source of truth.
- **Google Drive:** documentation, memory, genealogy, checkpoints, protocols, library, ingestion queue.
- **Mobile / Termux:** offline field and recovery node.
- **PC:** heavy build/test/workshop node; not archive master.
- **GitHub:** code, tests, branches, releases, public-safe recovery metadata.
- **Hugging Face:** models, datasets, Spaces, training artifacts and ML demos.

## Recovery behavior

If one node is unavailable, continue from the most recent verified capsule plus the authority nodes still reachable. Queue local changes for reconciliation. When the missing node returns, compare authority, provenance, hashes and unique changes before merging.

A newer timestamp does not automatically win.

## Coverage law

**NOT READ != DOES NOT EXIST.**

Never claim a global total of repositories, skills, tools, models, datasets, projects, or assets from a partial source. Every inventory claim must state its scope.

## Writeback

After material work:

1. update the canonical authority;
2. update checkpoint/memory where appropriate;
3. update project/capability/node maps;
4. regenerate or patch the Recovery Capsule;
5. verify hashes and mark the replica's sync state.

## Local logical layout

Mobile and PC should expose the same logical tree where practical:

```text
KAI_ECOSYSTEM/
  00_RECOVERY_CAPSULE/
  10_ACTIVE_WORK/
  20_INGEST_QUEUE/
  30_SYNC_OUTBOX/
  40_LOCAL_TOOLS/
  50_PROJECT_WORKSPACES/
  90_CACHE_REBUILDABLE/
  99_PRIVATE_ENCRYPTED/
```

Every ingestion queue must trend to zero.

## Survival objective

Losing a provider account, connector, or device must not erase the ability to reconstruct identity documentation, project map, active checkpoints, capability map, canonical authorities, and recovery procedure.

> If a node falls, continue. If it returns, reconcile. If it disappears, rebuild.
