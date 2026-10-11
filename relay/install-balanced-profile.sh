#!/data/data/com.termux/files/usr/bin/sh
set -eu

SELF_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BASE="$HOME/.kai_mobile"
SERVICE="/data/data/com.termux/files/usr/var/service/kai-minecraft-live"
STAMP="$(date +%Y%m%dT%H%M%S)"

mkdir -p "$BASE/bin" "$BASE/profiles" "$BASE/backups" "$BASE/benchmarks"
chmod 700 "$BASE/bin" "$BASE/profiles" "$BASE/backups"

backup_if_exists() {
  src="$1"
  label="$2"
  if [ -e "$src" ] || [ -L "$src" ]; then
    cp -p "$src" "$BASE/backups/$label.$STAMP"
  fi
}

backup_if_exists "$BASE/kai_minecraft_live.py" "kai_minecraft_live.py"
backup_if_exists "$SERVICE/run" "kai-minecraft-live.run"

install -m 700 "$SELF_DIR/kai_minecraft_live.py" "$BASE/kai_minecraft_live.py"
install -m 700 "$SELF_DIR/kai_balanced_probe.py" "$BASE/kai_balanced_probe.py"
install -m 700 "$SELF_DIR/kai-profile" "$BASE/bin/kai-profile"
install -m 700 "$SELF_DIR/kai-codex-balanced" "$BASE/bin/kai-codex-balanced"
install -m 600 "$SELF_DIR/profiles/balanced.env" "$BASE/profiles/balanced.env"

mkdir -p "$SERVICE"
install -m 700 "$SELF_DIR/services/kai-minecraft-live.run" "$SERVICE/run"
ln -sfn balanced.env "$BASE/profiles/active.env"

if [ ! -f "$BASE/hardware.env" ]; then
  cat > "$BASE/hardware.env" <<'EOF'
# Device-local overrides only. Do not commit secrets or pairing data.
# Verified S24 example:
# export KAI_LIVE_VIDEO_ENCODER=c2.qti.avc.encoder
EOF
  chmod 600 "$BASE/hardware.env"
fi

python -m py_compile "$BASE/kai_minecraft_live.py" "$BASE/kai_balanced_probe.py"
sh -n "$BASE/bin/kai-profile" "$BASE/bin/kai-codex-balanced" "$SERVICE/run"

echo "Balanced profile installed but not restarted automatically."
echo "Review $BASE/hardware.env, then run: $BASE/bin/kai-profile apply balanced"
