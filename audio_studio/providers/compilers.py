from __future__ import annotations

from dataclasses import dataclass

from audio_studio.models import CapabilitySnapshot, SongRequest
from audio_studio.providers.base import MusicProviderAdapter
from audio_studio.providers.probes import ReadOnlyCapabilityProbe


@dataclass
class BlueprintCompilerAdapter(MusicProviderAdapter):
    provider_id: str
    snapshot: CapabilitySnapshot | ReadOnlyCapabilityProbe

    def probe(self) -> CapabilitySnapshot:
        if isinstance(self.snapshot, ReadOnlyCapabilityProbe):
            return self.snapshot.run()
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
        seed = b.get("seed")
        return {
            "prompt": caption,
            "lyrics": self._lyrics(b),
            "thinking": b.get("thinking", True),
            "audio_duration": b.get("duration_seconds"),
            "bpm": b.get("bpm"),
            "audio_format": b.get("audio_format", "mp3"),
            "use_format": b.get("format_rewriting", False),
            "use_random_seed": seed is None,
            "seed": -1 if seed is None else seed,
            "batch_size": b.get("batch_size", 1),
        }
class MiniMaxMusic3Adapter(BlueprintCompilerAdapter):
    def compile(self, request: SongRequest) -> dict:
        b = request.blueprint
        prompt = "; ".join(filter(None, [
            b.get("core_identity"), b.get("emotional_arc"),
            b.get("vocal_identity"), b.get("arrangement"),
        ]))
        return {
            "model": b.get("minimax_model", "music-3.0"),
            "prompt": prompt,
            "lyrics": self._lyrics(b),
            "stream": False,
            "output_format": "url",
            "audio_setting": b.get("audio_setting", {
                "sample_rate": 44100,
                "bitrate": 256000,
                "format": "mp3",
            }),
            "lyrics_optimizer": False,
            "is_instrumental": b.get("is_instrumental", False),
        }


class SunoV55Adapter(BlueprintCompilerAdapter):
    def compile(self, request: SongRequest) -> dict:
        b = request.blueprint
        style = "; ".join(filter(None, [
            b.get("core_identity"), b.get("emotional_arc"),
            b.get("vocal_identity"), b.get("arrangement"),
        ]))
        return {
            "contract_status": "UNVERIFIED_AUTH_REQUIRED",
            "executable": False,
            "blueprint_draft": {
                "model_intent": "v5.5",
                "style": style,
                "lyrics": self._lyrics(b),
                "exclude": b.get("avoid", []),
                "controls": b.get("suno_controls", {}),
                "duration": b.get("duration_seconds"),
            },
        }
