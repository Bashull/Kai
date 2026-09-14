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


def evaluate_peft_profile(profile: dict[str, Any]) -> PeftCompatibility:
    peft = profile.get("peft", {})
    if not peft:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.not_requested",))

    uses_trainable_tokens = (
        peft.get("trainable_tokens") is True
        or peft.get("lora_trainable_token_indices") is True
    )
    if not uses_trainable_tokens:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.trainable_tokens.not_used",))

    output_head_has_bias = peft.get("output_head_has_bias")
    if output_head_has_bias is None:
        return PeftCompatibility(
            PeftStatus.NEEDS_CANARY,
            ("peft.trainable_tokens.output_head_bias_identity",),
            ("peft_output_head_bias_identity",),
        )
    if output_head_has_bias is False:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.trainable_tokens.biasless_head",))

    if peft.get("trainable_tokens_bias_fix_present") is True:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.trainable_tokens.bias_fix_present",))

    if peft.get("adapter_init_logits_equal_canary_passed") is True:
        return PeftCompatibility(PeftStatus.SUPPORTED, decisions=("peft.adapter_init_logits_equal_verified",))

    return PeftCompatibility(
        PeftStatus.NEEDS_CANARY,
        ("peft.trainable_tokens.output_head_bias_integrity",),
        ("peft_adapter_init_logits_equal",),
    )
