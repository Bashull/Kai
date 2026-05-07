# BLOQUE 6 · Ronda 2 · Mecánica Interna × 5 Repos
## FusionMemoryCore v1.0 — Semantic Memory Layer

**Estado:** COMPLETADA  
**Fecha:** 2026-05-07  
**Anterior:** Ronda 1 · Reconocimiento  
**Objetivo:** Abrir el motor interno de cada repo. Entender flujos, contratos e interfaces. Producir prototipos extraídos.

---

## REPO 1/5 · mem0ai/mem0 — Mecánica interna

### Flujo completo de `add()`

```
add(messages, user_id, agent_id, session_id)
  │
  ├─1. Retrieve top-10 existing memories
  │     vector_store.search(embedding(messages), top_k=10)
  │
  ├─2. LLM call: extract memory candidates
  │     prompt: MEMORY_DEDUCTION_PROMPT + messages + existing_memories
  │     output: list[str]  # bullet list of atomic facts
  │
  ├─3. Batch embed all candidates
  │     embedder.embed_many(candidates)  # parallel
  │
  ├─4. Hash dedup (MD5 exact match)
  │     skip if hash already exists in KV store
  │
  ├─5. A.U.D.N. decision per candidate
  │     LLM call: existing_memories + new_candidate → {action, memory_id?}
  │     ADD    → vector_store.insert(candidate, embedding, metadata)
  │     UPDATE → vector_store.update(id, new_text, new_embedding)
  │     DELETE → vector_store.delete(id)
  │     NOOP   → skip
  │
  └─6. Graph update (si graph mode activo)
        entity_extractor(candidate) → (subject, relation, object) triplets
        graph_store.upsert_relation(triplets)
```

### Flujo completo de `search()`

```
search(query, user_id, top_k=10)
  │
  ├─1. Preprocess query
  │     lemmatize keywords, extract named entities
  │
  ├─2. Parallel scoring (3 señales independientes)
  │     Signal A: vector_store.search(embed(query)) → [(id, score_v)]
  │     Signal B: BM25 keyword search over memory texts → [(id, score_b)]
  │     Signal C: entity graph boost → [(id, score_e)]
  │
  ├─3. Score fusion (weighted sum)
  │     final_score = α·score_v + β·score_b + γ·score_e
  │     defaults: α=0.7, β=0.2, γ=0.1
  │
  └─4. Return top_k sorted by final_score
```

### Factory pattern (clave para adopción)

```python
# mem0/utils/factory.py (patrón)
class VectorStoreFactory:
    @staticmethod
    def create(config: dict) -> BaseVectorStore:
        provider = config["provider"]
        return {
            "chroma":   ChromaDB,
            "qdrant":   Qdrant,
            "pinecone": Pinecone,
            # 24 providers...
        }[provider](config=config["config"])
```

### Interfaz `BaseVectorStore` (contrato)

```python
class BaseVectorStore(ABC):
    def insert(self, vectors, payloads, ids) -> None: ...
    def search(self, query, limit, filters) -> list[dict]: ...
    def delete(self, vector_id) -> None: ...
    def update(self, vector_id, vector, payload) -> None: ...
    def get(self, vector_id) -> dict | None: ...
    def list(self, filters, limit) -> list[dict]: ...
```

### Patrón extraído para FusionAI

```
DeduplicationEngine:
  Layer 1: SHA-256 exact match (ya existe en MemoryNode)
  Layer 2: A.U.D.N. simplificado (sin LLM call para UPDATE/DELETE)
            → solo ADD/NOOP basado en cosine similarity > umbral

HybridQueryEngine:
  3 señales: vector + BM25 + (entities opcional)
  weighted fusion con α/β/γ configurables
```

### Código prototipo creado

`core/ingestor/adapters/dedup_engine.py` — ver implementación completa.

### Riesgos descubiertos R2

```
R2-M1: A.U.D.N. con LLM call por candidate es costoso (N calls por add).
        Mitigación: usar solo ADD/NOOP sin LLM. UPDATE manual explícito.
R2-M2: El hash MD5 de mem0 es débil → mantener SHA-256 (ya lo tenemos).
R2-M3: El fusion scoring requiere tunear α/β/γ por caso de uso.
```

### Decisión actualizada

```
C · patrón replicado con código propio — CONFIRMADA
Adoptar: DeduplicationEngine (SHA-256 + cosine), HybridQueryEngine,
         BaseVectorStore interface, Factory pattern.
No adoptar: A.U.D.N. LLM-based UPDATE/DELETE (demasiado costoso).
```

---

## REPO 2/5 · chroma-core/chroma — Mecánica interna

### Flujo completo de `add()` + `query()`

```
PersistentClient(path="./data/chroma")
  └─ SQLite backend + HNSW binary files en disco

collection.add(ids, documents, metadatas, embeddings=None)
  │
  ├─ si embeddings=None:
  │     EmbeddingFunction(documents) → embeddings
  │     default: SentenceTransformer("all-MiniLM-L6-v2")
  │
  ├─ BruteForceIndex.add(embedding, id)   # buffer temporal
  │
  └─ flush cuando buffer llega al threshold:
       BruteForce → HNSWIndex.add_items(embeddings, ids)
       metadata → SQLite segment (columnas: id, key, value)
       datos en disco: data_level0.bin + index_metadata.pkl

collection.query(query_texts, n_results, where, where_document)
  │
  ├─ EmbeddingFunction(query_texts) → query_embedding
  │
  ├─ HNSWIndex.knn_query(query_embedding, k=n_results)
  │     → [(ids, distances)]  # cosine por defecto si hnsw:space="cosine"
  │
  ├─ MetadataSegment.filter(where)      # post-hoc sobre los k resultados
  │
  └─ return: ids, documents, metadatas, distances
```

### Parámetros HNSW configurables

```python
collection = client.create_collection(
    name="fusion_memory",
    metadata={
        "hnsw:space":          "cosine",  # "l2" | "ip" | "cosine"
        "hnsw:construction_ef": 200,       # calidad del índice (default 100)
        "hnsw:search_ef":       100,       # calidad de búsqueda (default 10)
        "hnsw:M":               16,        # conexiones por nodo (default 16)
        "hnsw:batch_size":      100,       # flush threshold
    }
)
```

### Estructura de disco

```
./data/chroma/
├── chroma.sqlite3           # metadata de colecciones
└── <uuid-collection>/
    ├── data_level0.bin      # embeddings raw
    ├── header.bin           # metadata del índice HNSW
    ├── index_metadata.pkl   # parámetros HNSW serializados
    ├── length.bin
    └── link_lists.bin       # grafo HNSW
```

### Contrato de colección

```python
# Entrada add()
ids:        list[str]         # SHA-256 slice o UUID
documents:  list[str]         # texto original (MemoryNode.text)
metadatas:  list[dict]        # MemoryNode.metadata
embeddings: list[list[float]] # opcional — chroma los calcula si None

# Salida query()
{
  "ids":       [[str, ...]],        # top_k ids por query
  "documents": [[str, ...]],        # textos recuperados
  "metadatas": [[dict, ...]],       # metadata asociada
  "distances": [[float, ...]],      # distancia coseno [0, 2]
  "embeddings": None | [[float]]    # si include=["embeddings"]
}
```

### Filtros where (metadata)

```python
# Operadores: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or
where={"memory_stability": {"$in": ["stable", "provisional"]}}
where={"$and": [
    {"type": {"$eq": "chat_extraction"}},
    {"priority": {"$eq": "high"}}
]}
```

### Código prototipo creado

`core/ingestor/adapters/chroma_adapter.py` — ver implementación completa.

### Riesgos descubiertos R2

```
R2-C1: Primera ejecución descarga modelo SentenceTransformer (~90MB).
        Mitigación: pre-download en setup, o modo test sin embeddings reales.
R2-C2: HNSW es aproximado: puede no devolver los k más cercanos exactos.
        Para <10k nodos, BruteForce exacto sería más preciso.
        Mitigación: aceptable para memoria operativa de Kai.
R2-C3: El where filter es post-HNSW → reduce efectivos si muchos filtrados.
        Mitigación: incrementar n_results y filtrar después.
R2-C4: chroma v0.x vs v1.x API changes → fijar versión exacta.
```

### Decisión actualizada

```
A · dependencia real — CONFIRMADA
chromadb>=0.6.0 añadido a requirements conceptuales.
Usar PersistentClient siempre (nunca EphemeralClient en producción).
hnsw:space=cosine por defecto para MemoryNodes.
```

---

## REPO 3/5 · letta-ai/letta — Mecánica interna

### Implementación BaseMemory

```python
# Patrón letta/memory/base.py
class MemoryModule:
    value: str      # contenido de texto
    limit: int      # char limit (default 2000)

    def __len__(self): return len(self.value)

    def __str__(self): return (
        f"<{self.name} characters_used={len(self)}/{self.limit}>\n"
        f"{self.value}\n"
        f"</{self.name}>"
    )

class BaseMemory:
    memory: dict[str, MemoryModule]  # {"human": ..., "persona": ...}

    def to_flat_dict(self) -> dict[str, str]:
        return {k: v.value for k, v in self.memory.items()}

    def __str__(self) -> str:
        return "\n".join(str(m) for m in self.memory.values())
```

### Herramientas de edición (Core Memory)

```python
def core_memory_append(agent_state, name, content) -> str:
    """Añade contenido a una sección sin reemplazar."""
    agent_state.memory.memory[name].value += "\n" + content
    return f"Appended to {name}"

def core_memory_replace(agent_state, name, old_content, new_content) -> str:
    """Sustituye texto exacto en una sección."""
    current = agent_state.memory.memory[name].value
    if old_content not in current:
        raise ValueError(f"String not found in {name}")
    agent_state.memory.memory[name].value = current.replace(old_content, new_content)
    return f"Replaced in {name}"
```

### Herramientas de acceso a Archival Memory

```python
def archival_memory_insert(agent_state, content) -> str:
    """Escribe en la memoria fría (vector store)."""
    agent_state.archival_memory.insert(content)
    return f"Added to archival: '{content[:50]}...'"

def archival_memory_search(agent_state, query, page=0) -> str:
    """Busca en la memoria fría. El agente decide cuándo llamarla."""
    results = agent_state.archival_memory.search(query, start=page*RETRIEVAL_QUERY_DEFAULT_PAGE_SIZE)
    return json.dumps([r.text for r in results])
```

### Mapeo a FusionAI (3 niveles)

```
LETTA                     FUSIONAI
─────────────────────────────────────────────────────
Core Memory (RAM)    →  FusionCoreMemory
  secciones editables      secciones: "identity",
  ~2k chars/sección        "brain_state", "active_context"
  editable por el agente   editable por BrainStateMachine

Recall Memory (disco)→  FusionRecallMemory
  historial sesión         MemoryNode[] de sesión actual
  SQLite searchable        búsqueda BM25 + semantic reciente

Archival Memory (frío) → FusionArchivalMemory
  vector DB long-term      chroma PersistentClient
  tool-based access        query() solo cuando BrainState=Forja/Normal
```

### Context Repositories (2026) — patrón git-based

```python
# Idea central: cada persist() = commit de memoria
class ContextRepository:
    path: Path          # directorio de memoria
    _history: list      # lista de commits (hash + timestamp)

    def commit(self, message: str) -> str:
        snapshot = self._snapshot()
        hash_val = sha256(snapshot)
        self._history.append({"hash": hash_val, "msg": message, "ts": now()})
        return hash_val

    def checkout(self, hash_val: str) -> None:
        snapshot = self._find_snapshot(hash_val)
        self._restore(snapshot)
```

### Código prototipo creado

`core/ingestor/adapters/tiered_memory.py` — ver implementación completa.

### Riesgos descubiertos R2

```
R2-L1: Letta V1 depreca heartbeats y send_message → API en flujo activo.
        No dependencia directa: solo extraemos el patrón 3-tier.
R2-L2: Core Memory tiene char_limit → implica gestión de overflow.
        Mitigación: threshold de alerta, flush a Recall si >80%.
R2-L3: El acceso tool-based a Archival Memory requiere BrainStateMachine
        integrado → no implementar en Bloque 6, sino en Bloque 7.
```

### Decisión actualizada

```
B · inspiración arquitectónica — CONFIRMADA
Adoptar: 3-tier model, secciones etiquetadas en Core, persist=commit.
No adoptar: letta como dependencia, tool-based access (Bloque 7).
```

---

## REPO 4/5 · topoteretes/cognee — Mecánica interna

### Pipeline ECL — 6 tareas composables

```
add(data, dataset_name)
  │
  └─ content-hash check → skip si ya existe
     DataPoint(id=uuid, content=data, dataset=dataset_name)
     persiste en metadata store (SQLite)

cognify(dataset_ids=None)
  │
  Task 1: classify_documents
  │         DetectType(text|pdf|audio|code) → doc_type
  │
  Task 2: check_permissions
  │         verify dataset ownership
  │
  Task 3: extract_chunks
  │         ChunkingStrategy(doc_type) → list[TextChunk]
  │         chunk_size configurable (default: 1024 tokens)
  │
  Task 4: extract_graph
  │         LLM(chunk) → list[(entity, relation, entity)]
  │         graph_db.upsert(nodes, edges)
  │
  Task 5: summarize
  │         LLM(chunk) → summary_text
  │
  Task 6: add_data_points (index)
            embed(chunk_text + summary) → vector
            vector_store.upsert(id, vector, metadata)

search(query, query_type="auto")
  │
  ├─ auto-routing: detect if local or global query
  ├─ local:  vector_store.search(embed(query)) → chunks → graph traversal
  └─ global: graph summaries → answer
```

### DataPoint — contrato base

```python
from pydantic import BaseModel
from uuid import UUID, uuid4

class DataPoint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    metadata: dict = {}

    # Relaciones hacia otros DataPoints
    _related: list["DataPoint"] = []

    class Config:
        # Permite definir graph_model custom pasado a cognify()
        arbitrary_types_allowed = True
```

### Temporal Cognification (2026)

```python
class TemporalDataPoint(DataPoint):
    created_at: datetime
    expires_at: datetime | None = None   # validity window
    decay_factor: float = 1.0            # decreases over time

    @property
    def is_valid(self) -> bool:
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    @property
    def effective_score(self, base_score: float) -> float:
        age_days = (datetime.now() - self.created_at).days
        return base_score * (self.decay_factor ** age_days)
```

### Pipeline composable (patrón extraído)

```python
# Cada task es una función: data → data
# El pipeline encadena N tasks, pasando output de una a input de siguiente
class Task:
    name: str
    fn: Callable[[Any], Any]
    skip_on_error: bool = False

pipeline = Pipeline([
    Task("hash_check",   hash_check_fn),
    Task("chunk",        chunk_fn),
    Task("embed",        embed_fn),
    Task("index",        index_fn),
    # graph tasks opcionales
    Task("extract_graph", extract_graph_fn, skip_on_error=True),
])
result = pipeline.run(data)
```

### Código prototipo creado

`core/ingestor/adapters/cognify_pipeline.py` — ver implementación completa.

### Riesgos descubiertos R2

```
R2-K1: Task "extract_graph" requiere LLM call por chunk → desactivar
        por defecto. Solo activar en modo Forja.
R2-K2: cognee usa asyncio.run() — verificar compatibilidad con FastAPI.
R2-K3: networkx no escala a >100k nodos de forma eficiente.
        Para Kai (<10k nodos previstos) es completamente válido.
```

### Decisión actualizada

```
C · patrón replicado con código propio — CONFIRMADA
Adoptar: Pipeline composable, TemporalDataPoint, dual storage pattern.
No adoptar: cognee como dependencia (el patrón es simple de replicar).
```

---

## REPO 5/5 · microsoft/graphrag — Mecánica interna

### Pipeline de indexación (offline)

```
corpus (texto plano)
  │
  ├─ Chunk (1200 tokens recomendado, overlap 100)
  │
  ├─ Per-chunk LLM call: entity + relationship extraction
  │     prompt: GRAPH_EXTRACTION_PROMPT
  │     output: {entities: [{name, type, description}],
  │              relationships: [{source, target, description, weight}]}
  │
  ├─ Build NetworkX DiGraph
  │     G.add_node(entity, type=..., description=...)
  │     G.add_edge(source, target, weight=..., description=...)
  │
  ├─ Leiden Community Detection (graspologic)
  │     partitions = leiden(G, resolution=1.0)
  │     → {node: community_id} at each level
  │
  ├─ Per-community LLM call: summarize
  │     community_nodes + edges → community_summary_text
  │
  └─ Index embeddings
       embed(entity_description) → vector
       embed(community_summary)  → vector
       persist to parquet / lancedb
```

### Leiden — el algoritmo (patrón extraído)

```python
# graphrag/index/operations/cluster_graph/leiden.py (simplificado)
import networkx as nx
from graspologic.partition import leiden

def detect_communities(G: nx.Graph, levels: int = 3) -> dict[int, dict]:
    # G: nodes = entidades, edges = relaciones con weight
    all_partitions = {}
    for level in range(levels):
        resolution = 1.0 + level * 0.5  # más resolución → comunidades más pequeñas
        partitions = leiden(G, resolution=resolution)
        all_partitions[level] = partitions  # {node_id: community_id}
    return all_partitions

# Uso: nodos del mismo community_id → misma "comunidad temática"
```

### Dual query mode (local vs global)

```
Local search  → entity similarity → sub-grafo → answer
               (para preguntas sobre entidades específicas)

Global search → community_summaries[level=0] → map-reduce → answer
               (para preguntas sobre patrones del corpus completo)
```

### Mapeo a FusionAI

```
Community Level 0  →  Esencia de Kai (síntesis global de toda la memoria)
Community Level 1  →  Bloques FusionAI (grandes temas)
Community Level 2  →  Decisiones y patrones concretos

Global search      →  activar solo en BrainState=Forja o BrainState=Sueño
Local search       →  equivalente al query() actual de FusionMemoryCore
```

### Riesgos confirmados R2

```
R2-G1: Index construction: millones de tokens LLM para corpus mediano.
        No viable en tiempo real. Solo offline/batch.
R2-G2: graspologic es dependencia científica (scipy, numpy heavy).
        Usable standalone sin el resto de graphrag.
R2-G3: El índice resultante es un parquet grande (100MB+ para corpus mediano).
```

### Decisión actualizada

```
B/D · inspiración/descarte — CONFIRMADA para Bloque 6.
      MARCADO para Bloque 8 (FusionSynthesizer).
Extraer para Bloque 8: leiden(G) sobre el grafo networkx de cognee.
No implementar en Bloque 6.
```

---

# SÍNTESIS RONDA 2

## Decisiones canon provisionales (actualizadas)

| Repo | Decisión R1 | Decisión R2 | Cambio |
|------|-------------|-------------|--------|
| mem0 | C | C · CONFIRMADA | — |
| chroma | A | A · CONFIRMADA | — |
| letta | B | B · CONFIRMADA | — |
| cognee | C | C · CONFIRMADA | — |
| graphrag | B/D | B/D · CONFIRMADA, reservado Bloque 8 | — |

## Prototipos creados en esta ronda

```
core/ingestor/adapters/
├── __init__.py
├── chroma_adapter.py     — ChromaVectorAdapter (chroma mechanics)
├── dedup_engine.py       — DeduplicationEngine + HybridQueryEngine (mem0)
├── tiered_memory.py      — TieredMemoryStore + CoreMemory (letta)
└── cognify_pipeline.py   — CognifyPipeline + TemporalMemoryNode (cognee)

tests/test_bloque6_ronda2.py — tests unitarios sin servicios externos
```

## Contratos clave extraídos

```python
# Contrato BaseVectorAdapter (de mem0/chroma)
class BaseVectorAdapter(ABC):
    def upsert(self, nodes: list[MemoryNode]) -> list[str]: ...
    def search(self, query: str, top_k: int, filters: dict) -> list[MemoryNode]: ...
    def delete(self, node_id: str) -> None: ...
    def persist(self) -> None: ...
    def load(self) -> None: ...

# Contrato HybridSearch (de mem0)
class HybridSearchResult:
    node: MemoryNode
    score_semantic: float   # coseno [0,1]
    score_bm25:     float   # normalizado [0,1]
    score_entity:   float   # boost si entidad detectada [0,1]
    score_final:    float   # α·sem + β·bm25 + γ·entity

# Contrato CognifyPipeline (de cognee)
class PipelineTask:
    name: str
    fn: Callable[[PipelineData], PipelineData]
    skip_on_error: bool = False
```

## Arquitectura FusionMemoryCore v1.0 — confirmada

```
FusionMemoryCore v1.0
│
├── CoreMemory          (letta) — dict RAM, secciones etiquetadas
├── RecallMemory        (letta + chroma) — sesión actual, búsqueda rápida
├── ArchivalMemory      (chroma) — PersistentClient, HNSW, full index
│
├── ChromaVectorAdapter (chroma) — upsert / search / persist / load
├── DeduplicationEngine (mem0)   — SHA-256 exact + cosine threshold
├── HybridQueryEngine   (mem0)   — 3 señales: semantic + BM25 + entity
│
├── CognifyPipeline     (cognee) — ECL composable, tasks chain
├── TemporalMemoryNode  (cognee) — created_at + decay_factor
│
└── SynthesisLayer      (graphrag) — reservado Bloque 8
```

## Puerta de cierre Ronda 2

```
✓ Componentes internos documentados × 5 repos
✓ Flujos de datos entrada→salida × 5 repos
✓ Interfaces/contratos extraídos
✓ Patrones repetibles identificados
✓ Prototipos creados: 4 adapters + tests
✓ Riesgos R2 documentados
✓ Decisiones actualizadas (todas confirmadas)
✓ Arquitectura FusionMemoryCore v1.0 consolidada

→ RONDA 3 puede comenzar.
```

---

*Documento generado por Kai · Protocolo 5×5 de Forja Canon v1 · Bloque 6 Ronda 2*
