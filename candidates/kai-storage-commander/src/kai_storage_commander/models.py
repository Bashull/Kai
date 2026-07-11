from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ActionPlan:
    action: str
    risk: str
    requires_confirmation: bool
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
