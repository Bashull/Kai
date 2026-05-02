"""Canonical thresholds and caps for the Q-CHI Motor v1."""
from __future__ import annotations

# --- Default CHI state ---
DEFAULT_ENERGY: float = 0.78
DEFAULT_COHERENCE: float = 0.86
DEFAULT_ENTROPY: float = 0.22
DEFAULT_FATIGUE: float = 0.08

# --- CHI thresholds ---
COHERENCE_CRITICAL: float = 0.45
ENERGY_ALERT: float = 0.35
ENERGY_REST: float = 0.30
ENTROPY_ALERT: float = 0.72
ENTROPY_SAFE_MODE: float = 0.82
FATIGUE_ALERT: float = 0.68
FATIGUE_REST: float = 0.70

# --- Quantum variation caps by mode ---
QUANTUM_VARIATION_CAP: float = 0.08       # absolute max
QUANTUM_VARIATION_SAFE: float = 0.01      # modo_seguro
QUANTUM_VARIATION_RESTORATION: float = 0.0

QUANTUM_CAP_BY_MODE: dict[str, float] = {
    "charla_barrio": 0.06,
    "foco": 0.02,
    "reposo": 0.015,
    "modo_seguro": 0.01,
    "forja": 0.08,
    "restauracion": 0.0,
}

# --- Restore targets ---
RESTORE_ENERGY_DELTA: float = 0.12
RESTORE_COHERENCE_DELTA: float = 0.10
RESTORE_ENTROPY_DELTA: float = -0.10
RESTORE_FATIGUE_DELTA: float = -0.08
