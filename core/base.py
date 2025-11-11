from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging


logger = logging.getLogger("kai.base")


@dataclass(slots=True)
class ModuleResult:
    """Outcome of a module execution."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    score: Optional[float] = None

    def merge(self, other: "ModuleResult") -> "ModuleResult":
        """Merge another result into this one."""

        merged = ModuleResult(
            success=self.success and other.success,
            data={**self.data, **other.data},
            messages=[*self.messages, *other.messages],
            score=other.score if other.score is not None else self.score,
        )
        return merged


class KaiModule:
    """Base class that provides common logging and orchestration helpers."""

    name: str

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"kai.{self.name}")

    def emit(self, message: str, *, level: int = logging.INFO) -> None:
        """Log a message via the module logger."""

        self.logger.log(level, message)

    def run(self, context: "KaiContext", **kwargs: Any) -> ModuleResult:
        raise NotImplementedError


class StatefulModule(KaiModule):
    """A module that keeps an in-memory state between runs."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self.state: Dict[str, Any] = {}

    def reset(self) -> None:
        self.emit("Resetting internal state", level=logging.DEBUG)
        self.state.clear()
