#!/bin/bash

# Script de configuración para Autotrain Advanced
# Configura La Forja - el sistema de entrenamiento de Kai

set -e

echo "⚒️ Configurando Autotrain Advanced (La Forja) para Kai..."

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

# Instalar Autotrain
echo "⬇️ Instalando Autotrain Advanced..."
pip install --upgrade pip
pip install autotrain-advanced

# Instalar dependencias adicionales para diferentes tareas
echo "📦 Instalando dependencias adicionales..."
pip install torch transformers datasets

# Verificar instalación
echo "✅ Verificando instalación..."
autotrain --version

# Crear directorio de configuración
mkdir -p ~/.autotrain
mkdir -p ./forja-data/{datasets,models,logs}

echo "✅ ¡Autotrain Advanced instalado correctamente!"
echo ""
echo "📁 Estructura de La Forja creada:"
echo "  ./forja-data/datasets/ - Conjuntos de datos para entrenamiento"
echo "  ./forja-data/models/   - Modelos entrenados"
echo "  ./forja-data/logs/     - Registros de entrenamiento"
echo ""
echo "Uso básico:"
echo "  # Entrenamiento de clasificación de texto"
echo "  autotrain --task text-classification \\"
echo "    --model bert-base-uncased \\"
echo "    --data ./forja-data/datasets/train.csv \\"
echo "    --output ./forja-data/models/my-model"
echo ""
echo "  # Fine-tuning de LLM"
echo "  autotrain llm --train \\"
echo "    --model meta-llama/Llama-2-7b-hf \\"
echo "    --data-path ./forja-data/datasets/ \\"
echo "    --output ./forja-data/models/kai-llm"
echo ""
echo "🔗 Recursos:"
echo "  - Documentación: https://huggingface.co/docs/autotrain/"
echo "  - Hugging Face Hub: https://huggingface.co/models"
