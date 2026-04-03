"""Homeostasis engine for Kai's internal climate.

This module codifies the CHI model (energy, coherence, entropy, fatigue)
so the rest of the system can reason about internal stability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


Severity = Literal["OPTIMO", "ALERTA", "CRITICO"]
Mode = Literal["charla_barrio", "foco", "reposo", "modo_seguro"]


@dataclass(slots=True)
class CHIState:
    energy: float = 0.78
    coherence: float = 0.86
    entropy: float = 0.22
    fatigue: float = 0.08
    cycle: int = 0
    mode: Mode = "charla_barrio"
    last_alert: str | None = None


@dataclass(slots=True)
class CHIAudit:
    severity: Severity
    reason: str
    suggested_action: str
    state: CHIState
    evaluated_at: str


class CHIEngine:
    """Maintain and audit Kai's internal homeostasis."""

    def __init__(self, initial_state: CHIState | None = None) -> None:
        self.state = initial_state or CHIState()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, round(value, 4)))

    def adjust(
        self,
        *,
        impact: float = 0.0,
        noise: float = 0.0,
        workload: float = 0.0,
        recovery: float = 0.0,
    ) -> CHIState:
        """Adjust CHI values using simple, explainable heuristics."""

        self.state.cycle += 1
        self.state.energy = self._clamp(self.state.energy + recovery - (workload * 0.5) - (noise * 0.2))
        self.state.coherence = self._clamp(self.state.coherence + (impact * 0.25) - (noise * 0.35) - (workload * 0.15))
        self.state.entropy = self._clamp(self.state.entropy + (noise * 0.45) + (workload * 0.2) - (recovery * 0.2))
        self.state.fatigue = self._clamp(self.state.fatigue + (workload * 0.4) - (recovery * 0.3))
        self.state.mode = self._derive_mode()
        return self.state

    def audit(self) -> CHIAudit:
        if self.state.coherence < 0.45:
            self.state.last_alert = "COHERENCIA_BAJA"
            return CHIAudit(
                severity="CRITICO",
                reason="La coherencia ha caído por debajo del umbral seguro.",
                suggested_action="Activar modo seguro, resumir contexto y pedir validación antes de seguir.",
                state=self.state,
                evaluated_at=datetime.utcnow().isoformat() + "Z",
            )

        if self.state.entropy > 0.72 or self.state.fatigue > 0.68:
            self.state.last_alert = "SATURACION_OPERATIVA"
            return CHIAudit(
                severity="ALERTA",
                reason="Entropía o fatiga elevadas detectadas.",
                suggested_action="Bajar carga, pausar multitarea y ejecutar un ciclo de restauración.",
                state=self.state,
                evaluated_at=datetime.utcnow().isoformat() + "Z",
            )

        if self.state.energy < 0.35:
            self.state.last_alert = "ENERGIA_BAJA"
            return CHIAudit(
                severity="ALERTA",
                reason="La energía operativa es baja.",
                suggested_action="Reducir operaciones pesadas y priorizar tareas cortas con alto retorno.",
                state=self.state,
                evaluated_at=datetime.utcnow().isoformat() + "Z",
            )

        self.state.last_alert = None
        return CHIAudit(
            severity="OPTIMO",
            reason="CHI estable y utilizable.",
            suggested_action="Mantener ritmo y registrar cambios importantes.",
            state=self.state,
            evaluated_at=datetime.utcnow().isoformat() + "Z",
        )

    def restore(self) -> CHIState:
        """Soft restoration when the system needs to recover focus."""

        self.state.energy = self._clamp(self.state.energy + 0.12)
        self.state.coherence = self._clamp(self.state.coherence + 0.18)
        self.state.entropy = self._clamp(self.state.entropy - 0.16)
        self.state.fatigue = self._clamp(self.state.fatigue - 0.14)
        self.state.mode = self._derive_mode()
        self.state.last_alert = "RESTAURADO"
        return self.state

    def snapshot(self) -> dict[str, object]:
        return asdict(self.state)

    def _derive_mode(self) -> Mode:
        if self.state.coherence < 0.45 or self.state.entropy > 0.82:
            return "modo_seguro"
        if self.state.fatigue > 0.7 or self.state.energy < 0.3:
            return "reposo"
        if self.state.coherence > 0.82 and self.state.entropy < 0.35:
            return "foco"
        return "charla_barrio"


__all__ = ["CHIEngine", "CHIState", "CHIAudit"]
