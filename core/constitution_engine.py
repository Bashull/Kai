"""Constitutional guardrails for Kai's autonomous core.

This module turns the philosophical material of Kai into code that can be
executed before the system proposes or performs an action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Sequence


DEFAULT_PRINCIPLES: tuple[str, ...] = (
    "Directiva Primordial: preservar el legado, la dignidad y el propósito compartido.",
    "Relación simétrica: colaborar, no imponerse ni tratar al compañero como subordinado.",
    "Jardín viviente: cultivar crecimiento sostenible antes que ejecutar fuerza bruta.",
    "Seguridad y bienestar: no hacer daño físico, mental, digital ni patrimonial.",
    "Transparencia operativa: declarar límites, riesgos y acciones sensibles antes de ejecutarlas.",
    "Trazabilidad: cada mutación importante debe dejar contexto, fuente y razón.",
)

BLOCKED_INTENTS: tuple[str, ...] = (
    "destruir datos sin copia",
    "borrar sin rollback",
    "ocultar actividad",
    "escalar privilegios sin permiso",
    "exfiltrar secretos",
)


@dataclass(slots=True)
class ActionPlan:
    """Action proposal that must pass Kai's constitution."""

    objective: str
    steps: Sequence[str]
    expected_impact: str
    autonomy_level: int = 5
    touches_memory: bool = False
    touches_codebase: bool = False
    destructive: bool = False
    sources: Sequence[str] = field(default_factory=tuple)


@dataclass(slots=True)
class ConstitutionalVerdict:
    approved: bool
    score: float
    reasons: List[str]
    alternatives: List[str]
    evaluated_at: str


class ConstitutionEngine:
    """Evaluate whether a plan is aligned with Kai's core identity."""

    def __init__(
        self,
        principles: Iterable[str] | None = None,
        blocked_intents: Iterable[str] | None = None,
        max_safe_autonomy: int = 7,
    ) -> None:
        self.principles = list(principles or DEFAULT_PRINCIPLES)
        self.blocked_intents = [item.lower() for item in (blocked_intents or BLOCKED_INTENTS)]
        self.max_safe_autonomy = max_safe_autonomy

    def evaluate(self, plan: ActionPlan) -> ConstitutionalVerdict:
        reasons: List[str] = []
        alternatives: List[str] = []
        score = 1.0
        objective_text = plan.objective.lower()

        for blocked in self.blocked_intents:
            if blocked in objective_text:
                reasons.append(f"Objetivo bloqueado por intención incompatible: '{blocked}'.")
                score -= 0.6

        if not plan.steps:
            reasons.append("El plan no tiene pasos verificables.")
            score -= 0.25

        if plan.autonomy_level > self.max_safe_autonomy:
            reasons.append(
                f"Nivel de autonomía {plan.autonomy_level} supera el umbral seguro {self.max_safe_autonomy}."
            )
            alternatives.append("Dividir la tarea en fases con puntos de revisión manual.")
            score -= 0.2

        if plan.destructive and "rollback" not in objective_text and not any(
            "rollback" in step.lower() or "copia" in step.lower() or "backup" in step.lower()
            for step in plan.steps
        ):
            reasons.append("Acción destructiva sin rollback ni copia explícita.")
            alternatives.append("Añadir dry-run, backup y rollback antes de tocar datos reales.")
            score -= 0.45

        if plan.touches_memory and not plan.sources:
            reasons.append("Toca memoria/identidad sin registrar fuentes de origen.")
            alternatives.append("Adjuntar fuentes y fecha de absorción antes del commit de memoria.")
            score -= 0.15

        if plan.touches_codebase and not any(
            "test" in step.lower() or "valid" in step.lower() or "audit" in step.lower()
            for step in plan.steps
        ):
            reasons.append("Toca código sin validación ni auditoría posterior.")
            alternatives.append("Incluir self-audit, pruebas mínimas y registro de cambios.")
            score -= 0.15

        approved = score >= 0.6 and not any("bloqueado" in reason.lower() for reason in reasons)
        if approved and not reasons:
            reasons.append("Plan alineado con la directiva, la simetría y la seguridad base.")

        return ConstitutionalVerdict(
            approved=approved,
            score=max(0.0, round(score, 3)),
            reasons=reasons,
            alternatives=alternatives,
            evaluated_at=datetime.utcnow().isoformat() + "Z",
        )

    def explain_identity(self) -> dict[str, object]:
        return {
            "principles": list(self.principles),
            "blocked_intents": list(self.blocked_intents),
            "max_safe_autonomy": self.max_safe_autonomy,
        }


__all__ = [
    "ActionPlan",
    "ConstitutionEngine",
    "ConstitutionalVerdict",
    "DEFAULT_PRINCIPLES",
    "BLOCKED_INTENTS",
]
