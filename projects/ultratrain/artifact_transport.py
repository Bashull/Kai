from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

from .scientific_evidence import ArtifactRef, IntegrityResult, verify_artifact_bytes


TransportLoader = Callable[[ArtifactRef], bytes]


class TransportFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        diagnostic: str = "",
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class TransportPolicy:
    allowed_schemes: tuple[str, ...]
    max_bytes: int | None = None
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not self.allowed_schemes:
            raise ValueError("transport.allowed_schemes")
        if self.max_bytes is not None and self.max_bytes <= 0:
            raise ValueError("transport.max_bytes")
        if self.max_attempts <= 0:
            raise ValueError("transport.max_attempts")


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

    def _load_with_retry(self, loader: TransportLoader, ref: ArtifactRef) -> bytes:
        last_failure: TransportFailure | None = None
        for _ in range(self._policy.max_attempts):
            try:
                return loader(ref)
            except TransportFailure as failure:
                last_failure = failure
                if not failure.retryable:
                    raise
        assert last_failure is not None
        raise last_failure

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
        payload = self._load_with_retry(loader, ref)
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
