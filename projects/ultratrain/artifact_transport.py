from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

from .scientific_evidence import ArtifactRef, IntegrityResult, verify_artifact_bytes


TransportLoader = Callable[[ArtifactRef], bytes]


@dataclass(frozen=True)
class TransportPolicy:
    allowed_schemes: tuple[str, ...]
    max_bytes: int | None = None

    def __post_init__(self) -> None:
        if not self.allowed_schemes:
            raise ValueError("transport.allowed_schemes")
        if self.max_bytes is not None and self.max_bytes <= 0:
            raise ValueError("transport.max_bytes")


@dataclass(frozen=True)
class ResolvedArtifact:
    ref: ArtifactRef
    payload: bytes
    transport_id: str
    integrity: IntegrityResult

    def require_verified(self) -> bytes:
        if not self.integrity.allow_promotion:
            raise ValueError("artifact.integrity_not_verified")
        return self.payload


class ArtifactResolver:
    def __init__(
        self,
        transports: dict[str, tuple[str, TransportLoader]],
        policy: TransportPolicy,
    ) -> None:
        self._transports = transports
        self._policy = policy

    def resolve(self, ref: ArtifactRef) -> ResolvedArtifact:
        scheme = urlsplit(ref.uri).scheme.lower()
        if not scheme:
            raise ValueError("transport.uri_scheme_required")
        allowed = {item.lower() for item in self._policy.allowed_schemes}
        if scheme not in allowed:
            raise ValueError("transport.scheme_not_allowed")
        if scheme not in self._transports:
            raise ValueError("transport.loader_missing")

        transport_id, loader = self._transports[scheme]
        payload = loader(ref)
        if not isinstance(payload, bytes):
            raise TypeError("transport.payload_must_be_bytes")
        if self._policy.max_bytes is not None and len(payload) > self._policy.max_bytes:
            raise ValueError("transport.payload_too_large")

        return ResolvedArtifact(
            ref=ref,
            payload=payload,
            transport_id=transport_id,
            integrity=verify_artifact_bytes(ref, payload),
        )
