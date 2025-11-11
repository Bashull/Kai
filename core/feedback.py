from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .base import ModuleResult, StatefulModule


@dataclass(slots=True)
class FeedbackEvent:
    signal: float
    note: str


class FeedbackLoop(StatefulModule):
    """Adjust Kai's decision weights based on feedback signals."""

    def __init__(self, *, learning_rate: float = 0.1) -> None:
        super().__init__("feedback")
        self.learning_rate = learning_rate
        self.state["weights"] = 0.0

    def run(self, context, events: Sequence[FeedbackEvent] | None = None) -> ModuleResult:  # type: ignore[override]
        if not events:
            return ModuleResult(success=True, data={"weights": self.state.get("weights", 0.0)})

        weight = float(self.state.get("weights", 0.0))
        for event in events:
            weight += self.learning_rate * event.signal
            context.add_log(f"feedback: {event.note} ({event.signal:+.2f})")
        self.state["weights"] = weight
        context.update_metric("feedback.weights", weight)
        return ModuleResult(success=True, data={"weights": weight}, score=weight)
