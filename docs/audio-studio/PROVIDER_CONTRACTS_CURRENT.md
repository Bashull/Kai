# Provider Contracts CURRENT

Verified at: 2026-08-27
Scope: VERIFIED_SCOPE, not a full provider inventory.

## ACE-Step 1.5 local

Status: OFFICIAL_CONTRACT_VERIFIED · RUNTIME_OFFLINE_ON_TERMUX

- Authority: https://github.com/ace-step/ACE-Step-1.5
- API contract: https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md
- Safe probe: GET http://127.0.0.1:8001/health
- Identity requirement: data.status=ok, data.service=ACE-Step API, code=200.
- Model discovery: GET /v1/models.
- Generation: POST /release_task; never used as a health probe.
- Current Termux observation: ports 8001 and 7860 returned no HTTP response.
- Interpretation: OFFLINE only. Installation state remains UNKNOWN.

## MiniMax Music API

Status: OFFICIAL_LEGACY_CONTRACT · POLICY_BLOCKED_BY_DEFAULT

- Authority: https://platform.minimax.io/docs/api-reference/music-generation
- Generation: POST https://api.minimax.io/v1/music_generation.
- Current model contract names music-3.0, music-2.6 and music-cover.
- Official notice: after 2026-08-20, paid music APIs are unavailable to
  new users; existing paying users may continue.
- Official notice: free music APIs are discontinued.
- No documented zero-cost status endpoint was found in verified scope.
- Policy: never use music_generation as a probe.
- Reopen condition: verified legacy entitlement or a new official contract.

## Suno Platform

Status: PLATFORM_CONFIRMED · CONTRACT_UNKNOWN_AUTH_REQUIRED

- Authority: https://platform.suno.com/
- Official platform advertises songs, covers and mashups via REST API.
- Public landing page redirects to authentication for account management.
- No safe endpoint, schema, pricing or credential pointer was verified.
- Existing Suno compiler output is therefore a non-executable Blueprint draft.
- Reopen condition: authenticated official documentation is inspected.

## Safety invariant

A provider becomes AVAILABLE only when a harmless documented probe returns
the expected service identity. HTTP 200 alone is insufficient. Generation
endpoints are never probes, and secret values never enter evidence.


## ACE-Step 1.5 cloud completion route

Status: LIVE_READ_ONLY_VERIFIED · GENERATION_GATED

- Host: https://api.acemusic.ai
- Health: GET /health → HTTP 200 with exact body "health check".
- Generation: POST /v1/chat/completions; not used by probes.
- Model observed in two historical outputs: acemusic/acestep-v1.5-turbo.
- Credential pointer exists in Termux config; secret value is not recorded.
- Installed client payload contract is represented by AceMusicCompletionAdapter.
