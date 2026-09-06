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
- `smart_planner.py` — first physical Smart Planner slice; currently long-context planning only.

## Smart Planner v0.1 scope
- Defaults to chunked loss for targets >=131072 tokens when the user did not explicitly choose a loss.
- For >=1M tokens, prefers CP when the FSDP2/Accelerate/causal-SDPA stack is demonstrably available.
- Falls back to SP only when the DeepSpeed/Accelerate stack is valid and requested parallelism does not exceed KV-head capacity.
- Adds the expandable CUDA allocator guard for >=1M-token plans unless explicitly overridden.
- Preserves explicit user parallelism and validates it through `long_context_policy` rather than silently rewriting it.
- Never invents a positional-extension strategy.
- Never silently opts into unreleased Transformers activation-offload behavior.

## Verification state
- 2026-09-06 isolated-workspace TDD: RED confirmed because `smart_planner` did not exist; GREEN with 7 Smart Planner tests + 7 inherited long-context policy tests = 14/14 PASS.
- `py_compile` passed for `smart_planner.py` and `long_context_policy.py` in the isolated workspace.
- The remote GitHub branch contains the verified Smart Planner bytes.
- Full branch-suite verification remains pending until a connected project runtime is available; do not upgrade this branch to CANONICAL from the isolated verification alone.

## Implemented capability families
- Reconstructed Compatibility Core
- TrackingSecurityPolicy and upstream security floors
- Scientific Evidence Plane
- Artifact integrity / model-version / promotion alias contracts
- Governed ArtifactResolver / TransportPolicy
- Evaluation identity
- LongContextPolicy
- Smart Planner long-context selection slice

## Planned adapters / next slices
- KernelPolicy
- RuntimeCompatibilityProfile
- RolloutLifecycle
- TeacherProvider / Distillation
- FaultToleranceProvider
- WeightDeltaPlane integration
- Stateful cache capability integration
- Collective backend capability integration
- Smart Planner expansion to method/runtime/kernel selection

## Promotion rules
1. Recover or reconstruct source with explicit provenance.
2. Run inherited contract tests and all new tests before promotion.
3. Add real adapter canaries incrementally.
4. Require numerical/correctness checks before performance promotion.
5. Preserve rollback baseline.
6. Never infer capability from version string alone.
7. No global dependency upgrade solely because an upstream release exists.
8. Planner output is a proposal until the relevant Compatibility/Canary gates pass.
