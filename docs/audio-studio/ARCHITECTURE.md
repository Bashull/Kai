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

## v0.2 delta

- ManifestStore loads schema v1.0.0 cases and registries within a governed root.
- Path traversal and incomplete/unsupported manifests fail closed.
- ACE-Step compiler emits Caption, Lyrics, seed, duration and format-rewriting fields.
- MiniMax Music 3 compiler separates global metadata, vocal details and arrangement.
- Suno v5.5 compiler separates Style, Lyrics, Exclude and native controls.
- Compiler adapters accept externally supplied fresh capability snapshots; they do not invent provider health.
- Real Termux registry smoke loaded back-on-my-feet-001 and pajaro-001 successfully.

## v0.3 delta

- ReadOnlyCapabilityProbe checks credential presence through pointers and optional harmless status endpoints.
- Probe evidence records configuration, response class and error type; never the secret value.
- Dry-run planning freezes one fresh snapshot per provider and cannot call generate().
- BLOCKED reports preserve every provider snapshot and rejection reason.
- Back On My Feet and Pájaro are governed Blueprint acceptance fixtures.
- All three compilers pass the same fixture acceptance matrix.

Concrete provider status URLs and credential resolvers remain unconfigured until their official interfaces and local secret pointers are verified. Live generation remains intentionally gated.


## v0.4 delta

- Provider contracts are governed in PROVIDER_CONTRACTS_CURRENT.md.
- ACE-Step uses its official local GET /health contract with JSON identity validation.
- ACE compilation now emits official release_task fields.
- MiniMax compilation now emits the official music-3.0 request schema.
- MiniMax API is policy-blocked by default after the official 2026-08-20 lifecycle change.
- Suno remains a non-executable Blueprint draft until authenticated official docs are verified.
- HTTP 200 without the expected provider identity is rejected.


## v0.5 delta

- Federated ACE-Step inventory separates Termux client, PC hardware, HF state and donors.
- Verified acemusic.ai cloud target uses a governed credential pointer and plain-text health identity.
- AceMusicCompletionAdapter mirrors the installed OpenAI-compatible client contract.
- Termux composition resolves credential presence without exposing its value.
- Both real Blueprint fixtures now plan successfully through the live cloud route.
- Live generation remains gated; planning attempted zero generations.


## v0.6 — zero-spend execution gate and output ingestion

- `audio_studio.execution` is the only authorization boundary before a future
  generation call. Default policy is fail-closed: only FREE or LOCAL cost
  classes pass. UNKNOWN cost, paid routes without explicit approval, missing
  estimates, and estimates above budget are blocked with typed reasons.
- Approval identity is represented only as boolean evidence in the receipt;
  no credential or secret value is recorded.
- `audio_studio.ingestion.OutputIngestor` attaches returned media to benchmark
  manifests by governed path, SHA-256, size and MIME type.
- Media remains in the DJ KAI output authority. Ingestion is reference-only,
  idempotent for identical path+hash, and updates manifests atomically.
- Response metadata containing secret-like keys is rejected before writeback.
- This release adds no generation transport and cannot consume provider quota.


## v0.7 — official free-limited ZeroGPU route

- Added `ace-step-1.5-zerogpu` as a FREE remote planning route backed by
  the official ACE-Step v1.5 Hugging Face Space.
- Read-only contract probe verifies Gradio 6.2.0, `/gradio_api`, and the exact
  Space root from `/config`; it never calls `/generation_wrapper`.
- Cost authority: Hugging Face documents existing ZeroGPU Spaces as free to use.
  Quota is finite and daily; availability does not imply remaining quota.
- The adapter participates in dry-run planning and passes the zero-spend gate.
  No generation transport is implemented in this release.
