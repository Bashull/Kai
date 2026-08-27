from __future__ import annotations

import json
from pathlib import Path

from audio_studio.providers import (
    AceMusicCompletionAdapter,
    ReadOnlyCapabilityProbe,
    ace_step_cloud_target,
)
from audio_studio.providers.probes import read_text_status

_ALLOWED_POINTER = (
    "termux:~/.agents/skills/acestep/scripts/config.json#api_key"
)


def credential_present(pointer: str, home: Path | None = None) -> bool:
    """Resolve one governed pointer and return presence, never the value."""
    if pointer != _ALLOWED_POINTER:
        raise ValueError("unsupported credential pointer")
    root = (home or Path.home()).resolve()
    config_path = (
        root / ".agents" / "skills" / "acestep" / "scripts" / "config.json"
    ).resolve()
    if root not in config_path.parents:
        raise ValueError("credential path escapes Termux home")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("api_key"))


def build_termux_cloud_provider() -> AceMusicCompletionAdapter:
    probe = ReadOnlyCapabilityProbe(
        ace_step_cloud_target(),
        status_reader=read_text_status,
        credential_resolver=credential_present,
    )
    return AceMusicCompletionAdapter("ace-step-1.5-cloud", probe)
