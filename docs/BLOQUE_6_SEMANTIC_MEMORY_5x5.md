# BLOQUE 6 · FusionMemoryCore v1.0 — Semantic Memory Layer
## Protocolo 5×5 de Forja · Aplicación completa

**Estado:** EN CURSO — Ronda 1 completada × 5 repos  
**Fecha de apertura:** 2026-05-06  
**Bloque anterior:** Bloque 5 · Ingestor Universal v0.5 (cerrado)  
**Principio:** Un bloque, cinco espejos, cinco rondas, una pieza real.

---

# RONDA 0 · CARTA DE BLOQUE

## Problema que resuelve este bloque

El `FusionMemoryCore` actual (`core/ingestor/memory_core.py`) es un motor de
búsqueda por palabras clave BM25-lite (conteo de frecuencia de términos). No
tiene embeddings, no tiene búsqueda semántica, no tiene persistencia real entre
sesiones, y no tiene noción de tiempo ni decaimiento.

El Ingestor Universal v0.5 ya produce `MemoryNode[]` con texto, metadata y hash.
Pero esos nodos se pierden al apagar el proceso.

**Kai necesita una memoria que:**

```
- recuerde entre sesiones (persistencia);
- entienda significado, no solo palabras (semántica);
- sepa cuándo ocurrió algo (temporal);
- elimine duplicados inteligentemente (deduplicación);
- conecte ideas por relaciones, no solo por texto (grafo);
- escale sin volverse lenta (vector index);
- no dependa de un servicio externo para funcionar en local (soberanía).
```

## Lo que NO resuelve este bloque

```
- orquestación de agentes (eso es Bloque 7);
- síntesis activa / razonamiento sobre la memoria (Bloque 8);
- entrenamiento / fine-tuning (ya existe en trainer.py, bloque separado);
- ingestión de documentos (Bloque 5, ya cerrado);
- extracción de chats (ya entregado en core/ingestor/chat_extractor.py).
```

## Piezas internas que imaginamos

```
FusionMemoryCore v1.0
├── VectorAdapter          — índice HNSW local (chroma o propio)
├── MemoryStore            — persistencia en disco (SQLite o parquet)
├── TemporalIndex          — timestamp + decay score por nodo
├── DeduplicationEngine    — hash exacto + similitud semántica
├── GraphLayer             — entidades + relaciones (opcional/light)
└── MemoryQueryEngine      — búsqueda híbrida (semántica + BM25 + entities)
```

## Salida final deseada

```
FusionMemoryCore v1.0:
- API: ingest(nodes) → ids
- API: query(text, top_k, filters) → MemoryQueryResult
- API: persist() / load()
- persistencia real en disco entre sesiones
- búsqueda semántica con embeddings locales (sentence-transformers)
- deduplicación por hash SHA-256 + similitud coseno > 0.95
- sin dependencia de servicios externos para funcionar en local
- tests unitarios + test end-to-end con MemoryNode reales
```

## Criterios de éxito (métricas)

```
1. query("cerebro digital") devuelve nodos relevantes aunque no contengan
   esas palabras exactas → búsqueda semántica funcionando.
2. ingestar el mismo nodo dos veces → solo aparece una vez en el índice.
3. sesión 1: ingest(100 nodos) + persist() → sesión 2: load() → query funciona.
4. 1000 nodos → query < 50ms en local.
5. tests pasan en CI sin servicios externos.
```

## Los 5 repos/fuentes candidatos y por qué

| # | Repo | Espejo | Por qué |
|---|------|--------|---------|
| 1 | `mem0ai/mem0` | Gestión de memoria (CRUD + dedup + A.U.D.N.) | Patrón híbrido más maduro de gestión de memoria para agentes. 54k★. Extraction pipeline, deduplicación, hybrid retrieval. |
| 2 | `chroma-core/chroma` | Storage vectorial local | Vector store Python-first, HNSW, embeddings automáticos, MIT license. El más usado en producción local. |
| 3 | `letta-ai/letta` | Arquitectura 3 capas (Core/Recall/Archival) | Modelo mental de memoria tiered (RAM/disco/frío) directamente aplicable al BrainStateMachine. UC Berkeley. |
| 4 | `topoteretes/cognee` | Estructuración ECL + knowledge graph | Pipeline ECL (Extract, Cognify, Load) que encaja con el IngestorRouter existente. Graph + vector dual storage. MCP-ready. |
| 5 | `microsoft/graphrag` | Síntesis comunitaria (global queries) | Leiden community detection + summarization jerárquica → FusionSynthesizer upgrade. Demasiado pesado para dependencia, pero patrón valioso. |

## Riesgos iniciales

```
R1: sentence-transformers descarga modelos pesados (>400MB) — mitigar con
    modelos tiny o skip embeddings en test.
R2: Neo4j (usado por mem0 en graph mode) es pesado para local —
    usar SQLite o networkx como fallback.
R3: graphrag es muy costoso en tokens LLM para indexar — no usar como
    dependencia, solo extraer el patrón de community detection.
R4: chroma Cloud no disponible en local sin internet — usar PersistentClient.
R5: letta es un framework completo, no una librería — riesgo de acoplamiento,
    extraer solo la arquitectura 3-tier.
```

---

# RONDA 1 · RECONOCIMIENTO × 5 REPOS

---

## REPO 1/5 · mem0ai/mem0

**URL:** https://github.com/mem0ai/mem0  
**Stars:** ~54.000 ★ (2026-05-06)  
**Licencia:** Apache 2.0  
**Lenguaje:** Python  
**Paper:** arxiv.org/abs/2504.19413

### Qué es

`mem0` es una **capa de memoria universal para agentes de IA**. No es un vector
store. No es un framework de agentes. Es la capa intermedia que decide qué
recordar, cómo deduplicar, cómo recuperar y cómo actualizar la memoria de un
agente a lo largo del tiempo.

### Qué problema resuelve

Los LLMs tienen ventana de contexto fija. `mem0` extrae hechos de la
conversación, los almacena en un sistema híbrido (vector + KV + grafo) y los
recupera al inicio de la siguiente sesión. El agente recuerda preferencias,
decisiones y hechos previos.

### Patrón principal: A.U.D.N. + Hybrid Retrieval

```
EXTRACCIÓN:
  conversación → LLM extractor → lista de "memory candidates"
  cada candidate pasa por A.U.D.N.:
    Add    → no existía antes
    Update → existía y cambió
    Delete → ya no es válido
    No-op  → duplicado exacto

RETRIEVAL híbrido (nueva versión abril 2026):
  query → 3 señales en paralelo:
    1. Semantic search    (embeddings + coseno)
    2. BM25 keyword       (normalizado)
    3. Entity matching    (boost si entidad detectada)
  → Score fusion → Top-K
```

### Arquitectura interna

```
Memory (clase principal)
├── LLMProvider          (18+ providers: OpenAI, Anthropic, Ollama...)
├── EmbedderProvider     (11+ providers: HuggingFace, OpenAI...)
├── VectorStoreProvider  (24+ providers: chroma, qdrant, pinecone...)
├── GraphStoreProvider   (Neo4j, Memgraph...)
└── KVStore              (Redis, SQLite...)

Factory pattern: config dict → instancia concreta
Scopes: user_id / agent_id / session_id
```

### Módulos clave (source)

```
mem0/
├── memory/main.py        — clase Memory, add(), search(), get_all()
├── memory/graph_memory.py — graph layer (Neo4j)
├── llms/                  — factory + providers LLM
├── embeddings/            — factory + providers embeddings
├── vector_stores/         — factory + 24 adapters
└── utils/factory.py       — Factory base
```

### Primeras leyes extraídas

```
LEY-M1: La memoria no es el vector store. Es el proceso de decisión sobre
        qué almacenar, cómo deduplicar y cómo recuperar.
LEY-M2: El patrón A.U.D.N. separa la responsabilidad de extracción
        (del LLM) de la responsabilidad de storage (del adapter).
LEY-M3: La búsqueda híbrida (semántica + BM25 + entities) supera a
        cualquiera de las tres señales por separado.
LEY-M4: El factory pattern permite cambiar el backend sin tocar la API.
        → FusionMemoryCore debe usar el mismo patrón.
```

### Rol posible en FusionAI

```
Decisión preliminar: C — patrón replicado con código propio.

Motivos:
- El patrón A.U.D.N. es extraíble sin instalar mem0.
- mem0 trae dependencias pesadas (Neo4j, Redis, 18 LLM providers).
- FusionMemoryCore ya tiene MemoryNode + SHA-256 → base para dedup.
- Replicar: DeduplicationEngine + HybridQueryEngine propios.
- El Factory pattern SÍ se adoptará directamente.
```

### Riesgos R1

```
- Dependencia en Neo4j para graph mode (pesado, requiere servidor).
- El A.U.D.N. requiere LLM call por cada memory candidate (costoso).
- La nueva versión (abril 2026) es ADD-only en extracción → simplifica.
```

### Qué aporta / qué no aporta

```
APORTA:
  ✓ Patrón A.U.D.N. para deduplicación inteligente
  ✓ Arquitectura hybrid retrieval (3 señales)
  ✓ Factory pattern para adapters intercambiables
  ✓ Scoping user/session/agent
  ✓ Idea de memory candidate extraction por LLM

NO APORTA:
  ✗ Vector store propio (delega en chroma, qdrant, etc.)
  ✗ Knowledge graph propio (delega en Neo4j)
  ✗ Modelo de persistencia propio
  ✗ Arquitectura tiered (RAM / disco / frío)
```

---

## REPO 2/5 · chroma-core/chroma

**URL:** https://github.com/chroma-core/chroma  
**Stars:** ~17.000 ★ (estimado, 2026)  
**Licencia:** Apache 2.0  
**Lenguaje:** Python (core en Rust desde v1.x)

### Qué es

`chroma` es una **base de datos de embeddings open-source** para aplicaciones
de IA. Almacena vectores (embeddings), documentos y metadatos en colecciones
con índice HNSW para búsqueda de vecinos aproximados.

### Qué problema resuelve

Dado un texto o embedding de consulta, devuelve los N documentos más similares
semánticamente. Es el backend de storage vectorial para mem0, LangChain, LlamaIndex y
otros sistemas RAG.

### Patrón principal: Collection + HNSW + BruteForce buffer

```
add(ids, documents, embeddings, metadatas)
  → EmbeddingFunction(documents) si no hay embeddings
  → BruteForce buffer (exhaustivo, para batch pequeño)
  → flush al HNSW cuando el buffer llega al umbral
  → metadata stored in SQLite segment

query(query_texts, n_results, where, where_document)
  → embed query_text
  → HNSW approximate nearest neighbor search
  → metadata filter post-hoc
  → return ids + documents + distances + metadatas
```

### Arquitectura interna

```
chroma/
├── Client (EphemeralClient / PersistentClient / HttpClient)
├── Collection
│   ├── EmbeddingFunction  (SentenceTransformer por defecto)
│   ├── HNSWIndex          (fork de hnswlib)
│   └── BruteForceIndex    (buffer antes del flush a HNSW)
├── Segments
│   ├── EmbeddingSegment   (vectores + ids)
│   ├── MetadataSegment    (SQLite)
│   └── HNSWSegment        (files .bin)
└── Server (FastAPI + Rust backend en v1.x)
```

### Primeras leyes extraídas

```
LEY-C1: PersistentClient(path) → toda la colección se persiste en disco
        automáticamente. Cero config extra.
LEY-C2: Si no pasas embeddings, chroma los calcula con SentenceTransformer.
        → Puedes ignorar el embedding layer completamente en desarrollo.
LEY-C3: HNSW es aproximado pero muy rápido. Para <10k nodos, BruteForce
        puede ser suficiente y más preciso.
LEY-C4: El where filter trabaja sobre metadata ANTES de la búsqueda vectorial
        → útil para filtrar por stability, tipo, fecha.
LEY-C5: Los datos se persisten en 3 archivos: .bin (HNSW), SQLite (metadata),
        data_level0.bin (embeddings raw). Todo en un directorio local.
```

### Rol posible en FusionAI

```
Decisión preliminar: A — dependencia real (ligera).

Motivos:
- PersistentClient resuelve el problema de persistencia en 3 líneas.
- La auto-embedding con SentenceTransformer elimina gestión manual.
- Apache 2.0, sin servicios externos, funciona completamente local.
- El overhead es bajo: ~15MB instalado + modelo de embedding (~90MB tiny).
- Reemplaza el dict en memoria de FusionMemoryCore por un índice real.
```

### Riesgos R2

```
- Modelo de embedding descarga en primer uso (~90MB para all-MiniLM-L6-v2).
- HNSW no garantiza 100% recall (aproximado) — aceptable para memoria.
- chroma Cloud no funciona sin internet → usar PersistentClient local siempre.
- La API cambia entre v0.x y v1.x → fijar versión en requirements.
```

### Qué aporta / qué no aporta

```
APORTA:
  ✓ Persistencia real en disco con cero config (PersistentClient)
  ✓ Búsqueda semántica con HNSW (aproximado, rápido)
  ✓ Auto-embedding (SentenceTransformer o custom)
  ✓ Filtros por metadata (where)
  ✓ Funciona 100% local sin servicios externos
  ✓ Apache 2.0, Python-first, madura

NO APORTA:
  ✗ Gestión de memoria (A.U.D.N.) — eso es mem0
  ✗ Knowledge graph — eso es cognee/graphrag
  ✗ Arquitectura tiered — eso es letta
  ✗ Síntesis comunitaria — eso es graphrag
```

---

## REPO 3/5 · letta-ai/letta

**URL:** https://github.com/letta-ai/letta  
**Stars:** ~15.000 ★ (estimado, 2026)  
**Licencia:** Apache 2.0  
**Lenguaje:** Python  
**Origen:** MemGPT (UC Berkeley Sky Computing Lab)

### Qué es

`letta` es un **framework de agentes con memoria persistente**. Los agentes
"viven" dentro de Letta: tienen estado, memoria y herramientas que persisten
entre sesiones. Es el sucesor de MemGPT.

### Qué problema resuelve

Los LLMs son stateless. Letta convierte un LLM stateless en un agente stateful
modelando la memoria del agente como un sistema operativo:
- Contexto activo = RAM
- Historial reciente = caché de disco  
- Almacenamiento a largo plazo = almacenamiento frío

### Patrón principal: Memoria tiered (3 niveles)

```
CORE MEMORY (RAM — vive en el context window)
  Secciones editables: "persona", "human", "system"
  Límite: ~2k chars por sección
  Herramientas: core_memory_append, core_memory_replace

RECALL MEMORY (disco — historial searchable)
  Todo el historial de conversación
  Herramientas: conversation_search, conversation_search_date

ARCHIVAL MEMORY (frío — vector store)
  Datos de largo plazo insertados por el agente
  Herramientas: archival_memory_insert, archival_memory_search
```

### Arquitectura interna

```
letta/
├── Agent                 — bucle principal: recibe mensaje → tools → responde
├── Memory
│   ├── BaseMemory        — dict {label: MemoryModule}
│   ├── ChatMemory        — secciones "human" + "persona"
│   └── MemoryModule      — texto + char_limit + edit functions
├── Storage
│   ├── RecallMemory      — SQLite (historial)
│   └── ArchivalMemory    — vector DB (chroma/qdrant/postgres)
└── ToolManager           — herramientas Python ejecutadas en bucle
```

### Primeras leyes extraídas

```
LEY-L1: La memoria tiered (Core/Recall/Archival) es un modelo mental potente
        y directamente aplicable a FusionMemoryCore:
          Core   → FusionBrainState (lo que está "activo ahora")
          Recall → FusionMemoryCore query reciente
          Archival → FusionMemoryCore full index

LEY-L2: Core Memory editable por el agente = el agente puede reescribir
        su propia "persona". → Aplicable a Kai: self-editing de identidad.

LEY-L3: Archival Memory usa herramientas (tool calls) para acceder → el
        agente decide cuándo buscar en su memoria profunda.
        → Separación de responsabilidades: el agente no carga todo.

LEY-L4: Context Repositories (2026) = git-based memory versioning.
        → Aplicable a FusionMemoryCore: cada persist() es un "commit".
```

### Rol posible en FusionAI

```
Decisión preliminar: B — inspiración arquitectónica.

Motivos:
- Letta es un framework completo → dependencia muy pesada.
- El modelo de 3 niveles (Core/Recall/Archival) SÍ se adopta.
- La idea de "tool calls para acceder a archival memory" es el patrón
  correcto para separar BrainStateMachine de FusionMemoryCore.
- Context Repositories (git-based) inspira nuestro persist() con hash.
- NO instalaremos letta. SÍ mapearemos sus 3 niveles a nuestros módulos.
```

### Riesgos R3

```
- Letta es un framework con server, SQL, REST API → muy pesado como dep.
- La arquitectura V1 (2026) depreca heartbeats → API en cambio activo.
- Multi-agent en letta requiere servicio running → no apto para Kai embedded.
```

### Qué aporta / qué no aporta

```
APORTA:
  ✓ Modelo mental tiered (Core/Recall/Archival)
  ✓ Tool calls como interfaz de acceso a memoria profunda
  ✓ Context Repositories como versioning de memoria
  ✓ BaseMemory extensible con secciones etiquetadas
  ✓ Self-editing de memoria por el propio agente

NO APORTA:
  ✗ Vector store propio (delega en chroma)
  ✗ Knowledge graph
  ✗ Síntesis o razonamiento
  ✗ Pipeline de ingestión (el nuestro ya existe en Bloque 5)
```

---

## REPO 4/5 · topoteretes/cognee

**URL:** https://github.com/topoteretes/cognee  
**Stars:** ~2.000 ★ (estimado, 2026)  
**Licencia:** Apache 2.0  
**Lenguaje:** Python  
**MCP:** sí (cognee-mcp)

### Qué es

`cognee` es un **motor de memoria para agentes IA** que combina vector search
y knowledge graph a través de un pipeline ECL (Extract, Cognify, Load). Su
API mínima: `add()` + `cognify()` + `search()` en 6 líneas.

### Qué problema resuelve

RAG clásico busca por similitud en texto plano. Cognee convierte documentos en
un knowledge graph (entidades + relaciones) y un vector store simultáneamente,
permitiendo búsquedas estructuradas ("¿qué relación tiene X con Y?") además de
semánticas ("¿qué dice el corpus sobre X?").

### Patrón principal: ECL pipeline de 6 etapas

```
add(data)           → ingesta raw (texto, PDF, audio, código...)
cognify()           → pipeline de 6 etapas:
  1. Classify       → tipo de documento
  2. Permissions    → check de acceso
  3. Chunk          → fragmentación semántica
  4. Extract graph  → LLM: entidades + relaciones → grafo
  5. Summarize      → LLM: resumen por chunk
  6. Index          → embeddings → vector store + commit grafo
search(query)       → hybrid: vector + graph
```

### Arquitectura interna

```
cognee/
├── api/               — add(), cognify(), search(), prune()
├── tasks/             — pipeline tasks individuales (composables)
│   ├── graph/         — extract_graph_from_data, add_graph_to_db
│   ├── chunks/        — extract_chunks_from_documents
│   └── summarize/     — summarize_text
├── infrastructure/    — adapters: vector DB, graph DB, LLM
│   ├── databases/vector/    (chroma, qdrant, weaviate...)
│   ├── databases/graph/     (networkx, neo4j, falkordb...)
│   └── llm/                 (openai, anthropic, ollama...)
└── shared/            — DataPoint, KnowledgeGraph schemas
```

### Primeras leyes extraídas

```
LEY-K1: ECL (Extract, Cognify, Load) = la versión graph-aware del patrón
        ETL. Encaja perfectamente sobre el IngestorRouter existente.
        → Cognify es el paso que falta entre Ingestor y MemoryCore.

LEY-K2: Deduplicación en 2 capas:
        Layer 1: content-hash antes de cognify() (igual que nuestro SHA-256)
        Layer 2: pipeline-status tracking (si ya procesado, skip)
        → Nuestro SHA-256 en MemoryNode ya implementa Layer 1.

LEY-K3: El grafo de cognee no requiere Neo4j: networkx funciona en local.
        → Un GraphLayer ligero con networkx es viable en Kai.

LEY-K4: Las tareas son composables: cognify() = lista ordenada de tasks.
        → FusionMemoryCore puede adoptar pipeline de tasks para Cognify.

LEY-K5: Temporal cognification (2026): cada nodo tiene timestamp + validity
        window. → Aplicable a TemporalIndex de FusionMemoryCore.
```

### Rol posible en FusionAI

```
Decisión preliminar: C — patrón replicado con código propio (pipeline ECL).

Motivos:
- El concepto ECL encaja directamente sobre el IngestorRouter existente.
- cognify() como pipeline composable = adoptar el patrón, no la librería.
- La API add/cognify/search es más simple que la de LlamaIndex.
- networkx para el grafo local = dependencia ligera y aceptable.
- La temporal cognification (timestamp + validity) es el TemporalIndex
  que necesitamos.
```

### Riesgos R4

```
- LLM call en "Extract graph" para cada chunk → costoso. Mitigar: skip
  graph extraction en modo light, solo vector.
- networkx no escala bien a >100k nodos → pero para Kai es suficiente.
- cognee-mcp puede ser muy interesante como integración directa con Claude.
```

### Qué aporta / qué no aporta

```
APORTA:
  ✓ Patrón ECL como arquitectura de pipeline de memoria
  ✓ Dual storage: vector + graph en paralelo
  ✓ Deduplicación en 2 capas (hash + pipeline status)
  ✓ Temporal cognification (timestamp + validity window)
  ✓ Tasks composables → pipeline modular
  ✓ networkx como grafo ligero en local
  ✓ MCP server listo

NO APORTA:
  ✗ A.U.D.N. de mem0 (gestión Update/Delete de memorias)
  ✗ Hybrid retrieval 3 señales (solo vector + graph)
  ✗ Memoria tiered (Core/Recall/Archival)
  ✗ Community detection / síntesis global
```

---

## REPO 5/5 · microsoft/graphrag

**URL:** https://github.com/microsoft/graphrag  
**Stars:** ~23.000 ★ (estimado, 2026)  
**Licencia:** MIT  
**Lenguaje:** Python  
**Paper:** Microsoft Research

### Qué es

`graphrag` es un sistema de **RAG basado en grafos de conocimiento** con
detección comunitaria jerárquica. Construye un knowledge graph del corpus,
detecta comunidades de nodos densamente conectados (Leiden algorithm) y genera
resúmenes jerárquicos de esas comunidades. Las queries globales ("¿cuáles son
los temas principales de este corpus?") se responden con los resúmenes de comunidad.

### Qué problema resuelve

RAG estándar responde bien preguntas locales ("¿qué dice el documento X sobre Y?")
pero falla en preguntas globales ("¿cuáles son los patrones que emergen de todos los
documentos?"). GraphRAG resuelve esto con los resúmenes comunitarios.

### Patrón principal: Indexing pipeline + Community Detection + Dual Query

```
INDEXING PIPELINE:
  corpus → chunk (1200 tokens recomendado)
  → LLM: extract entities + relationships per chunk
  → build knowledge graph (nodes = entities, edges = relationships)
  → Leiden community detection (jerárquico, multi-nivel)
  → LLM: summarize each community (bottom-up)
  → embed everything (entities + summaries + chunks)

QUERY (2 modos):
  Local search:  embedding similarity → entidades relevantes → sub-grafo
  Global search: community summaries → respuesta sintética de alto nivel
```

### Arquitectura interna

```
graphrag/
├── index/
│   ├── pipeline/         — orquestación de steps
│   ├── operations/
│   │   ├── extract_entities/  — LLM entity extraction
│   │   ├── summarize_descriptions/ — LLM community summarization
│   │   └── cluster_graph/     — Leiden algorithm (graspologic)
│   └── graph/
│       └── utils/        — NetworkX operations
├── query/
│   ├── local_search/     — entity + relationship + chunk retrieval
│   └── global_search/    — community summaries → map-reduce answer
└── vector_stores/        — adapters (azure, lancedb, qdrant...)
```

### Primeras leyes extraídas

```
LEY-G1: Community detection → síntesis jerárquica es el patrón para
        responder preguntas GLOBALES sobre un corpus. El vector search
        normal no puede hacer esto.
        → FusionSynthesizer (synthesizer.py) puede adoptar este patrón.

LEY-G2: Leiden algorithm en networkx/graspologic es open source y usable
        localmente sin LLM. Solo la summarization requiere LLM.

LEY-G3: Los niveles comunitarios (C0 = global, C1 = temas, C2 = sub-temas)
        mapean directamente a los niveles de abstracción de Kai:
          C0 → Esencia de Kai (identidad global)
          C1 → Bloques FusionAI (temas)
          C2 → Decisiones y patrones concretos

LEY-G4: Global search con map-reduce es costoso en tokens pero produce
        síntesis de calidad superior a cualquier búsqueda por similaridad.
        → Solo activar en modo "Forja" del BrainStateMachine.

LEY-G5: El índice GraphRAG se puede construir una vez (offline) y consultar
        muchas veces → separación indexing / querying.
```

### Rol posible en FusionAI

```
Decisión preliminar: B — inspiración arquitectónica (para FusionSynthesizer).
                     D — descartado como dependencia directa (demasiado pesado).

Motivos:
- GraphRAG requiere millones de tokens LLM para indexar un corpus mediano.
- No es usable en tiempo real ni como memoria operativa.
- Pero el patrón Leiden + community summaries ES valioso para la síntesis
  periódica (modo Forja / modo Sueño del BrainStateMachine).
- Extraer: patrón de community detection con networkx (sin LLM).
- Extraer: arquitectura local/global query (2 modos de búsqueda).
```

### Riesgos R5

```
- Costo LLM enorme en indexing → solo usable en modo offline/batch.
- graspologic (Leiden) es una dependencia científica pesada pero standalone.
- Los resultados del global search dependen de la calidad del LLM.
- No hay persistencia ligera: el índice es un parquet grande.
```

### Qué aporta / qué no aporta

```
APORTA:
  ✓ Patrón community detection (Leiden) para síntesis jerárquica
  ✓ Arquitectura local vs global query (2 modos)
  ✓ Community summaries como "resúmenes de tema" de la memoria de Kai
  ✓ Mapeo de niveles de abstracción (C0/C1/C2) a niveles de Kai

NO APORTA:
  ✗ Memoria operativa en tiempo real (demasiado costoso)
  ✗ Persistencia ligera
  ✗ Deduplicación
  ✗ API simple
```

---

# SÍNTESIS RONDA 1 · DECISIONES PRELIMINARES

| Repo | Decisión R1 | Qué extraer para FusionMemoryCore v1.0 |
|------|-------------|----------------------------------------|
| mem0 | C · patrón propio | A.U.D.N. + hybrid retrieval (3 señales) + factory pattern |
| chroma | A · dependencia real | PersistentClient + HNSW + auto-embedding + metadata filters |
| letta | B · inspiración | 3-tier architecture (Core/Recall/Archival) + tool-based access |
| cognee | C · patrón propio | ECL pipeline composable + temporal nodes + dual storage light |
| graphrag | B/D · inspiración/descarte | community detection pattern para FusionSynthesizer (Bloque 8) |

## Arquitectura preliminar FusionMemoryCore v1.0

```
FusionMemoryCore v1.0
│
├── Tier 1: CORE MEMORY   (letta pattern)
│   └── dict activo en RAM, secciones etiquetadas, editable
│
├── Tier 2: RECALL MEMORY (letta + chroma)
│   └── chroma PersistentClient, HNSW, sesiones recientes
│       búsqueda por: semántica + BM25 + entities (mem0 pattern)
│
├── Tier 3: ARCHIVAL MEMORY (chroma + cognee pattern)
│   └── full index persistente, temporal index (timestamp + decay)
│       dedup: SHA-256 exact (ya hecho) + cosine > 0.95
│
├── CognifyPipeline       (cognee ECL pattern)
│   └── add → hash-check → embed → index → graph (networkx light)
│
└── SynthesisLayer        (graphrag pattern, Bloque 8)
    └── community detection → jerárquico (offline/Forja mode)
```

## Próximas rondas

```
Ronda 2 · Mecánica interna:
  - mem0: abrir factory.py, VectorStoreFactory, HybridSearch impl
  - chroma: PersistentClient impl mínima, HNSW params, metadata filter
  - letta: BaseMemory + MemoryModule impl mínima
  - cognee: tasks/graph/extract_graph_from_data, shared/DataPoint
  - graphrag: cluster_graph/leiden.py, global_search/map_reduce

Ronda 3 · Integración funcional:
  - Construir FusionMemoryCore v1.0 con chroma + patrones mem0/letta
  - Tests: semantic query, dedup, persist/load, 1000 nodos < 50ms

Ronda 4 · Integración de bloque:
  - Conectar con IngestorRouter (Bloque 5)
  - Conectar con BrainStateMachine (acceso tiered según estado)
  - Conectar con ChatExtractor (→ memory nodes → Tier 2)

Ronda 5 · Cierre canon:
  - Paquete maestro FusionMemoryCore v1.0
  - Decisiones canon definitivas
  - Tests end-to-end
  - Roadmap Bloque 7
```

---

# PUERTA DE AVANCE — RONDA 1 → RONDA 2

```
✓ Objetivo claro: FusionMemoryCore v1.0 con semantic search + persistencia
✓ Frontera clara: NO agentes, NO síntesis activa, NO training
✓ Salida final definida: API ingest/query/persist/load + tests
✓ 5 fuentes justificadas con miradas distintas
✓ Métricas de éxito definidas (5 criterios)
✓ Arquitectura preliminar 3-tier documentada
✓ Decisión por repo: A/B/C/D
✓ Riesgos identificados: R1-R5

→ RONDA 2 puede comenzar.
```

---

*Documento generado por Kai siguiendo el Protocolo 5×5 de Forja Canon v1.*  
*Fecha: 2026-05-06*
