from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence

from .base import KaiModule, ModuleResult
from .config import KaiConfig
from .context import KaiContext


@dataclass(slots=True)
class PipelineStep:
    module: KaiModule
    kwargs_factory: Callable[[KaiContext], Dict[str, Any]] | None = None
    name: str | None = None

    def execute(self, context: KaiContext) -> ModuleResult:
        kwargs = self.kwargs_factory(context) if self.kwargs_factory else {}
        return self.module.run(context, **kwargs)


@dataclass(slots=True)
class AutonomousReport:
    cycles: int
    best_score: float
    logs: List[str]
    metrics: Dict[str, float]
    artefacts: Dict[str, Any]


class KaiAutonomousLoop:
    """Run Kai's self-improvement pipeline until it meets stability criteria."""

    def __init__(self, config: KaiConfig, steps: Sequence[PipelineStep]) -> None:
        self.config = config
        self.steps = list(steps)

    def run(self, context: KaiContext, *, max_cycles: int = 3) -> AutonomousReport:
        threshold = context.metrics.get("promotion_threshold", self.config.stability_threshold)
        best_score = 0.0

        for cycle in range(1, max_cycles + 1):
            context.add_log(f"cycle {cycle}: starting")
            for step in self.steps:
                result = step.execute(context)
                if result.messages:
                    for message in result.messages:
                        context.add_log(f"{step.name or step.module.name}: {message}")
                if result.score is not None:
                    metric_name = f"score.{step.name or step.module.name}"
                    context.update_metric(metric_name, result.score)
                    best_score = max(best_score, result.score)
            context.add_log(f"cycle {cycle}: completed with best_score={best_score:.2f}")
            if best_score >= threshold:
                context.add_log("stability threshold reached; stopping loop")
                break

        return AutonomousReport(
            cycles=cycle,
            best_score=best_score,
            logs=list(context.logs),
            metrics=dict(context.metrics),
            artefacts=dict(context.artefacts),
        )
