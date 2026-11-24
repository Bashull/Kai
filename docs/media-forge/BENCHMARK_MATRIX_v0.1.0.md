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
11. Two characters visible, non-first subject speaks
12. Speaker alternation A → B → A across shots
13. Two dialogue turns from different speakers in one shot
14. New speaker without previous audio tail
15. Intentionally reversed visual reference order / adapter slot order
16. Off-center or visually non-dominant speaker
17. Previous-shot audio tail owned by a different subject
18. Voice identity persistence across multiple cuts

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
- cross-subject voice leakage count

### Prompt & reference adherence
- semantic adherence
- reference-role adherence
- reference ordering fidelity
- spatial relation correctness
- explicit speaker adherence
- subject-to-reference binding fidelity

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

Hard multi-subject gate: no accepted run may silently map one subject's voice/reference anchor to another subject. Explicit speaker identity outranks reference order, prompt mention frequency, visual prominence and provider slot convention.

## Evidence record
Every benchmark run must record:
- backend + exact model/revision
- adapter version
- MediaReferencePackage version
- ShotContinuityContract version when applicable
- seed
- prompt
- parameters
- input fingerprints
- output fingerprints
- runtime environment
- raw metrics
- gate result
- notes / failure class
- subject/slot/reference mapping evidence for multi-character tests

## Promotion rule
OBSERVED != IMPLEMENTED != RUNNING. A backend becomes `SUPPORTED` only after adapter tests plus at least one representative benchmark pack pass. `PREFERRED` requires comparative evidence against the current baseline.
