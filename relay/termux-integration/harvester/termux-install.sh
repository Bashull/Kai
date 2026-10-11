#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
printf '%s\n' 'Installing KAI offline Harvester (no credentials, no network harvest)...'
pkg install -y python
mkdir -p "$HOME/KAI_TOOLS/kai-harvester-fusion"
cp -R kai_harvester "$HOME/KAI_TOOLS/kai-harvester-fusion/"
cat > "$PREFIX/bin/kai-harvest" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
export PYTHONPATH="$HOME/KAI_TOOLS/kai-harvester-fusion${PYTHONPATH:+:$PYTHONPATH}"
exec python -m kai_harvester "$@"
SH
chmod 700 "$PREFIX/bin/kai-harvest"
umask 077
mkdir -p "$HOME/KAI_RUNTIME_LAB/chatgpt-harvester"
printf '%s\n' 'Installed. Optional once: termux-setup-storage (requires your Android permission).'
printf '%s\n' 'Example: kai-harvest ingest ~/storage/downloads/chatgpt-export.zip'
