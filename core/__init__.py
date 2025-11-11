"""Kai autonomous core package.

This package provides the foundational modules that allow Kai to operate in an
autonomous loop: fetching new information, analysing existing artefacts,
creating new ones and auditing the results.  The modules are intentionally
lightweight so that they can run in constrained environments while still
encapsulating the high-level workflows described in the Copilot integration
playbook.
"""

from __future__ import annotations

import logging
from typing import Iterable, Sequence

from .autonomous import KaiAutonomousLoop
from .base import KaiModule, ModuleResult
from .config import KaiConfig
from .context import KaiContext

__all__: Sequence[str] = (
    "KaiAutonomousLoop",
    "KaiConfig",
    "KaiContext",
    "KaiModule",
    "ModuleResult",
)


def configure_logging(level: int = logging.INFO, handlers: Iterable[logging.Handler] | None = None) -> None:
    """Configure a sane logging setup for Kai modules.

    The modules rely heavily on structured logs to coordinate work.  When the
    host application has not configured logging yet this helper creates a
    simple configuration that prints timestamps and module names.
    """

    if logging.getLogger("kai").handlers:
        # Logging already configured by the host application.
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=list(handlers) if handlers else None,
    )


configure_logging()
