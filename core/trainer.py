"""Local heuristics trainer used to evolve Kai's internal models."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TrainingRun:
    name: str
    score: float
    timestamp: str
    metadata: Dict[str, str] = field(default_factory=dict)


class LocalTrainer:
    """Keep track of local experiments and compute quality metrics."""

    def __init__(self, history_file: Path | str = Path("core_training_history.json")) -> None:
        self.history_file = Path(history_file)
        self._history: List[TrainingRun] = []
        if self.history_file.exists():
            self._history = [TrainingRun(**entry) for entry in json.loads(self.history_file.read_text())]

    # ------------------------------------------------------------------
    def record_run(self, name: str, score: float, metadata: Optional[Dict[str, str]] = None) -> TrainingRun:
        run = TrainingRun(
            name=name,
            score=score,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {},
        )
        self._history.append(run)
        self.history_file.write_text(json.dumps([run.__dict__ for run in self._history], indent=2) + "\n")
        return run

    # ------------------------------------------------------------------
    def recent_scores(self, limit: int = 10) -> List[float]:
        return [run.score for run in self._history[-limit:]]

    def moving_average(self, window: int = 5) -> float:
        scores = self.recent_scores(window)
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def best_run(self) -> Optional[TrainingRun]:
        if not self._history:
            return None
        return max(self._history, key=lambda run: run.score)

    # ------------------------------------------------------------------
    def should_promote(self, threshold: float = 0.95, window: int = 5) -> bool:
        """Decide whether the latest runs pass the stability threshold."""

        average = self.moving_average(window)
        return average >= threshold and len(self._history) >= window


__all__ = ["LocalTrainer", "TrainingRun"]
