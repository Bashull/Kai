#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local haystack=${1-}
  local needle=${2-}
  [[ "$haystack" == *"$needle"* ]] || fail "expected [$haystack] to contain [$needle]"
}

assert_eq() {
  local expected=${1-}
  local actual=${2-}
  [[ "$actual" == "$expected" ]] || fail "expected [$expected], got [$actual]"
}

assert_file() {
  [[ -f "$1" ]] || fail "expected file: $1"
}
