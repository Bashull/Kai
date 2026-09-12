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
- `kernel_policy.py` — SDPA baseline and canary-governed Liger routing, including capability-gated frozen-weight preference fast-path recognition.
- `weight_delta_policy.py` — governed rollout weight-transfer selection for full NCCL, sparse NCCL and vLLM 0.29 `sharded_rdt`.
- `smart_planner.py` — composes method/runtime/kernel/long-context planning and validates the generated profile through Compatibility Core.

## Smart Planner routing scope
- Explicit training method wins if valid; implicit signals select DPO from preference pairs, GRPO from reward signal, distillation from teacher availability, and otherwise default to SFT.
- Multiple implicit method signals are not guessed; they produce `NEEDS_CANARY` with `method_signal_ambiguity`.
- SFT/DPO prefer TRL when explicitly available and fall back to Transformers when TRL is unavailable.
- GRPO auto-selects vLLM only when vLLM is available, version >=0.28.0, and the runtime canary has passed; otherwise it stays on the in-process route.
- Distillation requires a teacher provider; async distillation requests vLLM but remains subject to existing Compatibility Core Transformers/FSDP2/vLLM gates.
- SDPA is the kernel baseline. Liger is never auto-promoted from version identity alone; auto-promotion requires availability plus a correctness canary.
- Explicit unverified Liger is preserved but returns `NEEDS_CANARY`; it is not silently rewritten to SDPA.
- Verified DPO + PEFT + frozen preference head can additionally surface `kernel.liger.preference_frozen_weight_fastpath`, but only when the Hardware Doctor/build probe supplies `liger_preference_frozen_weight_fastpath=True`; plain Liger availability never implies this capability.
- Existing long-context planning remains intact: chunked loss defaults, CP/SP selection, allocator guard, explicit override preservation and positional-extension non-invention.
- Context parallelism consumes the model-level `supports_context_parallel` capability when the Hardware Doctor/runtime supplies it; models explicitly declaring `False` are rejected and are not auto-selected for CP.
- `RegionRemat` is experimental-only: UltraTrain requires TorchTitan, `torch_remat`, explicit RNG handling, and a correctness canary before promotion. It is not an automatic default.
- Overall planner severity is monotonic: `UNSUPPORTED` > `NEEDS_CANARY` > `FALLBACK` > `SUPPORTED`.

## WeightDeltaPolicy scope
- `full_nccl` remains the safe default when advanced transport capabilities are unknown.
- `sharded_rdt` is only eligible for vLLM >=0.29.0 when the runtime proves that capability exists; automatic selection additionally requires TP or EP >1.
- `sharded_rdt` is not promoted without `vllm_sharded_rdt_weight_sync` correctness evidence.
- `sparse_nccl` is likewise capability- and canary-gated; release identity alone never activates it.
- Explicit requests for unavailable/too-old advanced transports are rejected rather than silently rewritten.

## 2026-09-08 upstream delta
- Transformers main commit `8eaf75f84e0ef68ccdaac14b739ace53a962bbee` adds `PreTrainedModel.supports_context_parallel`, explicitly rejecting configurations with sliding/chunked attention or recurrent sequence state that CP cannot preserve correctly.
- TorchTitan main commit `c6e416bbd76ded9b00a453105a96da06c07044cf` introduces model-aware region activation checkpointing through `torch_remat`, with semantic save regions and an FSDP2+TP2+CP2 numerical golden.
- Both are development-branch architectural capabilities, not stable-release floors. UltraTrain therefore records capability/canary gates rather than globally upgrading dependencies.

## 2026-09-09 upstream delta
- Liger-Kernel commit `77206f839d2c4c4f742b0d1ca391e3703bd9314a` changes fused preference losses so frozen `weight`/`bias` tensors are excluded from autodiff `argnums`; this removes unnecessary full-gradient buffers and chunk GEMMs for DPO/SimPO/CPO/ORPO/KTO.
- Upstream A100 bf16 benchmarks report 1.38x-1.53x speedups across tested preference workloads, including 1.44x for a long-context DPO case, while the commit notes roughly 1.25-2.5 GB of avoided weight-gradient allocation at 152K vocabulary scale.
- UltraTrain does not infer this fast-path from a version string or generic Liger presence. `kernel_policy.py` only emits the fast-path decision when the DPO request is resolved, PEFT is active, the preference head is explicitly frozen, generic Liger correctness has passed, and `liger_preference_frozen_weight_fastpath=True` is supplied by capability evidence.
- Ambiguous preference/reward/teacher method signals cannot claim the DPO fast-path.

## 2026-09-10 upstream delta
- TRL `v1.13.0` was published on 2026-09-10. It adds and documents a validated >1M-token training recipe, including Qwen3-8B at 1,048,576 tokens on 8xH100, and requires `transformers>=5.16` for activation-checkpoint offload.
- TRL `v1.13.0` moves the default `chunked_nll` lm-head projection onto bf16 tensor-core GEMMs. Upstream reports 6.0x for the isolated chunk kernel and 1.20x-1.69x end-to-end improvements across tested full-FT/LoRA/MoE workloads. UltraTrain surfaces this only as `long_context.loss.trl_113_tensorcore_fastpath`; it does not convert upstream benchmark numbers into a local performance guarantee.
- TRL vendors fused linear preference/distillation losses into `trl.losses`, while `use_liger_kernel=True` still requires `liger-kernel` for model-kernel patching. UltraTrain therefore keeps Liger as a separate kernel capability rather than treating TRL 1.13 as a replacement for Liger.
- TRL 1.13 raises dependency floors to `peft>=0.13.0` and `deepspeed>=0.18.6`. UltraTrain now blocks explicitly incompatible PEFT or DeepSpeed compositions and asks for identity evidence when versions are unknown.
- TRL 1.13 supports vLLM 0.28.0 and drops vLLM 0.19.0 support; UltraTrain already had a stricter vLLM security floor of 0.28.0, so no floor relaxation was needed.
- PPO is removed from TRL 1.13. UltraTrain's Method Selector never selected PPO, so no production routing path was removed.

## 2026-09-12 upstream delta
- vLLM `v0.29.0` was released on 2026-09-09. Its RL weight-sync path adds `sharded_rdt`, where each worker pulls only its TP/EP slice over NIXL or Ray Direct Transport; the same release adds rank-local IPC updates and sparse checkpoint-coordinate updates through native weight loaders.
- vLLM 0.29 also makes Model Runner V2 the default, enables FlashInfer all-reduce by default for TP CUDA groups, and deprecates Model Runner V1 for removal around v0.32. UltraTrain records those as runtime capability/deprecation evidence but does not force a global runner switch from version identity alone.
- The vLLM release additionally includes stateful trainer send over NCCL/sparse NCCL, tag-selective `CuMemAllocator.discard()`, and a LoRA level-2 sleep/wake/reload fix. These directly strengthen the future `RolloutLifecycle` and `WeightDeltaPlane` design.
- UltraTrain now has a physical `weight_delta_policy.py`: `full_nccl` is the rollback baseline; `sparse_nccl` and `sharded_rdt` need explicit capability evidence and transport-specific canaries before promotion.
- Axolotl `v0.19.0` was released on 2026-09-10 with declarative model-support profiles: a model selects a family template and declares only its deltas instead of scattering loader-specific conditionals. UltraTrain adopts this as Capability DNA for Hardware Doctor / Recipe Compiler: model family baseline + declarative capability deltas + preflight, rather than accumulating architecture-name if/else branches.
- Axolotl 0.19 also makes `flash_attention_4` and `flash_attention_torch` canonical attention backend values and preflights the torch backend against installed Transformers support. UltraTrain will treat attention backends as declared/probed capabilities, not infer them from package presence.
- Axolotl remains a donor/adapter candidate, not a newly mandated global dependency.

## Verification state
- 2026-09-06 TDD RED confirmed independently for `method_selector`, `runtime_policy`/`kernel_policy`, and composite `plan_training` before production code existed.
- Isolated-workspace discovery: 38/38 PASS across 7 method-selector tests, 6 runtime tests, 4 kernel tests, 7 composite planner tests, 7 inherited long-context policy tests, and 7 inherited long-context Smart Planner tests.
- 2026-09-08 focused isolated verification: 5/5 PASS for explicit CP model-capability rejection / legacy-unknown behavior and RegionRemat canary, RNG, and promotion rules; `py_compile` passed for the two affected policy modules.
- 2026-09-09 Liger fast-path TDD: RED reproduced against the previous `kernel_policy.py`; GREEN with 4/4 focused tests covering explicit DPO, unambiguous implicit DPO, ambiguous-signal rejection, and missing-capability non-claim; `py_compile` passed.
- 2026-09-10 TRL 1.13 contract tests were added before the policy writes, covering Transformers 5.16 activation-offload gating, TRL 1.13 DeepSpeed/PEFT floors, and the chunked-loss tensor-core capability hint.
- The 2026-09-10 contract suite remains `TEST_PENDING_RUNTIME`: the automation shell could not resolve `github.com`, and CircleCI reported `error` without accessible logs.
- 2026-09-12 WeightDeltaPolicy TDD: RED reproduced as missing `projects.ultratrain.weight_delta_policy`; GREEN with 5/5 focused tests covering verified sharded RDT promotion, canary gating, pre-0.29 rejection, sparse NCCL capability gating and full-NCCL fallback; `py_compile` passed.
- Direct clone/full-suite verification remains separate from focused isolated evidence; focused updates are `VERIFIED_SCOPE`, not `FULL_INVENTORY`.
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
- Liger frozen-weight DPO/PEFT fast-path capability hint
- TRL 1.13 activation-offload / dependency-floor / chunked-loss capability gates
- WeightDeltaPolicy for full NCCL / sparse NCCL / vLLM 0.29 sharded RDT
- Composite Training Smart Planner

## Adopted donor Capability DNA
- Axolotl 0.19 declarative model-support profiles: family baseline + model delta + explicit preflight.
- Axolotl 0.19 explicit attention-backend registry/preflight pattern for `flash_attention_4` and `flash_attention_torch`.
- These patterns inform Hardware Doctor and Recipe Compiler contracts; they do not make Axolotl the source of truth for model capability.

## Planned next slices
- Hardware Doctor -> planner capability input contract, including automatic `supports_context_parallel` discovery, TRL/Transformers/DeepSpeed/PEFT exact-version identity, probing whether the installed Liger build contains the frozen-weight preference fast-path, attention-backend capability discovery, and declarative model-family capability profiles.
- Recipe Compiler from immutable `TrainingSmartPlan`, including mapping abstract `chunked` loss to TRL `chunked_nll` when the selected TRL capability supports it, `RegionRemat.save_regions`, RNG hook materialization, preference-loss fast-path selection, and attention-backend materialization.
- Method-specific recipe adapters for SFT/DPO/GRPO/distillation.
- RolloutLifecycle adapter consuming WeightDeltaPolicy, including vLLM 0.29 sleep/discard/stateful-send capabilities.
- TeacherProvider operational adapter.
- FaultToleranceProvider.
- WeightDeltaPlane integration of sharded RDT / sparse NCCL with versioned model-weight identity.
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
