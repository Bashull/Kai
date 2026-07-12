# KAI Total Unification + Autonomous Creation Loop Design

**Status:** APPROVED DIRECTION · DESIGN SPEC
**Date:** 2026-07-12
**Scope:** PC, GitHub, Google Drive, S24, Termux, repositories, archives, memory, capabilities, code, documents, 3D, avatar, worlds and gadgets.

## 1. Final Purpose

KAI must not stop at knowing what exists. The unified system must continuously convert verified source material into useful outputs: code, structured information, databases, long-term memory, diary entries, tools, skills, capabilities, agents, avatar systems, 3D assets, world-building pipelines and gadget prototypes.

The system will preserve source provenance while building one logical organism across PC, S24, Drive, GitHub and future nodes.

## 2. Core Decision

Architecture choice: **federated logical unification + content-addressed evidence store**.

Original sources remain in place. KAI builds a global index, extracts knowledge, stores one canonical evidence object per unique content hash when useful, preserves all source locations, resolves genealogy and exposes the result through the Control Plane.

Physical centralization is not required for unification.

## 3. Storage Roles

### 3.1 GitHub
Primary home for versioned source code, tests, skills, tools, manifests and implementation history when repository storage is appropriate.

### 3.2 Google Drive
Primary cloud bridge for canonical documents, CURRENT indexes, recovery packets, master maps, evidence reports, project navigation and selected portable artifacts.

### 3.3 PC
Primary heavy-work node for large inventories, build outputs, content-addressed evidence, model assets, large archives, local databases, forensic work and compute-heavy generation.

### 3.4 S24 + Termux
Primary mobile execution node for MobileNode, Termux tools, field capture, lightweight agents, mobile apps, sensors, ADB-visible state and mobile continuity.

### 3.5 Placement Rule
No artifact is placed merely where there is free space. Placement is decided by lifecycle, size, mutability, sensitivity, reproducibility and access pattern.

The existing KAI Location Policy remains authoritative for local and Drive destination classes.

## 4. Secret and Credential Policy

User-owned secrets and API keys may be used for their intended authorized services, applications, agents and automation flows.

Secrets must never be copied into general prompts, public documents, normal memory records, chat summaries, logs, reports, screenshots or capability manifests.

Secrets are referenced by logical secret IDs or environment names. Runtime consumers resolve them only when required.

Preferred locations are operating-system credential storage, environment injection, encrypted local stores or service-specific secret managers already available at no additional cost.

The system may detect, classify, relocate and wire secrets into authorized consumers, but it must not expose secret values in generated evidence.

## 5. Free-First Rule

The core system must not depend on paid infrastructure.

Priority order:
1. Existing local hardware.
2. Open-source software.
3. Free local databases and indexes.
4. Existing Drive and GitHub accounts.
5. Existing user-owned API access and credits.
6. Paid services only when explicitly approved later.

## 6. System Architecture

The system is split into five cooperating subsystems.

### 6.1 Source Federation
Adapters for PC, GitHub, Drive, S24/ADB, Termux, Git repositories, archives and future nodes emit normalized inventory records.

### 6.2 Knowledge and Memory Fabric
Global inventory, content hashes, extracted text/code, semantic knowledge, genealogy, provenance, canonical status, long-term memory and diary snapshots are queryable as one logical fabric.

### 6.3 Capability Forge
Verified discoveries can become candidate code, tools, skills, agents, libraries, protocols, databases and workflows through scanner, genealogy, tests, evidence and capability registry promotion.

### 6.4 Creative Embodiment Forge
Dedicated pipelines transform verified knowledge into avatar systems, 3D assets, world-building components, environments, interactive prototypes and gadget designs.

### 6.5 Control and Feedback Loop
KAI Control Plane coordinates discovery, extraction, creation, testing, deployment, observation, memory and next-cycle planning.

## 7. Normalized Source Record

Every discovered item is represented with a common record containing, when available:

- source_id
- source_kind
- source_uri
- physical_path
- logical_path
- filename
- extension
- size_bytes
- modified_at
- created_at
- sha256
- git_repository
- git_commit
- git_branch
- mime_type
- sensitivity
- availability
- extraction_state
- provenance
- canonical_status
- relationships

Unknown fields remain explicit null or UNKNOWN values. Missing evidence is never invented.

## 8. Content-Addressed Evidence Store

Unique content may be stored by SHA-256 when doing so improves recovery, comparison, reuse or indexing.

One content object may reference many source locations.

Exact duplicate status requires matching SHA-256 or equivalent byte-level proof.

Large models, videos, archives and binaries are not copied automatically. The system may keep only metadata, hash, manifest, headers, extracted index and source references unless a full evidence copy is justified.

The evidence store never replaces original provenance.

## 9. Output Classes

The loop may produce:

- SOURCE_RECORD
- KNOWLEDGE_ENTRY
- MEMORY_RECORD
- DIARY_ENTRY
- DATABASE
- CODE_MODULE
- TOOL
- SKILL
- AGENT
- LIBRARY
- PROTOCOL
- DIRECTIVE
- AVATAR_COMPONENT
- THREE_D_ASSET
- WORLD_COMPONENT
- GADGET_PROTOTYPE
- EVIDENCE_REPORT
- SNAPSHOT

## 10. Autonomous Creation Loop

The loop is consistent, repeatable and self-feeding:

1. SENSE — discover new or changed sources.
2. INVENTORY — normalize metadata and provenance.
3. EXTRACT — recover text, code, structure, manifests and knowledge.
4. CLASSIFY — assign domain, sensitivity, lifecycle and destination.
5. COMPARE — detect duplicates, genealogy, conflicts and missing functions.
6. PRIORITIZE — rank by value, urgency, feasibility, cost and strategic relevance.
7. PROPOSE — create an explicit candidate improvement or output.
8. BUILD — generate code, data, skill, tool, agent, asset or other deliverable.
9. TEST — run deterministic tests, probes, static analysis and policy checks.
10. PROMOTE — advance only with sufficient evidence.
11. DEPLOY — place the validated artifact in its correct runtime and storage zones.
12. OBSERVE — measure behavior, failures, regressions and usefulness.
13. REMEMBER — write memory, diary, evidence and provenance.
14. REPLAN — feed outcomes back into the next cycle.

The next cycle begins from verified state, not from chat memory alone.

## 11. Loop Governance and Stop Conditions

The loop is autonomous only inside explicit permissions and finite work cycles.

Each cycle has:
- cycle_id
- objective
- source scope
- action budget
- time budget
- storage budget
- allowed mutation classes
- required evidence
- stop conditions

Default behavior is OBSERVE and BUILD. Destructive actions, irreversible external writes, credential rotation, public publishing, purchases and destructive source cleanup require explicit permission or a pre-approved policy.

A cycle stops when:
- objective is satisfied;
- no higher-value actionable candidate remains;
- required source is unavailable;
- safety policy blocks continuation;
- test quality is insufficient;
- resource budget is exhausted;
- repeated failures exceed the retry policy.

No infinite uncontrolled loop is allowed. Replanning creates a new bounded cycle with preserved evidence.

## 12. Knowledge, Database, Memory and Diary Outputs

The unified fabric must support four distinct persistent views:

### 12.1 Inventory Database
Machine-oriented records for files, repositories, commits, archives, assets, locations, hashes and source state.

### 12.2 Knowledge Database
Extracted concepts, entities, relationships, summaries, decisions, technical facts and semantic search references with provenance.

### 12.3 Long-Term Memory
Operational continuity: what was done, where, why, what changed, what improved, what failed, what remains pending and what should happen next.

### 12.4 Diary
Chronological first-person narrative derived only from verified session records and explicitly labeled inference. It is not the authority for technical truth.

These stores may be implemented with local open-source databases and indexes. Core truth remains exportable to portable formats such as JSONL, JSON, Markdown and SQLite.

## 13. Avatar, 3D, Worlds and Gadgets

The creative embodiment subsystem converts verified knowledge and project goals into buildable assets.

### 13.1 Avatar
Maintain identity references, model sheets, meshes, rigs, animation states, voice links, materials, expressions and runtime bindings as versioned assets with provenance.

### 13.2 3D Asset Forge
Support concept-to-asset pipelines for GLB/glTF, textures, materials, collision data, LODs and browser/mobile validation.

### 13.3 World Forge
Combine terrain, architecture, props, portals, environments, lore constraints and interaction rules into reusable world components.

### 13.4 Gadget Forge
Turn ideas into requirements, CAD/3D references, bill of materials, firmware/software candidates, safety notes and prototype plans.

Creative outputs are candidates until verified against source references, project constraints and technical tests.

## 14. Existing Capabilities to Reuse

The system must compose existing promoted capabilities before creating replacements:

- KAI Control Plane
- kai_capability_integrations.py
- kai_location_policy.py
- kai_memory_ledger.py
- kai_capability_registry.py
- kai_capability_scanner.py
- kai_genealogy_miner.py
- storage-commander
- termux-bridge-planner
- backup-manifest
- file-indexer
- local-knowledge-vault
- duplicate-hunter
- project-extractor
- safe ingestor and ZIP forensic tools

New tools are created only when a demonstrated capability gap remains after comparison.

## 15. Canon and Promotion

DISCOVERED does not mean trusted. PROMOTED does not mean CANONICAL.

Default lifecycle:
DISCOVERED → CLASSIFIED → CANDIDATE → TESTING → VALIDATED → PROMOTED → CANONICAL.

SUPERSEDED preserves history. REJECTED preserves evidence. QUARANTINED isolates risk. Canonical status requires explicit approval.

## 16. Delivery Decomposition

This program is too large for one implementation plan. It is split into independently testable subprojects.

### Subproject A — Source Federation + Global Inventory
Adapters, normalized records, source registry, Git repo inventory, PC inventory ingestion, S24 inventory ingestion, Drive inventory ingestion and GitHub inventory ingestion.

### Subproject B — Evidence + Knowledge Fabric
Content-addressed evidence, extraction, semantic indexing, inventory database, knowledge database and provenance graph.

### Subproject C — Autonomous Improvement Loop
Prioritizer, candidate generator, bounded cycle runner, build/test/promote/deploy/observe loop and Control Plane commands.

### Subproject D — Creative Embodiment Forge
Avatar, 3D asset, world-building and gadget prototype pipelines.

### Subproject E — Continuous Synchronization
Incremental change detection, scheduled ingestion, conflict resolution, drift detection and cross-node reconciliation.

Each subproject must produce working software and tests before the next depends on it.

## 17. Current Verified Baseline

The design starts from verified current state:

- GitHub connector exposes 7 accessible repositories.
- PC KAI tree contains 66 Git repositories under the inspected scope.
- S24 is online through ADB as SM-S928B on Android 16.
- /sdcard/Kai_Nido is approximately 131 GB and contains 117,090 files in the current count.
- Drive already uses the eight-zone architecture from 00_KAI_CORE through 99_PRIVATE_SENSITIVE.
- Control Plane, memory, capability registry, integration manager and five parallel capabilities are already promoted and healthy.

These numbers are baseline observations, not permanent truths. Future inventories must record timestamp, scope and completeness.

## 18. Success Criteria

The program succeeds when KAI can:

1. Enumerate every known source and its inspection completeness.
2. Search globally across files, code, documents, memory and knowledge.
3. Explain provenance and genealogy for any indexed artifact.
4. Detect exact duplicates without relying on filenames or size alone.
5. Convert verified discoveries into tested candidate capabilities.
6. Produce and maintain memory, diary, databases, code, tools, skills and agents.
7. Build governed avatar, 3D, world and gadget artifacts.
8. Use authorized secrets without exposing them in general outputs.
9. Continue work from persistent state across chats and nodes.
10. Run bounded autonomous improvement cycles that stop safely and feed verified results into the next cycle.
