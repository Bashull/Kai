# KAI Visual Production Pipeline · 5/5 Repository Fusion Pilot v01

**Date:** 2026-07-12  
**Branch:** `feat/kai-visual-production-pipeline-v0.1`  
**Purpose:** First repository 5/5 research pilot for the approved KAI Visual Production Pipeline v0.1.  
**Protocol:** 5 GitHub repositories + 5 Hugging Face repositories, scored and unified without blind copying.

## 1. Capability gap

The visual pipeline needs a governed route that can:

- preserve an approved visual base;
- make structural or surgical edits;
- isolate objects or regions;
- remove backgrounds and produce real alpha;
- audit exact text when possible;
- verify dimensions, hashes, format and transparency deterministically;
- keep provenance and rollback;
- operate across ChatGPT, Windows PC and later S24 + Termux.

Existing Kai governance already covers memory, capability lifecycle, location policy, evidence and promotion. This pilot must not duplicate those functions.

## 2. GitHub 5

### G1 · Comfy-Org/ComfyUI

Role considered: workflow orchestration DNA.

Useful patterns:

- modular node graph;
- API integration;
- queue;
- partial re-execution of changed workflow sections;
- save/load workflows as JSON;
- offline operation.

Decision: `ADAPT`.

Kai does not copy ComfyUI as the Control Plane. We borrow graph/queue/workflow ideas for future visual job execution and local PC pipelines.

### G2 · danielgatis/rembg

Role considered: background removal and alpha surgery.

Useful patterns:

- CLI, Python library, HTTP server and Docker entrypoints;
- single-file and folder processing;
- watch mode;
- output mask mode;
- alpha matting;
- custom-model route;
- session reuse for batch performance.

Decision: `ADAPT`.

Potential future adapter behind an allowlisted interface. No untrusted model execution during research.

### G3 · PaddlePaddle/PaddleOCR

Role considered: exact-text audit candidate.

Useful patterns:

- multilingual OCR;
- structured JSON/Markdown output;
- coordinate-aware extraction;
- CPU/GPU deployment options.

Decision: `REFERENCE_ONLY` in v0.1.

OCR is not core certification yet. Rendered text correctness remains human-reviewed unless an explicit OCR adapter is implemented and validated.

### G4 · facebookresearch/sam2

Role considered: reference locking and region masks.

Useful patterns:

- promptable segmentation;
- points;
- boxes;
- automatic masks;
- mask refinement;
- image and video paths.

Decision: `REFERENCE_ONLY` in v0.1, candidate adapter later.

The immediate Kai reference lock is metadata/hash based; segmentation may later generate protected/editable masks.

### G5 · ImageMagick/ImageMagick

Role considered: deterministic file operations.

Useful patterns:

- command-line scripting;
- image identification;
- composition;
- conversion;
- transparency handling;
- perceptual hashes;
- automation.

Decision: `ADAPT`.

Use only through explicit allowlisted commands and security policy.

## 3. Hugging Face 5

### H1 · briaai/RMBG-2.0

Role considered: alpha-matte background removal.

Strength: produces a grayscale alpha matte suitable for compositing.

Constraint: gated and non-commercial by default.

Decision: `BLOCKED` for unrestricted automatic reuse. Keep as research reference unless license/use is explicitly compatible.

### H2 · ZhengPeng7/BiRefNet

Role considered: high-resolution dichotomous segmentation.

Strengths:

- mask generation;
- background removal;
- high-resolution segmentation;
- MIT license in the model repository.

Decision: `ADAPT`.

Potential local model adapter after resource and dependency tests.

### H3 · facebook/sam2.1-hiera-large

Role considered: mask generation and promptable segmentation.

Strengths:

- point/box prompting;
- multi-object masks;
- refinement;
- Transformers integration.

Decision: `REFERENCE_ONLY` for v0.1.

### H4 · Qwen/Qwen-Image-Edit-2511

Role considered: creative surgery.

Strengths:

- image-to-image editing;
- improved consistency;
- reduced drift;
- geometric reasoning;
- multi-reference editing.

Decision: `ADAPT` through an authorized image-edit execution route.

The model is creative, not deterministic proof.

### H5 · microsoft/trocr-base-printed

Role considered: rendered-text OCR experiment.

Strength:

- printed single-line OCR.

Constraints:

- task scope is narrow;
- license must be explicitly verified before automatic reuse.

Decision: `REFERENCE_ONLY`.

## 4. Unified DNA

```text
Kai Control Plane
    governs state, evidence, promotion, memory and placement

Visual Production Router
    decides operation class and execution route

Graph/queue DNA
    <- ComfyUI

Mask/reference-lock DNA
    <- SAM2 / SAM2.1

Alpha/background DNA
    <- rembg / BiRefNet / RMBG research

Creative edit DNA
    <- Qwen Image Edit 2511

Text audit DNA
    <- PaddleOCR / TrOCR

Deterministic file DNA
    <- ImageMagick + Python/Pillow

Termux edge
    runs lightweight audit, hash and manifest steps

Windows PC
    runs heavier local models and batch processing
```

## 5. Protocol result

This pilot validates a new dual 5/5 system:

- Quality 5/5: fidelity, functionality, technical integrity, provenance, recoverability.
- Repository 5/5: five GitHub + five Hugging Face candidates.
- Fusion hierarchy: define, harvest, score, unify, build/test/promote.

No repository is automatically copied, executed, promoted or made canonical.

The first Kai-native additions proposed from this pilot are:

- skill `kai-visual-5x5-fusion`;
- tool `tools/kai_repo_5x5_fusion.py`;
- repository inventory and scorecard schemas;
- license/provenance gate before any code/model integration.