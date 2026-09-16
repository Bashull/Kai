#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PREFIX:-}" ]]; then
  printf 'BLOCKED: PREFIX is empty; this bootstrap must run inside Termux.\n' >&2
  exit 69
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BRIDGE_ROOT=${KAI_BRIDGE_ROOT:-"$HOME/.kai/mobile-bridge"}
PACKAGES=(
  termux-tools git curl jq openssh python nodejs-lts
  termux-api termux-services android-tools tmux rsync ripgrep
)

for required in \
  "$SCRIPT_DIR/kai-mobile" \
  "$SCRIPT_DIR/lib/common.sh" \
  "$SCRIPT_DIR/lib/android.sh" \
  "$SCRIPT_DIR/config/apps.tsv" \
  "$SCRIPT_DIR/boot/10-kai-mobile-bridge"; do
  [[ -f "$required" ]] || { printf 'BLOCKED: required bridge file missing: %s\n' "$required" >&2; exit 66; }
done

mkdir -p \
  "$BRIDGE_ROOT/bin" \
  "$BRIDGE_ROOT/lib" \
  "$BRIDGE_ROOT/config" \
  "$BRIDGE_ROOT/state" \
  "$BRIDGE_ROOT/logs" \
  "$BRIDGE_ROOT/private" \
  "$HOME/.termux/boot" \
  "$PREFIX/bin"
chmod 700 "$BRIDGE_ROOT/private"

pkg update -y
pkg upgrade -y
pkg install -y "${PACKAGES[@]}"

cp "$SCRIPT_DIR/kai-mobile" "$BRIDGE_ROOT/bin/kai-mobile"
cp "$SCRIPT_DIR/lib/common.sh" "$BRIDGE_ROOT/lib/common.sh"
cp "$SCRIPT_DIR/lib/android.sh" "$BRIDGE_ROOT/lib/android.sh"
cp "$SCRIPT_DIR/config/apps.tsv" "$BRIDGE_ROOT/config/apps.tsv"
cp "$SCRIPT_DIR/boot/10-kai-mobile-bridge" "$HOME/.termux/boot/10-kai-mobile-bridge"
chmod 700 "$BRIDGE_ROOT/bin/kai-mobile" "$HOME/.termux/boot/10-kai-mobile-bridge"
chmod 600 "$BRIDGE_ROOT/config/apps.tsv"
ln -sfn "$BRIDGE_ROOT/bin/kai-mobile" "$PREFIX/bin/kai-mobile"

info_present=false
if command -v termux-info >/dev/null 2>&1; then
  info_present=true
fi

now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > "$BRIDGE_ROOT/state/bootstrap-current.json" <<EOF
{"schema":"kai-termux-bootstrap-v1","classification":"OBSERVED","timestamp":"$now","prefix_present":true,"termux_info_available":$info_present}
EOF
chmod 600 "$BRIDGE_ROOT/state/bootstrap-current.json"

printf 'Kai Termux bootstrap complete.\n'
printf 'Bridge root: %s\n' "$BRIDGE_ROOT"
