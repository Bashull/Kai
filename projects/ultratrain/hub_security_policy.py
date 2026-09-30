from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HubSecurityDecision:
    allowed: bool
    rule: str
    needs_canary: bool = False


def evaluate_hub_policy(profile: dict) -> HubSecurityDecision:
    """Guard Hub/Xet cache and serialization capabilities introduced in Hub 1.32+."""
    hub = profile.get("hub", {})
    packages = profile.get("packages", {})
    version = packages.get("huggingface_hub")

    if hub.get("untrusted_torch_checkpoint") and not hub.get("safe_serialization", True):
        return HubSecurityDecision(False, "hub.serialization.safe_loader_required")

    if hub.get("shared_xet_blobs"):
        if not version:
            return HubSecurityDecision(False, "hub.shared_blobs.version_identity", True)
        try:
            parts = tuple(int(p) for p in version.split(".")[:3])
        except ValueError:
            return HubSecurityDecision(False, "hub.shared_blobs.version_identity", True)
        if parts < (1, 32, 0):
            return HubSecurityDecision(False, "hub.shared_blobs.requires_1_32")
        if not hub.get("shared_blob_canary_passed"):
            return HubSecurityDecision(False, "hub.shared_blobs.needs_canary", True)

    if hub.get("path_in_repo_contains_parent_segment"):
        return HubSecurityDecision(False, "hub.path_traversal.reject_parent_segments")

    return HubSecurityDecision(True, "hub.security.supported")
