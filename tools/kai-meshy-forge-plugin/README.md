# KAI Meshy Forge Omega

Version 0.3.0 STAGING. This package adapts the user's previous KAI Meshy Forge engine and the existing official Meshy CLI. One `Forge`, one SQLite state and one asset registry serve the scoped CLI, MCP stdio and authenticated loopback HTTP transport. It does not replace the KAI Master Bridge, Control Plane or PC Forge.

Implemented: Brick Figure prototype/build as separate steps, live free auth/balance, persistent job intents, credit reservations and actuals, explicit spending job scope, historical task import, bounded polling, local cancellation, recovery, hash-bound human preview approval, verified atomic asset downloads, structural model inspection, reference metadata, immutable asset lineage and SQLite backup/restore verification.

The research matrix covers 28 capability groups. Versioned executable contracts and the capability operation engine add standard REST and Creative Lab families to the same ledger. Schema validation, offline lifecycle tests and free live reads are distinct from paid end-to-end generation; no new spend is authorized. PC Blender execution remains unverified. The PC bridge currently proves path/list/hash and agent health but cannot read/export sources or execute Blender. ChatGPT E2E remains unverified.

Use Python 3.11+ with the dependencies in `pyproject.toml`. On the verified Termux environment those dependencies already exist. Keep Meshy OAuth in its existing secure CLI store; set `KAI_MESHY_CLI` to the installed MELYC executable. Never put its credentials in the plugin.

```sh
python launch.py doctor
python launch.py balance
python launch.py jobs
python launch.py stdio
```

Reference roots, workspace and the independent write/spend/approval gates are documented in [the runbook](skills/kai-meshy-forge/references/runbook.md). Defaults deny paid submissions and visual approval. The owner decision on 2026-10-18 is **no new spend; design gate closed**. Preserve the old A’Hú task as rejected.

Generic operation polling propagates its remaining time to each CLI read and stops on attempt/no-progress limits. Legacy Brick polling and an asset transfer are separate bounded calls; a CLI call can take up to 180 seconds and an asset download up to 120 seconds. Remote transports should use short queries and return job IDs rather than wait for production inside a single request. HTTP remains loopback-only; no permanent listener or external tunnel is installed.

Validation uses offline concurrency/recovery/authorization tests, real MCP stdio clients for both protocol eras, an ephemeral authenticated HTTP socket and free live CLI reads. Run `PYTHONPATH=. python -W error::ResourceWarning -m unittest discover -s tests -v`. These checks do not establish visual quality, printability or Blender round-trip QA.

Original donors and character images stay in private Drive/archive storage. Only KAI source, tests and nonprivate package documentation belong in GitHub staging. See [provenance](PROVENANCE.md) for the source lineage and third-party separation.

The capability workflow uses `capabilities`, `describe CAPABILITY`, `validate CAPABILITY --parameters-json JSON`, `quote CAPABILITY --parameters-json JSON`, `tasks CAPABILITY` and `remote-task CAPABILITY TASK_ID`. Write-gated `plan`, `operation-refresh`, `operation-poll`, `operation-cycle`, `operation-download` and checkpoint commands operate on `op:ID` stages in the existing database. Explicit submit is separately spending-gated; a quote and local plan confer no authorization. No arbitrary endpoint is exposed. Managed local media and task dependencies preserve content and parent identity.

`ForgeObservationWorker` adapts the existing guarded Loop Factory runner. Thirteen isolated tests exercised its real store, signed LAB lease, intent journal, receipt and checkpoint lifecycle, including restart, dependencies, STOP and epoch rejection. This is a read-only laboratory integration with explicit synthetic authorization; the live KAI scheduler is not connected or replaced.

Verified staging canary on 2026-10-18: exactly one Print Analyze POST over the existing Melyc GLB, task `01a15103-613b-725e-a82a-9ed08b082acb`, succeeded with API-reported consumed_credits=0 and unchanged balance 3079. An injected operator ceiling of zero credits constrained this single process/job; permanent transport gates remain disabled. Its typed analysis and content-parent evidence are registered in the same Forge database. This is technical analysis, not approval to print or a new character design. Final package verification: 157 tests passed.
