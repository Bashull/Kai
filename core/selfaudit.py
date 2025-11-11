from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping, Sequence

from .base import KaiModule, ModuleResult

if TYPE_CHECKING:
    from .context import KaiContext


@dataclass(slots=True)
class AuditRule:
    name: str
    description: str
    predicate: Callable[["KaiContext", Mapping[str, object]], bool]


class SelfAuditEngine(KaiModule):
    """Evaluate artefacts and metrics to ensure ethical and stability constraints."""

    def __init__(self, rules: Sequence[AuditRule] | None = None) -> None:
        super().__init__("selfaudit")
        self.rules = list(rules or [])

    def register_rule(self, rule: AuditRule) -> None:
        self.rules.append(rule)
        self.emit(f"Registered audit rule {rule.name}")

    def run(self, context, artefacts: Mapping[str, object] | None = None) -> ModuleResult:  # type: ignore[override]
        artefacts = artefacts or context.artefacts
        passed: list[str] = []
        failed: list[str] = []

        for rule in self.rules:
            try:
                result = bool(rule.predicate(context, artefacts))
            except Exception as exc:  # pragma: no cover - guard rails for user supplied predicates
                self.emit(f"Rule {rule.name} raised {exc}", level=40)
                result = False
            (passed if result else failed).append(rule.name)

        context.add_log(f"selfaudit: {len(passed)} passed / {len(failed)} failed")
        success = not failed
        messages = ["passed: " + ", ".join(passed)] if passed else []
        if failed:
            messages.append("failed: " + ", ".join(failed))
        return ModuleResult(success=success, data={"passed": passed, "failed": failed}, messages=messages, score=1.0 if success else 0.0)
