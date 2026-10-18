# KAI Meshy Forge Omega

Version 0.2.0 STAGING. This package adapts the user's previous KAI Meshy Forge engine and the existing official Meshy CLI. One `Forge`, one SQLite state and one asset registry serve the scoped CLI, MCP stdio and authenticated loopback HTTP transport. It does not replace the KAI Master Bridge, Control Plane or PC Forge.

Implemented: Brick Figure prototype/build as separate steps, live free auth/balance, persistent job intents, credit reservations and actuals, explicit spending job scope, historical task import, bounded polling, local cancellation, recovery, hash-bound human preview approval, verified atomic asset downloads, structural model inspection, reference metadata, immutable asset lineage and SQLite backup/restore verification.

The API catalog covers 28 capability groups. That research is separate from implemented providers: PC Blender execution and other generation families are not presented as completed integration. The PC bridge currently proves path/list/hash and agent health but cannot read/export sources or execute Blender. ChatGPT E2E remains unverified.

Use Python 3.11+ with the dependencies in `pyproject.toml`. On the verified Termux environment those dependencies already exist. Keep Meshy OAuth in its existing secure CLI store; set `KAI_MESHY_CLI` to the installed MELYC executable. Never put its credentials in the plugin.

```sh
python launch.py doctor
python launch.py balance
python launch.py jobs
python launch.py stdio
```

Reference roots, workspace and the independent write/spend/approval gates are documented in [the runbook](skills/kai-meshy-forge/references/runbook.md). Defaults deny paid submissions and visual approval. The owner decision on 2026-10-18 is **no new spend; design gate closed**. Preserve the old A’Hú task as rejected.

Polling timeout is a polling budget, not a wall-clock deadline for the whole production cycle. A vendor CLI call can take up to 180 seconds and an asset download up to 120 seconds. Remote transports should use short queries and return job IDs rather than wait for production inside a single request. HTTP remains loopback-only; no permanent listener or external tunnel is installed.

Validation uses offline concurrency/recovery/authorization tests, real MCP stdio clients for both protocol eras, an ephemeral authenticated HTTP socket and free live CLI reads. Run `PYTHONPATH=. python -W error::ResourceWarning -m unittest discover -s tests -v`. These checks do not establish visual quality, printability or Blender round-trip QA.

Original donors and character images stay in private Drive/archive storage. Only KAI source, tests and nonprivate package documentation belong in GitHub staging. See [provenance](PROVENANCE.md) for the source lineage and third-party separation.
