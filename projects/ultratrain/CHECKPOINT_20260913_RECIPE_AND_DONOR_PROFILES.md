# UltraTrain Checkpoint · Capability entrypoint, Recipe Compiler and donor profiles

Date: 2026-09-13

Status: CANDIDATE · FOCUSED_TESTED · BRANCH_CI_UNRESOLVED · NOT_CANONICAL

Branch: `feature/ultratrain-hardware-doctor-contract`

## Added after the Hardware Doctor checkpoint

### Planner capability adapter
`planner_capability_adapter.py` maps `PlannerCapabilityInput` into a copy of the existing request contract. Measured factual conflicts raise `CapabilityInputConflict`; explicit user preferences are preserved. Package presence never promotes capabilities. Attention/Liger auto-hints require PROBED/CANARY evidence.

### Capability-aware planner entrypoint
`planner_entrypoint.py` exposes `plan_training_with_capabilities()`. It adapts evidence and delegates to the existing Smart Planner without changing `smart_planner.py`, keeping the legacy call path byte-for-byte intact while branch CI is unresolved.

### Recipe Compiler
`recipe_compiler.py` converts an approved plan into `ultratrain.compiled_recipe/v1`.
- `NEEDS_CANARY` / `UNSUPPORTED` never become executable.
- TRL `chunked_nll` is materialized only when the plan carries `long_context.loss.trl_113_tensorcore_fastpath` and the selected engine is TRL.
- Liger and the frozen-weight preference fast-path are materialized only from Planner decisions.
- RegionRemat is rechecked through `activation_checkpoint_policy`; unverified RegionRemat yields a blocked recipe.
- Attention backend and isolated runtime provenance are preserved.

### Typed donor profiles
`donor_profiles.py` turns the inspected ZIP facts into explicit non-promoted descriptors.
- Unsloth Studio 2026.9.4: process-isolated descriptor with exact donor identities `trl==0.23.1`, `transformers==5.5.0`; conflicts with canonical TRL >=1.13 and Transformers >=5.16 are recorded.
- Donor code presence for Qwen3.8/GGUF/MLX/stable-diffusion.cpp is `DECLARED`, never `PROBED`.
- Qwen3.8-27B MLX model profile records qwen3_5 architecture, 262144 context, 64 layers, 24 attention heads, 4 KV heads, text/image/video, tool calls, thinking and modified refusal behavior; it does not claim `safe_autonomous_tools`.
- Observed LFS payload sums are represented as memory estimates: 2-bit 9,351,192,422 B; 4-bit 16,074,530,924 B; 6-bit 22,797,869,090 B; 8-bit 29,521,207,586 B. KV cache/runtime/vision activation memory remain explicitly excluded.

## Focused verification

TDD in an isolated local reconstruction progressed through expected RED missing-module stages and now reports 40/40 focused tests PASS plus `py_compile` PASS for all 2026-09-13 modules/tests.

This is VERIFIED_SCOPE only. It is not a full branch-suite claim.

## Relevant lineage

- `cca97d66cb0c62d110a5b73200f237ba20fca31c` — adapter tests.
- `c50ac30d2ef54f643123e7d156e594d21d972948` — planner capability adapter.
- `2d2e55282cc87130dca7817508e5951d5826bac0` — capability entrypoint tests.
- `d1ae2c4bd08abf73c8fbc0f132a956acc97a12f2` — capability-aware planner entrypoint.
- `b0ad4f6c5ef59a351694a3016efcfaa7d368beff` — Recipe Compiler tests.
- `373cdc95d121ba106d6503f70cb332b88c825101` — Recipe Compiler.
- `24508cd33a648195cc9b03e9cc115c633b011ee1` — donor profile tests.
- `e704e4fdcf8061437190dd9b72a45e2ed6fade56` — typed donor profiles.

## CI state

CircleCI for head `e704e4f` reports `error` (pipeline 609). No accessible CircleCI job log has established a code regression. Promotion remains forbidden until full branch tests run in a connected runtime and the CI error is classified.

## Next exact action

Add method-specific recipe adapters beginning with SFT and DPO, then GRPO/distillation. Keep engine-specific configuration downstream of `CompiledRecipe`, preserve rollback defaults, and do not activate isolated Unsloth execution until a provider canary proves the runtime boundary and round-trip artifacts.
