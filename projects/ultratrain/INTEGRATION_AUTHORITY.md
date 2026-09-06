# UltraTrain Integration Authority

Status: CANDIDATE · GOVERNED_BRANCH · NOT_CANONICAL

## Purpose
This branch is the governed code landing zone for the UltraTrain Compatibility Core, evidence/transport plane, Smart Planner and subsequent capability adapters.

## Authority
- Documentary authority: Google Drive KAI CURRENT/checkpoints.
- Code candidate authority: `Bashull/Kai` branch `feature/ultratrain-compatibility-core`.
- `main` remains untouched until tests, canaries and review pass.

## Genealogy
The documented Compatibility Core v0.1.0 defined a dependency-free capability graph and preflight validator with states `SUPPORTED`, `FALLBACK`, `NEEDS_CANARY`, `UNSUPPORTED`. The exact historical candidate bytes were not recovered in the bounded search, so the executable core was reconstructed from the documented contract with tests first and explicit provenance.

## Physical candidate modules
- `compatibility_core.py` — cross-stack capability/preflight guards.
- `scientific_evidence.py` — run/artifact/evaluation identity, integrity and promotion refs.
- `artifact_transport.py` — governed transport, retry classification and post-transport integrity verification.
- `long_context_policy.py` — CP/SP, long-context memory and version gates.
- `method_selector.py` — conservative SFT/DPO/GRPO/distillation method selection.
- `runtime_policy.py` — training engine, rollout and teacher-provider routing.
- `kernel_policy.py` — SDPA baseline and canary-governed Liger routing.
- `smart_planner.py` — composes method/runtime/kernel/long-context planning and validates the generated profile through Compatibility Core.

## Smart Planner routing scope
- Explicit training method wins if valid; implicit signals select DPO from preference pairs, GRPO from reward signal, distillation from teacher availability, and otherwise default to SFT.
- Multiple implicit method signals are not guessed; they produce `NEEDS_CANARY` with `method_signal_ambiguity`.
- SFT/DPO prefer TRL when explicitly available and fall back to Transformers when TRL is unavailable.
- GRPO auto-selects vLLM only when vLLM is available, version >=0.28.0, and the runtime canary has passed; otherwise it stays on the in-process route.
- Distillation requires a teacher provider; async distillation requests vLLM but remains subject to existing Compatibility Core Transformers/FSDP2/vLLM gates.
- SDPA is the kernel baseline. Liger is never auto-promoted from version identity alone; auto-promotion requires availability plus a correctness canary.
- Explicit unverified Liger is preserved but returns `NEEDS_CANARY`; it is not silently rewritten to SDPA.
- Existing long-context planning remains intact: chunked loss defaults, CP/SP selection, allocator guard, explicit override preservation and positional-extension non-invention.
- Overall planner severity is monotonic: `UNSUPPORTED` > `NEEDS_CANARY` > `FALLBACK` > `SUPPORTED`.

## Verification state
- 2026-09-06 TDD RED confirmed independently for `method_selector`, `runtime_policy`/`kernel_policy`, and composite `plan_training` before production code existed.
- Isolated-workspace discovery: 38/38 PASS across 7 method-selector tests, 6 runtime tests, 4 kernel tests, 7 composite planner tests, 7 inherited long-context policy tests, and 7 inherited long-context Smart Planner tests.
- `py_compile` passed for `method_selector.py`, `runtime_policy.py`, `kernel_policy.py`, `smart_planner.py`, `long_context_policy.py`, and the reconstructed local copy of `compatibility_core.py` used for composition tests.
- Remote GitHub bytes for the composite Smart Planner were re-fetched after commit.
- CircleCI reports `error` for the latest commit, but the CircleCI detail is not accessible from the current environment; do not classify that status as a verified code regression without logs.
- The complete historical branch snapshot was not materialized in this isolated workspace, so 38/38 is `VERIFIED_SCOPE`, not `FULL_INVENTORY` or full-branch-suite verification.

## Implemented capability families
- Reconstructed Compatibility Core
- TrackingSecurityPolicy and upstream security floors
- Scientific Evidence Plane
- Artifact integrity / model-version / promotion alias contracts
- Governed ArtifactResolver / TransportPolicy
- Evaluation identity
- LongContextPolicy
- Smart Planner long-context selection
- Training Method Selector
- Runtime Provider routing
- Kernel Policy routing
- Composite Training Smart Planner

## Planned next slices
- Hardware Doctor -> planner capability input contract
- Recipe Compiler from immutable `TrainingSmartPlan`
- Method-specific recipe adapters for SFT/DPO/GRPO/distillation
- RolloutLifecycle and TeacherProvider operational adapters
- FaultToleranceProvider
- WeightDeltaPlane integration
- Stateful cache capability integration
- Collective backend capability integration

## Promotion rules
1. Recover or reconstruct source with explicit provenance.
2. Run inherited contract tests and all new tests before promotion.
3. Add real adapter canaries incrementally.
4. Require numerical/correctness checks before performance promotion.
5. Preserve rollback baseline.
6. Never infer capability from version string alone.
7. No global dependency upgrade solely because an upstream release exists.
8. Planner output is a proposal until the relevant Compatibility/Canary gates pass.
