"""FusionIngestorRouter — main entry point for the Ingestor Universal.

Follows the canonical flow:
  Input → SourceResolver → DetectorCore → Router → Mode Engine
  → OutputBundle → MemoryNodes
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .detector import MagicDetector
from .modes import DeepMode, PartitionMode, QuickMode
from .schemas import (
    BinaryInput,
    IngestOptions,
    IngestResult,
    IngestStatus,
    IngestTarget,
    MemoryNode,
    OutputBundle,
)


class FusionIngestorRouter:
    """Route an input file through the correct processing mode and produce
    an IngestResult (wrapping an OutputBundle + MemoryNodes)."""

    def __init__(self) -> None:
        self._detector = MagicDetector()
        self._quick = QuickMode()
        self._deep = DeepMode()
        self._partition = PartitionMode()

    def ingest(
        self,
        source: str | Path,
        *,
        options: IngestOptions | None = None,
    ) -> "IngestResult":
        if options is None:
            options = IngestOptions()

        try:
            asset = BinaryInput.from_path(source)
        except Exception as e:
            return IngestResult.failed(source=str(source), error=str(e))

        detection = self._detector.detect(asset, target=options.target.value)

        try:
            if detection.chosen_mode == "deep":
                document = self._deep.process(asset, detection)
            elif detection.chosen_mode == "partition":
                document = self._partition.process(asset, detection)
            else:
                document = self._quick.process(asset, detection)
        except Exception as e:
            return IngestResult.failed(source=str(source), error=f"Processing failed: {e}")

        stability = "stable" if options.target == IngestTarget.MEMORY else "provisional"
        memory_nodes = [
            MemoryNode(
                id=str(uuid.uuid4()),
                text=chunk,
                metadata={
                    "source": asset.filename,
                    "media_type": detection.media_type,
                    "mode": detection.chosen_mode,
                    "memory_stability": stability,
                    "fusion_tags": [stability],
                },
            )
            for chunk in document.chunks
        ]

        bundle = OutputBundle(
            source=str(source),
            hash_value=asset.sha256(),
            decision=detection,
            document=document,
            memory_nodes=memory_nodes,
            status=IngestStatus.SUCCESS,
        )

        return IngestResult(bundle=bundle, status=IngestStatus.SUCCESS)


def write_output_bundle(result: "IngestResult", output_dir: str | Path) -> Path:
    """Write all canonical OutputBundle files to output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    b = result.bundle

    # DETECTION.json
    (out / "DETECTION.json").write_text(
        json.dumps({
            "media_type": b.decision.media_type,
            "extension": b.decision.extension,
            "detector_name": b.decision.detector_name,
            "chosen_mode": b.decision.chosen_mode,
            "confidence": b.decision.confidence,
        }, indent=2)
    )

    # INGEST_RESULT.json
    (out / "INGEST_RESULT.json").write_text(
        json.dumps({
            "source": b.source,
            "hash_value": b.hash_value,
            "status": b.status.value,
            "ingested_at": b.ingested_at,
        }, indent=2)
    )

    # DOCUMENT.json
    (out / "DOCUMENT.json").write_text(
        json.dumps({
            "id": b.document.id,
            "source": b.document.source,
            "media_type": b.document.media_type,
            "metadata": b.document.metadata,
            "created_at": b.document.created_at,
        }, indent=2)
    )

    # DOCUMENT.md
    (out / "DOCUMENT.md").write_text(b.document.text or "")

    # ELEMENTS.json
    (out / "ELEMENTS.json").write_text(
        json.dumps([
            {"id": e.id, "category": e.category, "text": e.text, "metadata": e.metadata}
            for e in b.document.elements
        ], indent=2)
    )

    # CHUNKS.json
    (out / "CHUNKS.json").write_text(json.dumps(b.document.chunks, indent=2))

    # MEMORY_NODES.json
    (out / "MEMORY_NODES.json").write_text(
        json.dumps([
            {"id": n.id, "text": n.text, "metadata": n.metadata, "hash_value": n.hash_value}
            for n in b.memory_nodes
        ], indent=2)
    )

    # INGEST_REPORT.md
    report = _build_report(b)
    (out / "INGEST_REPORT.md").write_text(report)

    return out


def _build_report(b: OutputBundle) -> str:
    return f"""# INGEST REPORT

**Source:** {b.source}
**Status:** {b.status.value}
**Media type:** {b.decision.media_type}
**Mode:** {b.decision.chosen_mode}
**Detector:** {b.decision.detector_name}
**Hash (SHA-256):** {b.hash_value}
**Ingested at:** {b.ingested_at}

## Summary

- Elements: {len(b.document.elements)}
- Chunks: {len(b.document.chunks)}
- Memory nodes: {len(b.memory_nodes)}

*Una memoria sin fuente no es memoria FusionAI.*
"""
