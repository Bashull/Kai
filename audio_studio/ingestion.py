from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from audio_studio.manifests import ManifestStore


class OutputIngestionError(ValueError):
    pass


_SECRET_FRAGMENTS = ("api_key", "token", "secret", "password", "authorization")


class OutputIngestor:
    """Attach immutable output evidence to a benchmark manifest without moving media."""

    VERSION = "1.0.0"

    def __init__(self, benchmark_root: Path, output_root: Path):
        self.store = ManifestStore(benchmark_root)
        self.output_root = output_root.resolve()

    def ingest(self, manifest_path: Path, source_files: Iterable[Path], response_metadata: dict, *, provider_id: str, ingested_at: str | None = None) -> dict:
        manifest = self.store.load(manifest_path)
        clean_metadata = _sanitize_metadata(response_metadata)
        assets = [self._asset(path) for path in source_files]
        if not assets:
            raise OutputIngestionError("at least one output file is required")
        payload = dict(manifest.payload)
        existing = {(item.get("sha256"), item.get("source_path")) for item in payload.get("assets", []) if isinstance(item, dict)}
        payload["assets"] = list(payload.get("assets", [])) + [asset for asset in assets if (asset["sha256"], asset["source_path"]) not in existing]
        generation = dict(payload.get("generation", {}))
        generation.update({"status": "INGESTED", "provider_id": provider_id, "response_metadata": clean_metadata})
        payload["generation"] = generation
        evidence = dict(payload.get("evidence", {}))
        evidence["output_ingestion"] = {"ingestor_version": self.VERSION, "ingested_at": ingested_at or datetime.now(UTC).isoformat(), "source_mode": "REFERENCE_ONLY_NO_MOVE", "asset_count": len(assets)}
        payload["evidence"] = evidence
        payload["status"] = "GENERATED"
        _atomic_json_write(manifest.path, payload)
        return payload

    def _asset(self, path: Path) -> dict:
        resolved = path.resolve()
        if self.output_root != resolved and self.output_root not in resolved.parents:
            raise OutputIngestionError("output file escapes governed output root")
        if not resolved.is_file() or resolved.is_symlink():
            raise OutputIngestionError("output file must be a regular non-symlink file")
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"role": "generated_audio", "source_path": str(resolved), "relative_path": resolved.relative_to(self.output_root).as_posix(), "sha256": digest.hexdigest(), "size_bytes": resolved.stat().st_size, "mime_type": mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"}


def _sanitize_metadata(value, path: str = "response_metadata"):
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in _SECRET_FRAGMENTS):
                raise OutputIngestionError(f"secret-like metadata rejected at {path}.{key}")
            clean[key] = _sanitize_metadata(item, f"{path}.{key}")
        return clean
    if isinstance(value, list):
        return [_sanitize_metadata(item, path) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise OutputIngestionError(f"unsupported metadata type at {path}")


def _atomic_json_write(path: Path, payload: dict) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
