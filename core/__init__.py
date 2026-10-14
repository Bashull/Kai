"""Core autonomous infrastructure for Kai.

Importing a specific subpackage (such as core.loop_factory) must not
eagerly import optional application dependencies. The legacy public
symbols remain available through module-level lazy attribute loading.

This deliberately does not install dependencies or silently ignore import
errors when a caller explicitly requests one of the legacy facilities.
"""
from importlib import import_module

_LEGACY_SYMBOL_MODULES = {
    "Fetcher": "fetcher",
    "Adapter": "adapter",
    "RepositoryScanner": "scanner",
    "Synthesizer": "synthesizer",
    "Refactorer": "refactor",
    "LocalTrainer": "trainer",
    "SelfAuditor": "selfaudit",
    "FeedbackController": "feedback",
    "EvolutionEngine": "evolution",
}

__all__ = list(_LEGACY_SYMBOL_MODULES)


def __getattr__(name):
    module_name = _LEGACY_SYMBOL_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    symbol = getattr(import_module(f".{module_name}", __name__), name)
    globals()[name] = symbol
    return symbol


def __dir__():
    return sorted(set(globals()) | set(__all__))
