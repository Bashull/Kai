"""QCHIRuntime — orchestrator of the Q-CHI Motor v1.

Execution order (canonical):
  1. CHIEngine.adjust()
  2. CHIEngine.audit()
  3. If CRITICO → CHIEngine.restore() + force modo_seguro
  4. PituitaryModulator.build_state()
  5. NhipTheVote.resolve()
  6. EntropicFingerprintBuilder.build()
  7. Return structured output
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .chi_engine import CHIEngine
from .entropic_fingerprint import EntropicFingerprintBuilder
from .nhip_the_vote import NhipTheVote
from .pituitary_modulator import PituitaryModulator
from .schemas import NucleusVote


class QCHIRuntime:
    """Cose los 4 componentes del Motor Q-CHI en un flujo único."""

    def __init__(
        self,
        chi_engine: CHIEngine,
        pituitary: PituitaryModulator,
        voter: NhipTheVote,
        fingerprint_builder: EntropicFingerprintBuilder,
    ) -> None:
        self._chi = chi_engine
        self._pituitary = pituitary
        self._voter = voter
        self._fp = fingerprint_builder

    def process(
        self,
        *,
        input_payload: dict[str, Any],
        nuclei_votes: list[NucleusVote],
        impact: float = 0.0,
        operational_noise: float = 0.0,
        workload: float = 0.0,
        recovery: float = 0.0,
        context_bias: float = 0.0,
    ) -> dict[str, Any]:
        # 1. Adjust CHI
        chi_state = self._chi.adjust(
            impact=impact,
            operational_noise=operational_noise,
            workload=workload,
            recovery=recovery,
        )

        # 2. Audit
        audit = self._chi.audit()

        # 3. Critical state → restore and force safe mode
        if audit.severity == "CRITICO":
            chi_state = self._chi.restore()
            chi_state.mode = "modo_seguro"
            audit = self._chi.audit()

        # 4. Build pituitary climate
        pituitary_state = self._pituitary.build_state(
            chi=chi_state,
            context_bias=context_bias,
        )

        # 5. Resolve votes
        vote_outcome = self._voter.resolve(
            nuclei_votes,
            chi=chi_state,
            pituitary=pituitary_state,
        )

        # 6. Build fingerprint
        nuclei_called = [v.nucleus for v in nuclei_votes]
        final_output = vote_outcome.winning_proposal
        fingerprint = self._fp.build(
            chi=chi_state,
            pituitary=pituitary_state,
            nuclei_called=nuclei_called,
            votes=nuclei_votes,
            final_output=final_output,
            mode=chi_state.mode,
        )

        # 7. Return structured output
        return {
            "chi": asdict(chi_state),
            "audit": {
                "severity": audit.severity,
                "reason": audit.reason,
                "suggested_action": audit.suggested_action,
                "evaluated_at": audit.evaluated_at,
            },
            "pituitary": asdict(pituitary_state),
            "vote_outcome": {
                "winning_nucleus": vote_outcome.winning_nucleus,
                "winning_proposal": vote_outcome.winning_proposal,
                "weighted_score": vote_outcome.weighted_score,
                "conflicts_detected": vote_outcome.conflicts_detected,
                "total_votes": len(vote_outcome.votes),
            },
            "fingerprint": {
                "timestamp": fingerprint.timestamp,
                "hash_value": fingerprint.hash_value,
                "nuclei_called": fingerprint.nuclei_called,
                "mode": fingerprint.mode,
            },
            "final_output": final_output,
        }

    def snapshot(self) -> dict[str, Any]:
        return self._chi.snapshot()

    def audit(self) -> dict[str, Any]:
        a = self._chi.audit()
        return {
            "severity": a.severity,
            "reason": a.reason,
            "suggested_action": a.suggested_action,
            "evaluated_at": a.evaluated_at,
        }

    def restore(self) -> dict[str, Any]:
        self._chi.restore()
        return self.snapshot()
