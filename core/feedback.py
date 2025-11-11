"""Feedback loops that help Kai adjust its internal decision weights."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class FeedbackRecord:
    event: str
    score: float
    weight: float
    timestamp: str
    notes: str = ""


class FeedbackController:
    """Aggregate feedback and derive updated confidence weights."""

    def __init__(self) -> None:
        self.history: List[FeedbackRecord] = []
        self.weights: Dict[str, float] = {}

    def register(self, event: str, score: float, weight: float = 1.0, notes: str = "") -> FeedbackRecord:
        record = FeedbackRecord(
            event=event,
            score=score,
            weight=weight,
            timestamp=datetime.utcnow().isoformat() + "Z",
            notes=notes,
        )
        self.history.append(record)
        self._recalculate(event)
        return record

    def _recalculate(self, event: str) -> None:
        relevant = [r for r in self.history if r.event == event]
        if not relevant:
            return
        weighted_total = sum(r.score * r.weight for r in relevant)
        weight_sum = sum(r.weight for r in relevant)
        self.weights[event] = weighted_total / weight_sum if weight_sum else 0.0

    def summary(self) -> Dict[str, float]:
        return dict(self.weights)


__all__ = ["FeedbackController", "FeedbackRecord"]
