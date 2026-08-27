from __future__ import annotations

from dataclasses import dataclass

from audio_studio.models import CapabilitySnapshot, SongRequest
from audio_studio.providers.base import MusicProviderAdapter


@dataclass
class BlueprintCompilerAdapter(MusicProviderAdapter):
    provider_id: str
    snapshot: CapabilitySnapshot

    def probe(self) -> CapabilitySnapshot:
        return self.snapshot

    @staticmethod
    def _lyrics(blueprint: dict) -> str:
        return blueprint.get("lyrics", "")


class AceStepAdapter(BlueprintCompilerAdapter):
    def compile(self, request: SongRequest) -> dict:
        b = request.blueprint
        caption = b.get("caption") or "; ".join(filter(None, [
            b.get("core_identity"), b.get("emotional_arc"), b.get("arrangement")
        ]))
        return {
            "caption": caption,
            "lyrics": self._lyrics(b),
            "seed": b.get("seed"),
            "duration": b.get("duration_seconds"),
            "format_rewriting": b.get("format_rewriting", False),
        }
class MiniMaxMusic3Adapter(BlueprintCompilerAdapter):
    def compile(self, request: SongRequest) -> dict:
        b = request.blueprint
        return {
            "lyrics": self._lyrics(b),
            "global_metadata": b.get("core_identity", ""),
            "vocal_details": b.get("vocal_identity", ""),
            "arrangement": b.get("arrangement", ""),
            "duration": b.get("duration_seconds"),
            "seed": b.get("seed"),
        }


class SunoV55Adapter(BlueprintCompilerAdapter):
    def compile(self, request: SongRequest) -> dict:
        b = request.blueprint
        style = "; ".join(filter(None, [
            b.get("core_identity"), b.get("emotional_arc"),
            b.get("vocal_identity"), b.get("arrangement"),
        ]))
        return {
            "model": "v5.5",
            "style": style,
            "lyrics": self._lyrics(b),
            "exclude": b.get("avoid", []),
            "controls": b.get("suno_controls", {}),
            "duration": b.get("duration_seconds"),
        }
