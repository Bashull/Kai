#!/data/data/com.termux/files/usr/bin/bash
set -e
BASE="https://raw.githubusercontent.com/Bashull/Kai/main/mobile/qwen-image-edit"
APP="$HOME/.qwen-image-edit"
BIN="$PREFIX/bin/qwen-edit"

echo "[1/5] Preparando Termux…"
pkg update -y
pkg install -y python curl

echo "[2/5] Instalando cliente ligero…"
python -m pip install --upgrade fastapi uvicorn python-multipart gradio_client

echo "[3/5] Descargando Qwen Image Edit Mobile…"
mkdir -p "$APP"
curl -fsSL "$BASE/app.py" -o "$APP/app.py"
curl -fsSL "$BASE/index.html" -o "$APP/index.html"
curl -fsSL "$BASE/qwen-edit" -o "$BIN"
chmod +x "$BIN"

echo "[4/5] Comprobando instalación…"
python -m py_compile "$APP/app.py"

echo "[5/5] Arrancando…"
qwen-edit restart
qwen-edit open

echo
echo "LISTO. A partir de ahora escribe: qwen-edit"
echo "Otros comandos: qwen-edit stop | status | logs | restart"
