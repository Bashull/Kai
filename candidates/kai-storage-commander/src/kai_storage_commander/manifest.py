from __future__ import annotations

import hashlib
import json
from typing import Any


def build_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "capability": "storage-commander",
        "payload": dict(payload),
    }


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def fingerprint_manifest(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(manifest)).hexdigest()


def verify_manifest_fingerprint(manifest: dict[str, Any], expected: str) -> bool:
    return fingerprint_manifest(manifest) == expected
