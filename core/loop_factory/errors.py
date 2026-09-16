"""Typed operational failures for Loop Factory."""
from __future__ import annotations

from .model import ErrorClass


class LoopFactoryError(RuntimeError):
    def __init__(self, error_class: ErrorClass, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.error_class = ErrorClass(error_class)
        self.message = message
        self.retryable = bool(retryable)

    def __str__(self) -> str:
        return f"{self.error_class.value}: {self.message}"
