from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class Pattern:
    name: str
    description: str
    template: str


class PatternSynthesizer(KaiModule):
    """Combine patterns to produce candidate artefacts."""

    def __init__(self, patterns: Sequence[Pattern] | None = None) -> None:
        super().__init__("synthesizer")
        self.patterns: Dict[str, Pattern] = {p.name: p for p in patterns or ()}

    def register(self, pattern: Pattern) -> None:
        self.patterns[pattern.name] = pattern
        self.emit(f"Registered pattern {pattern.name}")

    def run(self, context, *, use: Sequence[str] | None = None, variables: Dict[str, str] | None = None) -> ModuleResult:  # type: ignore[override]
        selected = use or self.patterns.keys()
        artefacts: Dict[str, str] = {}
        variables = variables or {}

        for name in selected:
            pattern = self.patterns.get(name)
            if not pattern:
                continue
            artefact = pattern.template.format(**variables)
            artefacts[name] = artefact
            context.add_artefact(name, artefact)

        context.add_log(f"synthesizer: generated {len(artefacts)} artefacts")
        return ModuleResult(success=bool(artefacts), data={"artefacts": artefacts}, messages=list(artefacts))
