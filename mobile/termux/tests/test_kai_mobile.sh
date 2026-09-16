#!/usr/bin/env bash
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../../.." && pwd)
# shellcheck source=test_common.sh
source "$HERE/test_common.sh"

CLI="$ROOT/mobile/termux/kai-mobile"
[[ -f "$CLI" ]] || fail "kai-mobile missing"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/bridge/state" "$tmp/bridge/logs" "$tmp/bridge/private"
export CALL_LOG="$tmp/calls.log"
: > "$CALL_LOG"

cat > "$tmp/bin/am" <<'EOF'
#!/usr/bin/env bash
printf 'am %s\n' "$*" >> "$CALL_LOG"
[[ "${FAKE_AM_FAIL:-0}" = "1" ]] && exit 1
exit 0
EOF
chmod +x "$tmp/bin/am"

cat > "$tmp/bin/input" <<'EOF'
#!/usr/bin/env bash
printf 'input %s\n' "$*" >> "$CALL_LOG"
[[ "${FAKE_INPUT_FAIL:-0}" = "1" ]] && exit 1
exit 0
EOF
chmod +x "$tmp/bin/input"

cat > "$tmp/bin/adb" <<'EOF'
#!/usr/bin/env bash
if [[ "${1-}" = "get-state" ]]; then
  [[ "${FAKE_ADB_STATE:-}" = "device" ]] || exit 1
  printf 'device\n'
  exit 0
fi
printf 'adb %s\n' "$*" >> "$CALL_LOG"
exit 0
EOF
chmod +x "$tmp/bin/adb"

export PATH="$tmp/bin:/usr/bin:/bin"
export KAI_BRIDGE_ROOT="$tmp/bridge"
export KAI_AM_BIN="$tmp/bin/am"
export KAI_INPUT_BIN="$tmp/bin/input"
export KAI_APPS_FILE="$ROOT/mobile/termux/config/apps.tsv"

run_kai() {
  set +e
  output=$(bash "$CLI" "$@" 2>&1)
  status=$?
  set -e
}

run_kai health
assert_eq 0 "$status"
assert_contains "$output" '"ok":true'

: > "$CALL_LOG"
run_kai open-app com.example.notallowed
assert_eq 64 "$status"
assert_eq "" "$(cat "$CALL_LOG")"

: > "$CALL_LOG"
unset FAKE_AM_FAIL FAKE_ADB_STATE
run_kai open-whatsapp
assert_eq 0 "$status"
assert_contains "$(cat "$CALL_LOG")" "am start -W -n com.whatsapp/.Main"

: > "$CALL_LOG"
export FAKE_AM_FAIL=1
export FAKE_ADB_STATE=device
run_kai open-whatsapp
assert_eq 0 "$status"
assert_contains "$(cat "$CALL_LOG")" "adb shell am start -W -n com.whatsapp/.Main"

: > "$CALL_LOG"
unset FAKE_AM_FAIL
run_kai home
assert_eq 0 "$status"
assert_contains "$(cat "$CALL_LOG")" "input keyevent KEYCODE_HOME"

: > "$CALL_LOG"
run_kai wake
assert_eq 0 "$status"
assert_contains "$(cat "$CALL_LOG")" "input keyevent KEYCODE_WAKEUP"

printf 'PASS: typed mobile control contract\n'
