"""DeduplicationEngine + HybridQueryEngine — Bloque 6 Ronda 2.

Patrón extraído de mem0ai/mem0:
  - A.U.D.N. simplificado (sin LLM call): ADD / NOOP por hash + cosine
  - HybridQueryEngine: 3 señales (semantic + BM25 + entity boost)

Mecánica interna documentada en docs/BLOQUE_6_RONDA_2_MECANICA_INTERNA.md §Repo 1.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from ..schemas import MemoryNode


# ---------------------------------------------------------------------------
# A.U.D.N. action (simplificado — sin LLM call para UPDATE/DELETE)
# ---------------------------------------------------------------------------

class AUDNAction(Enum):
    ADD  = "add"   # nuevo nodo — insertar
    NOOP = "noop"  # duplicado exacto o demasiado similar — ignorar


@dataclass
class DeduplicationResult:
    action: AUDNAction
    node: MemoryNode
    duplicate_id: str | None = None   # id del nodo existente si NOOP
    similarity: float = 0.0           # cosine similarity con el más cercano


# ---------------------------------------------------------------------------
# DeduplicationEngine
# ---------------------------------------------------------------------------

class DeduplicationEngine:
    """Layer 1: SHA-256 exact match.
    Layer 2: cosine similarity (si embeddings disponibles) o BM25-lite (fallback).

    Decisión: simplificamos el A.U.D.N. de mem0 → solo ADD / NOOP.
    UPDATE y DELETE son operaciones manuales explícitas, no automáticas.
    Esto evita LLM calls por cada candidate.
    """

    def __init__(self, cosine_threshold: float = 0.95) -> None:
        self.cosine_threshold = cosine_threshold

    def check(
        self,
        node: MemoryNode,
        existing: Sequence[MemoryNode],
        *,
        use_embeddings: bool = False,
    ) -> DeduplicationResult:
        """Determina si `node` debe añadirse o descartarse como duplicado."""

        # Layer 1: exact SHA-256 hash match
        for existing_node in existing:
            if existing_node.hash_value and node.hash_value:
                if existing_node.hash_value == node.hash_value:
                    return DeduplicationResult(
                        action=AUDNAction.NOOP,
                        node=node,
                        duplicate_id=existing_node.id,
                        similarity=1.0,
                    )

        # Layer 2: cosine similarity (embeddings) o BM25-lite (fallback)
        if use_embeddings:
            best_id, best_sim = self._cosine_search(node, existing)
        else:
            best_id, best_sim = self._bm25_lite_similarity(node, existing)

        if best_sim >= self.cosine_threshold:
            return DeduplicationResult(
                action=AUDNAction.NOOP,
                node=node,
                duplicate_id=best_id,
                similarity=best_sim,
            )

        return DeduplicationResult(action=AUDNAction.ADD, node=node, similarity=best_sim)

    def filter_batch(
        self,
        nodes: list[MemoryNode],
        existing: Sequence[MemoryNode],
    ) -> list[MemoryNode]:
        """Filtra una lista de nodos nuevos, devolviendo solo los que deben insertarse."""
        seen_hashes: set[str] = {n.hash_value for n in existing if n.hash_value}
        to_add: list[MemoryNode] = []

        for node in nodes:
            # Fast path: hash ya visto en este batch o en existing
            if node.hash_value and node.hash_value in seen_hashes:
                continue
            result = self.check(node, list(existing) + to_add)
            if result.action == AUDNAction.ADD:
                to_add.append(node)
                if node.hash_value:
                    seen_hashes.add(node.hash_value)

        return to_add

    # ------------------------------------------------------------------
    # Similarity helpers
    # ------------------------------------------------------------------

    def _cosine_search(
        self, node: MemoryNode, existing: Sequence[MemoryNode]
    ) -> tuple[str | None, float]:
        """Busca el nodo más similar usando embeddings almacenados en metadata."""
        node_emb = node.metadata.get("_embedding")
        if not node_emb or not existing:
            return None, 0.0

        best_id, best_sim = None, 0.0
        for e in existing:
            e_emb = e.metadata.get("_embedding")
            if e_emb:
                sim = _cosine(node_emb, e_emb)
                if sim > best_sim:
                    best_sim, best_id = sim, e.id
        return best_id, best_sim

    def _bm25_lite_similarity(
        self, node: MemoryNode, existing: Sequence[MemoryNode]
    ) -> tuple[str | None, float]:
        """BM25-lite: Jaccard sobre tokens normalizados como proxy de similitud."""
        if not existing:
            return None, 0.0

        node_tokens = _tokenize(node.text)
        if not node_tokens:
            return None, 0.0

        best_id, best_sim = None, 0.0
        for e in existing:
            e_tokens = _tokenize(e.text)
            if not e_tokens:
                continue
            sim = _jaccard(node_tokens, e_tokens)
            if sim > best_sim:
                best_sim, best_id = sim, e.id

        return best_id, best_sim


# ---------------------------------------------------------------------------
# HybridQueryEngine — patrón mem0 3 señales
# ---------------------------------------------------------------------------

@dataclass
class HybridSearchResult:
    node: MemoryNode
    score_semantic: float = 0.0
    score_bm25: float = 0.0
    score_entity: float = 0.0
    score_final: float = field(init=False)

    def __post_init__(self) -> None:
        self.score_final = self.score_semantic  # se recalcula con compute()

    def compute(self, alpha: float = 0.7, beta: float = 0.2, gamma: float = 0.1) -> "HybridSearchResult":
        self.score_final = (
            alpha * self.score_semantic +
            beta  * self.score_bm25 +
            gamma * self.score_entity
        )
        return self


class HybridQueryEngine:
    """Búsqueda híbrida: semantic + BM25 + entity boost.

    Pesos por defecto (mem0 defaults):
      alpha = 0.70  (semántica)
      beta  = 0.20  (BM25 keyword)
      gamma = 0.10  (entity boost)

    Si no hay embeddings disponibles, usa solo BM25 (alpha→0, beta→1).
    """

    def __init__(
        self,
        alpha: float = 0.7,
        beta: float = 0.2,
        gamma: float = 0.1,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def search(
        self,
        query: str,
        corpus: Sequence[MemoryNode],
        *,
        top_k: int = 10,
        entity_hints: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Busca en corpus con las 3 señales combinadas."""
        if not corpus:
            return []

        query_tokens = _tokenize(query)
        entity_set = {e.lower() for e in (entity_hints or [])}

        results: list[HybridSearchResult] = []
        for node in corpus:
            # Signal B: BM25-lite
            score_b = _bm25_score(query_tokens, node.text)

            # Signal C: entity boost
            score_e = 0.0
            if entity_set:
                node_text_lower = node.text.lower()
                hits = sum(1 for e in entity_set if e in node_text_lower)
                score_e = min(1.0, hits / max(1, len(entity_set)))

            # Signal A: semantic (usa _distance de chroma si disponible)
            raw_dist = node.metadata.get("_distance", None)
            if raw_dist is not None:
                # chroma cosine distance [0, 2] → similarity [0, 1]
                score_a = max(0.0, 1.0 - raw_dist / 2.0)
            else:
                # fallback: BM25 normalizado como proxy semántico
                score_a = score_b

            result = HybridSearchResult(
                node=node,
                score_semantic=score_a,
                score_bm25=score_b,
                score_entity=score_e,
            ).compute(self.alpha, self.beta, self.gamma)

            if result.score_final > 0:
                results.append(result)

        results.sort(key=lambda r: r.score_final, reverse=True)
        return results[:top_k]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    "el la los las un una de del en y a es que se con para por al"
    " como no lo su sus pero si más ya".split()
)


def _tokenize(text: str) -> set[str]:
    words = re.findall(r'\b\w+\b', text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _bm25_score(query_tokens: set[str], doc_text: str, k1: float = 1.5, b: float = 0.75) -> float:
    """BM25-lite sin IDF (single-doc). Normalizado a [0,1]."""
    if not query_tokens:
        return 0.0
    words = re.findall(r'\b\w+\b', doc_text.lower())
    doc_len = len(words)
    if doc_len == 0:
        return 0.0
    avg_len = 100.0  # estimación fija razonable para nodos de memoria
    tf_map: dict[str, int] = {}
    for w in words:
        tf_map[w] = tf_map.get(w, 0) + 1

    score = 0.0
    for term in query_tokens:
        tf = tf_map.get(term, 0)
        if tf == 0:
            continue
        score += (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))

    # Normalizar a [0,1] aproximado
    return min(1.0, score / (len(query_tokens) * (k1 + 1)))


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
