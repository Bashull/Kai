from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Availability(StrEnum):
    AVAILABLE = "AVAILABLE"
    BLOCKED_QUOTA = "BLOCKED_QUOTA"
    OFFLINE = "OFFLINE"
    TOOL_BLOCKED = "TOOL_BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SongRequest:
    case_id: str
    blueprint: dict
    required_capabilities: frozenset[str] = frozenset({"text_to_music"})
    prefer_free: bool = True
    local_only: bool = False


@dataclass(frozen=True)
class CapabilitySnapshot:
    provider_id: str
    availability: Availability
    capabilities: frozenset[str]
    cost_class: str = "UNKNOWN"
    runtime: str = "UNKNOWN"
    evidence: dict = field(default_factory=dict)