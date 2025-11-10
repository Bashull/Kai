from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import KaiAutonomousLoop, KaiConfig, KaiContext
from core.autonomous import PipelineStep
from core.feedback import FeedbackEvent, FeedbackLoop
from core.synthesizer import Pattern, PatternSynthesizer
from core.trainer import Trainer, TrainingSample
from core.selfaudit import AuditRule, SelfAuditEngine
from core.evolution import EvolutionEngine


def main() -> None:
    config = KaiConfig.from_environment(workspace=str(Path.cwd()))
    context = KaiContext(workspace=config.workspace_root, goals=["Mantener la evolución constante", "Crear artefactos útiles"])
    context.update_metric("promotion_threshold", config.stability_threshold)

    synthesizer = PatternSynthesizer(
        patterns=[
            Pattern(
                name="status_report",
                description="Informe en español sobre el avance de Kai",
                template=(
                    "Kai continúa avanzando sin pausa. Ciclo: {cycle}\n"
                    "Objetivos: {goals}\n"
                    "Confianza acumulada: {confidence:.2f}"
                ),
            )
        ]
    )
    trainer = Trainer()
    feedback = FeedbackLoop(learning_rate=0.2)
    audit = SelfAuditEngine(
        rules=[
            AuditRule(
                name="metrica_positiva",
                description="La confianza debe mantenerse por encima de 0.4",
                predicate=lambda ctx, artefacts: ctx.metrics.get("trainer.avg_outcome", 0) >= 0.4,
            )
        ]
    )
    evolution = EvolutionEngine()

    def synth_kwargs(ctx: KaiContext) -> dict:
        confidence = ctx.metrics.get("trainer.avg_outcome", 0.5)
        return {
            "variables": {
                "cycle": len(ctx.logs) + 1,
                "goals": ", ".join(ctx.goals),
                "confidence": confidence,
            }
        }

    def trainer_kwargs(ctx: KaiContext) -> dict:
        base = ctx.metrics.get("feedback.weights", 0.5)
        samples = [
            TrainingSample(features={"base": base}, outcome=min(1.0, base + 0.1)),
            TrainingSample(features={"base": base + 0.1}, outcome=min(1.0, base + 0.15)),
        ]
        return {"samples": samples}

    def feedback_kwargs(ctx: KaiContext) -> dict:
        return {
            "events": [
                FeedbackEvent(signal=0.3, note="Auto-refuerzo de confianza"),
                FeedbackEvent(signal=0.2, note="Evaluación externa positiva"),
            ]
        }

    def audit_kwargs(ctx: KaiContext) -> dict:
        return {"artefacts": ctx.artefacts}

    def evolution_kwargs(ctx: KaiContext) -> dict:
        score = max(ctx.metrics.get("score.selfaudit", 0.0), ctx.metrics.get("feedback.weights", 0.0))
        return {"candidate_score": score, "notes": "Ciclo automático completado"}

    loop = KaiAutonomousLoop(
        config,
        steps=[
            PipelineStep(module=synthesizer, kwargs_factory=synth_kwargs, name="synth"),
            PipelineStep(module=trainer, kwargs_factory=trainer_kwargs, name="trainer"),
            PipelineStep(module=feedback, kwargs_factory=feedback_kwargs, name="feedback"),
            PipelineStep(module=audit, kwargs_factory=audit_kwargs, name="selfaudit"),
            PipelineStep(module=evolution, kwargs_factory=evolution_kwargs, name="evolution"),
        ],
    )

    report = loop.run(context, max_cycles=5)
    print("=== Kai Autonomous Report ===")
    print(f"Cycles executed: {report.cycles}")
    print(f"Best score: {report.best_score:.2f}")
    print("\nMetrics:")
    for key, value in sorted(report.metrics.items()):
        print(f"  - {key}: {value:.2f}")
    print("\nArtefacts:")
    for name, artefact in report.artefacts.items():
        print(f"--- {name} ---\n{artefact}\n")
    print("\nActivity log:")
    for entry in report.logs:
        print(f" * {entry}")


if __name__ == "__main__":
    main()
