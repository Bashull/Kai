"""Version-aware preflight for Hugging Face Hub 2.2.0 behavior changes.

This module is intentionally dependency-free. It does not substitute for runtime
canaries, content hashes, transport verification, or artifact promotion gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HubPolicyFinding:
    status: str
    rule: str
    canary: str | None = None


def _parse_version(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def evaluate_hub_220(profile: dict[str, Any]) -> HubPolicyFinding | None:
    """Return the first material Hub 2.2 preflight finding, if any.

    Profile keys are opt-in: hub.jobs.metrics_mode='stream'|'snapshot',
    hub.jobs.follow, hub.parallel_xet_downloads, hub.filesystem_cache_refresh,
    and packages.huggingface_hub (or hub.version). Missing identity is not
    treated as evidence of compatibility.
    """
    hub = profile.get("hub", {})
    if not isinstance(hub, dict):
        return HubPolicyFinding("UNSUPPORTED", "hub.profile.invalid")
    jobs = hub.get("jobs", {})
    if not isinstance(jobs, dict):
        return HubPolicyFinding("UNSUPPORTED", "hub.jobs.profile.invalid")
    mode = jobs.get("metrics_mode")
    xet = hub.get("parallel_xet_downloads") is True
    fs_refresh = hub.get("filesystem_cache_refresh") is True
    if mode is None and not xet and not fs_refresh:
        return None
    if mode not in {None, "stream", "snapshot"}:
        return HubPolicyFinding("UNSUPPORTED", "hub.jobs.metrics_mode.invalid")

    packages = profile.get("packages", {})
    version = (packages.get("huggingface_hub") if isinstance(packages, dict) else None) or hub.get("version")
    parsed = _parse_version(version)
    if parsed is None:
        return HubPolicyFinding("NEEDS_CANARY", "hub.220_version_identity", "hub_220_version_identity")

    if mode == "stream" and parsed >= (2, 2, 0) and jobs.get("follow") is not True:
        return HubPolicyFinding("UNSUPPORTED", "hub.jobs.220_stream_requires_follow")
    if mode == "snapshot" and parsed < (2, 2, 0):
        return HubPolicyFinding("UNSUPPORTED", "hub.jobs.snapshot_requires_220")
    if mode == "snapshot" and jobs.get("follow") is True:
        return HubPolicyFinding("UNSUPPORTED", "hub.jobs.snapshot_follow_conflict")
    if mode == "stream" and parsed < (2, 2, 0) and "follow" in jobs:
        return HubPolicyFinding("NEEDS_CANARY", "hub.jobs.legacy_follow_semantics", "hub_jobs_metrics_legacy")

    if xet and parsed < (2, 2, 0) and not hub.get("parallel_xet_canary_passed"):
        return HubPolicyFinding("NEEDS_CANARY", "hub.xet.parallel_download_race", "hub_parallel_xet_integrity")
    if fs_refresh and parsed < (2, 2, 0) and not hub.get("filesystem_cache_canary_passed"):
        return HubPolicyFinding("NEEDS_CANARY", "hub.filesystem.cache_refresh_consistency", "hub_filesystem_cache_consistency")
    return None
