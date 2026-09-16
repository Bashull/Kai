from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PeftStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class PeftCompatibility:
    status: PeftStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def _version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) < 2:
        return None
    parsed: list[int] = []
    for part in parts[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            return None
        parsed.append(int(digits))
    while len(parsed) < 3:
        parsed.append(0)
    return tuple(parsed)


def evaluate_peft_profile(profile: dict[str, Any]) -> PeftCompatibility:
    peft = profile.get("peft", {})
    if not peft:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.not_requested",))

    version = _version_tuple(peft.get("version"))
    method = str(peft.get("method", "")).lower()
    optimizer = str(peft.get("optimizer", "")).lower()

    # PEFT 0.21 introduces this LoRA-specific optimizer. Keep it opt-in: an
    # upstream release is capability evidence, not a reason to rewrite recipes.
    if optimizer == "riemannian_lora":
        if version is None or version < (0, 21, 0):
            return PeftCompatibility(
                PeftStatus.UNSUPPORTED,
                ("peft.riemannian_lora.requires_021",),
            )
        if method != "lora":
            return PeftCompatibility(
                PeftStatus.UNSUPPORTED,
                ("peft.riemannian_lora.requires_lora",),
            )

    # PEFT 0.21 extends target_parameters to multiple adapters, which matters
    # for packed MoE expert parameters. Older builds must not receive recipes
    # that rely on the new multi-adapter behavior.
    if peft.get("target_parameters") is True and int(peft.get("adapter_count", 1)) > 1:
        if version is None or version < (0, 21, 0):
            return PeftCompatibility(
                PeftStatus.UNSUPPORTED,
                ("peft.target_parameters.multi_adapter.requires_021",),
            )

    uses_trainable_tokens = (
        peft.get("trainable_tokens") is True
        or peft.get("lora_trainable_token_indices") is True
    )
    if uses_trainable_tokens:
        output_head_has_bias = peft.get("output_head_has_bias")
        if output_head_has_bias is None:
            return PeftCompatibility(
                PeftStatus.NEEDS_CANARY,
                ("peft.trainable_tokens.output_head_bias_identity",),
                ("peft_output_head_bias_identity",),
            )
        if output_head_has_bias is True:
            # As of PEFT 0.21.0, upstream PR #3688 is still open. Do not infer
            # the fix from version identity; require capability evidence or a
            # behavioral logits-equivalence canary before the first step.
            if peft.get("trainable_tokens_bias_fix_present") is True:
                return PeftCompatibility(
                    PeftStatus.SUPPORTED,
                    decisions=("peft.trainable_tokens.bias_fix_present",),
                )
            if peft.get("adapter_init_logits_equal_canary_passed") is True:
                return PeftCompatibility(
                    PeftStatus.SUPPORTED,
                    decisions=("peft.adapter_init_logits_equal_verified",),
                )
            return PeftCompatibility(
                PeftStatus.NEEDS_CANARY,
                ("peft.trainable_tokens.output_head_bias_integrity",),
                ("peft_adapter_init_logits_equal",),
            )

    decisions: list[str] = []
    if uses_trainable_tokens:
        decisions.append("peft.trainable_tokens.biasless_head")
    else:
        decisions.append("peft.trainable_tokens.not_used")
    if optimizer == "riemannian_lora":
        decisions.append("peft.riemannian_lora.explicit")
    if peft.get("target_parameters") is True and int(peft.get("adapter_count", 1)) > 1:
        decisions.append("peft.target_parameters.multi_adapter_021")
    return PeftCompatibility(PeftStatus.SUPPORTED, decisions=tuple(decisions))
