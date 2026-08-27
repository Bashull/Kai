# ZeroGPU canary — 2026-08-27

## Scope

- Provider: `ace-step-1.5-zerogpu`
- Official Space: `ACE-Step/Ace-Step-v1.5`
- Endpoint: `/generation_wrapper`
- Model: `acestep-v15-turbo`
- Duration: 10 seconds
- Batch: 1
- DiT steps: 8
- Scoring: disabled
- LRC: disabled
- Automatic retries: 0
- Cost class: FREE

## Gate evidence

- Read-only provider probe: `AVAILABLE`
- Execution receipt: `allowed=True`, `FREE_OR_LOCAL_ROUTE_APPROVED`
- PC Hugging Face identity: authenticated as `Bashull`
- Contract observed before execution: Gradio 6.2.0, 49 inputs

## Result

One request was submitted from the authenticated PC. It ended after 286.13 seconds
with `gradio_client.exceptions.AppError: GPU task aborted`.

No retry was submitted. No audio file was produced. No paid route or credit-spend
path was enabled.

## Engineering outcome

The repository now contains a fail-closed compiler and Gradio submitter. It requires
an allowed FREE receipt, pins the official Space and endpoint, enforces the 10-second
batch-1 canary limits, disables scoring/LRC, and contains no retry loop.
