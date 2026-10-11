# Safe integration runbook

Stage 0: candidate only
- unit tests; static checks; no pack activation; no bridge restart.

Stage 1: runtime forensics
Record at one timestamp for kai-bedrock-ws and kai-mcwss:
run script, PID, /proc/PID/cmdline, cwd, listeners/owner, effective env where possible, status timestamp/content.
Choose one transport owner and non-colliding ports. Prepare rollback.

Stage 2: safe test world
- duplicate/test world;
- sensor only;
- prove silence while disabled;
- run /scriptevent kai:nerve_enable;
- capture real ENABLED/STATE/playerSpawn;
- verify identical session_id+seq across selected transport into candidate SQLite/WorldBus;
- prove source is not a fixture.

Stage 3: faults
Test stale frame + fresh mtime, repeated seq, delayed event, new session reset, disconnect/reconnect, status rewrite without new capture.

Stage 4: actuation
Only after Stage 2/3: one owner, short armed lease, calibrated movement, terrain checks, dry-run, then controlled flee_creeper.
