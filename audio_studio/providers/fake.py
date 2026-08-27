from __future__ import annotations

from dataclasses import dataclass

from audio_studio.models import CapabilitySnapshot, SongRequest
from audio_studio.providers.base import MusicProviderAdapter


@dataclass
class FakeMusicProvider(MusicProviderAdapter):
    provider_id: str
    snapshot: CapabilitySnapshot

    def probe(self) -> CapabilitySnapshot:
        return self.snapshot

    def compile(self, request: SongRequest) -> dict:
        return {
            "provider_id": self.provider_id,
            "case_id": request.case_id,
            "blueprint": request.blueprint,
        }
