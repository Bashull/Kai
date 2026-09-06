from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TrainingMethod(str, Enum):
    SFT = "sft"
    DPO = "dpo"
    GRPO = "grpo"
    DISTILLATION = "distillation"


class MethodStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class MethodSelection:
    method: TrainingMethod | None
    status: MethodStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def select_training_method(request: dict[str, Any]) -> MethodSelection:
    explicit = request.get("method")
    if explicit is not None:
        try:
            method = TrainingMethod(str(explicit).lower())
        except ValueError:
            return MethodSelection(None, MethodStatus.UNSUPPORTED, ("method.explicit.invalid",))
        return MethodSelection(method, MethodStatus.SUPPORTED, decisions=("method.explicit",))

    signals: list[tuple[str, TrainingMethod]] = []
    if request.get("preference_pairs") is True:
        signals.append(("method.preference_pairs", TrainingMethod.DPO))
    if request.get("reward_signal") is True:
        signals.append(("method.reward_signal", TrainingMethod.GRPO))
    if request.get("teacher_available") is True:
        signals.append(("method.teacher_available", TrainingMethod.DISTILLATION))

    if len(signals) > 1:
        return MethodSelection(
            None,
            MethodStatus.NEEDS_CANARY,
            ("method.implicit.ambiguous",),
            ("method_signal_ambiguity",),
        )
    if len(signals) == 1:
        decision, method = signals[0]
        return MethodSelection(method, MethodStatus.SUPPORTED, decisions=(decision,))
    return MethodSelection(
        TrainingMethod.SFT,
        MethodStatus.SUPPORTED,
        decisions=("method.sft_default",),
    )
