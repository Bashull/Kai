#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PAIR_CODE="${1:-}"
DEVICE_NAME="${2:-}"
CLIENT_URL="https://raw.githubusercontent.com/Bashull/Kai/main/relay/v2/kai_termux_bridge.py"
CLIENT_BIN="$PREFIX/bin/kai-termux-bridge-v2"
ROOT="$HOME/.kai_termux_bridge_v2"
BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/kai-termux-bridge-v2"

if [ -z "$PAIR_CODE" ]; then
  echo "Usage: curl -fsSL https://raw.githubusercontent.com/Bashull/Kai/main/relay/v2/install.sh | bash -s -- <PAIR_CODE> [DEVICE_NAME]" >&2
  exit 2
fi

if ! command -v python >/dev/null 2>&1; then
  pkg install -y python
fi
if ! command -v curl >/dev/null 2>&1; then
  pkg install -y curl
fi
if ! command -v nohup >/dev/null 2>&1; then
  pkg install -y coreutils
fi

mkdir -p "$ROOT" "$BOOT_DIR"
chmod 700 "$ROOT" "$BOOT_DIR"

curl -fsSL "$CLIENT_URL" -o "$CLIENT_BIN"
chmod 700 "$CLIENT_BIN"

if [ -z "$DEVICE_NAME" ]; then
  DEVICE_NAME="$(getprop ro.product.model 2>/dev/null || true)"
  [ -n "$DEVICE_NAME" ] || DEVICE_NAME="$(hostname 2>/dev/null || echo termux-android)"
fi

"$CLIENT_BIN" stop >/dev/null 2>&1 || true
"$CLIENT_BIN" pair "$PAIR_CODE" "$DEVICE_NAME"

cat > "$BOOT_SCRIPT" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock >/dev/null 2>&1 || true
if ! pgrep -f "$PREFIX/bin/kai-termux-bridge-v2 run" >/dev/null 2>&1; then
  nohup "$PREFIX/bin/kai-termux-bridge-v2" run >> "$HOME/.kai_termux_bridge_v2/daemon.log" 2>&1 &
fi
EOF
chmod 700 "$BOOT_SCRIPT"

termux-wake-lock >/dev/null 2>&1 || true
nohup "$CLIENT_BIN" run >> "$ROOT/daemon.log" 2>&1 &
sleep 3

"$CLIENT_BIN" status

echo
echo "Kai Termux Bridge v2 installed and started."
echo "Status: $CLIENT_BIN status"
echo "Logs:   tail -f $ROOT/agent.log"
echo "Stop:   $CLIENT_BIN stop"
echo "Boot hook installed at: $BOOT_SCRIPT"
