#!/usr/bin/env bash
set -euo pipefail

KAI_BRIDGE_ROOT=${KAI_BRIDGE_ROOT:-"$HOME/.kai/mobile-bridge"}
KAI_APPS_FILE=${KAI_APPS_FILE:-"$KAI_BRIDGE_ROOT/config/apps.tsv"}

bridge_json_ok() {
  printf '{"ok":true,"bridge":"kai-mobile","version":"0.1.0"}\n'
}

resolve_component_for_package() {
  local package=${1-}
  [[ -f "$KAI_APPS_FILE" ]] || return 1
  awk -F '\t' -v p="$package" '$2 == p { print $3; found=1; exit } END { if (!found) exit 1 }' "$KAI_APPS_FILE"
}

adb_state() {
  command -v adb >/dev/null 2>&1 || return 1
  adb get-state 2>/dev/null
}
