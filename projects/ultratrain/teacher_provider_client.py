from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .teacher_provider import TeacherCanaryEvidence, TeacherEndpoint, TeacherIdentity


class TeacherProtocolError(RuntimeError):
    pass


Transport = Callable[[str, str, dict[str, Any] | None, float], dict[str, Any]]


@dataclass(frozen=True)
class TeacherLogitsBatch:
    logits: tuple[tuple[float, ...], ...]
    vocab_size: int
    token_count: int


class TeacherProviderClient:
    """Protocol client whose injected transport owns authentication out of band."""

    def __init__(self, endpoint: TeacherEndpoint, *, transport: Transport) -> None:
        self.endpoint = endpoint
        self.transport = transport

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.endpoint.base_url.rstrip("/") + path
        response = self.transport(method, url, payload, self.endpoint.timeout_seconds)
        if not isinstance(response, dict):
            raise TeacherProtocolError("teacher response must be a JSON object")
        return response

    def health(self) -> bool:
        response = self._call("GET", "/v1/health")
        return response.get("ok") is True and response.get("protocol") == self.endpoint.protocol

    def identity(self) -> TeacherIdentity:
        response = self._call("GET", "/v1/identity")
        if response.get("protocol") != self.endpoint.protocol:
            raise TeacherProtocolError("teacher protocol mismatch")
        try:
            return TeacherIdentity(
                model_id=str(response["model_id"]),
                revision=str(response["revision"]),
                tokenizer_id=str(response["tokenizer_id"]),
                vocab_size=int(response["vocab_size"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TeacherProtocolError("invalid teacher identity payload") from exc

    def logits(self, input_ids: list[int]) -> TeacherLogitsBatch:
        if not input_ids or any(not isinstance(token, int) or token < 0 for token in input_ids):
            raise ValueError("input_ids must be a non-empty list of non-negative integers")
        response = self._call(
            "POST",
            "/v1/logits",
            {"input_ids": list(input_ids), "return_full_vocab_logits": True},
        )
        if response.get("protocol") != self.endpoint.protocol:
            raise TeacherProtocolError("teacher protocol mismatch")
        if response.get("full_vocab_logits") is not True:
            raise TeacherProtocolError("teacher did not return full-vocabulary logits")
        try:
            vocab_size = int(response["vocab_size"])
            rows = response["logits"]
        except (KeyError, TypeError, ValueError) as exc:
            raise TeacherProtocolError("invalid logits payload") from exc
        if not isinstance(rows, list) or len(rows) != len(input_ids):
            raise TeacherProtocolError("logits token dimension does not match input_ids")
        normalized: list[tuple[float, ...]] = []
        for row in rows:
            if not isinstance(row, list) or len(row) != vocab_size:
                raise TeacherProtocolError("logits vocabulary dimension mismatch")
            try:
                normalized.append(tuple(float(value) for value in row))
            except (TypeError, ValueError) as exc:
                raise TeacherProtocolError("logits must be numeric") from exc
        return TeacherLogitsBatch(tuple(normalized), vocab_size=vocab_size, token_count=len(input_ids))

    def run_canary(
        self,
        *,
        expected_identity: TeacherIdentity,
        student_tokenizer_id: str,
        student_vocab_size: int,
        probe_input_ids: list[int],
        evidence_ref: str,
    ) -> TeacherCanaryEvidence:
        health_ok = False
        identity_ok = False
        tokenizer_ok = False
        vocab_ok = False
        full_logits = False
        contract_ok = False
        try:
            health_ok = self.health()
            observed = self.identity()
            identity_ok = observed == expected_identity
            tokenizer_ok = observed.tokenizer_id == student_tokenizer_id
            vocab_ok = observed.vocab_size == student_vocab_size
            batch = self.logits(probe_input_ids)
            full_logits = batch.vocab_size == student_vocab_size
            contract_ok = batch.token_count == len(probe_input_ids) and full_logits
        except (TeacherProtocolError, ValueError):
            pass
        return TeacherCanaryEvidence(
            health_ok=health_ok,
            identity_ok=identity_ok,
            tokenizer_compatible=tokenizer_ok,
            vocab_compatible=vocab_ok,
            full_vocab_logits=full_logits,
            logits_contract_ok=contract_ok,
            evidence_refs=(evidence_ref,),
        )
