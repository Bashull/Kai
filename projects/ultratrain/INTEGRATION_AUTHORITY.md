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
- `long_context_policy.py` — CP/SP, long-context memory, model-capability and version gates.
- `activation_checkpoint_policy.py` — full/selective AC plus canary-governed TorchTitan `RegionRemat` capability.
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
- Context parallelism now consumes the model-level `supports_context_parallel` capability when the Hardware Doctor/runtime supplies it; models explicitly declaring `False` are rejected and are not auto-selected for CP.
- `RegionRemat` is experimental-only: UltraTrain requires TorchTitan, `torch_remat`, explicit RNG handling, and a correctness canary before promotion. It is not an automatic default.
- Overall planner severity is monotonic: `UNSUPPORTED` > `NEEDS_CANARY` > `FALLBACK` > `SUPPORTED`.

## 2026-09-08 upstream delta
- Transformers main commit `8eaf75f84e0ef68ccdaac14b739ace53a962bbee` adds `PreTrainedModel.supports_context_parallel`, explicitly rejecting configurations with sliding/chunked attention or recurrent sequence state that CP cannot preserve correctly.
- TorchTitan main commit `c6e416bbd76ded9b00a453105a96da06c07044cf` introduces model-aware region activation checkpointing through `torch_remat`, with semantic save regions and an FSDP2+TP2+CP2 numerical golden.
- Both are development-branch architectural capabilities, not stable-release floors. UltraTrain therefore records capability/canary gates rather than globally upgrading dependencies.

## Verification state
- 2026-09-06 TDD RED confirmed independently for `method_selector`, `runtime_policy`/`kernel_policy`, and composite `plan_training` before production code existed.
- Isolated-workspace discovery: 38/38 PASS across 7 method-selector tests, 6 runtime tests, 4 kernel tests, 7 composite planner tests, 7 inherited long-context policy tests, and 7 inherited long-context Smart Planner tests.
- 2026-09-08 focused isolated verification: 5/5 PASS for explicit CP model-capability rejection / legacy-unknown behavior and RegionRemat canary, RNG, and promotion rules; `py_compile` passed for the two affected policy modules.
- Direct clone/full-suite verification was blocked because the local container could not resolve `github.com`; this update is `VERIFIED_SCOPE`, not `FULL_INVENTORY`.
- CircleCI status remains separate evidence; do not infer a code regression without logs.

## Implemented capability families
- Reconstructed Compatibility Core
- TrackingSecurityPolicy and upstream security floors
- Scientific Evidence Plane
- Artifact integrity / model-version / promotion alias contracts
- Governed ArtifactResolver / TransportPolicy
- Evaluation identity
- LongContextPolicy
- Model-declared Context Parallel capability gate
- RegionRemat Activation Checkpoint Policy (experimental/canary)
- Smart Planner long-context selection
- Training Method Selector
- Runtime Provider routing
- Kernel Policy routing
- Composite Training Smart Planner

## Planned next slices
- Hardware Doctor -> planner capability input contract, including automatic `supports_context_parallel` discovery.
- Recipe Compiler from immutable `TrainingSmartPlan`, including `RegionRemat.save_regions` and RNG hook materialization.
- Method-specific recipe adapters for SFT/DPO/GRPO/distillation.
- RolloutLifecycle and TeacherProvider operational adapters.
- FaultToleranceProvider.
- WeightDeltaPlane integration.
- Stateful cache capability integration.
- Collective backend capability integration.

## Promotion rules
1. Recover or reconstruct source with explicit provenance.
2. Run inherited contract tests and all new tests before promotion.
3. Add real adapter canaries incrementally.
4. Require numerical/correctness checks before performance promotion.
5. Preserve rollback baseline.
6. Never infer capability from version string alone.
7. No global dependency upgrade solely because an upstream release exists.
8. Planner output is a proposal until the relevant Compatibility/Canary gates pass.
