# ZeroGPU canary governance v0.9

Date: 2026-08-27
Status: IMPLEMENTED · TESTED · NO_GENERATION

## Purpose

Make every ZeroGPU canary an explicit, one-shot, auditable act. This layer does not
improve model quality directly; it prevents silent retries, duplicated quota use and
untraceable upstream failures while the free route is still unreliable.

## Contract

1. Compile the bounded call through the v0.8 FREE execution receipt.
2. Create a manual permit bound to the SHA-256 fingerprint of that exact call.
3. Consume the permit durably before submission.
4. Submit at most once.
5. Append sanitized `SUBMITTED` and terminal `SUCCEEDED` or `FAILED` records to
   an NDJSON journal.
6. A new attempt requires a different manual permit. Failed permits cannot replay.

## Structured errors

- `UPSTREAM_GPU_ABORTED`
- `QUOTA_EXHAUSTED`
- `QUEUE_FAILURE`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_ERROR`

Messages are flattened, capped at 240 characters and scrubbed for bearer strings,
Hugging Face token shapes and token/API-key/authorization query parameters.

## Stored evidence

The permit ledger stores permit/provider/fingerprint/approver/timestamps only. It
does not store prompts, provider credentials or token values. The event journal
stores attempt state, elapsed time, sanitized error classification and output
reference count. Successful output files remain the responsibility of the governed
ingestor.

## Acceptance

- Manual permit matches the exact call fingerprint.
- Permit is consumed before transport invocation.
- Replay is blocked without invoking the transport.
- Failure invokes the submitter exactly once.
- The observed `GPU task aborted` maps to `UPSTREAM_GPU_ABORTED`.
- Journal round-trip preserves state transitions and removes secret-like content.
- No live generation is performed by this revision.
