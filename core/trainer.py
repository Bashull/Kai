from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class TrainingSample:
    features: Mapping[str, float]
    outcome: float


class Trainer(KaiModule):
    """Maintain lightweight metrics for Kai's decision heuristics."""

    def __init__(self) -> None:
        super().__init__("trainer")
        self.history: List[TrainingSample] = []

    def run(self, context, samples: Sequence[TrainingSample] | None = None) -> ModuleResult:  # type: ignore[override]
        if not samples:
            return ModuleResult(success=True, data={"history": list(self.history)}, messages=["No samples provided"])

        self.history.extend(samples)
        avg = sum(sample.outcome for sample in self.history) / len(self.history)
        context.update_metric("trainer.avg_outcome", avg)
        context.add_log(f"trainer: updated average outcome to {avg:.2f}")
        return ModuleResult(success=True, data={"history": list(self.history), "average": avg}, score=avg)
