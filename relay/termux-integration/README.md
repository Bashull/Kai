# KAI Termux integration 0.4.1 + Harvester 0.2.2

Candidate prepared from NERVE v0.4 and the actual Termux scripts observed on 2026-10-11. Deployment status is recorded separately in the checkpoint; this README alone does not establish deployment.

## Changes

- Capture, publication and detection use separate monotonic timestamps with boot/session identity. Rewriting a state cannot refresh an old capture. Consumers recalculate ages.
- Persistent atomic replay ledger, strict sequence types, bounded parser and RAW CAS, separate fixture/process/engine provenance, and durable WorldBus pending deliveries.
- WorldModel reads the actual sensor payload, keeps individual modded IDs, distinguishes scan failure/partial scans and expires tracks.
- Existing WorldBus owns sensor ingress. No additional daemon, bridge or physical driver is installed. PID-filtered logcat is process-bound evidence; engine verification is still pending.
- Sensor v0.4.1 is observation-only, disabled by default and includes the self-exclusion/truncation fix. The installer does not install or enable the pack.
- Harvester 0.2.2 fixes concurrent CAS writes, corrupt-object audit exit status, malformed graph isolation and duplicate derived search indexing. Original sources and revisions remain.

## Deploy from this extracted directory on Termux

`python install_termux.py` runs preflight only.

`python install_termux.py --apply` runs preflight, checks original script hashes, backs up SQLite using its backup API, stages immutable releases, updates three runit run files, restarts those three services and verifies new status timestamps, PID and command identity. Reflex remains disarmed. A failure after service changes restores the previous run scripts and wrappers.

The installer prints the backup path. Rollback: `python install_termux.py --rollback /absolute/path/to/deployment-backup`.

Original runtime scripts remain in ~/.kai_mobile and original Harvester versions remain in ~/KAI_TOOLS. Rollback preserves DB history. Interrupted staging is preserved for inspection and must not be overwritten blindly.

After installation: `kai-nerve status`, `kai-harvest-next doctor`, `kai-harvest-next --root /your/private/corpus audit`.

## Limits

Local tests are not Android integration tests. Bedrock API compatibility, Content Log→logcat and a real sensor event remain pending until a test world is used. CAS has a 64 MiB/50,000 occurrence cap and fails closed when full. RAW→ledger→EventStore are not one cross-database transaction: a crash between ledger advancement and the internal event commit requires recovery from preserved RAW; no exactly-once guarantee is claimed. ADB endpoints rotate. Existing WS bridge consolidation requires fresh ownership inspection after the mobile restart.

Runtime is separate from ChatGPT account automation. Harvester performs offline import/search and does not log in, message anyone or download the account automatically.
