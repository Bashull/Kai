# Architecture / operational contract

## Runtime graph

ChatGPT browser session → user-initiated read-only bridge → segmented local JSON → Termux offline ingest → immutable SHA-256 blobs + SQLite lineage → branch/asset projections → integrity audit → offline reader → separately governed `/extrae` writeback.

## Trust boundaries

- Browser has access to the user's existing signed-in session. Bearer token is short-lived and only held in the in-memory content-script closure. No localStorage, cookie serialization, external fetch, background alarms, or telemetry.
- Host domain allowlist is `https://chatgpt.com/*`. Endpoint path factory refuses hosts other than chatgpt.com and accepts only `/api/auth/` or `/backend-api/`, with hard-coded operation paths constructed by code.
- Termux has **no authenticated ChatGPT network access**, so there is no token to transport, forward, or leak. Browser output remains under user control. Termux native path under `$HOME` uses private permissions; Android Downloads is treated as temporary transit, not secret vault.
- No deletion, mutation, archiving/unarchiving, sharing or update operations against ChatGPT are supported.
- This package is separate from KAI Devourer CURRENT, and the Drive canonical records remain authoritative until user-verified promotion.

## Source and projection identity

`objects/<2_hex>/<remaining_sha256>` stores exact source-file bytes, and canonical JSON serialization of each recognized conversation as a separate immutable object. The JSON serialization is a projection: the **original source file** remains verbatim under its own SHA-256. `sources` row maps origin filename/hash. The parser does not overwrite providers' original objects. `views/` is always derived.

SQLite records `sources`, `conversations`, `assets`, `asset_refs`, `warnings`. A re-run is idempotent for same filename/hash. Modified RAW is a separate source revision instead of overwrite. Do not infer that different workspaces sharing a conversation ID contain the same object.

## Scope and completeness certificate

Dimensions: `inventory_scope`, `read_body`, `graph`, `assets_discovered`, `assets_physical`, `hash_integrity`, `derived_fidelity`.

Current v0.1 only certifies offline evidence integrity and inspected graph records. It **cannot** produce account-level FULL_INVENTORY or FULL_ASSET_RECOVERY. Keep `inventory_complete=false`, `assets_complete=false`, `full_history_complete=false`. A paginated messages endpoint is not full regenerative DAG proof. `429`, premature empty pages and cursor errors are failures, never completion. Each browser part requests a local download, but only local file hashes from actual saved files validate possession.

## Threats addressed

1. Partial export looks complete → explicit incomplete flags.
2. Rate limit presented as zero conversations → bounded retries and exception.
3. Auth vs workspace permissions → explicit preflight, no false logout inference.
4. Cursor cycles → fail closed with a status.
5. RAW normalized in-place → original blobs immutable.
6. Markdown entity/unicode distortions → direct text inclusion, raw source still available.
7. Browser ZIP drop/size → segmented JSON parts; CLI zip bomb and path guards.
8. Private URL/token leak → reference fingerprint instead of storing raw signed URLs in index; browser does not export credentials.
9. Cross-repository licensing → no verbatim third-party code was copied into package; architecture and concepts are attributed.

## Known architecture gaps / vNEXT

Large-file streaming import, bytes/file contextual resolver, complete Projects workspace semantics, shared chat endpoint, user-chosen workspace discovery, account artifacts, formal checkpoint resume from verified saved parts, continuous browser background job, offline deep RAG, total branch validation for page-only shape, journaled writeback into Drive and in-place runtime integration. These are **not** implemented. Browser code needs integration tests with a test account and a supported browser before promotion.
