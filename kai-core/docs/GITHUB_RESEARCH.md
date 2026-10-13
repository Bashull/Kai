# GITHUB RESEARCH

## Metodología

Se evaluaron repositorios por: actualidad, licencia reportada, estrellas, actividad, documentación, seguridad e integración con KAI CORE.

## Candidatos principales

| Tecnología | Repositorio | Señales | Decisión |
|---|---|---|---|
| OpenAI Agents SDK | `openai/openai-agents-python` | ~26k⭐, activo, enfoque multiagente Python | **Adoptar para capa de agentes** |
| LangGraph | `langchain-ai/langgraph` | ~32k⭐, workflows stateful robustos | **Adoptar para orquestación stateful** |
| LlamaIndex | `run-llama/llama_index` | ~49k⭐, fuerte en ingestión/RAG/documentos | **Adoptar para ingestión+RAG** |
| Haystack | `deepset-ai/haystack` | ~25k⭐, pipelines modulares productivos | **Evaluar como alternativa/interop** |
| Mem0 | `mem0ai/mem0` | ~56k⭐, memoria de largo plazo para agentes | **Adoptar mediante adaptador** |
| Qdrant | `qdrant/qdrant-client` | cliente Python maduro, amplio uso | **Vector store recomendado** |
| Chroma | `chroma-core/chroma` | ~28k⭐, despliegue simple local | **Alternativa local rápida** |
| GitHub MCP | `github/github-mcp-server` | oficial, ~30k⭐, alta integración agentes | **Preferido para investigación de repos** |

## Hallazgos por query objetivo

- "agent memory framework python" → Mem0/Haystack y frameworks de memoria.
- "google drive rag agent" → ejemplos comunitarios; útil como referencia de integración.
- "llamaindex github repository reader" → confirma ecosistema LlamaIndex para conectores de repos y documentos.
- "langgraph long term memory agent" → múltiples implementaciones de memoria durable.
- "apps script api deployment automation" → repos orientados a gestión de deployments por API.
- "qdrant rag agent memory" y "chroma persistent memory agent" → evidencia de ambos como backends viables.
- "mem0 agent memory" → Mem0 destaca en adopción y enfoque específico.
- "github mcp server agent" → servidor oficial GitHub MCP recomendado.

## Justificación final de stack para KAI CORE

- **Agentes**: OpenAI Agents SDK.
- **Workflows stateful**: LangGraph.
- **Ingestión/RAG**: LlamaIndex (+ Haystack opcional).
- **Memoria persistente**: Mem0 adaptado.
- **Vector store**: Qdrant primario, Chroma alternativo.
- **Research de repos**: GitHub MCP Server con fallback REST API.
- **Ejecución de tareas de código**: Codex CLI/Web bajo protocolo de aprobación.
