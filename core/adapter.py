from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class AdaptationRequest:
    source_snippet: str
    target_style: str
    metadata: Mapping[str, str] | None = None


class CodeAdapter(KaiModule):
    """Apply lightweight transformations to match Kai's conventions."""

    def __init__(self, *, style_map: Mapping[str, Dict[str, str]] | None = None) -> None:
        super().__init__("adapter")
        self.style_map = style_map or {}

    def run(self, context, request: AdaptationRequest) -> ModuleResult:  # type: ignore[override]
        transformations = self.style_map.get(request.target_style, {})
        adapted = request.source_snippet
        for find, replace in transformations.items():
            adapted = adapted.replace(find, replace)

        context.add_log(f"adapter: transformed snippet for style {request.target_style}")
        return ModuleResult(success=True, data={"code": adapted, "metadata": dict(request.metadata or {})})

    def register_style(self, name: str, replacements: Mapping[str, str]) -> None:
        self.style_map[name] = dict(replacements)
        self.emit(f"Registered transformation style {name}")
