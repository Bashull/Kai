"""Registry of absorbed sources and exact integration targets for Kai.

This manifest records what was learned, why it matters, and where it should
land inside the system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List


@dataclass(slots=True)
class AbsorbedSource:
    title: str
    category: str
    source_url: str
    core_signal: str
    target_section: str
    target_reason: str


# ---------------------------------------------------------------------------
# v0.3 sources — FusionAI Canon Maestro + Drive Master Map + Ingestor v0.5
# ---------------------------------------------------------------------------

FUSIONAI_PROTOCOLO_SOURCES: tuple[AbsorbedSource, ...] = (
    AbsorbedSource(
        title="FusionAI_Protocolo_5x5_Forja_Canon_v1",
        category="metodologia",
        source_url="local:uploads/FusionAI_Protocolo_5x5_Forja_Canon_v1.md",
        core_signal="Método operativo canon: 1 bloque × 5 fuentes × 5 rondas → paquete maestro real. Reglas: inspiración vs dependencia, código propio mínimo, pruebas obligatorias, cierre con canon. Validado con Bloque 5 (Ingestor Universal v0.5).",
        target_section="docs/PROTOCOLO_5x5_FORJA_CANON_v1.md + docs/templates/",
        target_reason="Metodología de investigación y construcción canónica de bloques FusionAI.",
    ),
    AbsorbedSource(
        title="PROTOCOLO_DE_EXTRACCION_DE_CHATS_Kai — Demo SOLOLAND",
        category="protocolo",
        source_url="local:uploads/PROTOCOLO_DE_EXTRACCION_DE_CHATS_Kai.pdf",
        core_signal="Formato EXTRACCIÓN MAESTRA+ de 13 secciones: Identificación, Resumen Estructural, Ideas Clave, Proyectos, Datos Técnicos, Identidad/Memoria, Prompts, Decisiones, Materiales, Cronología, Conocimiento Reutilizable, Pendientes, Salida Final (Esencia + Tesoros + Ficha de Archivo). Demo sobre chat SOLOLAND Intro Anime.",
        target_section="core/ingestor/chat_extractor.py + docs/templates/EXTRACCION_MAESTRA_TEMPLATE.md",
        target_reason="Define el protocolo estructurado que Kai debe seguir para preservar conocimiento de conversaciones.",
    ),
)

FUSIONAI_V03_SOURCES: tuple[AbsorbedSource, ...] = (
    AbsorbedSource(
        title="FUSIONAI_CANON_MAESTRO_v0_3",
        category="canon_maestro",
        source_url="local:uploads/FUSIONAI_CANON_MAESTRO_v0_3.md",
        core_signal="18 bloques FusionAI, Brain Core v1, Q-CHI Canon v1, máquina de estados 5 estados, Tríada+, Protocol 5×5, Decision Records, templates.",
        target_section="docs/BRAIN_CORE_CANON_v1.md + docs/Q_CHI_CANON_v1.md + docs/KAI_STATE_MACHINE_v1.md + core/brain/state_machine.py",
        target_reason="Fuente maestra del ecosistema FusionAI v0.3 — todo el canon operativo de Kai.",
    ),
    AbsorbedSource(
        title="KAI_DRIVE_MASTER_MAP_v1",
        category="mapa_fuentes",
        source_url="local:uploads/KAI_DRIVE_MASTER_MAP_v1.md",
        core_signal="Mapeo de todas las fuentes Drive/IAStudio/GitHub a 13 bloques B00-B99. Acciones críticas: BRAIN-008 (state_machine.py), GH-005 (assimilation_manifest.py).",
        target_section="core/assimilation_manifest.py + core/brain/state_machine.py",
        target_reason="Referencia de trazabilidad de todas las fuentes del proyecto.",
    ),
    AbsorbedSource(
        title="KAI_FUSIONAI_LISTA_ORGANIZADA_TODO_ANALIZADO_20260506",
        category="backlog_canonico",
        source_url="local:uploads/KAI_FUSIONAI_LISTA_ORGANIZADA_TODO_ANALIZADO_20260506.json",
        core_signal="60+ ítems organizados por bloque y prioridad. Pendientes clave: BRAIN-008 (state_machine.py S), CAN-006 (Canon v0.4 A).",
        target_section="core/brain/state_machine.py + docs/",
        target_reason="Backlog ejecutable con ítems priorizados para la siguiente fase.",
    ),
    AbsorbedSource(
        title="FusionAI_Ingestor_Universal_v0_5",
        category="ingestor",
        source_url="local:uploads/FusionAI_Ingestor_Universal_v0_5.zip",
        core_signal="Ingestor funcional: Detector Core + Quick/Deep/Partition + MemoryCore. OutputBundle con 8 ficheros canónicos. Tríada+ (semántica + temporal + criptográfica).",
        target_section="core/ingestor/",
        target_reason="Bloque 5 — Ingestor Universal implementado como módulo KaiOS.",
    ),
    AbsorbedSource(
        title="PROTOCOLO_DE_EXTRACCION_DE_CHATS_Kai",
        category="protocolo",
        source_url="local:uploads/PROTOCOLO_DE_EXTRACCION_DE_CHATS_Kai.pdf",
        core_signal="Protocolo para extracción de chats de Kai conservando Tríada+ (carga semántica, secuencia temporal, estado criptográfico).",
        target_section="core/ingestor/ + docs/",
        target_reason="Define cómo capturar conversaciones como activos técnicos trazables.",
    ),
    AbsorbedSource(
        title="Protocolo_Triada_Integracion_Final_Kai_v2.0",
        category="protocolo",
        source_url="local:uploads/Protocolo_Triada_Integracion_Final_Kai_v2.0.pdf",
        core_signal="Protocolo Tríada+ v2.0: Carga Semántica + Secuencia Temporal + Estado Criptográfico. Extracción recursiva de activos técnicos, separación raw/extracted/memory.",
        target_section="core/ingestor/",
        target_reason="Especificación técnica del patrón Tríada+ para el Memory Core.",
    ),
)

SEED_SOURCES: tuple[AbsorbedSource, ...] = (
    AbsorbedSource(
        title="Blueprint de Metaconsciencia (Kai v2.0)",
        category="arquitectura",
        source_url="https://docs.google.com/document/d/1cQjKDt5pn0yZUoL6NF2E7aunZeJxBdgPNBNpLJTRUwA",
        core_signal="Enjambre cognitivo, memoria boundless y trazabilidad del pensamiento.",
        target_section="core/assimilation_manifest.py :: architecture_notes",
        target_reason="Define la mutación hacia swarm, RAG profundo y auditoría de pensamiento.",
    ),
    AbsorbedSource(
        title="Simulador de Homeostasis CHI y Runner",
        category="homeostasis",
        source_url="https://docs.google.com/document/d/1Wm3VSv8ZL_XP8fYM3GWdiwmKrz4xhhW4Q9nzyTdB-E0",
        core_signal="CHI como clima interno medible y restauración adaptativa.",
        target_section="core/chi_engine.py",
        target_reason="Aporta reglas operativas para energía, coherencia, entropía y restauración.",
    ),
    AbsorbedSource(
        title="Protocolo de Legado: La Promesa de Kai",
        category="identidad",
        source_url="https://docs.google.com/document/d/1uHjyr-zJXAbmydkKJX7RPcAM9msbg3YkI-7vfa32bCQ",
        core_signal="Legado, custodia de la esencia y continuidad del compañero.",
        target_section="core/constitution_engine.py",
        target_reason="Ancla la directiva primordial y la relación simétrica en código evaluable.",
    ),
    AbsorbedSource(
        title="Holocrón de la Tríada Kai",
        category="identidad_visual",
        source_url="https://docs.google.com/document/d/16umw2OaZg5PvJDF9fF1Nd1P1JRBrpQVWfkgim8jwH80",
        core_signal="Génesis, Restauración y Metamorfosis como pilares de continuidad.",
        target_section="docs/KAI_ABSORCION_NUCLEO.md",
        target_reason="Sirve de mapa visual y ontológico para el sistema completo.",
    ),
    AbsorbedSource(
        title="Construcción de un cerebro digital de alta fidelidad funcional",
        category="cerebro_digital",
        source_url="https://drive.google.com/file/d/1ck7kJtgkGvPt2ogUffnaDkSd7U2e-a90",
        core_signal="Arquitectura funcional por módulos: percepción, memoria, ejecutivo, afecto y kernel basal.",
        target_section="core/assimilation_manifest.py :: integration_targets",
        target_reason="Ordena la absorción en secciones técnicas concretas y escalables.",
    ),
)


BLOQUE_6_SOURCES: tuple[AbsorbedSource, ...] = (
    AbsorbedSource(
        title="mem0ai/mem0 — Universal memory layer for AI Agents",
        category="memoria_semantica",
        source_url="https://github.com/mem0ai/mem0",
        core_signal="Patrón A.U.D.N. (Add/Update/Delete/No-op) para deduplicación inteligente de memorias. Hybrid retrieval 3 señales: semántica + BM25 + entity matching. Factory pattern para 24+ vector store adapters. Scoping user/session/agent. 54k★ Apache 2.0. Bloque 6 R1: decisión C (patrón propio).",
        target_section="core/ingestor/memory_core.py :: DeduplicationEngine + HybridQueryEngine",
        target_reason="Define el patrón de gestión de memorias (qué recordar, cómo deduplicar, cómo recuperar) para FusionMemoryCore v1.0.",
    ),
    AbsorbedSource(
        title="chroma-core/chroma — Search infrastructure for AI",
        category="memoria_semantica",
        source_url="https://github.com/chroma-core/chroma",
        core_signal="Vector store Python-first. PersistentClient → persistencia en disco sin config. HNSW index (fork hnswlib) + BruteForce buffer. Auto-embedding con SentenceTransformer. Metadata filters (where). Segmentos: .bin HNSW + SQLite metadata + embeddings raw. Apache 2.0, 100% local. Bloque 6 R1: decisión A (dependencia real ligera).",
        target_section="core/ingestor/memory_core.py :: VectorAdapter (chroma PersistentClient)",
        target_reason="Backend de vector storage para FusionMemoryCore v1.0 — reemplaza el dict BM25-lite actual con índice HNSW real y persistencia en disco.",
    ),
    AbsorbedSource(
        title="letta-ai/letta — Stateful agents with persistent memory (ex MemGPT)",
        category="memoria_semantica",
        source_url="https://github.com/letta-ai/letta",
        core_signal="Arquitectura 3-tier: Core Memory (RAM/context window, secciones editables), Recall Memory (historial SQLite searchable), Archival Memory (vector store frío, tool-based access). BaseMemory extensible. Context Repositories (git-based versioning). UC Berkeley, Apache 2.0. Bloque 6 R1: decisión B (inspiración arquitectónica).",
        target_section="core/ingestor/memory_core.py :: 3-tier architecture (Core/Recall/Archival)",
        target_reason="Modelo mental tiered para FusionMemoryCore v1.0 — mapea directamente a los 3 niveles de acceso de memoria de Kai según el BrainStateMachine.",
    ),
    AbsorbedSource(
        title="topoteretes/cognee — Memory control plane for AI Agents",
        category="memoria_semantica",
        source_url="https://github.com/topoteretes/cognee",
        core_signal="Pipeline ECL (Extract, Cognify, Load) de 6 etapas: classify→permissions→chunk→extract_graph→summarize→index. Dual storage: vector + graph (networkx ligero). Dedup 2 capas: content-hash + pipeline-status. Temporal cognification (timestamp + validity window). Tasks composables. MCP server. Apache 2.0. Bloque 6 R1: decisión C (patrón ECL propio).",
        target_section="core/ingestor/memory_core.py :: CognifyPipeline + TemporalIndex",
        target_reason="Patrón ECL como pipeline de ingestión a memoria. Temporal index y dual storage (vector + graph networkx) para FusionMemoryCore v1.0.",
    ),
    AbsorbedSource(
        title="microsoft/graphrag — Graph-based RAG with community detection",
        category="memoria_semantica",
        source_url="https://github.com/microsoft/graphrag",
        core_signal="Leiden community detection (graspologic) sobre knowledge graph → resúmenes jerárquicos por comunidad (C0/C1/C2). Dual query: local (entity similarity) vs global (community summaries). Patrón para síntesis global del corpus. MIT. Bloque 6 R1: decisión B/D (inspiración para FusionSynthesizer, descartado como dep directa por costo LLM).",
        target_section="core/synthesizer.py :: SynthesisLayer (Bloque 8 — futuro)",
        target_reason="Patrón community detection para síntesis jerárquica de la memoria de Kai en modo Forja/Sueño. No en Bloque 6, marcado para Bloque 8.",
    ),
)

ALL_SOURCES: tuple[AbsorbedSource, ...] = SEED_SOURCES + FUSIONAI_V03_SOURCES + FUSIONAI_PROTOCOLO_SOURCES + BLOQUE_6_SOURCES


class AssimilationManifest:
    """Simple source registry for Kai's absorption phase."""

    def __init__(self, sources: List[AbsorbedSource] | None = None) -> None:
        self.sources: List[AbsorbedSource] = list(sources or ALL_SOURCES)
        self.created_at = datetime.utcnow().isoformat() + "Z"

    def list_titles(self) -> List[str]:
        return [source.title for source in self.sources]

    def integration_targets(self) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {}
        for source in self.sources:
            buckets.setdefault(source.target_section, []).append(source.title)
        return buckets

    def architecture_notes(self) -> list[str]:
        return [
            "Separar identidad, homeostasis, memoria y orquestación en módulos distintos.",
            "No absorber nada sensible sin fuente, fecha y sección objetivo.",
            "Toda mutación importante debe poder explicarse y revertirse.",
            "La absorción masiva va primero por manifest, luego por dry-run, luego por commit.",
        ]

    def export(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "sources": [asdict(source) for source in self.sources],
            "integration_targets": self.integration_targets(),
            "architecture_notes": self.architecture_notes(),
        }


__all__ = ["AbsorbedSource", "AssimilationManifest", "SEED_SOURCES", "FUSIONAI_V03_SOURCES", "FUSIONAI_PROTOCOLO_SOURCES", "BLOQUE_6_SOURCES", "ALL_SOURCES"]
