from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from audio_studio.models import CapabilitySnapshot, SongRequest


class MusicProviderAdapter(ABC):
    """Replaceable provider boundary; never stores secret values."""

    provider_id: str

    @abstractmethod
    def probe(self) -> CapabilitySnapshot:
        """Return fresh availability and capability evidence."""

    @abstractmethod
    def compile(self, request: SongRequest) -> dict[str, Any]:
        """Translate the neutral Blueprint into provider-native fields."""

    def generate(self, compiled: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Generation is gated behind a verified runtime adapter")
