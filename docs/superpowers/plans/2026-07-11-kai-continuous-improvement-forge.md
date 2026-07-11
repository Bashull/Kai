# Kai Continuous Improvement Forge Implementation Plan

> **For agentic workers:** use TDD task by task. No promotion claim without fresh verification.

**Goal:** Convert verified discoveries from code, documents, prompts, protocols, libraries, infrastructure and historical archives into traceable capability candidates, tested tools or reusable skills without contaminating Kai with secrets, duplicates or unsupported claims.

**Architecture:** Three standard-library Python tools plus three skills. The capability scanner performs static evidence extraction and initial classification. The genealogy miner compares versions by exact hashes and structural evidence. The capability registry stores append-only state transitions and a deterministic current manifest. Skills govern when each tool is used and how evidence becomes a promoted capability.

**Tech stack:** Python 3.11+ standard library, `unittest`, JSON/JSONL, AST, SHA-256, Markdown skill contracts.

## Global safety rules

- Never execute discovered code during scanning.
- Never print raw secret values.
- Never infer exact duplicates from filename or size alone; use hashes.
- Never claim ancestry from timestamps alone.
- Historical code is source material, not automatic canon.
- Newer code is not automatically superior.
- Promotion requires provenance, risk classification and appropriate tests.
- Private runtime registries stay outside public Git unless they contain only synthetic fixtures.

---

### Task 1: Capability scanner core

**Files:**
- Create: `tools/kai_capability_scanner.py`
- Create: `tests/test_kai_capability_scanner.py`

**Core interfaces:**
- `sha256_file(path: Path) -> str`
- `scan_artifact(path: Path, known_hashes: set[str] | None = None) -> dict`
- `detect_secret_signals(path: Path, text: str | None) -> list[str]`
- `extract_python_structure(text: str) -> dict`
- `infer_capabilities(path: Path, text: str | None, structure: dict | None) -> list[str]`

**Decision labels:** `TOOL_CANDIDATE`, `SKILL_CANDIDATE`, `PROTOCOL_CANDIDATE`, `LIBRARY_CANDIDATE`, `INFRASTRUCTURE_CANDIDATE`, `MEMORY_CANDIDATE`, `DUPLICATE`, `QUARANTINED`, `NEEDS_RESEARCH`.

- [ ] Write failing tests for Python structure extraction, SHA-256 duplicate detection, secret-signal redaction and protocol classification.
- [ ] Run targeted tests and verify RED.
- [ ] Implement the smallest static scanner that passes.
- [ ] Verify full scanner tests GREEN.
- [ ] Commit: `feat: add Kai capability scanner`.

### Task 2: Genealogy miner core

**Files:**
- Create: `tools/kai_genealogy_miner.py`
- Create: `tests/test_kai_genealogy_miner.py`

**Core interfaces:**
- `fingerprint(path: Path) -> dict`
- `compare_files(left: Path, right: Path) -> dict`
- `compare_python_structure(left_text: str, right_text: str) -> dict`

**Relation labels:** `EXACT_COPY`, `CORRUPTED_PLACEHOLDER`, `FUNCTIONAL_ANCESTOR_CANDIDATE`, `DIVERGED_BRANCH`, `UNRELATED_OR_UNKNOWN`.

Rules:
- Exact copy requires SHA-256 equality.
- Ancestry remains a candidate unless provenance/order evidence supports direction.
- Python comparison uses functions, classes and imports; parse failure is explicit evidence, not hidden.

- [ ] Write failing tests for exact copies, zero-byte placeholders, changed Python descendants and unrelated files.
- [ ] Run targeted tests and verify RED.
- [ ] Implement minimal comparison logic.
- [ ] Verify all genealogy tests GREEN.
- [ ] Commit: `feat: add Kai genealogy miner`.

### Task 3: Capability registry

**Files:**
- Create: `tools/kai_capability_registry.py`
- Create: `tests/test_kai_capability_registry.py`

**Core interfaces:**
- `CapabilityRegistry(home: Path)`
- `register(candidate: dict) -> dict`
- `transition(capability_id: str, new_state: str, evidence: dict) -> dict`
- `current_manifest() -> list[dict]`

**States:** `DISCOVERED`, `CLASSIFIED`, `CANDIDATE`, `TESTING`, `VALIDATED`, `PROMOTED`, `CANONICAL`, `QUARANTINED`, `SUPERSEDED`, `REJECTED`.

Promotion guards:
- `VALIDATED` requires provenance and test evidence.
- `PROMOTED` requires prior `VALIDATED` state.
- `CANONICAL` requires explicit approval evidence.
- Exact duplicate registration is idempotent.

- [ ] Write failing tests for registration, idempotency, invalid transitions and promotion guards.
- [ ] Verify RED.
- [ ] Implement JSONL event log plus deterministic current JSON manifest.
- [ ] Verify GREEN.
- [ ] Commit: `feat: add Kai capability registry`.

### Task 4: Three governing skills

**Files:**
- Create: `skills/kai-continuous-improvement-forge/SKILL.md`
- Create: `skills/kai-discovery-to-capability/SKILL.md`
- Create: `skills/kai-genealogy-mining/SKILL.md`
- Modify: `tests/test_skill_contracts.py`

Required skill sections:
- Overview
- When to use
- Evidence contract
- Safety contract
- Workflow
- Decision labels

Additional requirements:
- Descriptions start with `Use when` and contain triggers only.
- Forge skill requires compare-before-promote behavior.
- Discovery skill requires scanner output and provenance.
- Genealogy skill requires SHA-256 for exact-copy claims and forbids timestamp-only ancestry claims.

- [ ] Write failing contract tests for all three skills.
- [ ] Verify RED.
- [ ] Write minimal skills that satisfy contracts and encode the validated workflow.
- [ ] Verify GREEN.
- [ ] Commit: `feat: add Kai continuous improvement skills`.

### Task 5: CLI surfaces and integrated evidence package

**Files:**
- Modify each tool to include `argparse` CLI.
- Add CLI tests to the three test modules.

Commands:
- Capability scanner: `scan --path ... --out ... [--known-manifest ...]`
- Genealogy miner: `compare --left ... --right ... --out ...`
- Capability registry: `register --candidate ...`, `transition ...`, `manifest`, `doctor`.

- [ ] Write failing CLI tests.
- [ ] Verify RED.
- [ ] Implement CLI commands with JSON output and non-zero failures.
- [ ] Verify GREEN across all tools and skill contracts.
- [ ] Commit: `feat: add Forge tool CLIs`.

### Task 6: Deploy, seed registry and connect to long-term memory

**Deployment targets:**
- `_KAI_BRIDGE\agent_tools\kai_capability_scanner`
- `_KAI_BRIDGE\agent_tools\kai_genealogy_miner`
- `_KAI_BRIDGE\agent_tools\kai_capability_registry`
- `_KAI_BRIDGE\skills\kai-continuous-improvement-forge`
- `_KAI_BRIDGE\skills\kai-discovery-to-capability`
- `_KAI_BRIDGE\skills\kai-genealogy-mining`

Private registry runtime:
- `C:\Users\ASIER\.kai_capabilities`

- [ ] Run complete fresh tests.
- [ ] Deploy source/skill files and verify exact SHA-256 source/destination matches.
- [ ] Initialize private capability registry.
- [ ] Scan at least three real historical artifacts without executing them.
- [ ] Register candidates and preserve evidence.
- [ ] Record implementation in long-term memory and close a session.
- [ ] Regenerate boot packet and runtime manifests.
- [ ] Update private Drive recovery document with current boot state.
- [ ] Commit deployment metadata.

## Completion gate

Do not claim the Forge complete unless fresh verification proves:

- all scanner tests pass;
- all genealogy tests pass;
- all registry tests pass;
- all four skill contracts pass, including long-term memory;
- deployed hashes match validated source hashes;
- registry doctor is healthy;
- private memory doctor is healthy;
- no private databases or secret values appear in Git status.
