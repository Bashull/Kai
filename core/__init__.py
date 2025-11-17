"""Core autonomous infrastructure for Kai.

This package exposes utilities that allow Kai to fetch
external knowledge, adapt new artefacts to the local
codebase and continuously evaluate its own evolution.
"""

from .fetcher import Fetcher
from .adapter import Adapter
from .scanner import RepositoryScanner
from .synthesizer import Synthesizer
from .refactor import Refactorer
from .trainer import LocalTrainer
from .selfaudit import SelfAuditor
from .feedback import FeedbackController
from .evolution import EvolutionEngine

__all__ = [
    "Fetcher",
    "Adapter",
    "RepositoryScanner",
    "Synthesizer",
    "Refactorer",
    "LocalTrainer",
    "SelfAuditor",
    "FeedbackController",
    "EvolutionEngine",
]
