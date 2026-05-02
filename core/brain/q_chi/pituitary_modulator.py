"""Pituitary Modulator — quantum variation layer and climate of decision.

Bridges CHI state and quantum entropy into a climate that modulates voting.
Does NOT invent truth, touch identity, or access sacred memory.
"""
from __future__ import annotations

import hashlib
import os
import time

from .constants import QUANTUM_CAP_BY_MODE, QUANTUM_VARIATION_CAP
from .schemas import CHIState, Mode, PituitaryState


class PituitaryModulator:
    """Compute the hormonal/quantum climate that colours judgment."""

    def __init__(self, *, variation_cap: float = QUANTUM_VARIATION_CAP) -> None:
        self._cap = variation_cap

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def generate_quantum_seed(self) -> str:
        raw = f"{time.time_ns()}{os.urandom(8).hex()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ------------------------------------------------------------------
    # Creative aperture — how much quantum can breathe
    # ------------------------------------------------------------------

    def compute_creative_aperture(self, chi: CHIState) -> float:
        """Healthy CHI opens the aperture; sickness collapses it."""
        aperture = (
            0.15
            + (chi.energy * 0.25)
            + (chi.coherence * 0.20)
            - (chi.entropy * 0.30)
            - (chi.fatigue * 0.20)
        )
        return max(0.0, min(1.0, aperture))

    # ------------------------------------------------------------------
    # Quantum variation — small, bounded, mode-gated
    # ------------------------------------------------------------------

    def compute_quantum_variation(self, *, mode: Mode, aperture: float) -> float:
        seed_hash = self.generate_quantum_seed()
        raw = int(seed_hash[:8], 16) / 0xFFFFFFFF  # [0, 1)
        mode_cap = QUANTUM_CAP_BY_MODE.get(mode, self._cap)
        # Variation is aperture-gated: sick system → near zero
        variation = raw * aperture * mode_cap
        return round(min(variation, self._cap), 6)

    # ------------------------------------------------------------------
    # Mood state — emotional climate
    # ------------------------------------------------------------------

    def compute_mood_state(
        self,
        *,
        chi: CHIState,
        quantum_variation: float,
        context_bias: float = 0.0,
    ) -> float:
        base = (chi.coherence * 0.4) + (chi.energy * 0.3) - (chi.fatigue * 0.2) - (chi.entropy * 0.1)
        mood = base + (quantum_variation * 0.5) + (context_bias * 0.1)
        return max(0.0, min(1.0, round(mood, 4)))

    # ------------------------------------------------------------------
    # Vote modulation — how much the pituitary tilts voting
    # ------------------------------------------------------------------

    def compute_vote_modulation(self, *, chi: CHIState, mood_state: float) -> float:
        # bounded_quantum_bias ∈ [-0.08, +0.08]
        bounded_bias = (mood_state - 0.5) * 0.16  # maps [0,1] → [-0.08, +0.08]
        return round(1.0 + bounded_bias, 4)

    # ------------------------------------------------------------------
    # Risk tolerance
    # ------------------------------------------------------------------

    def compute_risk_tolerance(self, chi: CHIState) -> float:
        return round(
            max(0.0, min(1.0, (chi.coherence * 0.5) + (chi.energy * 0.3) - (chi.entropy * 0.2))),
            4,
        )

    # ------------------------------------------------------------------
    # Build full state in one call
    # ------------------------------------------------------------------

    def build_state(self, *, chi: CHIState, context_bias: float = 0.0) -> PituitaryState:
        seed = self.generate_quantum_seed()
        aperture = self.compute_creative_aperture(chi)
        variation = self.compute_quantum_variation(mode=chi.mode, aperture=aperture)
        mood = self.compute_mood_state(chi=chi, quantum_variation=variation, context_bias=context_bias)
        modulation = self.compute_vote_modulation(chi=chi, mood_state=mood)
        risk = self.compute_risk_tolerance(chi)
        return PituitaryState(
            quantum_seed=seed,
            quantum_variation=variation,
            creative_aperture=aperture,
            mood_state=mood,
            vote_modulation=modulation,
            risk_tolerance=risk,
        )
