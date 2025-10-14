# 🚀 Guía de Configuración Completa - Kai

Esta guía te ayudará a configurar Kai desde cero con todas sus integraciones.

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración del Frontend](#configuración-del-frontend)
3. [Configuración de Integraciones Python](#configuración-de-integraciones-python)
4. [Configuración de Infraestructura GCP](#configuración-de-infraestructura-gcp)
5. [Verificación de Instalación](#verificación-de-instalación)
6. [Troubleshooting](#troubleshooting)

---

## 1️⃣ Requisitos Previos

### Software Base

- **Node.js** 16 o superior ([Descargar](https://nodejs.org/))
- **Python** 3.8 o superior ([Descargar](https://www.python.org/))
- **npm** o **yarn** (incluido con Node.js)
- **Git** ([Descargar](https://git-scm.com/))

### Dependencias del Sistema

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv ffmpeg build-essential
```

#### macOS
```bash
brew install ffmpeg python
```

#### Windows (con WSL2)
```bash
# En WSL2 Ubuntu
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv ffmpeg build-essential
```

### Opcional: GPU Support

Para acelerar FAISS y procesamiento de voz:

```bash
# Verificar CUDA
nvidia-smi

# Instalar CUDA Toolkit (si no está instalado)
# Seguir: https://developer.nvidia.com/cuda-downloads
```

---

## 2️⃣ Configuración del Frontend

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/Bashull/Kai.git
cd Kai
```

### Paso 2: Instalar Dependencias Node

```bash
npm install
```

### Paso 3: Configurar Variables de Entorno

Crear archivo `.env.local`:

```bash
cat > .env.local << 'EOF'
# Gemini API Key (requerido)
GEMINI_API_KEY=tu_gemini_api_key_aqui

# Opcional: Otras API keys
OPENAI_API_KEY=tu_openai_api_key
ANTHROPIC_API_KEY=tu_anthropic_api_key

# Configuración de desarrollo
NODE_ENV=development
VITE_API_URL=http://localhost:5173
EOF
```

**Obtener API Keys:**
- Gemini: https://makersuite.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/

### Paso 4: Ejecutar Frontend

```bash
npm run dev
```

Acceder a: http://localhost:5173

---

## 3️⃣ Configuración de Integraciones Python

### Paso 1: Crear Entorno Virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Paso 2: Instalar Dependencias Python Base

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 3: Instalar Integraciones Específicas

#### 🔊 Síntesis de Voz (Coqui TTS)

```bash
./tools/setup/install-tts.sh
```

**Verificar:**
```bash
tts --list_models
tts --text "Hola, soy Kai" --model_name "tts_models/es/css10/vits" --out_path test.wav
```

#### 🎤 Reconocimiento de Voz (Whisper)

```bash
./tools/setup/install-whisper.sh
```

**Verificar:**
```bash
whisper --help
# Con un archivo de audio:
# whisper audio.mp3 --model base --language Spanish
```

#### 🧠 Búsqueda Vectorial (FAISS)

```bash
./tools/setup/install-faiss.sh
```

**Verificar:**
```bash
python tools/integrations/faiss-client.py
```

#### ⚒️ Entrenamiento de Modelos (Autotrain)

```bash
./tools/setup/setup-autotrain.sh
```

**Verificar:**
```bash
autotrain --version
```

#### 🔗 Orquestación (LangChain)

```bash
pip install langchain langchain-community langchain-core
pip install openai  # Para usar GPT
pip install google-generativeai  # Para usar Gemini
```

**Verificar:**
```bash
python tools/integrations/langchain-tools.py
```

---

## 4️⃣ Configuración de Infraestructura GCP

### Prerrequisitos

- Cuenta de Google Cloud Platform
- `gcloud` CLI instalado ([Guía](https://cloud.google.com/sdk/docs/install))
- Terraform instalado ([Descargar](https://www.terraform.io/downloads))

### Paso 1: Autenticación

```bash
# Autenticar con GCP
gcloud auth login
gcloud auth application-default login

# Configurar proyecto
gcloud config set project gen-lang-client-0592741070
```

### Paso 2: Configurar Terraform

```bash
# Inicializar Terraform
terraform init

# Revisar plan
terraform plan -var-file="input.tfvars"

# Aplicar infraestructura
terraform apply -var-file="input.tfvars"
```

### Paso 3: Configurar Secretos

```bash
# Añadir API key de OpenAI
echo -n "tu_openai_api_key" | gcloud secrets create openai-chatgpt-api-key \
    --data-file=- \
    --project=gen-lang-client-0592741070
```

---

## 5️⃣ Verificación de Instalación

### Checklist de Verificación

#### Frontend
```bash
✅ npm run dev            # Debe iniciar sin errores
✅ npm run build          # Debe compilar exitosamente
```

#### Backend Python
```bash
✅ python tools/integrations/tts-adapter.py
✅ python tools/integrations/faiss-client.py
✅ python tools/integrations/langchain-tools.py
```

#### Integraciones de Voz
```bash
# TTS
✅ tts --text "Test" --model_name "tts_models/es/css10/vits" --out_path /tmp/test.wav

# Whisper (requiere archivo de audio)
✅ whisper test.wav --model base
```

### Script de Verificación Completa

Crear y ejecutar:

```bash
cat > verify-setup.sh << 'EOF'
#!/bin/bash
echo "🔍 Verificando instalación de Kai..."

# Verificar Node.js
echo -n "Node.js: "
node --version || echo "❌ No instalado"

# Verificar Python
echo -n "Python: "
python3 --version || echo "❌ No instalado"

# Verificar ffmpeg
echo -n "ffmpeg: "
ffmpeg -version > /dev/null 2>&1 && echo "✅ Instalado" || echo "❌ No instalado"

# Verificar dependencias Python
echo "Verificando paquetes Python..."
python3 << 'PYEOF'
packages = ['TTS', 'whisper', 'faiss', 'langchain', 'transformers']
for pkg in packages:
    try:
        __import__(pkg)
        print(f"✅ {pkg}")
    except ImportError:
        print(f"❌ {pkg} no instalado")
PYEOF

# Verificar npm packages
echo "Verificando paquetes Node..."
npm list @google/genai --depth=0 > /dev/null 2>&1 && echo "✅ @google/genai" || echo "❌ @google/genai"

echo ""
echo "✅ Verificación completa!"
EOF

chmod +x verify-setup.sh
./verify-setup.sh
```

---

## 6️⃣ Troubleshooting

### Problemas Comunes

#### Error: "TTS no está instalado"

```bash
# Solución
./tools/setup/install-tts.sh
# o manualmente:
pip install TTS
```

#### Error: "ffmpeg not found"

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows (WSL2)
sudo apt-get install ffmpeg
```

#### Error: "CUDA not available"

Si no tienes GPU, FAISS funcionará en modo CPU (más lento pero funcional).

Para usar GPU:
1. Instalar [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
2. Reinstalar FAISS: `pip uninstall faiss-cpu && pip install faiss-gpu`

#### Error: "ModuleNotFoundError"

```bash
# Asegurarse de estar en el entorno virtual
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

#### Error: "npm ERR! peer dependency"

```bash
# Limpiar caché y reinstalar
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

#### Error al compilar TypeScript

```bash
# Verificar versión de TypeScript
npm list typescript

# Reinstalar TypeScript
npm install -D typescript@~5.7.2
```

### Logs de Debug

#### Frontend
```bash
# Ver logs detallados
npm run dev -- --debug

# Ver errores de compilación
npm run build 2>&1 | tee build.log
```

#### Python
```bash
# Activar logs verbose
export PYTHONVERBOSE=1
python tools/integrations/tts-adapter.py
```

### Contacto de Soporte

Si encuentras problemas no resueltos:

1. **Issues GitHub**: https://github.com/Bashull/Kai/issues
2. **Discusiones**: https://github.com/Bashull/Kai/discussions
3. **Documentación**: [docs/integrations.md](integrations.md)

---

## 📚 Próximos Pasos

Una vez completada la instalación:

1. **Explorar la UI**: Navega por las diferentes secciones (Chat, D&D, Kernel, Forja)
2. **Probar Integraciones**: Ejecuta los ejemplos de cada adaptador
3. **Personalizar Kai**: Modifica prompts y configura preferencias
4. **Entrenar Modelos**: Usa La Forja para fine-tuning
5. **Leer Documentación**: [docs/integrations.md](integrations.md)

---

## 🎉 ¡Listo!

Kai está ahora completamente configurado. ¡Disfruta de tu compañero virtual!

```
  _  __     _    ___  
 | |/ /__ _(_)  / _ \ 
 | ' </ _` | | | | | |
 | . \ (_| | | | |_| |
 |_|\_\__,_|_|  \___/ 
                      
 🤖 Tu compañero virtual está listo
```

---

**Última actualización**: 2025-10-14  
**Versión**: 1.0.0
