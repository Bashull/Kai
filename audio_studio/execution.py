from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from audio_studio.models import Availability, CapabilitySnapshot


class ExecutionBlocked(PermissionError):
    pass


@dataclass(frozen=True)
class ExecutionPolicy:
    """Fail-closed spending policy. Free/local routes are the default authority."""

    free_only: bool = True
    max_cost_usd: Decimal = Decimal("0")
    approved_by: str | None = None
    approved_at: str | None = None
    allow_unknown_cost: bool = False


@dataclass(frozen=True)
class AuthorizationReceipt:
    provider_id: str
    allowed: bool
    reason: str
    cost_class: str
    estimated_cost_usd: str | None
    policy: dict
    checked_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def authorize_execution(snapshot: CapabilitySnapshot, policy: ExecutionPolicy | None = None, *, estimated_cost_usd: Decimal | str | None = None, now: str | None = None) -> AuthorizationReceipt:
    policy = policy or ExecutionPolicy()
    estimate = _decimal_or_none(estimated_cost_usd)
    checked_at = now or datetime.now(UTC).isoformat()
    reason = _block_reason(snapshot, policy, estimate)
    return AuthorizationReceipt(snapshot.provider_id, reason is None, reason or "FREE_OR_LOCAL_ROUTE_APPROVED", snapshot.cost_class, None if estimate is None else str(estimate), {"free_only": policy.free_only, "max_cost_usd": str(policy.max_cost_usd), "approved": bool(policy.approved_by and policy.approved_at), "allow_unknown_cost": policy.allow_unknown_cost}, checked_at)


def require_execution_authorization(*args, **kwargs) -> AuthorizationReceipt:
    receipt = authorize_execution(*args, **kwargs)
    if not receipt.allowed:
        raise ExecutionBlocked(receipt.reason)
    return receipt


def _block_reason(snapshot: CapabilitySnapshot, policy: ExecutionPolicy, estimate: Decimal | None) -> str | None:
    if snapshot.availability is not Availability.AVAILABLE:
        return f"PROVIDER_{snapshot.availability.value}"
    cost_class = snapshot.cost_class.upper()
    if cost_class in {"FREE", "LOCAL"}:
        return None
    if cost_class == "UNKNOWN" and not policy.allow_unknown_cost:
        return "UNKNOWN_COST_BLOCKED"
    if policy.free_only:
        return "FREE_ONLY_POLICY"
    if not (policy.approved_by and policy.approved_at):
        return "EXPLICIT_APPROVAL_REQUIRED"
    if estimate is None:
        return "COST_ESTIMATE_REQUIRED"
    if estimate < 0:
        return "INVALID_COST_ESTIMATE"
    if estimate > policy.max_cost_usd:
        return "BUDGET_EXCEEDED"
    return None


def _decimal_or_none(value: Decimal | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid estimated cost") from exc
