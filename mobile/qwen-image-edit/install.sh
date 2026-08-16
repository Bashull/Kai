#!/data/data/com.termux/files/usr/bin/bash
set -e
BASE="https://raw.githubusercontent.com/Bashull/Kai/main/mobile/qwen-image-edit"
APP="$HOME/.qwen-image-edit"
TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
BIN="$TERMUX_PREFIX/bin/qwen-edit"
ASSETS="index.html app.mjs state.mjs manifest.webmanifest sw.js icon.svg server.py"

echo "[1/4] Preparando Termux…"
pkg update -y
pkg install -y python curl

echo "[2/4] Instalando Kai Edit Mobile…"
mkdir -p "$APP" "$TERMUX_PREFIX/bin"
for asset in $ASSETS; do
  curl -fsSL "$BASE/$asset" -o "$APP/$asset"
done
curl -fsSL "$BASE/qwen-edit" -o "$BIN"
chmod 755 "$BIN"

echo "[3/4] Comprobando archivos…"
for asset in $ASSETS; do test -s "$APP/$asset"; done
test -x "$BIN"
python -c "import http.server; print('Servidor Python OK')"

echo "[4/4] Arrancando Kai Edit…"
"$BIN" restart
"$BIN" open

echo "LISTO · escribe: qwen-edit"
