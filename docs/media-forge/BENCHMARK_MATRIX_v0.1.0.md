# KAI Media Forge · Benchmark Matrix v0.1.0

Status: DRAFT_IMPLEMENTABLE

## Goal
Compare candidate backends with the same canonical inputs and record evidence before promotion.

## Backends in first pass
- LTX-2.5
- LTX-2.3 fallback/current compatibility baseline
- Wan2.2 Animate-14B
- MiniMax H3 / H3 Turbo where runnable

## Test packs
1. Single-character identity lock
2. Multi-shot same character
3. Two-character identity separation
4. Wardrobe continuity
5. Dance / driving-video motion transfer
6. Voice + lip-sync
7. Music-driven motion
8. Low-resolution generation + upscale
9. Camera/viewpoint change
10. Negative test: missing/invalid metadata

## Metrics
### Identity
- face embedding similarity
- landmark drift
- hair/skin/marking anchor consistency
- wardrobe anchor consistency
- subject swap / leakage count

### Temporal
- frame-to-frame flicker
- motion discontinuity
- cut continuity
- blink anomalies
- repeated/frozen frames

### Audio
- AV sync offset
- voice identity similarity
- speech intelligibility
- music timing preservation
- clipping / silence / artifacts

### Prompt & reference adherence
- semantic adherence
- reference-role adherence
- reference ordering fidelity
- spatial relation correctness

### Runtime
- cold start
- preprocess time
- inference time
- peak VRAM/RAM
- remote GPU type
- retries/failures
- estimated cost when applicable

## Scoring
Each test produces raw metrics plus PASS/WARN/REJECT gates. A backend cannot be promoted on an aggregate score if it violates an identity-critical hard gate.

## Evidence record
Every benchmark run must record:
- backend + exact model/revision
- adapter version
- MediaReferencePackage version
- seed
- prompt
- parameters
- input fingerprints
- output fingerprints
- runtime environment
- raw metrics
- gate result
- notes / failure class

## Promotion rule
OBSERVED != IMPLEMENTED != RUNNING. A backend becomes `SUPPORTED` only after adapter tests plus at least one representative benchmark pack pass. `PREFERRED` requires comparative evidence against the current baseline.
