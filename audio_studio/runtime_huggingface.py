from __future__ import annotations

from collections.abc import Callable

from audio_studio.providers import AceStepAdapter, ReadOnlyCapabilityProbe, ace_step_zerogpu_target
from audio_studio.providers.probes import read_json_status


def build_zerogpu_provider(
    status_reader: Callable[[str], int | tuple[int, dict]] = read_json_status,
) -> AceStepAdapter:
    """Build the official free-limited planner adapter; it has no generation transport."""
    target = ace_step_zerogpu_target()
    return AceStepAdapter(
        target.provider_id,
        ReadOnlyCapabilityProbe(target, status_reader=status_reader),
    )
