# Runtime and recovery

Default runtime: `~/KAI_VISUAL_STUDIO/KAI_MESHY_FORGE_OMEGA`. Code authority: GitHub Bashull/Kai staging. Documentation authority: Google Drive `KAI/20_PROJECTS/KAI_MEDIA_FORGE_OMEGA/KAI_MESHY_FUSION_HUB`.

`python launch.py doctor`, `balance`, `jobs`, `job JOB` and `cycle JOB` recover state without a paid submission. `python launch.py stdio` runs the MCP adapter. Configure `KAI_MESHY_CLI` to the existing MELYC `tooling/node_modules/.bin/meshy`; retain its Android `@img/sharp-wasm32@0.35.5`. Never package OAuth or Meshy configuration.

The installed CLI can read nonsecret runtime pointers from `~/.config/kai-meshy-forge/runtime.json` (mode 0600, schema `kai.meshy.runtime/v1`, fields `workspace`, `cli`, `reference_roots`). Environment variables override those pointers. This file cannot grant write, spend or visual approval permissions. The adapter invokes a detected Node entrypoint with an absolute Node executable, so Android does not depend on `/usr/bin/env` or inherited `LD_PRELOAD`.

`KAI_MESHY_WORKSPACE` selects the single runtime. Reference access is confined to `KAI_MESHY_REFERENCE_ROOTS` (JSON list of local directories) or the workspace itself. `KAI_MESHY_ALLOW_WRITES`, `KAI_MESHY_ALLOW_SPEND`, and `KAI_MESHY_ALLOW_APPROVALS` default to `0`; enabling a transport gate is still subject to domain checks and owner scope.

Keep one runtime SQLite state. The donor engine is extended by additive migrations; do not start another database to avoid an unresolved intent or to reset budget. Import the known historical rejected task by its immutable ID before budgeting new A’Hú work. Back up SQLite with its backup API, restore into an isolated directory and compare jobs, stages and hashes before treating a backup as proven.

STOP local jobs with the cancel operation; this stops future local submission and polling, not the vendor task. Meshy cancellation availability is operation-specific and is not simulated. Preserve reservations for uncertain or running vendor tasks.

On Android the accepted-download boundary is the SQLite receipt after exclusive file creation, flush and fsync. If interrupted bytes exist without a receipt, they are preserved and blocked. Quarantine that staged, unaccepted file with its hash and download the same task again; never resubmit generation. A changed accepted asset remains preserved for diagnosis rather than being silently overwritten.

Rollback: remove only the `kai-meshy-mcp` Codex entry and the installed `kai-meshy-forge` skill symlink; keep the runtime and all receipts. Restore the private Codex config backup if needed. No existing KAI service, PC adapter or CLI installation is replaced. No permanent listener or tunnel is installed by the package.

The scoped installation also creates `kai-meshy-job-engine` and `kai-meshy-mcp` launchers in the existing Python scripts directory. They call the same installed package; no pip distribution or new dependency was installed on this node. Remove only those recorded new launchers and the nonsecret runtime-pointer config when rolling back this installation. Preserve the runtime database, assets and rollback backup.
