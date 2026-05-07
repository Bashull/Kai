"""ChromaVectorAdapter — Bloque 6 Ronda 2 · patrón extraído de chroma-core/chroma.

Wraps chromadb.PersistentClient con la interfaz BaseVectorAdapter.
Funciona 100% local sin servicios externos. Si chromadb no está instalado,
levanta ImportError con instrucción clara.

Mecánica interna documentada en docs/BLOQUE_6_RONDA_2_MECANICA_INTERNA.md §Repo 2.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..schemas import MemoryNode


# ---------------------------------------------------------------------------
# Contract: BaseVectorAdapter
# ---------------------------------------------------------------------------

class BaseVectorAdapter(ABC):
    """Interfaz mínima extraída de mem0 + chroma. Todos los adapters la implementan."""

    @abstractmethod
    def upsert(self, nodes: list[MemoryNode]) -> list[str]:
        """Inserta o actualiza nodos. Devuelve lista de ids procesados."""

    @abstractmethod
    def search(self, query: str, *, top_k: int = 10, filters: dict | None = None) -> list[MemoryNode]:
        """Búsqueda semántica. filters = chroma where-clause o equivalente."""

    @abstractmethod
    def delete(self, node_id: str) -> None:
        """Elimina un nodo del índice."""

    @abstractmethod
    def count(self) -> int:
        """Número de nodos en el índice."""

    def persist(self) -> None:
        """Flush a disco si el backend lo requiere. Default: no-op (chroma auto-persiste)."""

    def load(self) -> None:
        """Carga desde disco. Default: no-op (chroma carga lazy)."""


# ---------------------------------------------------------------------------
# ChromaVectorAdapter
# ---------------------------------------------------------------------------

class ChromaVectorAdapter(BaseVectorAdapter):
    """Adapter sobre chroma PersistentClient.

    Parámetros HNSW (de la mecánica interna de chroma):
      hnsw:space          = "cosine"  → distancia [0, 2], optimizada para texto
      hnsw:construction_ef = 200      → calidad del índice (más alto = mejor recall)
      hnsw:search_ef       = 100      → calidad en búsqueda
      hnsw:M               = 16       → conexiones por nodo en el grafo HNSW

    Estructura de disco:
      <path>/chroma.sqlite3          — metadata de colecciones
      <path>/<uuid>/data_level0.bin  — embeddings raw
      <path>/<uuid>/index_metadata.pkl
      <path>/<uuid>/link_lists.bin   — grafo HNSW
    """

    DEFAULT_COLLECTION = "fusion_memory"
    DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # ~90MB, muy rápido

    def __init__(
        self,
        path: str | Path = "./data/chroma",
        collection_name: str = DEFAULT_COLLECTION,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        hnsw_space: str = "cosine",
    ) -> None:
        self._path = Path(path)
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._hnsw_space = hnsw_space
        self._client = None
        self._collection = None

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError as exc:
            raise ImportError(
                "chromadb no está instalado. Ejecuta: pip install chromadb"
            ) from exc

        self._path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._path))

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self._embedding_model
        )
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            embedding_function=ef,
            metadata={
                "hnsw:space":            self._hnsw_space,
                "hnsw:construction_ef":  200,
                "hnsw:search_ef":        100,
                "hnsw:M":                16,
                "hnsw:batch_size":       100,
            },
        )

    # ------------------------------------------------------------------
    # BaseVectorAdapter implementation
    # ------------------------------------------------------------------

    def upsert(self, nodes: list[MemoryNode]) -> list[str]:
        self._ensure_client()
        if not nodes:
            return []

        ids = [n.id for n in nodes]
        documents = [n.text for n in nodes]
        metadatas = [self._serialize_metadata(n.metadata) for n in nodes]

        # chroma upsert: si el id ya existe lo actualiza; si no, lo inserta.
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        return ids

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[MemoryNode]:
        self._ensure_client()

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(top_k, max(1, self.count())),
        }
        if filters:
            kwargs["where"] = filters

        results = self._collection.query(**kwargs)

        nodes: list[MemoryNode] = []
        for i, node_id in enumerate(results["ids"][0]):
            text = results["documents"][0][i]
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0.0
            nodes.append(MemoryNode(
                id=node_id,
                text=text,
                metadata={**meta, "_distance": round(distance, 4)},
            ))
        return nodes

    def delete(self, node_id: str) -> None:
        self._ensure_client()
        self._collection.delete(ids=[node_id])

    def count(self) -> int:
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _serialize_metadata(self, metadata: dict) -> dict:
        """chroma solo acepta str/int/float/bool en metadata — serializa el resto."""
        clean: dict = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif isinstance(v, list):
                clean[k] = json.dumps(v)
            else:
                clean[k] = str(v)
        return clean


# ---------------------------------------------------------------------------
# FallbackAdapter — keyword BM25-lite para tests sin chromadb
# ---------------------------------------------------------------------------

class FallbackInMemoryAdapter(BaseVectorAdapter):
    """BM25-lite adapter para tests sin chromadb instalado.

    Mantiene los nodos en un dict en RAM. No persiste. Usado en CI.
    """

    def __init__(self) -> None:
        self._store: dict[str, MemoryNode] = {}

    def upsert(self, nodes: list[MemoryNode]) -> list[str]:
        for node in nodes:
            self._store[node.id] = node
        return [n.id for n in nodes]

    def search(self, query: str, *, top_k: int = 10, filters: dict | None = None) -> list[MemoryNode]:
        terms = query.lower().split()
        scored: list[tuple[float, MemoryNode]] = []
        for node in self._store.values():
            text_lower = node.text.lower()
            score = sum(text_lower.count(t) for t in terms)
            if score > 0:
                scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [n for _, n in scored[:top_k]]

    def delete(self, node_id: str) -> None:
        self._store.pop(node_id, None)

    def count(self) -> int:
        return len(self._store)


def make_adapter(
    path: str | Path = "./data/chroma",
    collection_name: str = ChromaVectorAdapter.DEFAULT_COLLECTION,
    *,
    fallback_if_no_chroma: bool = True,
) -> BaseVectorAdapter:
    """Factory: devuelve ChromaVectorAdapter si chroma está instalado, FallbackInMemoryAdapter si no."""
    try:
        import chromadb  # noqa: F401
        return ChromaVectorAdapter(path=path, collection_name=collection_name)
    except ImportError:
        if fallback_if_no_chroma:
            return FallbackInMemoryAdapter()
        raise
