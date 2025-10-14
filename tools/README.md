# 🛠️ Herramientas de Kai

Este directorio contiene scripts de instalación, adaptadores de integración y utilidades para el ecosistema de Kai.

## 📁 Estructura

```
tools/
├── setup/              # Scripts de instalación
├── integrations/       # Adaptadores de integración Python
└── deployment/         # Scripts de despliegue (próximamente)
```

---

## 🔧 Scripts de Instalación (`setup/`)

Scripts automatizados para instalar y configurar dependencias externas.

### `install-tts.sh`
Instala **Coqui TTS** para síntesis de voz.

```bash
./tools/setup/install-tts.sh
```

**Funcionalidad:**
- Crea entorno virtual Python
- Instala Coqui TTS
- Descarga modelo en español
- Verifica instalación

### `install-whisper.sh`
Instala **OpenAI Whisper** para reconocimiento de voz.

```bash
./tools/setup/install-whisper.sh
```

**Funcionalidad:**
- Verifica dependencias (ffmpeg)
- Instala Whisper
- Muestra modelos disponibles

### `install-faiss.sh`
Instala **FAISS** para búsqueda vectorial.

```bash
./tools/setup/install-faiss.sh
```

**Funcionalidad:**
- Detecta GPU disponible
- Instala FAISS-CPU o FAISS-GPU según hardware
- Ejecuta prueba de funcionamiento

### `setup-autotrain.sh`
Configura **Autotrain Advanced** (La Forja).

```bash
./tools/setup/setup-autotrain.sh
```

**Funcionalidad:**
- Instala Autotrain Advanced
- Crea estructura de directorios para La Forja
- Configura entorno de entrenamiento

---

## 🔌 Adaptadores de Integración (`integrations/`)

Adaptadores Python que proporcionan interfaces unificadas para servicios externos.

### `tts-adapter.py`
Adaptador para Coqui TTS.

```python
from tools.integrations.tts_adapter import TTSAdapter

# Inicializar
adapter = TTSAdapter(model_name="tts_models/es/css10/vits")

# Generar voz
audio_file = adapter.speak(
    "Hola, soy Kai",
    output_path="kai_greeting.wav"
)
```

**Características:**
- Soporte multi-idioma
- Selección de speakers
- Generación de audio a partir de texto

### `whisper-adapter.py`
Adaptador para OpenAI Whisper.

```python
from tools.integrations.whisper_adapter import WhisperAdapter

# Inicializar
adapter = WhisperAdapter(model_size="medium")

# Transcribir audio
result = adapter.transcribe("audio.mp3", language="es")
print(result['text'])

# Con timestamps
segments = adapter.transcribe_with_timestamps("audio.mp3")
for seg in segments:
    print(f"[{seg['start']}s]: {seg['text']}")
```

**Características:**
- Transcripción con/sin timestamps
- Detección automática de idioma
- Múltiples tamaños de modelo

### `faiss-client.py`
Cliente para gestión de memoria vectorial con FAISS.

```python
from tools.integrations.faiss_client import FAISSMemoryClient

# Inicializar
client = FAISSMemoryClient(dimension=768)

# Añadir recuerdo
embedding = model.encode("El usuario prefiere D&D")
client.add_memory(embedding, metadata={
    "text": "El usuario prefiere D&D",
    "type": "preference"
})

# Buscar recuerdos similares
query_embedding = model.encode("qué le gusta al usuario?")
ids, distances, metadata = client.search(query_embedding, k=5)

# Guardar/cargar índice
client.save("kai_memory")
client.load("kai_memory")
```

**Características:**
- Múltiples tipos de índice (FlatL2, IVFFlat, HNSW)
- Soporte GPU
- Persistencia de índice y metadata
- Búsqueda por similitud vectorial

### `langchain-tools.py`
Herramientas LangChain para orquestación de Kai.

```python
from tools.integrations.langchain_tools import KaiLangChainTools

# Inicializar
kai_tools = KaiLangChainTools(llm=your_llm)

# Crear cadena de conversación
conversation = kai_tools.create_conversation_chain()

# Crear cadena para D&D
dnd_chain = kai_tools.create_dnd_campaign_chain()

# Obtener herramientas predefinidas
tools = KaiLangChainTools.create_kai_tools()
# Incluye: KaiMemory, DiceRoller, DnDRules

# Crear agente con herramientas
agent = kai_tools.create_agent_with_tools(tools)
```

**Características:**
- Cadenas de conversación con memoria
- Generación de campañas D&D
- RAG para búsqueda en memoria
- Herramientas predefinidas (dados, reglas D&D)
- Agentes con múltiples herramientas

---

## 🚀 Uso Rápido

### Instalación completa

```bash
# Instalar todas las dependencias
cd /home/runner/work/Kai/Kai

# Síntesis de voz
./tools/setup/install-tts.sh

# Reconocimiento de voz
./tools/setup/install-whisper.sh

# Búsqueda vectorial
./tools/setup/install-faiss.sh

# Entrenamiento de modelos
./tools/setup/setup-autotrain.sh

# LangChain (orquestación)
pip install langchain openai
```

### Ejemplo de integración completa

```python
# main.py - Ejemplo de uso completo

from tools.integrations.tts_adapter import TTSAdapter
from tools.integrations.whisper_adapter import WhisperAdapter
from tools.integrations.faiss_client import FAISSMemoryClient
from tools.integrations.langchain_tools import KaiLangChainTools

# 1. Configurar voz
tts = TTSAdapter()
stt = WhisperAdapter(model_size="medium")

# 2. Configurar memoria
memory = FAISSMemoryClient(dimension=768)

# 3. Configurar orquestación
kai = KaiLangChainTools(llm=your_llm)
conversation = kai.create_conversation_chain()

# 4. Ciclo de interacción
def interact_with_kai(audio_input_path):
    # Transcribir voz del usuario
    user_text = stt.transcribe(audio_input_path)['text']
    print(f"Usuario: {user_text}")
    
    # Buscar recuerdos relevantes
    query_embedding = your_embedding_model.encode(user_text)
    relevant_memories = memory.search(query_embedding, k=3)
    
    # Generar respuesta con contexto
    response = conversation.predict(input=user_text)
    print(f"Kai: {response}")
    
    # Sintetizar respuesta a voz
    audio_output = tts.speak(response, output_path="kai_response.wav")
    
    # Guardar interacción en memoria
    interaction_embedding = your_embedding_model.encode(
        f"Usuario: {user_text}\nKai: {response}"
    )
    memory.add_memory(interaction_embedding, metadata={
        "user_input": user_text,
        "kai_response": response,
        "timestamp": datetime.now().isoformat()
    })
    
    return audio_output

# Usar
interact_with_kai("user_audio.mp3")
```

---

## 📋 Requisitos

### Sistema Operativo
- Linux (Ubuntu/Debian recomendado)
- macOS
- Windows con WSL2

### Software
- Python 3.8+
- Node.js 16+ (para frontend)
- ffmpeg (para procesamiento de audio)
- CUDA (opcional, para GPU)

### Python Packages
```bash
pip install TTS openai-whisper faiss-cpu langchain transformers
```

### Node Packages
```bash
npm install @google/genai
```

---

## 🧪 Testing

Cada adaptador puede ejecutarse de forma independiente para testing:

```bash
# Test TTS
python tools/integrations/tts-adapter.py

# Test Whisper (requiere archivo audio)
python tools/integrations/whisper-adapter.py audio.mp3

# Test FAISS
python tools/integrations/faiss-client.py

# Test LangChain
python tools/integrations/langchain-tools.py
```

---

## 📚 Documentación Adicional

- [Integrations Guide](../docs/integrations.md) - Documentación completa de todas las integraciones
- [Architecture](../docs/architecture.md) - Arquitectura del sistema Kai (próximamente)
- [API Reference](../docs/api-reference.md) - Referencia de APIs (próximamente)

---

## 🤝 Contribuir

Para añadir nuevos adaptadores o scripts:

1. Crear script en directorio apropiado (`setup/` o `integrations/`)
2. Seguir convenciones de nomenclatura existentes
3. Incluir documentación en docstrings
4. Añadir ejemplo de uso en `__main__`
5. Actualizar este README

---

## 🐛 Troubleshooting

### Error: "TTS no está instalado"
```bash
./tools/setup/install-tts.sh
```

### Error: "ffmpeg no encontrado"
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Error: "CUDA no disponible"
FAISS funcionará en modo CPU. Para usar GPU:
- Instalar NVIDIA drivers
- Instalar CUDA Toolkit
- Reinstalar con: `pip install faiss-gpu`

---

**Última actualización**: 2025-10-14  
**Mantenedor**: Equipo Kai
