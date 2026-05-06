"""Canonical contracts for the FusionAI Ingestor Universal (Bloque 5)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class IngestTarget(str, Enum):
    MEMORY = "memory"
    PREVIEW = "preview"
    ARCHIVE = "archive"


class IngestStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class BinaryInput:
    path: Path
    raw_bytes: bytes
    filename: str

    @classmethod
    def from_path(cls, path: str | Path) -> "BinaryInput":
        p = Path(path)
        return cls(path=p, raw_bytes=p.read_bytes(), filename=p.name)

    def sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()


@dataclass
class DetectedAsset:
    media_type: str
    extension: str
    detector_name: str
    chosen_mode: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentElement:
    id: str
    category: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FusionDocument:
    id: str
    source: str
    media_type: str
    text: str
    elements: list[DocumentElement]
    chunks: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MemoryNode:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    hash_value: str = ""

    def __post_init__(self) -> None:
        if not self.hash_value:
            payload = json.dumps({"id": self.id, "text": self.text}, sort_keys=True)
            self.hash_value = hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class OutputBundle:
    source: str
    hash_value: str
    decision: DetectedAsset
    document: FusionDocument
    memory_nodes: list[MemoryNode]
    status: IngestStatus
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None


@dataclass
class IngestOptions:
    target: IngestTarget = IngestTarget.MEMORY
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestResult:
    bundle: "OutputBundle | None"
    status: IngestStatus
    decision: "DetectedAsset | None" = None
    document: "FusionDocument | None" = None
    memory_nodes: list["MemoryNode"] = field(default_factory=list)
    error: str | None = None

    def __post_init__(self) -> None:
        if self.bundle is not None:
            self.decision = self.bundle.decision
            self.document = self.bundle.document
            self.memory_nodes = self.bundle.memory_nodes

    @classmethod
    def failed(cls, *, source: str, error: str) -> "IngestResult":
        return cls(bundle=None, status=IngestStatus.FAILED, error=error)
