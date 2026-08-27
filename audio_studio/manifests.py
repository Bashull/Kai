from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class BenchmarkManifest:
    case_id: str
    status: str
    payload: dict
    path: Path


class ManifestStore:
    REQUIRED = frozenset({
        "schema_version", "case_id", "status", "blueprint",
        "provider", "generation", "assets", "evidence",
    })

    def __init__(self, root: Path):
        self.root = root.resolve()
    def load(self, path: Path) -> BenchmarkManifest:
        resolved = self._inside_root(path)
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read manifest: {resolved}") from exc
        missing = self.REQUIRED - payload.keys()
        if missing:
            raise ManifestError("missing fields: " + ",".join(sorted(missing)))
        if payload["schema_version"] != "1.0.0":
            raise ManifestError("unsupported schema_version")
        return BenchmarkManifest(payload["case_id"], payload["status"], payload, resolved)

    def load_registry(self, path: Path) -> tuple[BenchmarkManifest, ...]:
        registry_path = self._inside_root(path)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        base = registry_path.parent
        return tuple(self.load(base / item["manifest"]) for item in registry["cases"])

    def _inside_root(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ManifestError("path escapes benchmark root")
        return resolved
