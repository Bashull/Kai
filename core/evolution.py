from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class EvolutionRecord:
    version: str
    score: float
    timestamp: datetime
    notes: str


class EvolutionEngine(KaiModule):
    """Track Kai's iterations and decide whether to promote them."""

    def __init__(self) -> None:
        super().__init__("evolution")
        self.history: List[EvolutionRecord] = []

    def run(self, context, *, candidate_score: float, notes: str = "") -> ModuleResult:  # type: ignore[override]
        version = f"v{len(self.history) + 1:03d}"
        record = EvolutionRecord(version=version, score=candidate_score, timestamp=datetime.utcnow(), notes=notes)
        self.history.append(record)
        context.add_log(f"evolution: registered {version} with score {candidate_score:.2f}")
        context.update_metric("evolution.latest_score", candidate_score)
        should_promote = candidate_score >= context.metrics.get("promotion_threshold", 0.95)
        return ModuleResult(
            success=True,
            data={"version": version, "history": list(self.history)},
            score=candidate_score,
            messages=["promote" if should_promote else "hold"],
        )
