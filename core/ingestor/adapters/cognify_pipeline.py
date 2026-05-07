"""CognifyPipeline + TemporalMemoryNode — Bloque 6 Ronda 2.

Patrón extraído de topoteretes/cognee:
  - Pipeline ECL composable (Extract, Cognify, Load)
  - Tasks encadenadas: output de una = input de la siguiente
  - TemporalMemoryNode: timestamp + decay_factor + validity window
  - Deduplicación 2 capas: content-hash (add) + pipeline-status (cognify)

Mecánica interna documentada en docs/BLOQUE_6_RONDA_2_MECANICA_INTERNA.md §Repo 4.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from ..schemas import MemoryNode


# ---------------------------------------------------------------------------
# TemporalMemoryNode — temporal cognification (cognee 2026)
# ---------------------------------------------------------------------------

@dataclass
class TemporalMemoryNode:
    """MemoryNode con dimensión temporal.

    decay_factor: cuánto decae el score por día de antigüedad.
      1.0 = sin decay, 0.95 = pierde 5% de relevancia por día.

    validity window: si expires_at es past → nodo inválido.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    metadata: dict = field(default_factory=dict)
    hash_value: str = ""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    decay_factor: float = 1.0

    def __post_init__(self) -> None:
        if not self.hash_value:
            self.hash_value = hashlib.sha256(self.text.encode()).hexdigest()

    @property
    def is_valid(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def age_days(self) -> float:
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.total_seconds() / 86400

    def effective_score(self, base_score: float) -> float:
        """Aplica decay temporal al score base."""
        return base_score * (self.decay_factor ** self.age_days)

    def to_memory_node(self) -> MemoryNode:
        meta = {
            **self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "decay_factor": self.decay_factor,
            "is_valid": self.is_valid,
        }
        return MemoryNode(id=self.id, text=self.text, metadata=meta, hash_value=self.hash_value)

    @classmethod
    def from_memory_node(
        cls,
        node: MemoryNode,
        *,
        decay_factor: float = 1.0,
        ttl_days: int | None = None,
    ) -> "TemporalMemoryNode":
        expires_at = None
        if ttl_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        return cls(
            id=node.id,
            text=node.text,
            metadata=node.metadata,
            hash_value=node.hash_value,
            decay_factor=decay_factor,
            expires_at=expires_at,
        )


# ---------------------------------------------------------------------------
# Pipeline composable — patrón cognee ECL
# ---------------------------------------------------------------------------

@dataclass
class PipelineData:
    """Contenedor que fluye entre tasks del pipeline."""
    nodes: list[MemoryNode]
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)   # ids que se saltaron
    errors: list[str] = field(default_factory=list)    # errores no fatales


@dataclass
class PipelineTask:
    name: str
    fn: Callable[[PipelineData], PipelineData]
    skip_on_error: bool = False


class CognifyPipeline:
    """Pipeline ECL composable inspirado en cognee.

    Uso básico:
        pipeline = CognifyPipeline()
        pipeline.add_task("hash_check", hash_check_fn)
        pipeline.add_task("embed",      embed_fn, skip_on_error=True)
        pipeline.add_task("index",      index_fn)
        result = pipeline.run(PipelineData(nodes=my_nodes))

    Tasks predefinidas disponibles como métodos estáticos:
        CognifyPipeline.task_hash_dedup(existing_hashes)
        CognifyPipeline.task_filter_valid_temporal()
        CognifyPipeline.task_add_timestamps()
        CognifyPipeline.task_enrich_metadata(extra)
    """

    def __init__(self, name: str = "fusion_cognify") -> None:
        self.name = name
        self._tasks: list[PipelineTask] = []
        self._status: dict[str, str] = {}  # node_hash → "completed" | "skipped"

    def add_task(
        self,
        name: str,
        fn: Callable[[PipelineData], PipelineData],
        *,
        skip_on_error: bool = False,
    ) -> "CognifyPipeline":
        self._tasks.append(PipelineTask(name=name, fn=fn, skip_on_error=skip_on_error))
        return self

    def run(self, data: PipelineData) -> PipelineData:
        """Ejecuta las tasks en orden. Cada task recibe el PipelineData del anterior."""
        for task in self._tasks:
            try:
                data = task.fn(data)
            except Exception as exc:
                if task.skip_on_error:
                    data.errors.append(f"[{task.name}] {exc}")
                else:
                    raise RuntimeError(f"Pipeline '{self.name}' falló en task '{task.name}': {exc}") from exc
        return data

    # ------------------------------------------------------------------
    # Tasks predefinidas (building blocks)
    # ------------------------------------------------------------------

    @staticmethod
    def task_hash_dedup(existing_hashes: set[str]) -> Callable[[PipelineData], PipelineData]:
        """Layer 1 dedup: descarta nodos cuyo hash ya existe."""
        def _fn(data: PipelineData) -> PipelineData:
            new_nodes = []
            for node in data.nodes:
                if node.hash_value in existing_hashes:
                    data.skipped.append(node.id)
                else:
                    new_nodes.append(node)
                    if node.hash_value:
                        existing_hashes.add(node.hash_value)
            data.nodes = new_nodes
            return data
        return _fn

    @staticmethod
    def task_filter_valid_temporal() -> Callable[[PipelineData], PipelineData]:
        """Descarta nodos TemporalMemoryNode expirados."""
        def _fn(data: PipelineData) -> PipelineData:
            valid = []
            for node in data.nodes:
                expires_at_str = node.metadata.get("expires_at")
                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if datetime.now(timezone.utc) > expires_at:
                            data.skipped.append(node.id)
                            continue
                    except (ValueError, TypeError):
                        pass
                valid.append(node)
            data.nodes = valid
            return data
        return _fn

    @staticmethod
    def task_add_timestamps(
        decay_factor: float = 1.0,
        ttl_days: int | None = None,
    ) -> Callable[[PipelineData], PipelineData]:
        """Añade created_at, decay_factor y expires_at a la metadata."""
        def _fn(data: PipelineData) -> PipelineData:
            now = datetime.now(timezone.utc).isoformat()
            expires = None
            if ttl_days is not None:
                expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat()

            for node in data.nodes:
                node.metadata.setdefault("created_at", now)
                node.metadata.setdefault("decay_factor", decay_factor)
                if expires:
                    node.metadata.setdefault("expires_at", expires)
            return data
        return _fn

    @staticmethod
    def task_enrich_metadata(extra: dict) -> Callable[[PipelineData], PipelineData]:
        """Añade campos fijos a la metadata de todos los nodos."""
        def _fn(data: PipelineData) -> PipelineData:
            for node in data.nodes:
                for k, v in extra.items():
                    node.metadata.setdefault(k, v)
            return data
        return _fn

    @staticmethod
    def task_extract_light_graph() -> Callable[[PipelineData], PipelineData]:
        """Extracción ligera de entidades sin LLM (regex-based).

        Alternativa al task_extract_graph de cognee que requiere LLM call.
        Detecta: nombres propios (CamelCase), URLs, siglas.
        """
        _CAMEL = re.compile(r'\b[A-Z][a-zA-Z]{2,}\b')
        _SIGLA = re.compile(r'\b[A-Z]{2,5}\b')

        def _fn(data: PipelineData) -> PipelineData:
            for node in data.nodes:
                entities = list(set(
                    _CAMEL.findall(node.text) + _SIGLA.findall(node.text)
                ))[:10]  # max 10 entidades por nodo
                if entities:
                    existing = node.metadata.get("entities", [])
                    if isinstance(existing, str):
                        existing = json.loads(existing)
                    node.metadata["entities"] = json.dumps(list(set(existing + entities)))
            return data
        return _fn


# ---------------------------------------------------------------------------
# Factory: standard FusionAI cognify pipeline
# ---------------------------------------------------------------------------

def make_fusion_cognify_pipeline(
    existing_hashes: set[str] | None = None,
    source_tag: str = "fusion",
    decay_factor: float = 1.0,
    ttl_days: int | None = None,
    extract_entities: bool = True,
) -> CognifyPipeline:
    """Pipeline estándar FusionAI listo para usar.

    Tasks:
      1. hash_dedup        — Layer 1: descarta duplicados exactos
      2. filter_temporal   — descarta nodos expirados
      3. add_timestamps    — añade created_at, decay, expires
      4. enrich_metadata   — añade source, type
      5. extract_entities  — extracción regex de entidades (opcional, sin LLM)
    """
    pipeline = CognifyPipeline(name="fusion_cognify")
    pipeline.add_task(
        "hash_dedup",
        CognifyPipeline.task_hash_dedup(existing_hashes or set()),
    )
    pipeline.add_task(
        "filter_temporal",
        CognifyPipeline.task_filter_valid_temporal(),
    )
    pipeline.add_task(
        "add_timestamps",
        CognifyPipeline.task_add_timestamps(decay_factor=decay_factor, ttl_days=ttl_days),
    )
    pipeline.add_task(
        "enrich_metadata",
        CognifyPipeline.task_enrich_metadata({"source": source_tag, "type": "fusion_node"}),
    )
    if extract_entities:
        pipeline.add_task(
            "extract_entities",
            CognifyPipeline.task_extract_light_graph(),
            skip_on_error=True,
        )
    return pipeline
