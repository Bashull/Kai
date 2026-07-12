#!/data/data/com.termux/files/usr/bin/sh
set -eu

REPO_URL="https://github.com/Bashull/Kai.git"
BRANCH="feat/kai-visual-production-pipeline-v0.1"
ROOT="$HOME/.kai_visual_tdd/repo"

say() { printf '\n[KAI-TERMUX] %s\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || return 1
}

say "Preparing Termux TDD node"
mkdir -p "$HOME/.kai_visual_tdd"

if ! need_cmd git || ! need_cmd python; then
  say "Installing missing runtime packages"
  pkg install -y git python
fi

if [ -d "$ROOT/.git" ]; then
  if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
    say "STOP: existing Termux worktree has local changes"
    git -C "$ROOT" status --short
    exit 2
  fi
  say "Refreshing existing isolated clone"
  git -C "$ROOT" fetch origin "$BRANCH"
  git -C "$ROOT" checkout "$BRANCH"
  git -C "$ROOT" reset --hard "origin/$BRANCH"
else
  say "Cloning isolated branch"
  git clone --single-branch --branch "$BRANCH" "$REPO_URL" "$ROOT"
fi

say "Runtime"
python --version
git --version

say "HEAD"
git -C "$ROOT" log -1 --oneline

say "Running RED test suite"
cd "$ROOT"
set +e
python -m unittest tests/test_kai_repo_5x5_fusion.py -v
STATUS=$?
set -e

if [ "$STATUS" -eq 0 ]; then
  say "UNEXPECTED: RED tests passed before implementation"
  exit 3
fi

say "RED confirmed: tests fail as expected before production code"
printf 'KAI_TDD_RED_CONFIRMED exit_code=%s\n' "$STATUS"
exit 0
