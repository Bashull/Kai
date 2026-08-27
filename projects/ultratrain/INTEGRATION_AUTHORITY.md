# UltraTrain Integration Authority

Status: CANDIDATE · GOVERNED_BRANCH · NOT_CANONICAL

## Purpose
This branch is the governed code landing zone for the UltraTrain Compatibility Core and subsequent capability adapters.

## Authority
- Documentary authority: Google Drive KAI CURRENT/checkpoints.
- Code candidate authority: `Bashull/Kai` branch `feature/ultratrain-compatibility-core`.
- `main` remains untouched until tests, canaries and review pass.

## Reconciliation baseline
The documented Compatibility Core v0.1.0 already defines a dependency-free capability graph and preflight validator with states `SUPPORTED`, `FALLBACK`, `NEEDS_CANARY`, `UNSUPPORTED` and 13/13 CPU tests previously reported as passing.

Do not recreate that core blindly. Recover the exact candidate bytes if possible; otherwise reconstruct from the documented contract with tests first and mark genealogy explicitly.

## Planned adapters
- KernelPolicy
- RuntimeCompatibilityProfile
- RolloutLifecycle
- TeacherProvider / Distillation
- FaultToleranceProvider
- TrackingSecurityPolicy
- WeightDeltaPlane integration
- Stateful cache capability integration
- Collective backend capability integration

## Promotion rules
1. Recover or reconstruct source with explicit provenance.
2. Re-run the inherited 13-test contract suite.
3. Add real adapter canaries incrementally.
4. Require numerical/correctness checks before performance promotion.
5. Preserve rollback baseline.
6. Never infer capability from version string alone.
7. No global dependency upgrade solely because an upstream release exists.

## Current limitation
No executable UltraTrain core was found in the searched `Bashull/Kai` scope or bounded `C:\KAI` search during this reconciliation pass. This is `NOT_FOUND_IN_SEARCHED_SCOPE`, not proof of global absence.
