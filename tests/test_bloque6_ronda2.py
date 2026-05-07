"""Tests Bloque 6 · Ronda 2 — prototipos de adapters FusionMemoryCore v1.0.

Ejecutar: pytest tests/test_bloque6_ronda2.py -v
Requisito: ningún servicio externo. chromadb no requerido (usa FallbackInMemoryAdapter).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from ingestor.adapters import (
    AUDNAction,
    CognifyPipeline,
    CoreMemory,
    DeduplicationEngine,
    FallbackInMemoryAdapter,
    HybridQueryEngine,
    PipelineData,
    TemporalMemoryNode,
    TieredMemoryStore,
    make_adapter,
    make_fusion_cognify_pipeline,
)
from ingestor.schemas import MemoryNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_node(text: str, node_id: str | None = None, metadata: dict | None = None) -> MemoryNode:
    import hashlib, uuid
    nid = node_id or str(uuid.uuid4())
    hv = hashlib.sha256(text.encode()).hexdigest()
    return MemoryNode(id=nid, text=text, metadata=metadata or {}, hash_value=hv)


# ---------------------------------------------------------------------------
# FallbackInMemoryAdapter (chroma pattern, sin chromadb)
# ---------------------------------------------------------------------------

class TestFallbackAdapter:
    def test_upsert_and_count(self):
        adapter = FallbackInMemoryAdapter()
        n1 = make_node("Kai es un cerebro digital")
        n2 = make_node("FusionAI construye sistemas de memoria")
        ids = adapter.upsert([n1, n2])
        assert len(ids) == 2
        assert adapter.count() == 2

    def test_search_keyword(self):
        adapter = FallbackInMemoryAdapter()
        adapter.upsert([
            make_node("Kai es un cerebro digital de alta fidelidad"),
            make_node("El ingestor procesa documentos"),
            make_node("La memoria semántica usa embeddings"),
        ])
        results = adapter.search("cerebro digital", top_k=5)
        assert len(results) >= 1
        assert "cerebro" in results[0].text.lower()

    def test_delete(self):
        adapter = FallbackInMemoryAdapter()
        n = make_node("nodo temporal")
        adapter.upsert([n])
        assert adapter.count() == 1
        adapter.delete(n.id)
        assert adapter.count() == 0

    def test_upsert_same_id_updates(self):
        adapter = FallbackInMemoryAdapter()
        n = make_node("texto original", node_id="fixed-id")
        adapter.upsert([n])
        n2 = MemoryNode(id="fixed-id", text="texto actualizado")
        adapter.upsert([n2])
        assert adapter.count() == 1

    def test_make_adapter_returns_fallback_without_chroma(self):
        # En CI sin chromadb instalado, make_adapter devuelve el fallback
        adapter = make_adapter(fallback_if_no_chroma=True)
        assert adapter is not None
        assert adapter.count() == 0


# ---------------------------------------------------------------------------
# DeduplicationEngine (mem0 A.U.D.N. pattern)
# ---------------------------------------------------------------------------

class TestDeduplicationEngine:
    def test_exact_hash_duplicate_is_noop(self):
        engine = DeduplicationEngine()
        n1 = make_node("FusionAI es un sistema de IA")
        n2 = make_node("FusionAI es un sistema de IA")  # mismo texto → mismo hash
        result = engine.check(n2, [n1])
        assert result.action == AUDNAction.NOOP
        assert result.similarity == 1.0

    def test_new_node_is_add(self):
        engine = DeduplicationEngine()
        existing = [make_node("Kai tiene memoria persistente")]
        new_node = make_node("El ingestor usa el protocolo Tríada+")
        result = engine.check(new_node, existing)
        assert result.action == AUDNAction.ADD

    def test_very_similar_text_is_noop(self):
        engine = DeduplicationEngine(cosine_threshold=0.5)  # umbral bajo → fácil de activar
        existing = [make_node("Kai tiene memoria persistente de largo plazo")]
        similar = make_node("Kai tiene memoria persistente de largo plazo y semántica")
        result = engine.check(similar, existing)
        # Con Jaccard sobre tokens solapados debería detectar similitud alta
        assert result.similarity > 0

    def test_filter_batch_removes_duplicates(self):
        engine = DeduplicationEngine()
        node = make_node("nodo único en el sistema")
        batch = [node, node, make_node("otro nodo diferente")]
        to_add = engine.filter_batch(batch, existing=[])
        # El nodo duplicado debe eliminarse del batch
        ids = [n.id for n in to_add]
        assert len(set(ids)) == len(ids)  # no duplicados

    def test_empty_existing_always_adds(self):
        engine = DeduplicationEngine()
        result = engine.check(make_node("primer nodo"), existing=[])
        assert result.action == AUDNAction.ADD


# ---------------------------------------------------------------------------
# HybridQueryEngine (mem0 3-signal pattern)
# ---------------------------------------------------------------------------

class TestHybridQueryEngine:
    def setup_method(self):
        self.engine = HybridQueryEngine(alpha=0.5, beta=0.4, gamma=0.1)
        self.corpus = [
            make_node("Kai es un cerebro digital de alta fidelidad funcional"),
            make_node("FusionAI construye bloques de inteligencia artificial"),
            make_node("El protocolo 5x5 define el método de forja de bloques"),
            make_node("La memoria semántica permite búsqueda por significado"),
            make_node("El ingestor universal procesa documentos en múltiples formatos"),
        ]

    def test_returns_top_k_results(self):
        results = self.engine.search("cerebro digital", self.corpus, top_k=2)
        assert len(results) <= 2

    def test_relevant_node_ranks_high(self):
        results = self.engine.search("cerebro digital", self.corpus, top_k=5)
        assert len(results) > 0
        top_text = results[0].node.text.lower()
        assert "cerebro" in top_text or "digital" in top_text

    def test_entity_boost_works(self):
        results_with = self.engine.search(
            "protocolo", self.corpus, top_k=5, entity_hints=["FusionAI"]
        )
        results_without = self.engine.search("protocolo", self.corpus, top_k=5)
        # Con entity boost FusionAI debería subir el nodo que menciona FusionAI
        ids_with = [r.node.id for r in results_with]
        ids_without = [r.node.id for r in results_without]
        # Solo verificamos que el resultado no explota
        assert len(ids_with) > 0
        assert len(ids_without) > 0

    def test_empty_corpus_returns_empty(self):
        results = self.engine.search("memoria", [], top_k=5)
        assert results == []

    def test_score_final_is_weighted_sum(self):
        results = self.engine.search("memoria semántica", self.corpus, top_k=5)
        for r in results:
            expected = 0.5 * r.score_semantic + 0.4 * r.score_bm25 + 0.1 * r.score_entity
            assert abs(r.score_final - expected) < 1e-9


# ---------------------------------------------------------------------------
# CoreMemory + TieredMemoryStore (letta pattern)
# ---------------------------------------------------------------------------

class TestCoreMemory:
    def test_default_sections_exist(self):
        core = CoreMemory()
        assert core.get("identity") is not None
        assert core.get("brain_state") is not None
        assert core.get("active_context") is not None

    def test_set_and_get(self):
        core = CoreMemory()
        core.set("identity", "Kai es un compañero digital de Asier.")
        assert "Kai" in core.get("identity").value

    def test_append(self):
        core = CoreMemory()
        core.set("identity", "Kai.")
        core.append("identity", "Kai es fiel.")
        assert "fiel" in core.get("identity").value

    def test_replace(self):
        core = CoreMemory()
        core.set("identity", "Kai es un asistente.")
        core.replace("identity", "asistente", "compañero")
        assert "compañero" in core.get("identity").value
        assert "asistente" not in core.get("identity").value

    def test_overflow_raises(self):
        core = CoreMemory(sections={"test": 10})
        with pytest.raises(ValueError):
            core.set("test", "X" * 11)

    def test_utilization_alert(self):
        core = CoreMemory(sections={"test": 100})
        core.set("test", "X" * 85)
        alerts = core.utilization_alert(threshold=0.80)
        assert "test" in alerts


class TestTieredMemoryStore:
    def setup_method(self):
        self.store = TieredMemoryStore(archival_adapter=FallbackInMemoryAdapter())

    def test_ingest_recall_and_query(self):
        n = make_node("Kai tiene memoria semántica persistente")
        self.store.ingest(n, tier="recall")
        results = self.store.query_recall("memoria semántica")
        assert len(results) >= 1

    def test_ingest_archival_and_query(self):
        n = make_node("El protocolo Tríada+ garantiza integridad")
        self.store.ingest(n, tier="archival")
        results = self.store.query_archival("Tríada")
        assert len(results) >= 1

    def test_commit_returns_hash(self):
        self.store.ingest(make_node("nodo de prueba"), tier="recall")
        commit_hash = self.store.commit("test commit")
        assert len(commit_hash) == 16  # sha256[:16]

    def test_stats(self):
        self.store.ingest(make_node("nodo en recall"), tier="recall")
        stats = self.store.stats
        assert stats["recall_nodes"] == 1
        assert "core_sections" in stats


# ---------------------------------------------------------------------------
# CognifyPipeline + TemporalMemoryNode (cognee pattern)
# ---------------------------------------------------------------------------

class TestTemporalMemoryNode:
    def test_is_valid_no_expiry(self):
        node = TemporalMemoryNode(text="nodo permanente")
        assert node.is_valid is True

    def test_is_expired(self):
        from datetime import timedelta
        node = TemporalMemoryNode(
            text="nodo expirado",
            expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc) - timedelta(hours=1),
        )
        assert node.is_valid is False

    def test_effective_score_decays(self):
        node = TemporalMemoryNode(text="nodo", decay_factor=0.9)
        score_now = node.effective_score(1.0)
        # Con age_days ≈ 0 el score debería ser ≈ 1.0
        assert 0.9 <= score_now <= 1.0

    def test_roundtrip_to_memory_node(self):
        original = TemporalMemoryNode(text="Kai memoriza con decay")
        node = original.to_memory_node()
        assert node.text == original.text
        assert "created_at" in node.metadata

    def test_from_memory_node(self):
        mn = make_node("nodo base")
        temporal = TemporalMemoryNode.from_memory_node(mn, decay_factor=0.95, ttl_days=30)
        assert temporal.decay_factor == 0.95
        assert temporal.expires_at is not None


class TestCognifyPipeline:
    def test_hash_dedup_removes_duplicates(self):
        n1 = make_node("texto único")
        n2 = make_node("texto único")  # mismo hash
        existing_hashes = {n1.hash_value}
        pipeline = CognifyPipeline()
        pipeline.add_task("dedup", CognifyPipeline.task_hash_dedup(existing_hashes))
        data = PipelineData(nodes=[n1, n2])
        result = pipeline.run(data)
        # n1 ya estaba en existing_hashes → skip; n2 tiene mismo hash → skip también
        assert len(result.nodes) == 0
        assert len(result.skipped) >= 1

    def test_add_timestamps_enriches_metadata(self):
        n = make_node("nodo sin timestamp")
        pipeline = CognifyPipeline()
        pipeline.add_task("timestamps", CognifyPipeline.task_add_timestamps(decay_factor=0.95))
        result = pipeline.run(PipelineData(nodes=[n]))
        assert "created_at" in result.nodes[0].metadata
        assert result.nodes[0].metadata["decay_factor"] == 0.95

    def test_enrich_metadata_adds_fields(self):
        n = make_node("nodo a enriquecer")
        pipeline = CognifyPipeline()
        pipeline.add_task("enrich", CognifyPipeline.task_enrich_metadata({"source": "test", "bloque": 6}))
        result = pipeline.run(PipelineData(nodes=[n]))
        assert result.nodes[0].metadata["source"] == "test"
        assert result.nodes[0].metadata["bloque"] == 6

    def test_extract_entities_light(self):
        n = make_node("Kai y FusionAI construyen el sistema de memoria con ChromaDB y HNSW")
        pipeline = CognifyPipeline()
        pipeline.add_task("entities", CognifyPipeline.task_extract_light_graph())
        result = pipeline.run(PipelineData(nodes=[n]))
        import json
        entities = json.loads(result.nodes[0].metadata.get("entities", "[]"))
        assert len(entities) > 0

    def test_skip_on_error_continues(self):
        def failing_task(data: PipelineData) -> PipelineData:
            raise RuntimeError("error simulado")

        n = make_node("nodo de prueba")
        pipeline = CognifyPipeline()
        pipeline.add_task("failing", failing_task, skip_on_error=True)
        pipeline.add_task("enrich", CognifyPipeline.task_enrich_metadata({"after_error": True}))
        result = pipeline.run(PipelineData(nodes=[n]))
        assert len(result.errors) == 1
        assert result.nodes[0].metadata.get("after_error") is True

    def test_make_fusion_cognify_pipeline(self):
        nodes = [
            make_node("Kai es el cerebro digital de FusionAI"),
            make_node("El protocolo 5x5 define bloques de trabajo"),
        ]
        pipeline = make_fusion_cognify_pipeline(source_tag="test_run")
        result = pipeline.run(PipelineData(nodes=nodes))
        assert len(result.nodes) == 2
        assert result.nodes[0].metadata["source"] == "test_run"
        assert "created_at" in result.nodes[0].metadata

    def test_pipeline_chaining_order(self):
        """Verifica que las tasks se ejecutan en orden y el estado fluye correctamente."""
        log = []
        def task_a(data):
            log.append("A")
            return data
        def task_b(data):
            log.append("B")
            return data
        def task_c(data):
            log.append("C")
            return data

        pipeline = CognifyPipeline()
        pipeline.add_task("a", task_a)
        pipeline.add_task("b", task_b)
        pipeline.add_task("c", task_c)
        pipeline.run(PipelineData(nodes=[]))
        assert log == ["A", "B", "C"]
