#!/bin/bash

# KAI Companion - Script de instalación para macOS/Linux

echo ""
echo "======================================"
echo "  KAI Companion - Setup Assistant"
echo "======================================"
echo ""

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js no está instalado"
    echo ""
    echo "Instala desde: https://nodejs.org/"
    echo "O usa: brew install node"
    exit 1
fi

echo "[OK] Node.js detectado:"
node --version
echo ""

# Verificar npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm no está instalado"
    exit 1
fi

echo "[OK] npm detectado:"
npm --version
echo ""

# Crear directorios
echo "[*] Creando directorios..."
mkdir -p data/uploads data/tools logs
echo "[OK] Directorios creados"
echo ""

# Copiar .env.example
if [ ! -f ".env" ]; then
    echo "[*] Creando archivo .env..."
    cp .env.example .env
    echo "[OK] .env creado"
else
    echo "[OK] .env ya existe"
fi
echo ""

# Instalar dependencias backend
echo "[*] Instalando dependencias del backend..."
npm install || exit 1
echo "[OK] Backend listo"
echo ""

# Instalar dependencias frontend
echo "[*] Instalando dependencias del frontend..."
cd frontend
npm install || { cd ..; exit 1; }
cd ..
echo "[OK] Frontend listo"
echo ""

echo "======================================"
echo "  Setup completado exitosamente!"
echo "======================================"
echo ""
echo "Próximos pasos:"
echo "  1. Ejecuta: npm run dev"
echo "  2. Abre: http://localhost:3000"
echo ""
