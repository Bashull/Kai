from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChiQState:
    coherence: float
    heat: float
    integration: float
    queue: float
    quality: float
    risk: float
    recovery: float


DEFAULT_WEIGHTS = {
    "coherence": 0.22,
    "heat": -0.14,
    "integration": 0.18,
    "queue": -0.12,
    "quality": 0.20,
    "risk": -0.10,
    "recovery": 0.16,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def calculate_chi_q(state: ChiQState, weights: dict[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    score = (
        state.coherence * w["coherence"]
        + state.heat * w["heat"]
        + state.integration * w["integration"]
        + state.queue * w["queue"]
        + state.quality * w["quality"]
        + state.risk * w["risk"]
        + state.recovery * w["recovery"]
    )
    return _clamp(score)


def decision_hint(state: ChiQState) -> str:
    score = calculate_chi_q(state)
    if score < 0.35 or state.risk > 0.75:
        return "detener_edicion_y_pedir_aprobacion"
    if state.queue > 0.75:
        return "priorizar_memoria_y_cola"
    if score < 0.55:
        return "continuar_con_precaucion"
    return "avanzar"
