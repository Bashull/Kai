#!/usr/bin/env bash
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../../.." && pwd)
# shellcheck source=test_common.sh
source "$HERE/test_common.sh"

BOOTSTRAP="$ROOT/mobile/termux/bootstrap.sh"
[[ -f "$BOOTSTRAP" ]] || fail "bootstrap.sh missing"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home/.kai/mobile-bridge" "$tmp/prefix"
printf 'keep\n' > "$tmp/home/.kai/mobile-bridge/keep.txt"

cat > "$tmp/bin/pkg" <<'EOF'
#!/usr/bin/env bash
printf 'pkg %s\n' "$*" >> "$CALL_LOG"
exit 0
EOF
chmod +x "$tmp/bin/pkg"

cat > "$tmp/bin/termux-info" <<'EOF'
#!/usr/bin/env bash
printf 'TERMUX_VERSION=0.118.3\nAndroid version: 16\n'
EOF
chmod +x "$tmp/bin/termux-info"

export HOME="$tmp/home"
export PREFIX="$tmp/prefix"
export CALL_LOG="$tmp/calls.log"
export PATH="$tmp/bin:/usr/bin:/bin"

bash "$BOOTSTRAP"

calls=$(cat "$CALL_LOG")
assert_contains "$calls" "pkg update -y"
assert_contains "$calls" "pkg upgrade -y"
assert_contains "$calls" "pkg install -y termux-tools git curl jq openssh python nodejs-lts termux-api termux-services android-tools tmux rsync ripgrep"
assert_file "$HOME/.kai/mobile-bridge/keep.txt"
assert_eq "700" "$(stat -c %a "$HOME/.kai/mobile-bridge/private")"
assert_file "$HOME/.kai/mobile-bridge/state/bootstrap-current.json"
printf 'PASS: bootstrap contract\n'
