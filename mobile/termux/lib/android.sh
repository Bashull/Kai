#!/usr/bin/env bash
set -euo pipefail

android_launch_component() {
  local component=${1-}
  local am_bin=${KAI_AM_BIN:-/system/bin/am}

  if [[ -x "$am_bin" ]] && "$am_bin" start -W -n "$component" >/dev/null 2>&1; then
    return 0
  fi

  if [[ "$(adb_state 2>/dev/null || true)" == "device" ]]; then
    adb shell am start -W -n "$component" >/dev/null 2>&1
    return $?
  fi

  return 77
}

android_keyevent() {
  local key=${1-}
  local input_bin=${KAI_INPUT_BIN:-/system/bin/input}

  if [[ -x "$input_bin" ]] && "$input_bin" keyevent "$key" >/dev/null 2>&1; then
    return 0
  fi

  if [[ "$(adb_state 2>/dev/null || true)" == "device" ]]; then
    adb shell input keyevent "$key" >/dev/null 2>&1
    return $?
  fi

  return 77
}
