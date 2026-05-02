"""Metabolic base of the Q-CHI system.

Owns energy, coherence, entropy, fatigue, cycle and mode.
Does NOT handle quantum variation — that belongs to PituitaryModulator.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from .constants import (
    COHERENCE_CRITICAL,
    DEFAULT_COHERENCE,
    DEFAULT_ENERGY,
    DEFAULT_ENTROPY,
    DEFAULT_FATIGUE,
    ENERGY_ALERT,
    ENTROPY_ALERT,
    ENTROPY_SAFE_MODE,
    FATIGUE_ALERT,
    RESTORE_COHERENCE_DELTA,
    RESTORE_ENERGY_DELTA,
    RESTORE_ENTROPY_DELTA,
    RESTORE_FATIGUE_DELTA,
)
from .schemas import CHIAudit, CHIState, Mode, Severity


class CHIEngine:
    """Maintain and audit Kai's internal homeostasis."""

    def __init__(self, initial_state: CHIState | None = None) -> None:
        self.state = initial_state or CHIState(
            energy=DEFAULT_ENERGY,
            coherence=DEFAULT_COHERENCE,
            entropy=DEFAULT_ENTROPY,
            fatigue=DEFAULT_FATIGUE,
            cycle=0,
            mode="charla_barrio",
        )

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, round(value, 4)))

    def adjust(
        self,
        *,
        impact: float = 0.0,
        operational_noise: float = 0.0,
        workload: float = 0.0,
        recovery: float = 0.0,
    ) -> CHIState:
        """Update CHI metrics based on operational inputs.

        `operational_noise` is saturation/interference — distinct from quantum_variation.
        """
        s = self.state
        s.cycle += 1
        s.energy = self._clamp(s.energy + recovery - (workload * 0.5) - (operational_noise * 0.2))
        s.coherence = self._clamp(s.coherence + (impact * 0.25) - (operational_noise * 0.35) - (workload * 0.15))
        s.entropy = self._clamp(s.entropy + (operational_noise * 0.45) + (workload * 0.2) - (recovery * 0.2))
        s.fatigue = self._clamp(s.fatigue + (workload * 0.4) - (recovery * 0.3))
        s.mode = self.derive_mode()
        return s

    def derive_mode(self) -> Mode:
        s = self.state
        if s.coherence < COHERENCE_CRITICAL or s.entropy > ENTROPY_SAFE_MODE:
            return "modo_seguro"
        if s.energy < ENERGY_ALERT:
            return "reposo"
        if s.coherence > 0.82 and s.entropy < 0.35 and s.fatigue < 0.30:
            return "foco"
        return "charla_barrio"

    def audit(self) -> CHIAudit:
        s = self.state
        now = datetime.utcnow().isoformat() + "Z"

        if s.coherence < COHERENCE_CRITICAL:
            s.last_alert = "COHERENCIA_BAJA"
            return CHIAudit(
                severity="CRITICO",
                reason="La coherencia ha caído por debajo del umbral seguro.",
                suggested_action="Activar modo seguro, resumir contexto y pedir validación.",
                state=s,
                evaluated_at=now,
            )
        if s.entropy > ENTROPY_SAFE_MODE:
            s.last_alert = "ENTROPIA_CRITICA"
            return CHIAudit(
                severity="CRITICO",
                reason="La entropía ha superado el umbral de modo seguro.",
                suggested_action="Forzar restauración y reducir carga operativa.",
                state=s,
                evaluated_at=now,
            )
        if s.entropy > ENTROPY_ALERT or s.fatigue > FATIGUE_ALERT:
            s.last_alert = "SATURACION_OPERATIVA"
            return CHIAudit(
                severity="ALERTA",
                reason="Entropía o fatiga elevadas.",
                suggested_action="Bajar carga, pausar multitarea y ejecutar ciclo de restauración.",
                state=s,
                evaluated_at=now,
            )
        if s.energy < ENERGY_ALERT:
            s.last_alert = "ENERGIA_BAJA"
            return CHIAudit(
                severity="ALERTA",
                reason="La energía operativa es baja.",
                suggested_action="Reducir operaciones pesadas y priorizar tareas cortas.",
                state=s,
                evaluated_at=now,
            )

        s.last_alert = None
        return CHIAudit(
            severity="OPTIMO",
            reason="CHI estable y utilizable.",
            suggested_action="Mantener ritmo y registrar cambios importantes.",
            state=s,
            evaluated_at=now,
        )

    def restore(self) -> CHIState:
        """Soft restoration: nudge metrics back toward healthy defaults."""
        s = self.state
        s.energy = self._clamp(s.energy + RESTORE_ENERGY_DELTA)
        s.coherence = self._clamp(s.coherence + RESTORE_COHERENCE_DELTA)
        s.entropy = self._clamp(s.entropy + RESTORE_ENTROPY_DELTA)
        s.fatigue = self._clamp(s.fatigue + RESTORE_FATIGUE_DELTA)
        s.mode = self.derive_mode()
        s.last_alert = None
        return s

    def snapshot(self) -> dict[str, object]:
        return asdict(self.state)
