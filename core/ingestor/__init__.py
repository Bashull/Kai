"""FusionAI Ingestor Universal — KaiOS integration.

Implements the Tríada+ pattern (Canon v0.3 section 31):
  - Carga Semántica: parsed text, elements, chunks
  - Secuencia Temporal: timestamps, provenance
  - Estado Criptográfico: SHA-256 hash per asset, manifest

Reference: FusionAI_Ingestor_MasterSpec_v0_5.md
"""
from .router import FusionIngestorRouter, IngestOptions, IngestTarget, write_output_bundle
from .schemas import (
    BinaryInput,
    DetectedAsset,
    DocumentElement,
    FusionDocument,
    IngestResult,
    IngestStatus,
    MemoryNode,
    OutputBundle,
)

__all__ = [
    "FusionIngestorRouter",
    "IngestOptions",
    "IngestTarget",
    "write_output_bundle",
    "BinaryInput",
    "DetectedAsset",
    "DocumentElement",
    "FusionDocument",
    "IngestResult",
    "IngestStatus",
    "MemoryNode",
    "OutputBundle",
]
