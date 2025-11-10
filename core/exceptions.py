class KaiError(Exception):
    """Base exception for Kai autonomous modules."""


class ModuleExecutionError(KaiError):
    """Raised when a module fails in a recoverable way."""


class PermanentFailure(KaiError):
    """Raised when the pipeline should abort."""
