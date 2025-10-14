# Integraciones y Dependencias Externas - Proyecto Kai

Este documento describe todas las dependencias externas, repositorios y herramientas que forman parte del ecosistema de Kai como compañero virtual avanzado.

## Índice

- [IA y Razonamiento](#ia-y-razonamiento)
- [Procesamiento de Voz](#procesamiento-de-voz)
- [Entrenamiento y Ajuste de Modelos](#entrenamiento-y-ajuste-de-modelos)
- [Memoria y Búsqueda Vectorial](#memoria-y-búsqueda-vectorial)
- [Infraestructura y Despliegue](#infraestructura-y-despliegue)
- [Seguridad y Gestión de Secretos](#seguridad-y-gestión-de-secretos)
- [Complementos para D&D y Conversacional](#complementos-para-dd-y-conversacional)
- [Compatibilidad de Licencias](#compatibilidad-de-licencias)

---

## IA y Razonamiento

### langchain-ai/langchain

**Repositorio**: [https://github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)

**Función**: Framework para construir cadenas de razonamiento complejas y gestión de memoria híbrida para agentes conversacionales.

**Uso en Kai**:
- Orquestación de múltiples llamadas a LLMs
- Gestión de contexto y memoria a largo plazo
- Cadenas de razonamiento para resolución de problemas complejos
- Integración con herramientas y APIs externas

**Licencia**: MIT

**Estado**: ✅ Integrado (ver `src/store/slices/createDiarySlice.ts`)

---

## Procesamiento de Voz

### coqui-ai/TTS

**Repositorio**: [https://github.com/coqui-ai/TTS](https://github.com/coqui-ai/TTS)

**Función**: Sistema de síntesis de voz (Text-to-Speech) de código abierto para generar voz natural.

**Uso en Kai**:
- Síntesis de voz para respuestas de Kai
- Generación de voces personalizadas para personajes D&D
- Soporte multiidioma para interacciones globales

**Licencia**: MPL 2.0

**Estado**: ✅ Integrado (ver `src/store/slices/createDiarySlice.ts`)

**Integración sugerida**:
```bash
# Instalación local
pip install TTS

# Uso básico
tts --text "Hola, soy Kai" --model_name "tts_models/es/css10/vits"
```

### openai/whisper

**Repositorio**: [https://github.com/openai/whisper](https://github.com/openai/whisper)

**Función**: Modelo de reconocimiento automático de voz (ASR) para transcripción de audio.

**Uso en Kai**:
- Transcripción de comandos de voz del usuario
- Procesamiento de audio para sesiones D&D
- Subtítulos automáticos y accesibilidad

**Licencia**: MIT

**Estado**: ✅ Integrado (ver `src/store/slices/createKernelSlice.ts`)

**Integración sugerida**:
```bash
# Instalación
pip install openai-whisper

# Uso básico
whisper audio.mp3 --model medium --language Spanish
```

---

## Entrenamiento y Ajuste de Modelos

### huggingface/autotrain-advanced

**Repositorio**: [https://github.com/huggingface/autotrain-advanced](https://github.com/huggingface/autotrain-advanced)

**Función**: Plataforma automatizada para entrenamiento y fine-tuning de modelos de IA sin necesidad de código.

**Uso en Kai**:
- Motor de "La Forja" - sistema de entrenamiento interno de Kai
- Fine-tuning de modelos con datos personalizados del usuario
- Ajuste de modelos para respuestas específicas de D&D

**Licencia**: Apache 2.0

**Estado**: ✅ Integrado (ver `src/store/slices/createKernelSlice.ts`, `src/components/panels/ForgePanel.tsx`)

**Integración sugerida**:
```bash
# Instalación
pip install autotrain-advanced

# Entrenamiento básico
autotrain --task text-classification --model bert-base-uncased --data ./data
```

---

## Memoria y Búsqueda Vectorial

### facebookresearch/faiss

**Repositorio**: [https://github.com/facebookresearch/faiss](https://github.com/facebookresearch/faiss)

**Función**: Biblioteca para búsqueda eficiente de similitud y clustering de vectores densos.

**Uso en Kai**:
- Búsqueda semántica en memoria de Kai (RAG - Retrieval Augmented Generation)
- Indexación de recuerdos y contexto histórico
- Recuperación rápida de información relevante del Kernel

**Licencia**: MIT

**Estado**: ✅ Integrado (ver `src/store/slices/createDiarySlice.ts`)

**Integración sugerida**:
```python
import faiss
import numpy as np

# Crear índice de vectores
dimension = 768  # Dimensión de embeddings
index = faiss.IndexFlatL2(dimension)

# Añadir vectores
vectors = np.random.random((1000, dimension)).astype('float32')
index.add(vectors)

# Búsqueda
query = np.random.random((1, dimension)).astype('float32')
distances, indices = index.search(query, k=5)
```

---

## Infraestructura y Despliegue

### terraform-google-modules/terraform-google-project-factory

**Repositorio**: [https://github.com/terraform-google-modules/terraform-google-project-factory](https://github.com/terraform-google-modules/terraform-google-project-factory)

**Función**: Módulo Terraform para automatización de proyectos y servicios en Google Cloud Platform.

**Uso en Kai**:
- Aprovisionamiento automatizado de proyectos GCP
- Gestión de APIs y servicios (Gemini AI, Cloud Run)
- Configuración de permisos y roles IAM

**Licencia**: Apache 2.0

**Estado**: ✅ Integrado (ver `main.tf`)

**Configuración actual**:
```hcl
module "gemini-api-connector" {
  source        = "github.com/terraform-google-modules/terraform-google-project-factory//modules/project_services?ref=v18.0.0"
  project_id    = "gen-lang-client-0592741070"
  activate_apis = ["aiplatform.googleapis.com"]
}
```

---

## Seguridad y Gestión de Secretos

### GoogleCloudPlatform/terraform-google-secret-manager

**Repositorio**: [https://github.com/GoogleCloudPlatform/terraform-google-secret-manager](https://github.com/GoogleCloudPlatform/terraform-google-secret-manager)

**Función**: Gestión segura de claves API y secretos en Google Cloud Secret Manager.

**Uso en Kai**:
- Almacenamiento seguro de API keys (OpenAI, Gemini, etc.)
- Gestión de credenciales de bases de datos
- Rotación automática de secretos

**Licencia**: Apache 2.0

**Estado**: ✅ Integrado (ver `main.tf`)

**Configuración actual**:
```hcl
module "openai-api-key" {
  source      = "github.com/GoogleCloudPlatform/terraform-google-secret-manager//modules/simple-secret?ref=v0.9.0"
  project_id  = "gen-lang-client-0592741070"
  name        = "openai-chatgpt-api-key"
  secret_data = "YOUR_OPENAI_API_KEY_HERE"
}
```

### GoogleCloudPlatform/terraform-google-cloud-run

**Repositorio**: [https://github.com/GoogleCloudPlatform/terraform-google-cloud-run](https://github.com/GoogleCloudPlatform/terraform-google-cloud-run)

**Función**: Despliegue de aplicaciones serverless en Cloud Run.

**Uso en Kai**:
- Despliegue del orquestador multi-agente
- Escalado automático según demanda
- Integración con load balancers y servicios GCP

**Licencia**: Apache 2.0

**Estado**: ✅ Integrado (ver `main.tf`)

**Configuración actual**:
```hcl
module "ai-agent-orchestrator" {
  source       = "github.com/GoogleCloudPlatform/terraform-google-cloud-run//modules/v2?ref=v0.21.2"
  project_id   = "gen-lang-client-0592741070"
  location     = "us-central1"
  service_name = "ai-agent-orchestrator"
}
```

---

## Complementos para D&D y Conversacional

### Repositorios Adicionales Recomendados

#### 1. **chromadb/chroma**
**Repositorio**: [https://github.com/chroma-core/chroma](https://github.com/chroma-core/chroma)

**Función**: Base de datos vectorial para aplicaciones de IA con embeddings.

**Uso potencial en Kai**:
- Alternativa/complemento a FAISS para memoria semántica
- Almacenamiento persistente de embeddings
- Filtrado por metadatos para búsquedas contextuales

**Licencia**: Apache 2.0

**Estado**: 🔄 Recomendado para implementación futura

---

#### 2. **rasa/rasa**
**Repositorio**: [https://github.com/RasaHQ/rasa](https://github.com/RasaHQ/rasa)

**Función**: Framework de código abierto para construir asistentes conversacionales con NLU.

**Uso potencial en Kai**:
- Comprensión de intenciones del usuario (NLU)
- Gestión de diálogos multi-turno
- Entrenamiento de respuestas personalizadas

**Licencia**: Apache 2.0

**Estado**: 🔄 Evaluación pendiente

---

#### 3. **botpress/botpress**
**Repositorio**: [https://github.com/botpress/botpress](https://github.com/botpress/botpress)

**Función**: Plataforma para crear chatbots conversacionales con visual flow builder.

**Uso potencial en Kai**:
- Diseño visual de flujos de conversación
- Integración con múltiples canales
- Gestión de contexto conversacional

**Licencia**: MIT

**Estado**: 🔄 Evaluación pendiente

---

#### 4. **Significant-Gravitas/AutoGPT**
**Repositorio**: [https://github.com/Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)

**Función**: Agente de IA autónomo que puede completar tareas complejas.

**Uso potencial en Kai**:
- Automatización de tareas del usuario
- Planificación y ejecución de objetivos complejos
- Inspiración para arquitectura de agentes

**Licencia**: MIT

**Estado**: 🔄 Para investigación arquitectónica

---

#### 5. **microsoft/semantic-kernel**
**Repositorio**: [https://github.com/microsoft/semantic-kernel](https://github.com/microsoft/semantic-kernel)

**Función**: SDK para integrar modelos LLM con aplicaciones convencionales.

**Uso potencial en Kai**:
- Orquestación de habilidades y plugins
- Gestión de memoria semántica
- Planeación de tareas complejas

**Licencia**: MIT

**Estado**: 🔄 Evaluación en progreso

---

#### 6. **bentoml/BentoML**
**Repositorio**: [https://github.com/bentoml/BentoML](https://github.com/bentoml/BentoML)

**Función**: Framework para crear y desplegar servicios de ML de producción.

**Uso potencial en Kai**:
- Empaquetado de modelos custom para La Forja
- Servir modelos fine-tuned como APIs
- Monitoreo y versionado de modelos

**Licencia**: Apache 2.0

**Estado**: 🔄 Recomendado para La Forja

---

#### 7. **oobabooga/text-generation-webui**
**Repositorio**: [https://github.com/oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui)

**Función**: Interfaz web para ejecutar LLMs localmente.

**Uso potencial en Kai**:
- Hosting local de modelos open-source
- Reducción de costos de API
- Mayor privacidad para datos sensibles

**Licencia**: AGPL 3.0

**Estado**: ⚠️ Evaluación de licencia necesaria

---

#### 8. **pgvector/pgvector**
**Repositorio**: [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)

**Función**: Extensión de PostgreSQL para búsqueda de similitud vectorial.

**Uso potencial en Kai**:
- Almacenamiento de embeddings en PostgreSQL existente
- Búsqueda semántica con SQL
- Integración con base de datos actual

**Licencia**: PostgreSQL License

**Estado**: 🔄 Alta prioridad para implementación

---

#### 9. **StanGirard/quivr**
**Repositorio**: [https://github.com/StanGirard/quivr](https://github.com/StanGirard/quivr)

**Función**: "Segundo cerebro" personal usando IA generativa y vectores.

**Uso potencial en Kai**:
- Inspiración para arquitectura de memoria
- Gestión de conocimiento personal
- RAG para documentos personales

**Licencia**: Apache 2.0

**Estado**: 🔄 Investigación de patrones arquitectónicos

---

#### 10. **AI-Dungeon/AIDungeon** (conceptual)
**Referencia**: Sistemas similares de narrativa D&D con IA

**Función**: Generación de narrativa interactiva y aventuras de rol.

**Uso potencial en Kai**:
- Generación de campañas D&D personalizadas
- Narración adaptativa basada en acciones del jugador
- Gestión de NPCs y eventos dinámicos

**Estado**: 🔄 Investigación de técnicas narrativas

---

## Compatibilidad de Licencias

### Resumen de Licencias

| Dependencia | Licencia | Compatible con Kai | Notas |
|-------------|----------|-------------------|-------|
| langchain | MIT | ✅ | Uso comercial permitido |
| coqui-ai/TTS | MPL 2.0 | ✅ | Copyleft débil, compatible |
| openai/whisper | MIT | ✅ | Uso comercial permitido |
| autotrain-advanced | Apache 2.0 | ✅ | Uso comercial permitido |
| faiss | MIT | ✅ | Uso comercial permitido |
| terraform-google-* | Apache 2.0 | ✅ | Uso comercial permitido |
| chromadb | Apache 2.0 | ✅ | Uso comercial permitido |
| rasa | Apache 2.0 | ✅ | Uso comercial permitido |
| semantic-kernel | MIT | ✅ | Uso comercial permitido |
| pgvector | PostgreSQL | ✅ | Permisivo, similar a MIT |
| text-generation-webui | AGPL 3.0 | ⚠️ | Copyleft fuerte, evaluar uso |

### Recomendaciones

1. **Licencias MIT y Apache 2.0**: Totalmente compatibles para uso comercial y modificación.
2. **MPL 2.0 (Coqui TTS)**: Compatible, pero cambios al código de Coqui deben compartirse.
3. **AGPL 3.0**: Usar con precaución - requiere liberar código si se usa como servicio.

---

## Estructura de Carpetas Propuesta

```
Kai/
├── docs/
│   ├── integrations.md          # Este documento
│   ├── architecture.md           # Arquitectura del sistema
│   └── api-reference.md          # Referencia de APIs
│
├── tools/
│   ├── setup/
│   │   ├── install-tts.sh       # Setup de Coqui TTS
│   │   ├── install-whisper.sh   # Setup de Whisper
│   │   ├── install-faiss.sh     # Setup de FAISS
│   │   └── setup-autotrain.sh   # Setup de Autotrain
│   │
│   ├── integrations/
│   │   ├── tts-adapter.py       # Adaptador para Coqui TTS
│   │   ├── whisper-adapter.py   # Adaptador para Whisper
│   │   ├── faiss-client.py      # Cliente de FAISS
│   │   └── langchain-tools.py   # Herramientas LangChain
│   │
│   └── deployment/
│       ├── deploy-dev.sh        # Despliegue desarrollo
│       ├── deploy-prod.sh       # Despliegue producción
│       └── terraform/           # Configs Terraform adicionales
│
├── src/
│   ├── adapters/                # Adaptadores de integración
│   │   ├── voice/
│   │   │   ├── tts.ts          # Interfaz TTS
│   │   │   └── stt.ts          # Interfaz STT (Whisper)
│   │   │
│   │   ├── memory/
│   │   │   ├── faiss.ts        # Búsqueda vectorial
│   │   │   └── pgvector.ts     # PostgreSQL vectorial
│   │   │
│   │   └── training/
│   │       └── autotrain.ts    # La Forja - Autotrain
│   │
│   └── services/
│       └── kaiTools.ts          # Herramientas existentes
│
└── tests/
    └── integrations/            # Tests de integración
        ├── tts.test.ts
        ├── whisper.test.ts
        └── faiss.test.ts
```

---

## Próximos Pasos

1. **Implementar adaptadores** en `src/adapters/` para cada servicio externo
2. **Crear scripts de setup** en `tools/setup/` para facilitar instalación
3. **Documentar APIs** de cada integración en `docs/api-reference.md`
4. **Añadir tests de integración** para validar cada dependencia
5. **Evaluar repositorios adicionales** marcados como 🔄
6. **Configurar CI/CD** para validar compatibilidad de dependencias

---

## Referencias

- [LangChain Documentation](https://python.langchain.com/)
- [Coqui TTS Documentation](https://tts.readthedocs.io/)
- [Whisper Documentation](https://github.com/openai/whisper#readme)
- [AutoTrain Documentation](https://huggingface.co/docs/autotrain/)
- [FAISS Documentation](https://faiss.ai/)
- [Terraform Google Modules](https://registry.terraform.io/namespaces/terraform-google-modules)

---

**Última actualización**: 2025-10-14  
**Mantenedor**: Equipo Kai  
**Versión del documento**: 1.0
