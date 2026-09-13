# UltraTrain Checkpoint · Unsloth donor + Hardware Doctor contract

Date: 2026-09-13

Status: CANDIDATE · FOCUSED_TESTED · BRANCH_CI_UNRESOLVED · NOT_CANONICAL

Branch: `feature/ultratrain-hardware-doctor-contract`
Base: `feature/ultratrain-compatibility-core`

## Donor decision

Unsloth snapshot `2026.9.4` is accepted as Capability DNA and as a candidate isolated runtime provider. It is not a replacement for UltraTrain's Compatibility Core, Smart Planner, Hardware Doctor, Recipe Compiler, Ray/MLflow planes, or current TRL/Transformers policy.

The observed dependency envelopes conflict with the canonical UltraTrain line: the donor snapshot constrains TRL to the 0.23/0.24 generation and Transformers through 5.5, while current UltraTrain policy tracks TRL 1.13 and requires Transformers >=5.16 for activation-checkpoint offload. Therefore a donor runtime with those identities must cross a process/container/remote isolation boundary; it cannot share the canonical Python environment.

License boundary is also explicit: core Unsloth code is Apache-2.0 while Studio/CLI surfaces are AGPL-3.0. This branch contains clean UltraTrain code only; no Studio/CLI implementation was copied.

## Qwen3.8 donor decision

The inspected Qwen3.8-27B MLX archive is metadata/reference material in this ingestion because its large model files are Git LFS pointers rather than embedded weights. Its family/capability facts may populate a `ModelCapabilityProfile`, but modified refusal behavior never implies permission for autonomous shell/tool execution. Tool safety remains an external policy/canary concern.

## New physical modules

- `hardware_doctor_contract.py` — dependency-free contracts for exact package identity, explicit capability evidence, GPU/RAM snapshots, memory estimates, declarative model family baseline+deltas, runtime isolation, and stable planner-input serialization.
- `hardware_doctor.py` — dependency-free environment probe for Python distribution identities, RAM/platform/CPU and optional NVIDIA discovery through `nvidia-smi`.

## Invariants introduced

1. Package presence or version identity never implies capability support.
2. PROBED/CANARY capability states require evidence references.
3. A runtime with declared dependency conflicts cannot use `shared` isolation.
4. GPU memory is represented per device rather than as a single implicit total.
5. Memory estimates record measured-vs-estimated basis, confidence and assumptions.
6. Model support is family baseline plus explicit deltas; architecture-name conditionals are not the contract.
7. Planner capability input has deterministic JSON serialization.

## TDD evidence

- Contract RED: missing `projects.ultratrain.hardware_doctor_contract`.
- Contract GREEN: 8/8 focused tests; `py_compile` PASS in isolated local reconstruction.
- Probe RED: missing `projects.ultratrain.hardware_doctor`.
- Combined GREEN: 13/13 focused tests; `py_compile` PASS for contract, probe and both new test modules.

This is VERIFIED_SCOPE for the isolated reconstructed slice only. It is not a full branch-suite claim.

## Git lineage

- `12115d68a53462af9504e988d1b16d87ca0c238e` — contract tests.
- `0f44d59b5b82d249839be5f23cebdafd12e4c1ae` — contract implementation.
- `c38b3129976a20f978c76121a7d34f982deaf5c6` — probe tests.
- `2a642dee5c0db9d50788f33cbcde9f049d663b70` — structured GPU evidence.
- `2fedfd3c880cb16b533b952da34a11e5b721933e` — dependency-free hardware/package probe.

## External CI

GitHub combined status for the implementation head reports `CircleCI Pipeline = error`. No accessible job log has yet established whether this is a code regression, infrastructure/configuration failure, or the pre-existing branch CI condition. Promotion is therefore forbidden until the branch suite is executed in a connected runtime and the CircleCI error is explained.

## Next exact action

Wire `PlannerCapabilityInput` into Smart Planner through an explicit adapter, without changing current request-dict callers. The adapter must map only evidence-backed fields (package versions, GPU availability, context-parallel capability, attention backend, Liger capability/canary) and preserve unknowns rather than inventing support. After that, build the Recipe Compiler mapping from immutable `TrainingSmartPlan`.
