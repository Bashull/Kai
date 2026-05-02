"""NhipTheVote — specialized nucleus voting system.

Votes win by quality (confidence × stability × mood), not by noise.
Quantum only modulates slightly. Identity conflicts escalate to Corona Rectora.
"""
from __future__ import annotations

from .schemas import CHIState, NucleusVote, PituitaryState, VoteOutcome

CORONA_RECTORA_TRIGGERS = frozenset({"identidad", "memoria sagrada", "seguridad", "irreversible"})


class NhipTheVote:
    """Resolve a list of nucleus votes into a single outcome."""

    # ------------------------------------------------------------------
    # Sub-computations
    # ------------------------------------------------------------------

    def compute_confidence(self, *, perception: float, reflection: float) -> float:
        """confidence = perception × (1 + reflection)"""
        return round(perception * (1.0 + reflection), 4)

    def compute_state_stability(self, chi: CHIState) -> float:
        stability = (chi.coherence + chi.energy + (1.0 - chi.entropy) + (1.0 - chi.fatigue)) / 4.0
        return max(0.0, min(1.0, round(stability, 4)))

    def compute_vote_weight(
        self,
        *,
        confidence: float,
        state_stability: float,
        vote_modulation: float,
        risk_penalty: float = 0.0,
    ) -> float:
        weight = confidence * state_stability * vote_modulation
        weight = max(0.0, weight - risk_penalty)
        return round(weight, 6)

    # ------------------------------------------------------------------
    # Corona Rectora escalation check
    # ------------------------------------------------------------------

    def _needs_corona_escalation(self, votes: list[NucleusVote]) -> bool:
        for vote in votes:
            proposal_lower = vote.proposal.lower()
            if any(trigger in proposal_lower for trigger in CORONA_RECTORA_TRIGGERS):
                return True
        return False

    def _detect_conflicts(self, votes: list[NucleusVote]) -> bool:
        if len(votes) < 2:
            return False
        scores = [v.confidence for v in votes]
        return (max(scores) - min(scores)) < 0.05  # near-tie = conflict

    # ------------------------------------------------------------------
    # Main resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        votes: list[NucleusVote],
        *,
        chi: CHIState,
        pituitary: PituitaryState,
    ) -> VoteOutcome:
        if not votes:
            return VoteOutcome(
                winning_nucleus="NONE",
                winning_proposal="sin propuesta",
                weighted_score=0.0,
                votes=[],
                conflicts_detected=False,
            )

        stability = self.compute_state_stability(chi)
        conflicts = self._detect_conflicts(votes)
        needs_corona = self._needs_corona_escalation(votes)

        weighted: list[tuple[float, NucleusVote]] = []
        for vote in votes:
            risk_penalty = vote.risk * 0.1
            weight = self.compute_vote_weight(
                confidence=vote.confidence,
                state_stability=stability,
                vote_modulation=pituitary.vote_modulation,
                risk_penalty=risk_penalty,
            )
            weighted.append((weight, vote))

        weighted.sort(key=lambda t: t[0], reverse=True)
        best_score, best_vote = weighted[0]

        # If Corona Rectora must intervene, flag it in the winning proposal
        proposal = best_vote.proposal
        if needs_corona:
            proposal = f"[CORONA_RECTORA_REQUIRED] {proposal}"

        return VoteOutcome(
            winning_nucleus=best_vote.nucleus,
            winning_proposal=proposal,
            weighted_score=round(best_score, 6),
            votes=votes,
            conflicts_detected=conflicts or needs_corona,
        )
