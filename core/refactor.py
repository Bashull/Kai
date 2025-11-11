from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class RefactorPlan:
    description: str
    replacements: Mapping[str, str]


class RefactorEngine(KaiModule):
    """Apply textual refactors in sequence."""

    def run(self, context, code: str, plans: Sequence[RefactorPlan] | None = None) -> ModuleResult:  # type: ignore[override]
        plans = plans or []
        if not plans:
            return ModuleResult(success=True, data={"code": code}, messages=["No refactors requested"])

        updated = code
        for plan in plans:
            for find, replace in plan.replacements.items():
                updated = updated.replace(find, replace)
            context.add_log(f"refactor: {plan.description}")

        return ModuleResult(success=True, data={"code": updated})
