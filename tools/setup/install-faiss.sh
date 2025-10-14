#!/bin/bash

# Script de instalación para FAISS
# Instala y configura el sistema de búsqueda vectorial para memoria de Kai

set -e

echo "🔍 Instalando FAISS para Kai..."

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

# Instalar FAISS
echo "⬇️ Instalando FAISS..."
pip install --upgrade pip

# Detectar si hay GPU disponible
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 GPU detectada, instalando FAISS-GPU..."
    pip install faiss-gpu
else
    echo "💻 Instalando FAISS-CPU..."
    pip install faiss-cpu
fi

# Instalar dependencias adicionales
pip install numpy

# Crear script de prueba
cat > /tmp/test_faiss.py << 'EOF'
import faiss
import numpy as np

# Crear índice simple
dimension = 128
index = faiss.IndexFlatL2(dimension)

# Añadir vectores
vectors = np.random.random((100, dimension)).astype('float32')
index.add(vectors)

print(f"✅ FAISS funcionando correctamente!")
print(f"📊 Índice creado con {index.ntotal} vectores de dimensión {dimension}")

# Realizar búsqueda
query = np.random.random((1, dimension)).astype('float32')
distances, indices = index.search(query, k=5)
print(f"🔍 Búsqueda completada: encontrados {len(indices[0])} vecinos más cercanos")
EOF

# Ejecutar prueba
echo "✅ Verificando instalación..."
python /tmp/test_faiss.py

echo ""
echo "✅ ¡FAISS instalado correctamente!"
echo ""
echo "Uso básico en Python:"
echo "  import faiss"
echo "  import numpy as np"
echo ""
echo "  # Crear índice"
echo "  dimension = 768  # Dimensión de embeddings"
echo "  index = faiss.IndexFlatL2(dimension)"
echo ""
echo "  # Añadir vectores"
echo "  vectors = np.random.random((1000, dimension)).astype('float32')"
echo "  index.add(vectors)"
echo ""
echo "  # Búsqueda"
echo "  query = np.random.random((1, dimension)).astype('float32')"
echo "  distances, indices = index.search(query, k=5)"
