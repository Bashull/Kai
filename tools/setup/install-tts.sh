#!/bin/bash

# Script de instalación para Coqui TTS
# Instala y configura el sistema de síntesis de voz para Kai

set -e

echo "🔊 Instalando Coqui TTS para Kai..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado. Por favor, instala Python 3.8 o superior."
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar TTS
echo "⬇️ Instalando TTS..."
pip install --upgrade pip
pip install TTS

# Verificar instalación
echo "✅ Verificando instalación..."
tts --list_models

# Descargar modelo en español (opcional)
echo "🌍 Descargando modelo en español..."
tts --model_name "tts_models/es/css10/vits" --text "Prueba" --out_path /tmp/test.wav

echo "✅ ¡Coqui TTS instalado correctamente!"
echo ""
echo "Uso básico:"
echo "  tts --text 'Hola, soy Kai' --model_name 'tts_models/es/css10/vits' --out_path output.wav"
echo ""
echo "Para ver todos los modelos disponibles:"
echo "  tts --list_models"
