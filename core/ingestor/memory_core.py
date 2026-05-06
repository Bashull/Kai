"""FusionMemoryCore — local in-memory retrieval following LlamaIndex pattern.

No external dependencies. Implements the Tríada+ Estado Criptográfico:
  each node is hashed, storage is persisted as JSON with an audit manifest.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import MemoryNode


_BLOCKED_STABILITIES = {"sensitive_review", "trash"}


@dataclass
class MemoryCoreConfig:
    chunk_size: int = 512
    storage_path: str = ""
    top_k: int = 5


@dataclass
class SourceNode:
    node: "MemoryNodeRef"
    score: float


@dataclass
class MemoryNodeRef:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQueryResult:
    answer: str
    source_nodes: list[SourceNode]
    audit: dict[str, Any] = field(default_factory=dict)


@dataclass
class _DocStore:
    documents: dict[str, MemoryNode] = field(default_factory=dict)


@dataclass
class _StorageContext:
    docstore: _DocStore = field(default_factory=_DocStore)


class FusionMemoryCore:
    """Simple keyword-based local retrieval core."""

    def __init__(self, config: MemoryCoreConfig | None = None) -> None:
        self.config = config or MemoryCoreConfig()
        self.storage_context = _StorageContext()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_memory_nodes(self, nodes: list[MemoryNode]) -> int:
        accepted = 0
        for node in nodes:
            stability = node.metadata.get("memory_stability", "stable")
            if stability in _BLOCKED_STABILITIES:
                continue
            self.storage_context.docstore.documents[node.id] = node
            accepted += 1
        return accepted

    def ingest_bundle(self, bundle_dir: str | Path) -> int:
        nodes_file = Path(bundle_dir) / "MEMORY_NODES.json"
        if not nodes_file.exists():
            return 0
        raw = json.loads(nodes_file.read_text(encoding="utf-8"))
        nodes = [
            MemoryNode(
                id=n["id"],
                text=n["text"],
                metadata=n.get("metadata", {}),
                hash_value=n.get("hash_value", ""),
            )
            for n in raw
        ]
        return self.ingest_memory_nodes(nodes)

    # ------------------------------------------------------------------
    # Query — keyword BM25-lite (TF approximation)
    # ------------------------------------------------------------------

    def query(self, query: Any, *, top_k: int | None = None) -> MemoryQueryResult:
        if isinstance(query, str):
            query_text = query
            k = top_k or self.config.top_k
            filters = None
        else:
            query_text = getattr(query, "text", str(query))
            k = getattr(query, "top_k", top_k or self.config.top_k)
            filters = getattr(query, "filters", None)

        docs = self.storage_context.docstore.documents
        if not docs:
            return MemoryQueryResult(
                answer="Respuesta basada en memoria local: sin nodos disponibles.",
                source_nodes=[],
                audit={"nodes": 0, "query": query_text},
            )

        terms = query_text.lower().split()

        candidates: list[tuple[float, MemoryNode]] = []
        for node in docs.values():
            # Apply metadata filters
            if filters is not None:
                if not self._apply_filters(node, filters):
                    continue
            text_lower = node.text.lower()
            score = sum(text_lower.count(t) for t in terms)
            if score > 0:
                candidates.append((score, node))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top = candidates[:k]

        source_nodes = [
            SourceNode(
                node=MemoryNodeRef(id=n.id, text=n.text, metadata=n.metadata),
                score=float(s),
            )
            for s, n in top
        ]

        if not source_nodes:
            answer = "Respuesta basada en memoria local: sin resultados relevantes."
        else:
            snippet = top[0][1].text[:300]
            answer = f"Respuesta basada en memoria local: {snippet}..."

        return MemoryQueryResult(
            answer=answer,
            source_nodes=source_nodes,
            audit={"nodes": len(docs), "hits": len(source_nodes), "query": query_text},
        )

    def _apply_filters(self, node: MemoryNode, filters: Any) -> bool:
        for f in getattr(filters, "filters", []):
            key = f.key if hasattr(f, "key") else f[0]
            val = f.value if hasattr(f, "value") else f[1]
            op = str(getattr(f, "operator", "==")).lower()
            node_val = node.metadata.get(key)
            if op in {"eq", "=="}:
                if node_val != val:
                    return False
            elif op in {"ne", "!="}:
                if node_val == val:
                    return False
        return True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist(self, storage_path: str | Path) -> None:
        out = Path(storage_path)
        out.mkdir(parents=True, exist_ok=True)

        nodes_data = [
            {"id": n.id, "text": n.text, "metadata": n.metadata, "hash_value": n.hash_value}
            for n in self.storage_context.docstore.documents.values()
        ]
        (out / "memory_nodes.json").write_text(json.dumps(nodes_data, indent=2))

        audit = {
            "persisted_at": datetime.now(timezone.utc).isoformat(),
            "total_nodes": len(nodes_data),
            "config": {
                "chunk_size": self.config.chunk_size,
                "storage_path": str(self.config.storage_path),
            },
        }
        (out / "memory_core_audit.json").write_text(json.dumps(audit, indent=2))

    @classmethod
    def load(cls, storage_path: str | Path, config: MemoryCoreConfig | None = None) -> "FusionMemoryCore":
        p = Path(storage_path)
        core = cls(config=config)
        nodes_file = p / "memory_nodes.json"
        if nodes_file.exists():
            raw = json.loads(nodes_file.read_text(encoding="utf-8"))
            nodes = [
                MemoryNode(
                    id=n["id"],
                    text=n["text"],
                    metadata=n.get("metadata", {}),
                    hash_value=n.get("hash_value", ""),
                )
                for n in raw
            ]
            core.ingest_memory_nodes(nodes)
        return core
