"""Autonomy, budget, promotion, and security policy evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import LoopFactoryError
from .guards import assert_noncanonical_branch, assert_write_scope
from .model import AutonomyLevel, ErrorClass, JobManifest


@dataclass(slots=True)
class ActionRequest:
    name: str
    required_level: AutonomyLevel = AutonomyLevel.A0
    mutation: bool = False
    target_branch: str | None = None
    target_path: Path | None = None
    estimated_cost_eur: float = 0.0
    destructive: bool = False
    security_sensitive: bool = False
    promotion: bool = False


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    error_class: ErrorClass | None
    reason: str

def _level_value(level: AutonomyLevel) -> int:
    return int(AutonomyLevel(level).value[1:])


class PolicyEngine:
    def evaluate(
        self,
        job: JobManifest,
        action: ActionRequest,
        *,
        explicit_authorization: bool = False,
    ) -> PolicyDecision:
        if action.estimated_cost_eur < 0:
            return PolicyDecision(False, ErrorClass.BUDGET_EXCEEDED, "Estimated cost cannot be negative")
        if action.estimated_cost_eur > job.budget.max_cost_eur:
            return PolicyDecision(False, ErrorClass.BUDGET_EXCEEDED, "Action exceeds job budget")
        if _level_value(action.required_level) > _level_value(job.autonomy_level):
            return PolicyDecision(False, ErrorClass.AUTH_REQUIRED, "Action exceeds delegated autonomy level")

        needs_a5_gate = (
            action.required_level == AutonomyLevel.A5
            or action.destructive
            or action.security_sensitive
        )
        if needs_a5_gate and not explicit_authorization:
            return PolicyDecision(False, ErrorClass.AUTH_REQUIRED, "A5/security action requires explicit authorization")

        if action.promotion and not explicit_authorization:
            return PolicyDecision(False, ErrorClass.AUTH_REQUIRED, "Promotion requires explicit authorization")

        try:
            if action.mutation and action.target_branch is not None:
                assert_noncanonical_branch(action.target_branch)
            if action.mutation and action.target_path is not None:
                assert_write_scope(
                    Path(action.target_path),
                    [Path(scope) for scope in job.write_scope],
                )
        except LoopFactoryError as exc:
            return PolicyDecision(False, exc.error_class, exc.message)

        return PolicyDecision(True, None, "Action is within delegated policy")
