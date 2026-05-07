"""Adapters de FusionMemoryCore v1.0 — Bloque 6.

Cada adapter extrae un patrón de un repo estudiado en el Protocolo 5×5:
  chroma_adapter    ← chroma-core/chroma  (Ronda 2 · Mecánica interna)
  dedup_engine      ← mem0ai/mem0         (Ronda 2 · Mecánica interna)
  tiered_memory     ← letta-ai/letta      (Ronda 2 · Mecánica interna)
  cognify_pipeline  ← topoteretes/cognee  (Ronda 2 · Mecánica interna)
"""
from .chroma_adapter import (
    BaseVectorAdapter,
    ChromaVectorAdapter,
    FallbackInMemoryAdapter,
    make_adapter,
)
from .dedup_engine import (
    AUDNAction,
    DeduplicationEngine,
    DeduplicationResult,
    HybridQueryEngine,
    HybridSearchResult,
)
from .tiered_memory import (
    CoreMemory,
    MemorySection,
    TieredMemoryStore,
)
from .cognify_pipeline import (
    CognifyPipeline,
    PipelineData,
    PipelineTask,
    TemporalMemoryNode,
    make_fusion_cognify_pipeline,
)

__all__ = [
    # chroma
    "BaseVectorAdapter",
    "ChromaVectorAdapter",
    "FallbackInMemoryAdapter",
    "make_adapter",
    # mem0
    "AUDNAction",
    "DeduplicationEngine",
    "DeduplicationResult",
    "HybridQueryEngine",
    "HybridSearchResult",
    # letta
    "CoreMemory",
    "MemorySection",
    "TieredMemoryStore",
    # cognee
    "CognifyPipeline",
    "PipelineData",
    "PipelineTask",
    "TemporalMemoryNode",
    "make_fusion_cognify_pipeline",
]
