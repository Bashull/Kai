#!/usr/bin/env bash
set -euo pipefail

KAI_BRIDGE_ROOT=${KAI_BRIDGE_ROOT:-"$HOME/.kai/mobile-bridge"}
KAI_APPS_FILE=${KAI_APPS_FILE:-"$KAI_BRIDGE_ROOT/config/apps.tsv"}
KAI_ACTION_LOCK="$KAI_BRIDGE_ROOT/state/action.lock"

bridge_ensure_dirs() {
  mkdir -p "$KAI_BRIDGE_ROOT/state" "$KAI_BRIDGE_ROOT/logs" "$KAI_BRIDGE_ROOT/private"
  chmod 700 "$KAI_BRIDGE_ROOT/private" 2>/dev/null || true
}

json_escape() {
  local value=${1-}
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  printf '%s' "$value"
}

bridge_log() {
  local event=${1-unknown}
  local status=${2-unknown}
  local detail=${3-}
  local lowered=${detail,,}
  case "$lowered" in
    *token*|*secret*|*password*|*authorization*|*cookie*|*pairing*) detail='[REDACTED]' ;;
  esac
  bridge_ensure_dirs
  printf '{"timestamp":"%s","event":"%s","status":"%s","detail":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "$(json_escape "$event")" \
    "$(json_escape "$status")" \
    "$(json_escape "$detail")" >> "$KAI_BRIDGE_ROOT/logs/events.jsonl"
  chmod 600 "$KAI_BRIDGE_ROOT/logs/events.jsonl" 2>/dev/null || true
}

assert_bridge_active() {
  [[ ! -e "$KAI_BRIDGE_ROOT/STOP" ]] || return 75
}

acquire_action_lock() {
  bridge_ensure_dirs
  mkdir "$KAI_ACTION_LOCK" 2>/dev/null || return 75
  trap 'rm -rf "$KAI_ACTION_LOCK"' EXIT INT TERM
}

release_action_lock() {
  rm -rf "$KAI_ACTION_LOCK"
  trap - EXIT INT TERM
}

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
