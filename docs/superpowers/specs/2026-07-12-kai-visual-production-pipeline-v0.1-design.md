# KAI Visual Production Pipeline v0.1 Design

**Status:** APPROVED DIRECTION -> DESIGN SPEC FOR REVIEW  
**Date:** 2026-07-12  
**Primary owner:** Kai / Asier  
**Governance:** KAI Control Plane  
**First validation case:** `CASE_001_504HN_SOLOLAND`  
**Primary specialist system:** Overlay Master System  
**Target nodes:** ChatGPT, Windows PC, S24 + Termux, Google Drive, GitHub and authorized cloud editors/generators.

## 1. Final Purpose

KAI Visual Production Pipeline turns a visual request into a governed, reproducible and auditable production job instead of a one-shot prompt.

The system must decide:

1. what the user is actually asking for;
2. which references are authoritative;
3. which base asset is locked and must not be reinterpreted;
4. which tool is best for each operation;
5. which operations require creativity and which require deterministic precision;
6. how to verify technical properties such as dimensions, alpha transparency, hashes and output format;
7. how to test the result in real use;
8. how to preserve evidence, rollback, memory and reusable lessons.

The system does not replace ImageGen, Adobe, Canva, Python, Termux, the PC, Drive or the Overlay Master System. It governs them as specialized execution organs.

## 2. Core Decision

Architecture choice: **Control-Plane-governed visual production router with specialist pipelines and deterministic verification gates**.

KAI Control Plane remains the governing entry point.

The new visual subsystem is composed from:

- a normalized visual job contract;
- a visual production router;
- domain adapters such as Overlay Master System;
- creative/external execution adapters;
- deterministic technical auditors;
- evidence and promotion hooks;
- optional Termux edge execution;
- existing memory, capability registry and placement policy.

No new subsystem may duplicate memory, capability lifecycle, artifact placement, evidence, promotion or canonical status logic already owned by KAI Control Plane.

## 3. Non-Negotiable Rules

1. **Source before runtime.** Skills and tools are authored in the validated worktree first.
2. **Base lock before editing.** An approved image is frozen by content hash and identity metadata before surgical edits.
3. **Creative generation is never used as proof.** It may create or transform, but verification is deterministic.
4. **Text is not trusted merely because it looks right.** Exact strings are audited separately.
5. **Transparency requested is not transparency verified.** Alpha must be inspected programmatically.
6. **No silent reinterpretation of an approved base.**
7. **No invention of usernames, slogans, logos, flags, identities, mascots, sponsors or social handles.**
8. **No direct promotion.** New capabilities follow the existing registry lifecycle.
9. **No secret leakage.** Credentials never enter prompts, manifests, evidence or general memory.
10. **No false success.** Blocked, degraded, partial and unverified states stay explicit.

## 4. 5/5 Quality Contract

Every production stage receives a five-axis gate.

A stage is `5/5` only when all five axes pass:

1. **Fidelity** — respects approved identity, references, text and locked constraints.
2. **Functionality** — serves the intended use and hierarchy.
3. **Technical integrity** — format, dimensions, alpha, file validity and deterministic checks pass.
4. **Provenance** — source references, tool route, hashes and decisions are recorded.
5. **Recoverability** — original input is preserved, output is versioned and rollback is possible.

Critical stages must not advance on 4/5.

Each axis is recorded as `PASS`, `FAIL` or `UNVERIFIED`, together with evidence or the explicit reason evidence is unavailable. `5/5` means five `PASS` results. An `UNVERIFIED` axis never counts as a pass.

Allowed result labels:

- `PASS_5_OF_5`
- `NEEDS_SURGERY`
- `NEEDS_REGENERATION`
- `BLOCKED`
- `UNVERIFIED`
- `REJECTED`
- `SUPERSEDED`

A human aesthetic preference can reject a technically valid asset. Technical validity never overrides Asier's approval.

## 5. System Architecture

```text
ASIER
  |
  v
CHAT / MOBILE / VOICE
  |
  v
KAI CONTROL PLANE
  |
  +--> MEMORY
  +--> CAPABILITY REGISTRY
  +--> LOCATION POLICY
  +--> EVIDENCE
  |
  v
KAI VISUAL PRODUCTION ROUTER
  |
  +--> DOMAIN ADAPTER
  |     +--> Overlay Master System
  |     +--> future character/comic/logo pipelines
  |
  +--> TOOL ROUTE
  |     +--> ImageGen
  |     +--> Adobe / Firefly
  |     +--> Canva
  |     +--> Python
  |     +--> Termux / S24
  |     +--> Windows PC
  |
  v
TECHNICAL AUDIT + REAL-USE TEST + PLATFORM AUDIT
  |
  v
HUMAN REVIEW
  |
  v
EVIDENCE -> REGISTRY -> MEMORY -> REUSE
```

## 6. Visual Job Contract

Every job is represented as a versioned JSON-compatible record.

Minimum contract:

```json
{
  "schema_version": 1,
  "job_id": "VJOB_YYYYMMDD_<slug>_<nonce>",
  "capability": "visual.overlay",
  "job_type": "derive_model_b",
  "source_case": "CASE_001_504HN_SOLOLAND",
  "source_model": "A2",
  "target_model": "B1",
  "status": "REQUESTED",
  "identity": {
    "primary": "504HN",
    "community": "Team 2 Dedos",
    "universe": "Sololand"
  },
  "exact_text": {
    "display_name": "『504HN』 🇭🇳",
    "social_handle": "@tu.diablito852",
    "server_address": "mc.sololand.club"
  },
  "base_lock": {
    "source_path": null,
    "sha256": null,
    "width": null,
    "height": null,
    "mode": null
  },
  "constraints": {
    "preserve_identity": true,
    "preserve_style": true,
    "preserve_exact_text": true,
    "real_alpha_required": true,
    "max_visual_change_percent": 15
  },
  "required_gates": [
    "isolated_visual_audit",
    "technical_audit",
    "real_use_test",
    "platform_occlusion_audit",
    "human_review"
  ],
  "tool_route": [],
  "artifacts": [],
  "evidence": [],
  "created_at": null,
  "updated_at": null
}
```

Unknown fields stay `null`, `UNKNOWN` or explicit unavailable states. They are never invented.

`max_visual_change_percent` is a declared scope budget, not a guaranteed pixel-difference measurement. v0.1 must not claim numeric compliance unless an explicit measurement implementation exists.

## 7. Job Lifecycle

The governed lifecycle is:

1. `REQUESTED`
2. `CONTEXT_LOADED`
3. `CLASSIFIED`
4. `PLANNED`
5. `BASE_LOCKED`
6. `CREATIVE_PASS`
7. `SURGERY_PASS`
8. `TECHNICALLY_AUDITED`
9. `REAL_USE_TESTED`
10. `PLATFORM_AUDITED`
11. `HUMAN_REVIEW`
12. `APPROVED`
13. `EVIDENCED`
14. `PROMOTABLE`
15. `MEMORIZED`
16. `REUSABLE`

Failure/recovery states:

- `NEEDS_SURGERY`
- `NEEDS_REGENERATION`
- `BLOCKED`
- `UNVERIFIED`
- `REJECTED`
- `SUPERSEDED`

State transitions are append-only in job history.

## 8. Tool Routing Matrix

### 8.1 ImageGen

Use for:

- new visual concepts;
- structural creative transformation;
- adding/removing major visual elements when generative reasoning is needed;
- style reinterpretation when explicitly requested.

Do not use as sole authority for:

- exact text;
- true alpha verification;
- deterministic dimensions;
- final certification.

### 8.2 Adobe / Firefly

Use for:

- surgical edits on an existing approved image;
- local object/text corrections;
- remove/replace content;
- background removal;
- region-specific changes;
- exact PNG output chains when supported.

### 8.3 Python

Use for deterministic verification and reproducible file operations:

- image dimensions;
- image mode;
- PNG validation;
- RGBA/alpha presence;
- transparent pixel statistics;
- SHA-256;
- image manifest generation;
- checkerboard/fake-transparency heuristics;
- compositing test content into known masks;
- packaging and reports.

### 8.4 Termux / S24

Use as an edge execution node for lightweight and field-available tasks:

- run the same image auditor locally;
- hash files;
- create manifests;
- organize job folders;
- receive bounded jobs;
- return evidence;
- validate mobile-visible outputs;
- execute approved lightweight scripts.

Termux does not replace heavy PC work.

### 8.5 Windows PC

Use for:

- heavy processing;
- large batch operations;
- local model execution;
- complex compositing;
- Blender/ComfyUI/local pipelines;
- large evidence stores;
- integration tests across the KAI filesystem.

### 8.6 Canva

Use optionally after a flat visual is approved:

- convert suitable flat designs into editable layouts;
- allow text/image replacement;
- create reusable user-facing templates.

Canva conversion is not required for certification of the source PNG.

### 8.7 Google Drive

Use for:

- project navigation;
- selected canonical project documents;
- evidence reports;
- recovery snapshots;
- approved portable artifacts.

Drive does not replace GitHub for source-controlled code and tests.

## 9. Candidate Skills

The first implementation program should create these focused skills.

### 9.1 `kai-visual-production`

Master routing skill.

Triggers on visual production tasks that require more than one tool, deterministic verification, evidence or reuse.

Responsibilities:

- classify the request;
- load project context;
- require base lock when editing an approved asset;
- choose domain adapter;
- invoke router and quality gates;
- close with evidence and memory.

### 9.2 `kai-visual-reference-lock`

Use when an approved visual base must be preserved while edits are applied.

Responsibilities:

- freeze source hash and metadata;
- define immutable/protected regions and exact text;
- record allowed change scope;
- reject ambiguous "recreate" behavior when surgical edit was requested.

### 9.3 `kai-visual-tool-routing`

Use when deciding which visual tool or node should perform a step.

Responsibilities:

- choose ImageGen, Adobe, Python, Canva, Termux or PC by operation class;
- prefer deterministic operations where possible;
- avoid whole-image regeneration for local fixes;
- record route reasons.

### 9.4 `kai-visual-audit`

Use before claiming a visual artifact is final, transparent, platform-safe or production-ready.

Responsibilities:

- require deterministic technical checks;
- run isolated visual audit;
- run real-use compositing test;
- run platform occlusion audit when relevant;
- require human review for aesthetic acceptance.

### 9.5 `kai-overlay-production`

Specialist skill that binds Overlay Master System to the general visual pipeline.

Responsibilities:

- load Overlay Master System canon;
- choose Model A/B family and geometry;
- classify identity, community and universe;
- apply overlay-specific locks and audits;
- preserve case history.

## 10. Candidate Tools

### 10.1 `tools/kai_visual_job.py`

Single responsibility: visual job schema, state transitions and append-only history.

Produces:

- `VisualJob`
- `VisualJobStore`
- deterministic JSON serialization
- transition validation

### 10.2 `tools/kai_visual_router.py`

Single responsibility: deterministic route planning from job type, constraints and available capabilities.

Produces:

- `VisualRoutePlanner`
- normalized route steps
- route reasons
- blocked/degraded states

It does not call cloud providers directly in v0.1.

### 10.3 `tools/kai_image_auditor.py`

Single responsibility: inspect image files and emit deterministic technical evidence.

Checks:

- file exists/readable;
- format;
- width/height;
- color mode;
- alpha channel;
- transparent pixel count and ratio;
- SHA-256;
- optional fake-checkerboard heuristic;
- optional expected-size check.

Produces JSON and process exit codes suitable for PC and Termux.

The checkerboard signal is advisory only and cannot fail a job by itself because deliberate checker patterns may exist in legitimate artwork. Real transparency is determined from the decoded alpha channel. Pillow is required for image-decoding checks; if unavailable, hashing may still run but image audit status must be explicit `BLOCKED` or `UNVERIFIED`, never success.

### 10.4 `tools/kai_visual_manifest.py`

Single responsibility: create a portable artifact manifest from job and audit results.

Includes:

- job ID;
- case;
- source hashes;
- output hashes;
- tool route;
- audit status;
- timestamps;
- artifact paths;
- evidence paths.

### 10.5 `tools/kai_overlay_adapter.py`

Single responsibility: translate Overlay Master System inputs and case metadata into the general visual job contract.

It does not generate images.

### 10.6 Future tool: `tools/kai_termux_visual_edge.py`

Not required for the first implementation slice.

Planned only after the portable auditor and manifest tool run successfully on Windows and their dependency footprint is proven acceptable for Termux.

## 11. Control Plane Integration

The Control Plane remains the authority.

Planned conversational aliases:

- `/visual-job` -> create or inspect a visual job
- `/visual-route` -> produce the governed tool route
- `/visual-audit` -> run deterministic audit on a local artifact
- `/visual-manifest` -> emit artifact manifest
- `/visual-doctor` -> report pipeline health and dependency availability

Initial implementation should avoid bloating `kai_control_plane.py`.

Preferred approach:

1. implement focused modules;
2. expose thin wrappers from the Control Plane;
3. reuse placement, evidence, registry and memory contracts;
4. keep external provider execution behind explicit adapters in later slices.

## 12. Storage and Evidence

Use the existing KAI Location Policy.

Recommended source locations:

- skills -> `skills/<skill-name>/SKILL.md`
- tools -> `tools/<tool-name>.py`
- tests -> `tests/test_<tool-name>.py`
- specs -> `docs/superpowers/specs/`
- plans -> `docs/superpowers/plans/`

Runtime and evidence locations are resolved through existing policy and Control Plane operations.

Per-job working layout:

```text
visual-jobs/<job_id>/
  job.json
  inputs/
  locked/
  working/
  outputs/
  audits/
  manifests/
  previews/
  rejected/
```

The runtime path is implementation-specific and must be policy-resolved rather than hardcoded globally.

## 13. Technical Audit Contract

A technical image audit emits at least:

```json
{
  "path": "asset.png",
  "exists": true,
  "readable": true,
  "format": "PNG",
  "width": 1080,
  "height": 1920,
  "mode": "RGBA",
  "has_alpha": true,
  "transparent_pixels": 123456,
  "transparent_ratio": 0.0595,
  "sha256": "<64 hex>",
  "expected_size_match": true,
  "checkerboard_suspected": false,
  "status": "PASS_5_OF_5"
}
```

The exact transparency ratio is evidence, not a universal pass threshold. Required transparency depends on the job contract.

## 14. Real-Use Audit Contract

A production asset is not approved only in isolation.

When applicable, generate a test preview with:

- representative gameplay;
- representative camera feed;
- representative profile image;
- representative chat content;
- representative alert content.

The test preview is temporary evidence and must not be mistaken for the clean template.

For TikTok or other platform-specific jobs, also audit against a real current UI capture when available.

## 15. Termux Integration

Termux is treated as a first-class edge node, not an afterthought.

v0.1 requirement:

- `kai_image_auditor.py` must be written with a portable Python core;
- no Windows-only path semantics in core functions;
- CLI accepts normal filesystem paths;
- JSON output is UTF-8;
- hashing uses Python standard library;
- Pillow is optional only for image decoding; dependency failure is explicit.

Later Termux slice:

- package auditor and manifest tools;
- create `inbox/`, `working/`, `audit/`, `approved/`, `rejected/`, `exports/`, `manifests/`;
- receive bounded jobs through existing authorized bridge;
- run `PING` before work;
- return audit evidence;
- never expose secrets.

Current historical control path to preserve:

```text
PC -> wireless ADB -> Kai MobileNode -> Termux RUN_COMMAND -> scripts/storage -> result
```

No live bridge capability is claimed without re-verification.

## 16. Error Handling

Errors are structured and never silently converted into success.

Required classes:

- invalid job contract;
- invalid state transition;
- missing base asset;
- base hash mismatch;
- unsupported image;
- missing alpha when required;
- dimensions mismatch;
- external tool unavailable;
- provider edit failure;
- audit failure;
- platform reference unavailable;
- human rejection.

A provider failure may trigger another route only when the router explicitly allows it.

Retries are bounded.

## 17. Security and Privacy

- No secrets in job JSON.
- No tokens in evidence.
- No private values in general Drive documents.
- Provider references use logical IDs or connector-managed handles when possible.
- Sensitive assets follow the existing sensitive placement route.
- Unclassified external material goes through the existing inbox/classification contract.
- Image metadata is not assumed safe; do not copy arbitrary metadata into memory without filtering.

## 18. Testing Strategy

Every executable behavior follows TDD.

Minimum test groups:

### 18.1 Visual job tests

- deterministic serialization;
- valid transition sequence;
- invalid transition rejection;
- append-only history;
- base lock hash persistence.

### 18.2 Router tests

- local edit routes to Adobe/surgery rather than whole-image regeneration;
- exact text requirement adds text audit;
- alpha requirement adds deterministic image audit;
- Termux-only environment chooses portable steps;
- unavailable provider returns `BLOCKED` or alternative route explicitly.

### 18.3 Image auditor tests

Use generated test fixtures:

- opaque RGB PNG;
- RGBA PNG with real transparency;
- fake checkerboard RGB image;
- wrong-size image;
- invalid/corrupt file.

Verify exact JSON keys and exit behavior.

Exact text constraints are stored and preserved deterministically in job metadata and adapters. Core v0.1 does not claim OCR-level verification of text rendered inside pixels. Final in-image text correctness requires human review or a later explicit OCR/provider adapter with its own evidence.

### 18.4 Overlay adapter tests

- 504HN exact strings preserved;
- A2 -> B1 job translation;
- identity/community/universe remain separate;
- no invented social handle;
- camera requirement added without deleting gameplay/chat constraints.

### 18.5 Skill contract tests

Each new `SKILL.md` must:

- use lowercase hyphenated name;
- description starts with `Use when`;
- include evidence contract;
- include safety contract;
- reference Control Plane and quality gates where relevant.

### 18.6 Regression

All existing tests must remain green.

Current isolated baseline before implementation:

- **95 tests passed**
- **0 failed**
- baseline commit: `e8bbb89255ac89376456b8a64929d61d9e10775e`

## 19. Subproject Decomposition

This program is intentionally split into independent slices.

### Slice A — Contract + Deterministic Auditor

Build:

- `kai_visual_job.py`
- `kai_image_auditor.py`
- tests
- one core skill: `kai-visual-production`

Delivers a useful standalone foundation.

### Slice B — Router + 5/5 Quality Gates

Build:

- `kai_visual_router.py`
- `kai_visual_manifest.py`
- route tests
- `kai-visual-tool-routing`
- `kai-visual-audit`

### Slice C — Overlay Master System Adapter

Build:

- `kai_overlay_adapter.py`
- `kai-overlay-production`
- CASE_001 translation tests
- A2 -> B1 job manifest

### Slice D — Reference Lock + Surgical Edit Contract

Build:

- base lock enforcement;
- hash mismatch detection;
- `kai-visual-reference-lock`;
- provider surgery adapter contract.

### Slice E — Control Plane Wrappers

Add thin commands and aliases after the underlying modules are stable.

### Slice F — Termux Edge Validation

Run the portable auditor and manifest tools on the S24 Termux environment, with fresh PING and evidence.

### Slice G — Provider Adapters

Only after core governance is stable:

- ImageGen route adapter;
- Adobe route adapter;
- optional Canva export/editable-template adapter.

No provider adapter may become a prerequisite for the deterministic core.

## 20. CASE_001 Acceptance Scenario

First end-to-end validation target:

`CASE_001_504HN_SOLOLAND`

Source:

- approved Model A2 visual base;
- Overlay Master System case metadata;
- exact identity and text;
- model sheet reference for the villager superhero.

Target:

- derive Model B1 with compact top camera + gameplay + chat;
- preserve approved identity and style;
- keep text exact;
- produce true-alpha final asset where required;
- create deterministic image audit;
- create manifest;
- create real-use preview;
- create TikTok UI occlusion preview when a current capture is available;
- require Asier's final aesthetic approval.

The previous bad B attempt is evidence of why the router must not permit unconstrained full regeneration after a base is approved.

## 21. Success Criteria

v0.1 succeeds when:

1. A visual job can be created and serialized deterministically.
2. An approved base can be hash-locked.
3. The router can explain its route without executing arbitrary providers.
4. A PNG can be audited deterministically on Windows.
5. The same auditor core is portable to Termux.
6. Exact text and identity constraints survive Overlay Master System translation.
7. Every artifact has hashes and provenance.
8. A failed audit blocks promotion.
9. Existing Control Plane tests remain green.
10. CASE_001 can be represented as a governed A2 -> B1 job.
11. New skills and tools remain `CANDIDATE` until test evidence exists.
12. No capability is called `PROMOTED` or `CANONICAL` without registry evidence and explicit approval.

## 22. Explicit Non-Goals for v0.1

- Building a full visual editor.
- Replacing Photoshop, Canva or ImageGen.
- Automatic autonomous publishing.
- Unbounded retries.
- Automatic promotion to canonical.
- Heavy local model rendering on Termux.
- Rewriting the entire Control Plane.
- Rebuilding existing Overlay Master System knowledge from scratch.
- Making provider-specific SDKs mandatory for the core.

## 23. Final Design Decision

KAI Visual Production Pipeline v0.1 is a **governed visual capability system**, not a prompt pack.

KAI Control Plane governs.  
The visual router decides.  
Domain systems such as Overlay Master System provide specialist knowledge.  
Creative tools create.  
Surgical tools modify.  
Python verifies.  
Termux audits at the edge.  
The PC performs heavy work.  
Drive and GitHub preserve evidence and source.  
The capability registry controls trust and promotion.  
Asier remains the final authority for aesthetic acceptance and canonical approval.

## 21. Dual 5/5 Protocol: Quality Gate + Repository Fusion

This pipeline now uses two complementary meanings of `5/5`.

### 21.1 Quality 5/5

Every critical stage must pass five evidence axes:

1. Fidelity.
2. Functionality.
3. Technical integrity.
4. Provenance.
5. Recoverability.

A stage advances only on `PASS_5_OF_5`.

### 21.2 Repository 5/5

When a demonstrated capability gap may benefit from external prior art, the system must research:

- 5 relevant GitHub repositories.
- 5 relevant Hugging Face repositories, models or Spaces.

The target is ten relevant sources, not ten filler results. If fewer than five credible candidates exist on either platform, the system records `UNDERCOVERED` with the search evidence and proceeds without inventing candidates.

### 21.3 Five-step fusion hierarchy

#### Step 1 — DEFINE THE GAP

Write the exact capability gap before searching.

Required fields:

- problem statement;
- desired input/output contract;
- execution nodes;
- resource constraints;
- licensing constraints;
- what existing Kai capabilities already cover;
- what must not be duplicated.

Output: `GAP_SPEC`.

#### Step 2 — HARVEST 5 + 5

Search and shortlist five GitHub and five Hugging Face candidates.

Every candidate records:

- repository ID;
- source platform;
- exact URL or stable repo identifier;
- current availability;
- license or `UNKNOWN`;
- primary capability;
- why it is relevant;
- whether code, model weights, documentation or architectural ideas are being considered.

Output: `REPO_5X5_INVENTORY`.

#### Step 3 — SCORE THE DNA

Each candidate is scored across five repository-fusion axes:

1. Relevance to the exact gap.
2. Maturity and evidence.
3. Portability across Kai nodes.
4. License and reuse safety.
5. Composability with existing Kai capabilities.

Allowed per-axis labels:

- `PASS`
- `FAIL`
- `UNVERIFIED`

No repository is fused merely because it is popular or new.

Output: `REPO_5X5_SCORECARD`.

#### Step 4 — UNIFY, DO NOT BLINDLY COPY

Extract reusable DNA only:

- architecture;
- interface ideas;
- algorithms;
- workflow patterns;
- test strategies;
- model choices;
- deployment patterns;
- failure handling;
- metadata/provenance contracts.

Code or weights are not copied automatically. Reuse must respect license, provenance, security, size, mutability and deployment cost.

The fusion result must state for every source:

- `ADOPT`
- `ADAPT`
- `REFERENCE_ONLY`
- `REJECT`
- `BLOCKED`

Output: `FUSION_BLUEPRINT`.

#### Step 5 — BUILD, TEST, PROMOTE

Build the smallest Kai-native capability that closes the gap.

Mandatory sequence:

1. source-first implementation in isolated worktree;
2. TDD or deterministic contract tests;
3. quality `PASS_5_OF_5`;
4. provenance and hashes;
5. capability-registry lifecycle;
6. deployment only after validation;
7. memory and rollback evidence.

Output: tested candidate capability and evidence bundle.

### 21.4 Fusion law

The complete protocol is therefore:

```text
QUALITY 5/5
Fidelity
Functionality
Technical integrity
Provenance
Recoverability
        +
REPOSITORY 5/5
5 GitHub
5 Hugging Face
        +
FUSION 5 STEPS
Define
Harvest
Score
Unify
Build/Test/Promote
```

This is one protocol, not three unrelated checklists.

### 21.5 Search and truth constraints

- Never pad the 5+5 with irrelevant repositories.
- Never claim a repository was inspected when only search metadata was available.
- Prefer official upstream repositories and model cards.
- Record the exact date and search scope.
- Mark gated, archived, unavailable or license-uncertain sources explicitly.
- Do not execute unknown external code during research.
- Do not copy secrets, tokens or credentials into evidence.
- Do not treat model popularity as proof of suitability.
- Do not treat a permissive code license as automatically covering model weights.
- Do not treat Hugging Face model availability as permission for unrestricted commercial use.

### 21.6 Candidate skill and tool additions

Add one focused skill:
`kai-visual-5x5-fusion`

Responsibilities:

- trigger repository 5/5 research for a demonstrated visual capability gap;
- require 5 GitHub + 5 Hugging Face candidates or explicit `UNDERCOVERED`;
- score relevance, maturity, portability, licensing and composability;
- produce an adoption map without blindly copying external code or weights;
- hand the approved fusion blueprint to the normal Kai capability-authoring lifecycle.

Add one focused tool:

`tools/kai_repo_5x5_fusion.py`

v0.1 responsibilities:

- ingest normalized repository/model records from connector snapshots;
- enforce maximum five selected GitHub and five selected Hugging Face candidates;
- preserve exact source IDs and provenance;
- calculate deterministic scorecards from explicit evidence fields;
- emit `REPO_5X5_INVENTORY`, `REPO_5X5_SCORECARD` and `FUSION_BLUEPRINT` JSON;
- never clone, execute or import external code in v0.1.

### 21.7 First visual-pipeline 5/5 pilot

The first repository-fusion pilot for this visual pipeline uses the following candidates.

GitHub:

1. `Comfy-Org/ComfyUI` — modular graph workflows, JSON workflow persistence, queueing, partial re-execution and API integration.
2. `danielgatis/rembg` — background removal via CLI/library/server/Docker, masks, alpha matting and batch/watch modes.
3. `PaddlePaddle/PaddleOCR` — multilingual OCR, structured output and coordinates for exact-text audit candidates.
4. `facebookresearch/sam2` — promptable segmentation with points, boxes, automatic masks and refinement.
5. `ImageMagick/ImageMagick` — deterministic command-line image identification, composition, conversion, transparency and perceptual hashing.

Hugging Face:

1. `briaai/RMBG-2.0` — background-removal model producing alpha mattes; gated and non-commercial by default, so it is not eligible for unrestricted automatic reuse.
2. `ZhengPeng7/BiRefNet` — high-resolution dichotomous segmentation and mask generation; MIT-licensed model repository.
3. `facebook/sam2.1-hiera-large` — mask generation and promptable segmentation model.
4. `Qwen/Qwen-Image-Edit-2511` — image editing with improved consistency and reduced drift.
5. `microsoft/trocr-base-printed` — OCR candidate for rendered-text verification experiments; single-line printed text focus and license must be verified before automatic reuse.

### 21.8 First unification blueprint

The ten sources do not become ten dependencies.

The Kai-native unified design adopts only the needed DNA:

```text
WORKFLOW ORCHESTRATION
<- ComfyUI patterns
   graph, queue, JSON workflow, partial re-execution

REFERENCE LOCK + MASKING
<- SAM2 / SAM2.1 patterns
   promptable masks, points, boxes, refinement

BACKGROUND / ALPHA SURGERY
<- rembg + BiRefNet patterns
   model adapters, mask output, alpha matting, batch mode

EXACT TEXT AUDIT
<- PaddleOCR + TrOCR candidates
   OCR as optional evidence, never sole aesthetic authority

CREATIVE SURGERY
<- Qwen-Image-Edit-2511
   consistency-aware image editing and drift mitigation

DETERMINISTIC FILE OPERATIONS
<- ImageMagick patterns
   identify, compose, convert, transparency, perceptual hash

GOVERNANCE
<- Kai Control Plane
   lifecycle, evidence, memory, location policy, capability registry
```

Initial adoption decisions:

- ComfyUI: `ADAPT`
- rembg: `ADAPT`
- PaddleOCR: `REFERENCE_ONLY` for v0.1, candidate adapter later
- SAM2: `REFERENCE_ONLY` for v0.1, candidate mask adapter later
- ImageMagick: `ADAPT`
- RMBG-2.0: `BLOCKED` for unrestricted reuse because of gating/non-commercial license constraints
- BiRefNet: `ADAPT`
- SAM2.1 Hiera Large: `REFERENCE_ONLY`
- Qwen-Image-Edit-2511: `ADAPT` through existing authorized image-edit routes
- TrOCR base printed: `REFERENCE_ONLY` until license and task fit are explicitly validated

No external repository is promoted as a Kai capability merely because it appears in this pilot.
