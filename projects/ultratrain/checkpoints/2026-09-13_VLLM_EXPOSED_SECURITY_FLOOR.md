# 2026-09-13 UltraTrain vLLM exposed-server security floor

Status: VERIFIED_SCOPE · CANDIDATE · NOT_CANONICAL

## Upstream evidence
vLLM 0.29.0 (released 2026-09-09) includes a security-hardening batch relevant to network-exposed serving: removal of diskcache pickle deserialization, a fix for a concurrent sparse-invariant validation race, resource bounds for derender endpoints, sanitized server paths in validation errors, bounded completion prompt fan-out, and regex-compilation timeouts. Model Runner V1 is also deprecated with removal targeted around v0.32, while V2 is the default.

## UltraTrain design decision
Do not globally raise the vLLM floor from 0.28 to 0.29. Preserve vLLM >=0.28 for isolated/local rollout use when its runtime canary passes. Raise the floor to vLLM >=0.29 only when `runtime.network_exposure` is `lan`/`public` or `runtime.vllm_tool_server=True`.

New rule: `runtime.vllm.exposed_security_floor_029`.

This keeps the architecture capability/threat-model driven rather than performing a global dependency upgrade solely because a release exists.

## TDD / verification
RED against previous Compatibility Core:
- 5 focused tests run.
- local isolated 0.28 and exposed 0.29 already behaved as desired.
- LAN 0.28, public 0.28 and local tool-server 0.28 incorrectly returned SUPPORTED: 3 failures.

GREEN after policy change:
- focused suite: 5/5 PASS.
- `py_compile` for `compatibility_core.py`: PASS.
- full UltraTrain discovery after patch: 141/144 PASS.
- baseline with the patch reverted: 138/144 PASS.
- therefore this delta fixes exactly the three new security-floor contracts and introduces no additional suite failures.

## Pre-existing failures kept separate
Three inherited long-context tests remain red because their expected activation-offload/allocator canary names predate the TRL 1.13 / Transformers 5.16 policy update:
- `test_activation_offload_is_not_release_capability_yet`
- `test_million_token_profile_requires_allocator_guard`
- `test_planner_does_not_silently_enable_unreleased_activation_offload`

These are existing contract-reconciliation debt, not regressions from the vLLM security-floor change.

## Genealogy
- Test contract: commit `70bdb8395ba3111f1eee0ddaf40e4d33d557e2c5`.
- Compatibility Core implementation: commit `6a040a2045eb9c031904f38d2afeb03f6fdc32dc`.
- Runtime used for verification: Termux / Android Python 3.14.6, fresh shallow clone of `feature/ultratrain-compatibility-core`.

## Next exact action
Reconcile the three superseded long-context expectations with the TRL 1.13 / Transformers 5.16 CURRENT contract, then rerun the full suite before any CANONICAL promotion.
