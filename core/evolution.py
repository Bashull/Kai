"""Self-evolution engine that maintains Kai's progression timeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional


@dataclass
class EvolutionStep:
    version: str
    summary: str
    timestamp: str
    metrics: Dict[str, float] = field(default_factory=dict)


class EvolutionEngine:
    """Track evolutionary steps and generate semantic version bumps."""

    def __init__(self, log_file: Path | str = Path("core_evolution_log.json")) -> None:
        self.log_file = Path(log_file)
        self.history: List[EvolutionStep] = []
        if self.log_file.exists():
            self.history = [EvolutionStep(**entry) for entry in json.loads(self.log_file.read_text())]
        elif self.log_file.parent and not self.log_file.parent.exists():
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def latest_version(self) -> str:
        if not self.history:
            return "0.0.0"
        return self.history[-1].version

    def _bump(self, version: str, level: Literal["major", "minor", "patch"]) -> str:
        major, minor, patch = [int(part) for part in version.split(".")]
        if level == "major":
            major += 1
            minor = 0
            patch = 0
        elif level == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"

    # ------------------------------------------------------------------
    def register_step(
        self,
        summary: str,
        metrics: Optional[Dict[str, float]] = None,
        level: Literal["major", "minor", "patch"] = "patch",
    ) -> EvolutionStep:
        new_version = self._bump(self.latest_version(), level)
        step = EvolutionStep(
            version=new_version,
            summary=summary,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metrics=metrics or {},
        )
        self.history.append(step)
        self.log_file.write_text(json.dumps([step.__dict__ for step in self.history], indent=2) + "\n")
        return step


__all__ = ["EvolutionEngine", "EvolutionStep"]
