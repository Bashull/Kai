"""Shared dataclasses for the Q-CHI Motor v1."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["OPTIMO", "ALERTA", "CRITICO"]
Mode = Literal["charla_barrio", "foco", "reposo", "modo_seguro", "forja", "restauracion"]


@dataclass(slots=True)
class CHIState:
    energy: float
    coherence: float
    entropy: float
    fatigue: float
    cycle: int
    mode: Mode
    last_alert: str | None = None


@dataclass(slots=True)
class CHIAudit:
    severity: Severity
    reason: str
    suggested_action: str
    state: CHIState
    evaluated_at: str


@dataclass(slots=True)
class PituitaryState:
    quantum_seed: str
    quantum_variation: float
    creative_aperture: float
    mood_state: float
    vote_modulation: float
    risk_tolerance: float


@dataclass(slots=True)
class NucleusVote:
    nucleus: str
    perception: float
    reflection: float
    confidence: float
    risk: float
    proposal: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VoteOutcome:
    winning_nucleus: str
    winning_proposal: str
    weighted_score: float
    votes: list[NucleusVote]
    conflicts_detected: bool


@dataclass(slots=True)
class EntropicFingerprint:
    timestamp: str
    mode: Mode
    chi_state: dict[str, Any]
    pituitary_state: dict[str, Any]
    nuclei_called: list[str]
    votes: list[dict[str, Any]]
    final_output: str
    hash_value: str
