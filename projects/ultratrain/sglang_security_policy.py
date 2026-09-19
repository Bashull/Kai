from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SGLangSecurityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    NEEDS_CANARY = "NEEDS_CANARY"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class SGLangSecurityResult:
    status: SGLangSecurityStatus
    rules: tuple[str, ...] = field(default_factory=tuple)
    canaries: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[str, ...] = field(default_factory=tuple)


def evaluate_sglang_security(request: dict[str, Any]) -> SGLangSecurityResult:
    """Security preflight for SGLang prefill/decode disaggregation.

    CVE-2026-93838 (published 2026-09-18) describes unbounded allocation
    from attacker-controlled STAGING_REQ chunk_idx on the decode engine's
    internal ZMQ rank port. Public records currently disagree on the exact
    first fixed version, so this policy deliberately does not infer safety
    from a version string alone.
    """
    if request.get("runtime_provider") != "sglang":
        return SGLangSecurityResult(SGLangSecurityStatus.SUPPORTED)

    if request.get("pd_disaggregation") is not True:
        return SGLangSecurityResult(
            SGLangSecurityStatus.SUPPORTED,
            decisions=("security.sglang.pd_not_enabled",),
        )

    exposure = request.get("sglang_zmq_rank_port_exposure")
    if exposure in {"public", "lan", "untrusted"}:
        return SGLangSecurityResult(
            SGLangSecurityStatus.UNSUPPORTED,
            rules=("security.sglang.cve_2026_93838.rank_port_untrusted",),
        )

    if exposure == "trusted_only":
        return SGLangSecurityResult(
            SGLangSecurityStatus.SUPPORTED,
            decisions=("security.sglang.cve_2026_93838.network_isolated",),
        )

    return SGLangSecurityResult(
        SGLangSecurityStatus.NEEDS_CANARY,
        rules=("security.sglang.cve_2026_93838.rank_port_exposure_unknown",),
        canaries=("sglang_pd_zmq_rank_port_exposure",),
    )
