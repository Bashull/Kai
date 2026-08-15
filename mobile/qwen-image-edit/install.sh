#!/data/data/com.termux/files/usr/bin/bash
set -e
BASE="https://raw.githubusercontent.com/Bashull/Kai/main/mobile/qwen-image-edit"
APP="$HOME/.qwen-image-edit"
BIN="$PREFIX/bin/qwen-edit"

echo "[1/4] Preparando Termux…"
pkg update -y
pkg install -y python curl

echo "[2/4] Instalando Qwen Image Edit Mobile…"
mkdir -p "$APP"
curl -fsSL "$BASE/index.html" -o "$APP/index.html"
curl -fsSL "$BASE/qwen-edit" -o "$BIN"
chmod +x "$BIN"

echo "[3/4] Comprobando archivos…"
test -s "$APP/index.html"
python -c "import http.server; print('Servidor Python OK')"

echo "[4/4] Arrancando editor…"
qwen-edit restart
qwen-edit open

echo
echo "LISTO. A partir de ahora escribe: qwen-edit"
echo "Otros comandos: qwen-edit stop | status | logs | restart"
