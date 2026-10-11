# Termux Runbook · install / operate / recover

## Requirements

Modern Termux build, Python 3.10+, local free storage. No pip requirements. Use an up-to-date Termux distribution from its official channel. The install script invokes `pkg install -y python` (network package manager) and copies the local code. All subsequent CLI ingest/audit operations are offline.

## Install sandbox

1. Extract the ZIP under a **private** home directory. Example: `mkdir -p ~/KAI_TOOLS/staging && cd ~/KAI_TOOLS/staging`.
2. `unzip ~/storage/downloads/KAI_Harvester_Fusion_v0_1.zip` then `cd KAI_Harvester_Fusion_v0_1`.
3. `bash termux-install.sh`.
4. `kai-harvest --help` and `python -m unittest discover -s tests -v` (run tests from extracted package, not global install).
5. Only if necessary: `termux-setup-storage` and grant Android permission. You can instead copy your ZIP directly into Termux HOME.

## Operating phases

- Import original official ChatGPT ZIP or Bridge JSON parts: `kai-harvest ingest /full/path/...`.
- Integrity: `kai-harvest audit`. Any `missing_blobs` or `corrupt_blobs` means the local evidence is NOT reliable.
- Explore: `kai-harvest reader`, then open `~/KAI_RUNTIME_LAB/chatgpt-harvester/index.html` in a local reader. On Android the browser may not permit local `file://` navigation; view Markdown directly or use a trusted local file viewer. Avoid a publicly bound web server.
- Manifest and import ledger: `kai-harvest manifest`, `kai-harvest stats`.

## Recovery

Do not delete imported files. To recover after interruption, run `ingest` again with exactly the same ZIP/JSON/JSONL. Raw sources deduplicate on filename + source hash. Distinct revisions are retained. If an object fails hash audit, preserve log/evidence and re-import from untouched original; do not repair by editing content-addressed files. If a download part never arrived, browser capture must be repeated and compared by conversation ID. This is not automated resume after app crash.

## Permissions/privacy

Archive root is private Termux HOME (`chmod 700` root). ZIP files stored in Android Downloads can be read by other apps with appropriate access. Avoid sharing via public cloud links. No token/password storage. Never export `.git` credential stores.

## Exact uninstall (after separately securing data)

Remove only installation code if deliberately requested: `$HOME/KAI_TOOLS/kai-harvester-fusion` and wrapper `$PREFIX/bin/kai-harvest`; **do not** remove `$HOME/KAI_RUNTIME_LAB/chatgpt-harvester` without separate explicit data-retirement approval.
