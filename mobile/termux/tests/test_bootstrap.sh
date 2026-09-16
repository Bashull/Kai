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
mkdir -p "$tmp/bin" "$tmp/home/.kai/mobile-bridge" "$tmp/prefix/bin"
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

assert_file "$HOME/.kai/mobile-bridge/bin/kai-mobile"
assert_file "$HOME/.kai/mobile-bridge/lib/common.sh"
assert_file "$HOME/.kai/mobile-bridge/lib/android.sh"
assert_file "$HOME/.kai/mobile-bridge/config/apps.tsv"
assert_file "$HOME/.termux/boot/10-kai-mobile-bridge"
assert_eq "700" "$(stat -c %a "$HOME/.termux/boot/10-kai-mobile-bridge")"

boot=$(cat "$HOME/.termux/boot/10-kai-mobile-bridge")
assert_contains "$boot" "termux-wake-lock"
assert_contains "$boot" "start-services.sh"
if [[ "$boot" == *"sshd"* ]]; then
  fail "boot script must not start sshd"
fi

[[ -L "$PREFIX/bin/kai-mobile" ]] || fail "expected kai-mobile symlink in PREFIX/bin"
assert_eq "$HOME/.kai/mobile-bridge/bin/kai-mobile" "$(readlink "$PREFIX/bin/kai-mobile")"
installed_health=$(bash "$PREFIX/bin/kai-mobile" health)
assert_contains "$installed_health" '"ok":true'
printf 'PASS: bootstrap and boot contract\n'
