# KAI Media Forge · ShotContinuityContract design

Date: 2026-08-23
Status: DESIGN_APPROVED_IN_CHAT · SPEC_FOR_REVIEW · NOT_IMPLEMENTED
Authority target: `Bashull/Kai`
Branch: `feature/media-reference-contract`
Companion contract: `MediaReferenceContract v0.1.0`

## 1. Problem

`MediaReferenceContract` already models reusable media references correctly: modality, role, order, timing metadata, provenance, constraints and optional `subjectId`. It can express that one image is an identity reference for subject A and one audio file is a voice reference for subject B.

It does not model shot-level participation. In particular, it cannot state independently:

- which subjects are visible in a shot;
- which subject is speaking;
- which dialogue interval belongs to which speaker;
- which continuity mechanism should be used for visual identity, audio identity, shot seams or episodic memory;
- how reusable subject references are bound into backend-specific slots for a particular shot.

Donor analysis of JoyLTX/Echo-style routing exposed the cost of conflating these dimensions: selecting one subject reference and then implicitly treating that subject as the speaker can cause voice leakage or identity swaps in multi-character shots. LTX-2.5 MSR-style multi-reference conditioning solves part of the visual problem, but slot position is not a semantic identity contract by itself.

## 2. Design goal

Add a backend-agnostic shot-level continuity contract that composes with `MediaReferenceContract` instead of replacing it.

The contract must let KAI say, for example:

> Subjects A and B are visible. B speaks from 1200–3400 ms. Preserve visual identity for both subjects, preserve B's voice identity, use a fresh visual shot seam, and keep episodic memory from the previous shot.

Backend adapters may translate this into MSR slots, AddGuide references, AV-extend, audio anchors, reference indices or other provider-specific mechanisms, but may not silently change subject/speaker semantics.

## 3. Non-goals

This contract is not:

- a screenplay format;
- a subtitle/ASR transcript standard;
- a timeline editor schema;
- a backend parameter dump;
- a replacement for `MediaReferenceContract`;
- an identity-recognition system;
- a guarantee that a backend can satisfy every requested continuity strategy.

If a backend cannot represent requested semantics, its adapter must return WARN/REJECT instead of guessing.

## 4. Architecture

The two contracts have separate responsibilities.

`MediaReferenceContract`
: reusable assets and their semantics — what a reference is, which subject it belongs to, its media properties, provenance and preservation constraints.

`ShotContinuityContract`
: per-shot casting and continuity intent — who appears, who speaks, which references are bound for the shot and which continuity mechanisms are requested.

The relationship is by stable IDs:

- `subjectId` links shot participants to reference ownership;
- `referenceId` links shot bindings back to `MediaReferencePackage.references[].id`;
- `shotId` identifies the temporal unit being rendered/evaluated.

No backend slot number becomes a canonical identity. Slot assignment is adapter output, derived from canonical subject/reference bindings.

## 5. Proposed v0.1.0 contract

```ts
export type SeamStrategy =
  | 'fresh'
  | 'av_extend'
  | 'audio_extend'
  | 'video_extend';

export type VisualIdentityStrategy =
  | 'reference_conditioning'
  | 'multi_subject_reference'
  | 'previous_frame'
  | 'none';

export type AudioIdentityStrategy =
  | 'speaker_anchor'
  | 'previous_tail'
  | 'reference_audio'
  | 'none';

export type EpisodicMemoryStrategy =
  | 'paired_memory'
  | 'previous_shot'
  | 'none';

export interface DialogueTurn {
  id: string;
  speakerSubjectId: string;
  startMs?: number;
  endMs?: number;
  text?: string;
}

export interface ShotReferenceBinding {
  subjectId?: string;
  referenceIds: string[];
  purpose?: 'identity' | 'appearance' | 'wardrobe' | 'voice' | 'motion' | 'environment' | 'other';
}

export interface ShotContinuityContract {
  version: '0.1.0';
  shotId: string;
  visibleSubjectIds: string[];
  speakerSubjectIds: string[];
  dialogueTurns?: DialogueTurn[];
  referenceBindings?: ShotReferenceBinding[];
  strategies: {
    seam: SeamStrategy;
    visualIdentity: VisualIdentityStrategy;
    audioIdentity: AudioIdentityStrategy;
    episodicMemory: EpisodicMemoryStrategy;
  };
  previousShotId?: string;
}
```

The exact TypeScript surface may be reduced during TDD if tests show a smaller API is sufficient. The invariants below are the stable design contract.

## 6. Core invariants

### 6.1 Visibility and speech are independent

A subject may be visible and silent. A subject may be the only speaker while several subjects are visible. Speaker selection must never be inferred from reference order, prompt mention frequency or visual prominence when explicit speaker data exists.

### 6.2 Dialogue turns own speaker identity

Each dialogue turn names a `speakerSubjectId`. If `speakerSubjectIds` is supplied, it must equal the unique set of speakers represented by dialogue turns when dialogue turns are present.

### 6.3 References remain canonical outside the shot

The shot contract stores reference IDs, not duplicated paths/URIs/media metadata. All media truth remains in `MediaReferenceContract`.

### 6.4 Backend slots are derived state

Adapters may produce mappings such as `subject-a -> MSR slot 1`, but slot indices are never stored as canonical subject identity.

### 6.5 Continuity strategies are orthogonal

Visual identity continuity, audio identity continuity, seam continuity and episodic memory are separate axes. There is no generic `continuity: true` flag.

### 6.6 No silent semantic degradation

An adapter that cannot represent two simultaneous visible subjects, multiple speakers, an audio identity anchor, or another requested invariant must emit WARN/REJECT with a reason. It must not silently collapse multiple subjects into one.

## 7. Validation rules

The first validator should be intentionally small and deterministic.

Hard REJECT cases:

1. empty `shotId`;
2. duplicate subject IDs inside `visibleSubjectIds` or `speakerSubjectIds`;
3. a dialogue turn with empty `speakerSubjectId`;
4. invalid dialogue interval (`startMs < 0`, `endMs < 0`, or `endMs < startMs`);
5. duplicate dialogue-turn IDs;
6. dialogue-turn speaker missing from `speakerSubjectIds`;
7. a `referenceBinding.referenceIds` entry that does not exist in the supplied `MediaReferencePackage` during cross-contract validation;
8. a binding with `subjectId` that disagrees with the bound reference's canonical `subjectId`, unless the reference intentionally has no subject ownership (for example environment/style).

WARN candidates:

- speaker not visible in the shot;
- `speaker_anchor` requested but no voice/audio reference exists for that speaker;
- `multi_subject_reference` requested with fewer than two visible subjects;
- previous-shot-dependent strategy without `previousShotId`;
- visible subject has no identity-critical reference while identity preservation is required by policy.

Warnings are adapter/policy sensitive and should not all be implemented in the first RED/GREEN cycle.

## 8. Cross-contract validation

Keep pure shot validation separate from validation that needs `MediaReferencePackage`.

Proposed API shape:

```ts
validateShotContinuityContract(shot)
validateShotReferenceBindings(shot, mediaPackage)
```

This keeps the shot contract independently testable and prevents circular ownership between modules.

## 9. Adapter contract

A backend adapter consumes canonical inputs and returns an explicit mapping/evidence object.

Conceptually:

```ts
interface ContinuityAdapterResult {
  severity: 'PASS' | 'WARN' | 'REJECT';
  issues: ContractIssue[];
  consumedReferenceIds: string[];
  ignoredReferenceIds: string[];
  subjectMappings?: Record<string, unknown>;
}
```

Provider-specific slot/index data belongs in `subjectMappings` or provider adapter output, never in the canonical contracts.

### LTX-2.5 / MSR-like adapter

Expected translation:

- visible subjects -> subject/reference bindings;
- identity/appearance references -> stable per-shot slots;
- environment reference -> background/reference slot where supported;
- explicit speaker semantics remain outside the visual slot mapping;
- slot assignment must be deterministic and recorded as evidence.

### JoyLTX/Echo-style adapter

Do not import its heuristic subject-selection behavior as authority. KAI supplies explicit speaker identity. Previous audio/video tails may be used only under the requested seam/audio strategy, and stored tails must remain associated with the producing subject/shot.

### MiniMax H3-like adapter

Preserve canonical reference order and media rates from `MediaReferenceContract`; derive any provider-specific ordered reference list from `referenceBindings` without losing subject ownership.

## 10. First TDD slice

The first implementation slice exists specifically to eliminate the donor failure class `selected visual subject != actual speaker`.

RED test scenario:

- subjects A and B visible;
- both have identity references;
- B is the explicit speaker;
- reference A appears first / has lower order;
- validator/router must preserve B as speaker and must not derive speaker from reference order.

The production change that makes the test pass is a typed shot contract plus deterministic speaker/reference separation. No backend inference is required in the first slice.

Second RED scenario:

- dialogue turn says B;
- `speakerSubjectIds` says A;
- validation must REJECT the contradiction.

Third RED scenario:

- binding declares subject B but references an identity asset canonically owned by A;
- cross-contract validation must REJECT subject/reference leakage.

Only after these are green should adapter-specific MSR/JoyLTX routing be added.

## 11. Benchmark additions

Extend the Media Forge benchmark with adversarial multi-character cases:

- A+B visible, B speaks;
- A -> B -> A speaker alternation across shots;
- two dialogue turns from different speakers inside one shot;
- newly introduced speaker with no previous audio tail;
- intentionally reversed visual reference order;
- intentionally reversed MSR slot order at adapter test level;
- off-center/non-dominant speaker;
- previous-shot audio tail belonging to a different subject;
- multi-character identity separation under camera cut;
- voice identity preservation after several cuts.

Hard identity/audio gate: no accepted run may silently map one subject's voice anchor to another subject.

## 12. Rollout and authority

1. Spec in the existing Media Forge feature branch.
2. Add failing unit tests first.
3. Add minimal `shotContinuityContract.ts` implementation.
4. Run specific tests plus all `src/media/__tests__` regression tests.
5. Update benchmark documentation.
6. Add provider adapter tests only after canonical contract is green.
7. Keep PR #33 draft until contract tests are green and the pre-existing repo build problem is clearly separated from this change.
8. No backend becomes SUPPORTED/PREFERRED merely because this contract exists.

## 13. Rejected alternatives

### Put shot semantics into MediaReferencePackage v0.2

Rejected because it mixes reusable asset truth with ephemeral shot/timeline state and makes a reference package harder to reuse across shots and backends.

### Keep routing logic only inside each backend adapter

Rejected because speaker/subject semantics would diverge between providers, recreating the exact heuristic ambiguity exposed by donor analysis.

### Single `continuity: true|false` field

Rejected because visual identity, voice identity, seam extension and episodic memory have different failure modes and backend support.

## 14. Success criteria

The design is successful when KAI can represent and validate a two-character shot where one subject speaks without relying on prompt heuristics, reference order, frame center, previous-tail ownership guesses or provider slot conventions.

Implementation is not considered complete until RED/GREEN evidence exists and no-regression media tests pass. Runtime/backend support remains a separate promotion gate.
