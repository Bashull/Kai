"""TieredMemoryStore — Bloque 6 Ronda 2.

Patrón extraído de letta-ai/letta (MemGPT):
  Core Memory   = RAM activo (secciones etiquetadas, editable por el agente)
  Recall Memory = nodos de sesión actual (búsqueda rápida, no persistente)
  Archival Memory = índice completo persistente (chroma o fallback)

Mecánica interna documentada en docs/BLOQUE_6_RONDA_2_MECANICA_INTERNA.md §Repo 3.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ..schemas import MemoryNode
from .chroma_adapter import BaseVectorAdapter, make_adapter


# ---------------------------------------------------------------------------
# Core Memory — secciones etiquetadas en RAM (patrón letta BaseMemory)
# ---------------------------------------------------------------------------

@dataclass
class MemorySection:
    """Una sección de la Core Memory. Editable, con límite de caracteres."""
    name: str
    value: str = ""
    char_limit: int = 2000

    def append(self, text: str) -> None:
        combined = (self.value + "\n" + text).strip()
        if len(combined) > self.char_limit:
            raise ValueError(
                f"Core Memory '{self.name}' llena ({len(combined)}/{self.char_limit} chars). "
                "Flush a Recall antes de añadir más."
            )
        self.value = combined

    def replace(self, old: str, new: str) -> None:
        if old not in self.value:
            raise ValueError(f"Texto '{old[:40]}...' no encontrado en sección '{self.name}'.")
        self.value = self.value.replace(old, new, 1)

    def utilization(self) -> float:
        return len(self.value) / self.char_limit

    def __str__(self) -> str:
        return (
            f"<{self.name} chars={len(self.value)}/{self.char_limit}>\n"
            f"{self.value}\n"
            f"</{self.name}>"
        )


class CoreMemory:
    """Memoria activa en RAM. Secciones editables, char-limited.

    Secciones por defecto de FusionAI:
      identity       — quién es Kai (permanente)
      brain_state    — estado actual del cerebro
      active_context — contexto de la conversación/tarea actual
    """

    DEFAULT_SECTIONS = {
        "identity":       2000,
        "brain_state":    500,
        "active_context": 2000,
    }

    def __init__(self, sections: dict[str, int] | None = None) -> None:
        self._sections: dict[str, MemorySection] = {
            name: MemorySection(name=name, char_limit=limit)
            for name, limit in (sections or self.DEFAULT_SECTIONS).items()
        }

    def get(self, name: str) -> MemorySection:
        if name not in self._sections:
            raise KeyError(f"Sección '{name}' no existe en CoreMemory.")
        return self._sections[name]

    def set(self, name: str, value: str) -> None:
        section = self.get(name)
        if len(value) > section.char_limit:
            raise ValueError(f"Valor demasiado largo para sección '{name}'.")
        section.value = value

    def append(self, name: str, text: str) -> None:
        self.get(name).append(text)

    def replace(self, name: str, old: str, new: str) -> None:
        self.get(name).replace(old, new)

    def utilization_alert(self, threshold: float = 0.80) -> list[str]:
        """Devuelve secciones que superan el threshold de utilización."""
        return [
            name for name, s in self._sections.items()
            if s.utilization() > threshold
        ]

    def to_dict(self) -> dict[str, str]:
        return {name: s.value for name, s in self._sections.items()}

    def __str__(self) -> str:
        return "\n\n".join(str(s) for s in self._sections.values())

    def __iter__(self) -> Iterator[MemorySection]:
        return iter(self._sections.values())


# ---------------------------------------------------------------------------
# TieredMemoryStore — los 3 niveles
# ---------------------------------------------------------------------------

class TieredMemoryStore:
    """Implementa el modelo 3-tier de letta sobre FusionAI:

    Tier 1 — Core Memory (RAM):
      Secciones editables. Baja latencia. Editable por el BrainStateMachine.

    Tier 2 — Recall Memory (sesión):
      MemoryNodes de la sesión actual. Búsqueda BM25-lite. No persiste.
      Flush automático a Archival cuando supera el límite.

    Tier 3 — Archival Memory (persistente):
      ChromaVectorAdapter. HNSW semántico. Persiste entre sesiones.
      Acceso más lento — activar cuando BrainState lo requiera.
    """

    RECALL_MAX = 200  # nodos máximos en Recall antes de flush a Archival

    def __init__(
        self,
        archival_adapter: BaseVectorAdapter | None = None,
        persist_path: str | Path = "./data/chroma",
        core_sections: dict[str, int] | None = None,
    ) -> None:
        self.core = CoreMemory(sections=core_sections)
        self._recall: list[MemoryNode] = []
        self.archival: BaseVectorAdapter = archival_adapter or make_adapter(path=persist_path)
        self._session_start = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, node: MemoryNode, *, tier: str = "recall") -> str:
        """Ingesta un nodo en el tier especificado.

        tier = "core"     → actualiza active_context
        tier = "recall"   → añade a la sesión actual (default)
        tier = "archival" → persiste directamente
        """
        if tier == "core":
            self.core.append("active_context", node.text[:200])
            return node.id
        elif tier == "archival":
            self.archival.upsert([node])
            return node.id
        else:  # recall (default)
            self._recall.append(node)
            if len(self._recall) >= self.RECALL_MAX:
                self._flush_recall_to_archival()
            return node.id

    def ingest_many(self, nodes: list[MemoryNode], *, tier: str = "recall") -> list[str]:
        return [self.ingest(node, tier=tier) for node in nodes]

    def _flush_recall_to_archival(self) -> int:
        """Mueve todos los nodos de Recall a Archival. Limpia Recall."""
        if not self._recall:
            return 0
        self.archival.upsert(self._recall)
        flushed = len(self._recall)
        self._recall.clear()
        return flushed

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_recall(self, query: str, top_k: int = 10) -> list[MemoryNode]:
        """Búsqueda BM25-lite en la sesión actual (Tier 2)."""
        terms = set(query.lower().split())
        scored = [
            (sum(n.text.lower().count(t) for t in terms), n)
            for n in self._recall
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for s, n in scored if s > 0][:top_k]

    def query_archival(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[MemoryNode]:
        """Búsqueda semántica en el índice completo persistente (Tier 3)."""
        return self.archival.search(query, top_k=top_k, filters=filters)

    def query(
        self,
        query: str,
        top_k: int = 10,
        *,
        tiers: list[str] | None = None,
        filters: dict | None = None,
    ) -> list[MemoryNode]:
        """Búsqueda combinada. tiers=['recall','archival'] por defecto."""
        active_tiers = tiers or ["recall", "archival"]
        results: list[MemoryNode] = []

        if "recall" in active_tiers:
            results.extend(self.query_recall(query, top_k=top_k))
        if "archival" in active_tiers:
            results.extend(self.query_archival(query, top_k=top_k, filters=filters))

        # Dedup por id
        seen: set[str] = set()
        deduped: list[MemoryNode] = []
        for n in results:
            if n.id not in seen:
                seen.add(n.id)
                deduped.append(n)

        return deduped[:top_k]

    # ------------------------------------------------------------------
    # Persistence (patrón Context Repository de letta — git-like commits)
    # ------------------------------------------------------------------

    def commit(self, message: str = "") -> str:
        """Flush Recall → Archival y devuelve un hash del estado actual.

        Inspirado en el Context Repository de letta (2026):
        cada commit es un snapshot verificable del estado de memoria.
        """
        flushed = self._flush_recall_to_archival()
        snapshot = json.dumps({
            "core": self.core.to_dict(),
            "session_start": self._session_start,
            "recall_flushed": flushed,
            "archival_count": self.archival.count(),
            "message": message,
        }, sort_keys=True)
        commit_hash = hashlib.sha256(snapshot.encode()).hexdigest()[:16]
        return commit_hash

    @property
    def stats(self) -> dict:
        return {
            "core_sections": {s.name: f"{len(s.value)}/{s.char_limit}" for s in self.core},
            "recall_nodes": len(self._recall),
            "archival_nodes": self.archival.count(),
            "session_start": self._session_start,
        }
