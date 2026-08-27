# KAI Audio Studio Core v0.1

Status: IMPLEMENTED_SKELETON · TESTED · NO LIVE GENERATION

## Boundary

The neutral Song Blueprint is authoritative. Provider adapters translate it and expose fresh capability evidence. The director routes; it never stores secret values or assumes historical availability.

## Routing gates

1. Probe every registered provider.
2. Accept only AVAILABLE snapshots.
3. Require every requested capability.
4. Enforce local_only when requested.
5. Prefer FREE/LOCAL routes under free-first policy.
6. Preserve rejected routes and exact reasons.
7. Compile only after a provider wins.
8. Keep live generation gated behind concrete adapters.

BLOCKED_QUOTA, OFFLINE, TOOL_BLOCKED and UNKNOWN remain distinct states.

## Current implementation

- SongRequest and immutable CapabilitySnapshot.
- MusicProviderAdapter contract: probe, compile, gated generate.
- MusicDirector.plan() with deterministic routing.
- FakeMusicProvider for cost-free development and regression tests.

## Next

Implement ACE, MiniMax and Suno compiler/probe adapters without embedding credentials. Connect decisions to benchmark manifests and add acceptance fixtures from the existing cases.
