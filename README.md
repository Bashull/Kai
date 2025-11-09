# 🤖 Kai - Compañero Virtual Avanzado

Kai es un compañero virtual avanzado especializado en Dungeons & Dragons y asistencia general, con capacidades de memoria, razonamiento complejo y síntesis de voz.

## ✨ Características Principales

- 💬 **Conversación Natural**: Interacción fluida usando modelos de lenguaje avanzados (Gemini, GPT)
- 🧠 **Memoria a Largo Plazo**: Sistema de memoria persistente que almacena conocimientos, preferencias y conversaciones importantes
- 🔍 **Búsqueda Semántica**: Recuperación inteligente de recuerdos relevantes durante conversaciones
- 🎲 **Dungeons & Dragons**: Especialización en D&D 5e con generación de narrativa y gestión de campañas
- 🔊 **Síntesis de Voz**: Respuestas en audio usando Coqui TTS
- 🎤 **Reconocimiento de Voz**: Transcripción con OpenAI Whisper
- ⚒️ **La Forja**: Sistema de entrenamiento y fine-tuning de modelos con Autotrain Advanced
- 🔗 **Orquestación Avanzada**: Cadenas de razonamiento complejas con LangChain

---

## 🚀 Inicio Rápido

### Prerrequisitos

- **Node.js** 16+
- **Python** 3.8+
- **ffmpeg** (para procesamiento de audio)

### Instalación del Frontend

```bash
# 1. Instalar dependencias
npm install

# 2. Configurar API key de Gemini
# Crear archivo .env.local con:
# GEMINI_API_KEY=tu_api_key_aqui

# 3. Ejecutar aplicación
npm run dev
```

La aplicación estará disponible en `http://localhost:5173`

---

## 🔌 Integraciones y Dependencias

Kai integra múltiples tecnologías de IA y herramientas externas. Para documentación completa, consulta:

📚 **[Guía de Integraciones](docs/integrations.md)** - Documentación detallada de todas las dependencias

### Dependencias Principales

| Tecnología | Función | Estado |
|------------|---------|--------|
| [langchain](https://github.com/langchain-ai/langchain) | Cadenas de razonamiento y memoria | ✅ Integrado |
| [coqui-ai/TTS](https://github.com/coqui-ai/TTS) | Síntesis de voz | ✅ Integrado |
| [openai/whisper](https://github.com/openai/whisper) | Reconocimiento de voz | ✅ Integrado |
| [autotrain-advanced](https://github.com/huggingface/autotrain-advanced) | Entrenamiento de modelos | ✅ Integrado |
| [faiss](https://github.com/facebookresearch/faiss) | Búsqueda vectorial | ✅ Integrado |
| Terraform GCP Modules | Infraestructura cloud | ✅ Configurado |

### Instalación de Servicios Backend

```bash
# Síntesis de voz (Coqui TTS)
./tools/setup/install-tts.sh

# Reconocimiento de voz (Whisper)
./tools/setup/install-whisper.sh

# Búsqueda vectorial (FAISS)
./tools/setup/install-faiss.sh

# Sistema de entrenamiento (Autotrain)
./tools/setup/setup-autotrain.sh

# Orquestación con LangChain
pip install langchain openai
```

Consulta **[tools/README.md](tools/README.md)** para más detalles sobre cada integración.

---

## 🏗️ Arquitectura

```
Kai/
├── src/                    # Código fuente frontend (React + TypeScript)
│   ├── components/         # Componentes React
│   ├── services/           # Servicios (kaiTools, APIs)
│   └── store/              # Estado global (Zustand)
│
├── tools/                  # Herramientas e integraciones
│   ├── setup/              # Scripts de instalación
│   └── integrations/       # Adaptadores Python
│
├── docs/                   # Documentación
│   └── integrations.md     # Guía de integraciones
│
├── main.tf                 # Infraestructura Terraform (GCP)
└── index.tsx               # Punto de entrada
```

### Integraciones Disponibles

#### 🔊 Síntesis de Voz (TTS)
```python
from tools.integrations.tts_adapter import TTSAdapter

tts = TTSAdapter(model_name="tts_models/es/css10/vits")
tts.speak("Hola, soy Kai", output_path="greeting.wav")
```

#### 🎤 Reconocimiento de Voz (STT)
```python
from tools.integrations.whisper_adapter import WhisperAdapter

whisper = WhisperAdapter(model_size="medium")
result = whisper.transcribe("audio.mp3", language="es")
print(result['text'])
```

#### 🧠 Memoria Vectorial
```python
from tools.integrations.faiss_client import FAISSMemoryClient

memory = FAISSMemoryClient(dimension=768)
memory.add_memory(embedding, metadata={"text": "Recuerdo importante"})
ids, distances, metadata = memory.search(query_embedding, k=5)
```

#### 🔗 Orquestación LangChain
```python
from tools.integrations.langchain_tools import KaiLangChainTools

kai = KaiLangChainTools(llm=your_llm)
tools = kai.create_kai_tools()  # KaiMemory, DiceRoller, DnDRules
agent = kai.create_agent_with_tools(tools)
```

---

## 📦 Estructura de Carpetas para Integraciones

```
Kai/
├── tools/
│   ├── setup/
│   │   ├── install-tts.sh          # Setup Coqui TTS
│   │   ├── install-whisper.sh      # Setup Whisper
│   │   ├── install-faiss.sh        # Setup FAISS
│   │   └── setup-autotrain.sh      # Setup Autotrain
│   │
│   └── integrations/
│       ├── tts-adapter.py          # Adaptador TTS
│       ├── whisper-adapter.py      # Adaptador Whisper
│       ├── faiss-client.py         # Cliente FAISS
│       └── langchain-tools.py      # Herramientas LangChain
│
├── src/adapters/                   # Adaptadores TypeScript (próximamente)
│   ├── voice/
│   ├── memory/
│   └── training/
│
└── forja-data/                     # Datos de La Forja (autogenerado)
    ├── datasets/
    ├── models/
    └── logs/
```

---

## 🎮 Uso

### Modo Conversación General
Interactúa con Kai como asistente personal. Kai puede recordar contexto de conversaciones anteriores gracias a su sistema de memoria a largo plazo.

### Sistema de Memoria a Largo Plazo 🧠

Kai cuenta con un avanzado sistema de memoria persistente que le permite recordar información importante a través de las sesiones:

#### Tipos de Recuerdos
- **Conversaciones**: Resúmenes de conversaciones importantes
- **Conocimientos**: Información y hechos aprendidos
- **Preferencias**: Gustos y preferencias del usuario
- **Eventos**: Acontecimientos significativos

#### Características
- **Creación Automática**: Al resumir conversaciones en el chat, se crean automáticamente recuerdos
- **Creación Manual**: Añade recuerdos manualmente desde el panel de Memoria
- **Búsqueda y Filtrado**: Encuentra recuerdos específicos por contenido, tipo o etiquetas
- **Contexto Inteligente**: Los recuerdos relevantes se incluyen automáticamente en las conversaciones
- **Persistencia**: Todos los recuerdos se guardan en localStorage y persisten entre sesiones

#### Cómo Usar
1. **Chat con contexto**: Kai recupera automáticamente recuerdos relevantes durante las conversaciones
2. **Resumir conversaciones**: Usa el botón "Archivar" en el chat cuando tengas 6+ mensajes
3. **Panel de Memoria**: Accede al panel "Memoria" para ver, buscar y gestionar todos tus recuerdos
4. **Añadir recuerdos**: Crea recuerdos manualmente con información importante

### Modo Dungeons & Dragons
Kai actúa como Dungeon Master, generando narrativa dinámica, gestionando NPCs y facilitando sesiones de D&D 5e.

### La Forja (Training)
Sistema de fine-tuning de modelos con tus propios datos usando Autotrain Advanced.

---

## 🌐 Despliegue en Cloud

Kai incluye configuración Terraform para despliegue en Google Cloud Platform:

```bash
# Inicializar Terraform
terraform init

# Planificar despliegue
terraform plan -var-file="input.tfvars"

# Aplicar infraestructura
terraform apply -var-file="input.tfvars"
```

**Servicios desplegados:**
- Cloud Run (orquestador multi-agente)
- Secret Manager (gestión de API keys)
- Cloud SQL PostgreSQL (base de datos)
- Cloud Memorystore Redis (caché)
- Load Balancer (balanceo de carga)

---

## 🔐 Seguridad

- **API Keys**: Almacenadas en Google Secret Manager
- **Autenticación**: Configuración IAM en GCP
- **Datos sensibles**: No se commitean en el repositorio
- **Variables de entorno**: Usar `.env.local` (gitignored)

---

## 📚 Documentación

- **[Guía de Integraciones](docs/integrations.md)** - Todas las dependencias y cómo usarlas
- **[Tools README](tools/README.md)** - Adaptadores y scripts de setup
- **Arquitectura** (próximamente) - Diseño del sistema
- **API Reference** (próximamente) - Referencia de APIs

---

## 🛠️ Desarrollo

### Comandos útiles

```bash
# Desarrollo frontend
npm run dev          # Ejecutar en modo desarrollo
npm run build        # Compilar para producción
npm run preview      # Vista previa de build

# Testing integraciones
python tools/integrations/tts-adapter.py
python tools/integrations/whisper-adapter.py audio.mp3
python tools/integrations/faiss-client.py
python tools/integrations/langchain-tools.py
```

### Añadir nuevas integraciones

1. Crear adaptador en `tools/integrations/`
2. Crear script de setup en `tools/setup/`
3. Documentar en `docs/integrations.md`
4. Actualizar este README

---

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Licencias

Kai integra múltiples proyectos de código abierto:

| Dependencia | Licencia | Compatible |
|-------------|----------|------------|
| langchain | MIT | ✅ |
| coqui-ai/TTS | MPL 2.0 | ✅ |
| openai/whisper | MIT | ✅ |
| autotrain-advanced | Apache 2.0 | ✅ |
| faiss | MIT | ✅ |
| Terraform GCP Modules | Apache 2.0 | ✅ |

Ver [docs/integrations.md](docs/integrations.md) para más detalles sobre compatibilidad de licencias.

---

## 🙏 Agradecimientos

- [LangChain](https://github.com/langchain-ai/langchain) - Framework de razonamiento
- [Coqui AI](https://github.com/coqui-ai/TTS) - Síntesis de voz
- [OpenAI Whisper](https://github.com/openai/whisper) - Reconocimiento de voz
- [Hugging Face](https://huggingface.co/) - Modelos y herramientas de ML
- [Meta AI - FAISS](https://github.com/facebookresearch/faiss) - Búsqueda vectorial
- [Google Cloud Platform](https://cloud.google.com/) - Infraestructura

---

## 📧 Contacto

- **Proyecto**: [github.com/Bashull/Kai](https://github.com/Bashull/Kai)
- **Issues**: [github.com/Bashull/Kai/issues](https://github.com/Bashull/Kai/issues)

---

**¡Gracias por usar Kai!** 🤖✨
