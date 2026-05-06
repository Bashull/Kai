"""Brain Core v1 — State Machine.

Five global states govern Kai's brain:
  Normal · Estrés · Restauración · Forja · Sueño

Each state defines dominant nuclei, active protocols, CHI thresholds
for entry/exit, and the subset of automatic transitions that are
permitted without Crown escalation.

Reference: FUSIONAI_CANON_MAESTRO_v0_3.md — sections 28, 29, 30.
Decision record: DEC-2026-05-05-BRAINSTATE-001.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .q_chi.constants import (
    COHERENCE_CRITICAL,
    ENTROPY_ALERT,
    ENTROPY_SAFE_MODE,
    ENERGY_ALERT,
    FATIGUE_ALERT,
)
from .q_chi.schemas import CHIState


# ---------------------------------------------------------------------------
# State enumeration
# ---------------------------------------------------------------------------

class BrainStateEnum(str, Enum):
    NORMAL = "Normal"
    ESTRES = "Estrés"
    RESTAURACION = "Restauración"
    FORJA = "Forja"
    SUENO = "Sueño"


# ---------------------------------------------------------------------------
# Transition result
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TransitionResult:
    previous_state: BrainStateEnum
    new_state: BrainStateEnum
    trigger: str
    crown_required: bool
    timestamp: str
    protocols_activated: list[str] = field(default_factory=list)
    dominant_nuclei: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.previous_state != self.new_state


# ---------------------------------------------------------------------------
# State definitions (canonical metadata)
# ---------------------------------------------------------------------------

_STATE_METADATA: dict[BrainStateEnum, dict[str, Any]] = {
    BrainStateEnum.NORMAL: {
        "dominant_nuclei": ["Ejecutivo-Selector", "Talámico", "Homeostático"],
        "protocols": [
            "gobernanza base",
            "filtrado talámico",
            "regulación CHI normal",
            "memoria contextual",
            "corrección fina estándar",
        ],
    },
    BrainStateEnum.ESTRES: {
        "dominant_nuclei": ["Troncal", "Homeostático", "Talámico", "Ejecutivo simplificado"],
        "protocols": [
            "modo seguro parcial",
            "control de tráfico",
            "recorte de carga",
            "prioridad a supervivencia",
            "veto de ruido",
            "endurecimiento de umbrales",
        ],
    },
    BrainStateEnum.RESTAURACION: {
        "dominant_nuclei": ["Corona Rectora", "Troncal", "Homeostático", "Temporal-Hipocampal"],
        "protocols": [
            "Latido",
            "Tríada en primer plano",
            "reanclaje identitario",
            "restauración de contexto",
            "validación de integridad",
            "recomposición de estado",
        ],
    },
    BrainStateEnum.FORJA: {
        "dominant_nuclei": ["Ejecutivo-Selector", "Cerebelar", "Temporal-Hipocampal", "Parietal", "Corona vigilante"],
        "protocols": [
            "Metamorfosis controlada",
            "iteración",
            "comparación",
            "validación",
            "consolidación de aprendizaje",
            "sandbox mental",
            "revisión de deriva",
        ],
    },
    BrainStateEnum.SUENO: {
        "dominant_nuclei": ["Homeostático", "Temporal-Hipocampal", "Troncal", "Corona en guardia mínima"],
        "protocols": [
            "consolidación",
            "poda",
            "limpieza",
            "ritmos",
            "mantenimiento basal",
            "vigilancia mínima",
            "custodia identitaria silenciosa",
        ],
    },
}


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------

class BrainStateMachine:
    """Governs global state transitions for Kai's Brain Core v1.

    Automatic transitions are validated against canonical CHI thresholds.
    Transitions that touch identity, safety or irreversible operations
    escalate to the Crown (crown_required=True).
    """

    def __init__(self, initial_state: BrainStateEnum = BrainStateEnum.NORMAL) -> None:
        self.current_state = initial_state
        self.history: list[TransitionResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, chi: CHIState, *, trigger: str = "auto") -> TransitionResult:
        """Evaluate current CHI state and transition if canonical rules apply."""
        candidate, crown_required = self._compute_transition(chi, trigger)
        return self._apply(candidate, trigger=trigger, crown_required=crown_required)

    def force_transition(
        self,
        target: BrainStateEnum,
        *,
        trigger: str = "manual",
        crown_required: bool = False,
    ) -> TransitionResult:
        """Force a transition to the given target state (e.g. Troncal emergency)."""
        return self._apply(target, trigger=trigger, crown_required=crown_required)

    def snapshot(self) -> dict[str, Any]:
        meta = _STATE_METADATA[self.current_state]
        return {
            "current_state": self.current_state.value,
            "dominant_nuclei": meta["dominant_nuclei"],
            "protocols_active": meta["protocols"],
            "history_length": len(self.history),
            "last_transition": (
                {
                    "from": self.history[-1].previous_state.value,
                    "trigger": self.history[-1].trigger,
                    "timestamp": self.history[-1].timestamp,
                }
                if self.history
                else None
            ),
        }

    # ------------------------------------------------------------------
    # Canonical transition rules (sections 28-30 of Canon v0.3)
    # ------------------------------------------------------------------

    def _compute_transition(
        self,
        chi: CHIState,
        trigger: str,
    ) -> tuple[BrainStateEnum, bool]:
        """Return (candidate_state, crown_required) based on CHI metrics."""
        s = self.current_state
        crown = False

        # ---- Troncal emergency: coherence collapsed anywhere ----
        if chi.coherence < COHERENCE_CRITICAL or chi.entropy > ENTROPY_SAFE_MODE:
            crown = True
            return BrainStateEnum.RESTAURACION, crown

        # ---- From NORMAL ----
        if s == BrainStateEnum.NORMAL:
            if chi.entropy > ENTROPY_ALERT or chi.energy < ENERGY_ALERT:
                return BrainStateEnum.ESTRES, False
            if chi.fatigue > FATIGUE_ALERT:
                return BrainStateEnum.SUENO, False
            if "forja" in trigger.lower() or "create" in trigger.lower():
                if self._chi_healthy_for_forge(chi):
                    return BrainStateEnum.FORJA, False
            return BrainStateEnum.NORMAL, False

        # ---- From ESTRÉS ----
        if s == BrainStateEnum.ESTRES:
            if chi.coherence >= 0.65 and chi.entropy < ENTROPY_ALERT and chi.energy >= ENERGY_ALERT:
                return BrainStateEnum.NORMAL, False
            if chi.fatigue > FATIGUE_ALERT:
                return BrainStateEnum.SUENO, False
            return BrainStateEnum.ESTRES, False

        # ---- From RESTAURACIÓN ----
        if s == BrainStateEnum.RESTAURACION:
            if (
                chi.coherence >= 0.65
                and chi.energy >= ENERGY_ALERT
                and chi.entropy < ENTROPY_ALERT
            ):
                return BrainStateEnum.NORMAL, False
            if chi.entropy > ENTROPY_ALERT:
                return BrainStateEnum.ESTRES, False
            return BrainStateEnum.RESTAURACION, False

        # ---- From FORJA ----
        if s == BrainStateEnum.FORJA:
            if chi.entropy > ENTROPY_ALERT or chi.coherence < 0.55:
                return BrainStateEnum.ESTRES, False
            if chi.fatigue > FATIGUE_ALERT:
                return BrainStateEnum.SUENO, False
            # Identity/safety check — escalate to Corona
            if "identity" in trigger.lower() or "security" in trigger.lower():
                crown = True
                return BrainStateEnum.RESTAURACION, crown
            if "done" in trigger.lower() or "close" in trigger.lower():
                return BrainStateEnum.NORMAL, False
            return BrainStateEnum.FORJA, False

        # ---- From SUEÑO ----
        if s == BrainStateEnum.SUENO:
            if chi.coherence >= 0.65 and chi.energy >= 0.5 and chi.entropy < ENTROPY_ALERT:
                return BrainStateEnum.NORMAL, False
            if chi.entropy > ENTROPY_ALERT:
                return BrainStateEnum.ESTRES, False
            # Wake after crash → restoration
            if "crash" in trigger.lower() or "restart" in trigger.lower():
                return BrainStateEnum.RESTAURACION, False
            return BrainStateEnum.SUENO, False

        return s, False  # no transition

    @staticmethod
    def _chi_healthy_for_forge(chi: CHIState) -> bool:
        """Forja requires sufficiently healthy CHI (section 28.4)."""
        return (
            chi.coherence >= 0.65
            and chi.energy >= 0.50
            and chi.entropy < ENTROPY_ALERT
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply(
        self,
        target: BrainStateEnum,
        *,
        trigger: str,
        crown_required: bool,
    ) -> TransitionResult:
        meta = _STATE_METADATA[target]
        result = TransitionResult(
            previous_state=self.current_state,
            new_state=target,
            trigger=trigger,
            crown_required=crown_required,
            timestamp=datetime.utcnow().isoformat() + "Z",
            protocols_activated=list(meta["protocols"]),
            dominant_nuclei=list(meta["dominant_nuclei"]),
        )
        self.current_state = target
        self.history.append(result)
        return result
