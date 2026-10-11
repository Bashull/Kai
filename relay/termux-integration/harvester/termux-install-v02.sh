#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
if [ ! -d /data/data/com.termux/files/usr/bin ]; then echo 'ERROR: Termux required' >&2; exit 2; fi
command -v python >/dev/null || { echo 'ERROR: Python missing. Use pkg install python after reviewing package sources.' >&2; exit 2; }
here="$(cd "$(dirname "$0")" && pwd)"
dst="$HOME/KAI_TOOLS/kai-harvester-fusion-v0.2.1"
bin=/data/data/com.termux/files/usr/bin/kai-harvest-v021
if [ -e "$dst" ] || [ -e "$bin" ]; then echo 'Existing v0.2 path; refusing overwrite' >&2; exit 3; fi
mkdir -p "$dst"
cp -R "$here/." "$dst/"
cat > "$bin" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
export PYTHONPATH="$HOME/KAI_TOOLS/kai-harvester-fusion-v0.2.1${PYTHONPATH:+:$PYTHONPATH}"
exec /data/data/com.termux/files/usr/bin/python -m kai_harvester "$@"
EOF
chmod 700 "$bin"
"$bin" doctor >/dev/null
printf 'Installed %s (v0.1 and v0.2 commands unchanged).\n' "$bin"
