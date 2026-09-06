# UltraTrain Smart Planner Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conservative Smart Planner path that selects SFT/DPO/GRPO/distillation, routes runtime/kernel providers, and validates the composed plan with Compatibility Core.

**Architecture:** Keep method selection, runtime routing, and kernel routing in focused dependency-light modules. `smart_planner.py` composes them with the existing long-context planner and `evaluate_profile()`; policy authority remains in Compatibility Core.

**Tech Stack:** Python 3.12 stdlib, `unittest`, dataclasses/enums, existing UltraTrain Compatibility Core.

**Spec:** `docs/superpowers/specs/2026-09-06-ultratrain-smart-planner-routing-design.md`

## Global Constraints
- Branch: `feature/ultratrain-compatibility-core`; never modify `main`.
- Explicit method/runtime/kernel choices are preserved and validated, never silently rewritten.
- vLLM auto-routing requires version >= 0.28.0 and `vllm_canary_passed=True`.
- Liger auto-routing requires availability plus `liger_canary_passed=True`; version alone is insufficient.
- Compatibility Core is authoritative for cross-stack compatibility.

---

### Task 1: Method Selector
**Files:** Create `projects/ultratrain/method_selector.py`; test `projects/ultratrain/tests/test_method_selector.py`.

**Interfaces:** `TrainingMethod(str, Enum)` and `select_training_method(request: dict[str, Any]) -> MethodSelection`.

- [ ] Write tests proving explicit valid method wins; preference pairs -> DPO; reward signal -> GRPO; teacher -> distillation; no signal -> SFT; multiple implicit signals -> `NEEDS_CANARY`; invalid explicit method -> `UNSUPPORTED`.
- [ ] Run the test and verify RED because the module does not exist.
- [ ] Implement immutable `MethodSelection(method, status, rules, canaries, decisions)` with no external dependency.
- [ ] Run the method-selector tests and verify GREEN.
- [ ] Commit `feat(ultratrain): add training method selector`.

### Task 2: Runtime and Kernel Routing
**Files:** Create `projects/ultratrain/runtime_policy.py`, `projects/ultratrain/kernel_policy.py`; tests `test_runtime_policy.py`, `test_kernel_policy.py`.

**Interfaces:** `route_runtime(method, request) -> RuntimeRoute`; `route_kernel(request) -> KernelRoute`.

- [ ] Write RED tests: SFT/DPO prefer TRL when available then Transformers fallback; GRPO only auto-selects vLLM when >=0.28.0 plus canary; distillation requires teacher; async distillation requests vLLM teacher route; SDPA is kernel baseline; Liger auto-selects only with availability+canary; explicit unverified Liger -> `NEEDS_CANARY`.
- [ ] Implement minimal immutable route records and deterministic routing.
- [ ] Run both test modules and verify GREEN.
- [ ] Commit `feat(ultratrain): add runtime and kernel routing`.

### Task 3: Composite Smart Planner
**Files:** Modify `projects/ultratrain/smart_planner.py`; create `projects/ultratrain/tests/test_smart_planner_training.py`.

**Interfaces:** `plan_training(request: dict[str, Any]) -> TrainingSmartPlan` while preserving existing `plan_long_context()`.

- [ ] Write RED tests for composed SFT baseline, DPO auto-selection, ambiguous method blocking, secure GRPO/vLLM route, Liger canary gating, async-distillation Compatibility Core rejection, and 1M-token CP composition.
- [ ] Implement profile composition without duplicating Compatibility Core rules. Map selected runtime/kernel/method into the existing profile schema and call `evaluate_profile()`.
- [ ] Merge optional long-context severity monotonically and record all decisions/canaries.
- [ ] Run new planner tests plus inherited long-context tests and verify GREEN.
- [ ] Run `python -m unittest discover -s projects/ultratrain/tests -p 'test*.py'` when the complete branch snapshot is available; otherwise report exact tested scope.
- [ ] Run `python -m py_compile` over changed modules.
- [ ] Commit `feat(ultratrain): compose training smart planner`.

### Task 4: Governance Writeback
**Files:** Update `projects/ultratrain/INTEGRATION_AUTHORITY.md`; create Drive checkpoint.

- [ ] Record physical modules and exact verification scope/status.
- [ ] Verify GitHub remote bytes after commit.
- [ ] Create `2026-09-06_CHECKPOINT_ULTRATRAIN_SMART_PLANNER_ROUTING_v1.5` in `10_ACTIVE_CHECKPOINTS` with commit SHAs, test evidence, limitations, and next step.