#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PREFIX:-}" ]]; then
  printf 'BLOCKED: PREFIX is empty; this bootstrap must run inside Termux.\n' >&2
  exit 69
fi

BRIDGE_ROOT=${KAI_BRIDGE_ROOT:-"$HOME/.kai/mobile-bridge"}
PACKAGES=(
  termux-tools git curl jq openssh python nodejs-lts
  termux-api termux-services android-tools tmux rsync ripgrep
)

mkdir -p \
  "$BRIDGE_ROOT/bin" \
  "$BRIDGE_ROOT/lib" \
  "$BRIDGE_ROOT/config" \
  "$BRIDGE_ROOT/state" \
  "$BRIDGE_ROOT/logs" \
  "$BRIDGE_ROOT/private"
chmod 700 "$BRIDGE_ROOT/private"

pkg update -y
pkg upgrade -y
pkg install -y "${PACKAGES[@]}"

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
