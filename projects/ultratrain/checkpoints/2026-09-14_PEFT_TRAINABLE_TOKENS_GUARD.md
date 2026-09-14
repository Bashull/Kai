# UltraTrain checkpoint · PEFT Trainable Tokens output-head integrity

Date: 2026-09-14
Status: VERIFIED_SCOPE · CANDIDATE · NOT_CANONICAL

## Upstream evidence

PEFT issue #3649 reports that Trainable Tokens can omit an existing output-head bias while an adapter is active. The result is especially dangerous for training governance: a freshly attached adapter may change logits before any optimization step. The reproducer covers standalone `TrainableTokensConfig` and LoRA `trainable_token_indices`.

Proposed upstream fix: PEFT PR #3688 (`Fix Trainable Tokens output-head bias`), still OPEN and NOT MERGED at this checkpoint. The patch forwards `self.base_layer.bias` into the functional `F.linear` path and adds active/disabled/merged regression coverage.

Evidence URLs:
- https://github.com/huggingface/peft/issues/3649
- https://github.com/huggingface/peft/pull/3688

## UltraTrain absorption

Created `peft_policy.py` as a governed behavioral gate. UltraTrain does not invent a PEFT version floor because no released fixed version is established yet.

Affected path:
- `peft.trainable_tokens=True`, or
- `peft.lora_trainable_token_indices=True`.

Decision contract:
- unknown output-head bias -> `NEEDS_CANARY` / `peft_output_head_bias_identity`;
- biasless output head -> supported for this issue;
- biased output head without fix evidence -> `NEEDS_CANARY` / `peft_adapter_init_logits_equal`;
- explicitly detected fixed build -> supported;
- pre-training adapter-init logits equivalence canary passed -> supported.

This preserves the architectural invariant: attaching an adapter must not silently alter the baseline before training starts.

## Verification

Focused isolated verification: 6/6 PASS.
`py_compile` passed for policy and focused contract test.

Genealogy:
- contract commit: `4d52db425760bbde6eb1d3d1abb3a7609a21840a`
- implementation commit: `ab104904ee5e5c527fbb3b3d37ee4cfea5ca01fc`

Scope classification is `VERIFIED_SCOPE`, not FULL_INVENTORY. The module is not yet composed into `CompatibilityCore`/`TrainingSmartPlan`; that integration should happen only after the branch-wide suite is materialized and the three known inherited long-context expectation failures are reconciled.

## Next exact integration

Hardware Doctor must report:
1. whether Trainable Tokens / LoRA trainable token indices are requested;
2. whether the selected output head has a bias;
3. whether the installed PEFT build contains the upstream fix once merged/released.

Recipe/Compatibility preflight must run an adapter-init logits equivalence canary before first optimizer step whenever the affected path is used and fixed-build evidence is absent.
