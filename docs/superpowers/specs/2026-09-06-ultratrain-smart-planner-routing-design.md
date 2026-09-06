# UltraTrain Smart Planner Routing Design

## Status
CANDIDATE · GOVERNED_BRANCH · NOT_CANONICAL

## Goal
Extend the existing long-context Smart Planner into a provider-neutral planning layer that selects a training method, a runtime route, and a kernel route, then validates the composed profile through the existing Compatibility Core.

## Scope
Planning only. This change does not launch training, install dependencies, mutate environments, or promote any runtime/kernel solely from a version string.

## Method selection
Supported methods: `sft`, `dpo`, `grpo`, `distillation`.

Explicit `method` always wins if valid. Without an explicit method, signals are intentionally conservative: `preference_pairs=True` proposes DPO, `reward_signal=True` proposes GRPO, `teacher_available=True` proposes distillation, and no signal defaults to SFT. More than one positive method signal is ambiguous and must not be guessed.

## Runtime routing
The runtime layer returns a training engine plus optional rollout and teacher providers. SFT/DPO use TRL when available and fall back to Transformers. GRPO uses TRL and may use vLLM only when the vLLM capability is explicitly available, at the UltraTrain security floor, and its runtime canary is already satisfied; otherwise it stays in-process. Distillation uses TRL and requires a teacher provider. Async distillation may request vLLM, but the existing Compatibility Core remains authoritative for Transformers/FSDP2/vLLM cross-stack gates.

## Kernel routing
`sdpa` is the safe baseline. Liger is never auto-promoted from version identity alone. It may be selected only when fused kernels are requested, Liger is available, and a correctness canary has passed. An explicit unverified Liger request remains gated instead of silently falling back.

## Composition
`plan_training()` composes method, runtime, kernel, and optional long-context planning into one immutable result. The generated compatibility profile is passed to `evaluate_profile()`; policy modules do not duplicate Compatibility Core rules. Overall severity is monotonic: `UNSUPPORTED` > `NEEDS_CANARY` > `FALLBACK` > `SUPPORTED`.

## Evidence and governance
Every automatic decision is recorded as a decision string. Explicit user choices are preserved. `main` remains untouched; all work lands on `feature/ultratrain-compatibility-core`. TDD is mandatory and full-branch verification is required when the complete branch is available in a runnable workspace.