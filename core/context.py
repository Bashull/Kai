from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass(slots=True)
class KaiContext:
    """Shared context for Kai's autonomous loop.

    The context captures goals, artefacts generated in previous cycles and
    high-level metrics.  Modules can update this object to communicate with
    later stages in the pipeline.
    """

    workspace: Path
    goals: List[str] = field(default_factory=list)
    artefacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def add_log(self, message: str) -> None:
        self.logs.append(message)
        self.last_updated = datetime.utcnow()

    def update_metric(self, name: str, value: float) -> None:
        self.metrics[name] = value
        self.last_updated = datetime.utcnow()

    def add_artefact(self, name: str, value: Any) -> None:
        self.artefacts[name] = value
        self.last_updated = datetime.utcnow()
