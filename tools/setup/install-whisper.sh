#!/bin/bash

# Script de instalación para OpenAI Whisper
# Instala y configura el sistema de reconocimiento de voz para Kai

set -e

echo "🎤 Instalando OpenAI Whisper para Kai..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado. Por favor, instala Python 3.8 o superior."
    exit 1
fi

# Verificar ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ Advertencia: ffmpeg no está instalado. Se requiere para procesar audio."
    echo "Instálalo con:"
    echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar Whisper
echo "⬇️ Instalando Whisper..."
pip install --upgrade pip
pip install -U openai-whisper

# Verificar instalación
echo "✅ Verificando instalación..."
whisper --help

echo "✅ ¡OpenAI Whisper instalado correctamente!"
echo ""
echo "Modelos disponibles:"
echo "  - tiny: Más rápido, menos preciso"
echo "  - base: Balance entre velocidad y precisión"
echo "  - small: Buena precisión"
echo "  - medium: Alta precisión (recomendado para Kai)"
echo "  - large: Máxima precisión (requiere GPU potente)"
echo ""
echo "Uso básico:"
echo "  whisper audio.mp3 --model medium --language Spanish"
echo ""
echo "Para transcribir con timestamps:"
echo "  whisper audio.mp3 --model medium --language Spanish --task transcribe"
