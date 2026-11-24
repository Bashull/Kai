# ShotContinuityContract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend-agnostic `ShotContinuityContract v0.1.0` that keeps visible subjects, explicit speakers, dialogue turns and canonical media-reference ownership separate, preventing speaker/reference leakage before any provider adapter is allowed to route a shot.

**Architecture:** Keep `MediaReferenceContract` as the reusable asset authority and add one focused companion module, `shotContinuityContract.ts`, for shot-level participation and continuity intent. The new module imports existing `MediaReferencePackage`/`ContractIssue` types one-way, performs pure shot validation, performs cross-contract reference ownership validation, and exposes deterministic speaker-reference resolution keyed by explicit `speakerSubjectIds` rather than prompt/reference order.

**Tech Stack:** TypeScript 5.5.x, Vitest 2.1.9 in the existing isolated Media Forge verification workspace, Bashull/Kai `feature/media-reference-contract` branch.

**Spec:** `docs/superpowers/specs/2026-08-23-shot-continuity-contract-design.md`

## Global Constraints

- Do not modify `main`; all work stays on `feature/media-reference-contract` until review/promotion.
- `MediaReferenceContract v0.1.0` remains the authority for media paths, modality, role, order, timing metadata, provenance, preservation constraints and canonical `subjectId` ownership.
- `ShotContinuityContract v0.1.0` stores IDs and shot intent only; it must not duplicate media paths or provider slot numbers.
- Visibility and speech are independent dimensions. Never infer speaker identity from reference order, visual prominence, frame center or prompt mention frequency.
- Dialogue turns explicitly own `speakerSubjectId`.
- When dialogue turns exist, `speakerSubjectIds` must equal the unique set of dialogue-turn speakers.
- Provider slot/index mappings are derived adapter state and are out of scope for this plan.
- Visual identity, audio identity, seam strategy and episodic-memory strategy remain orthogonal fields; no generic `continuity: boolean` is introduced.
- If a canonical reference declares a `subjectId`, a shot binding for another subject must REJECT rather than silently remap ownership.
- References with no canonical subject ownership may be bound without inventing a subject owner; environment/style assets remain valid examples.
- Provider adapters (LTX/MSR, JoyLTX/Echo, MiniMax H3) are intentionally excluded from this plan and require a separate plan after this canonical contract is green.
- Do not add Vitest to the repository dependency manifest in this plan. The current repository `package.json` has no test script/Vitest dependency; use the existing isolated verification workspace used by Media Forge evidence.
- Repository-wide Vite build failure involving pre-existing `DynamicBackground`/dependency issues is not a success criterion for this feature. Record it separately if still present; do not misattribute it to ShotContinuityContract.

---

## File Structure

- **Create:** `src/media/shotContinuityContract.ts` — canonical shot types, pure shot validator, cross-contract binding validator, deterministic speaker-owned reference resolver.
- **Create:** `src/media/__tests__/shotContinuityContract.test.ts` — all RED/GREEN tests for the new contract; no provider mocks.
- **Modify after GREEN only:** `docs/superpowers/specs/2026-08-23-shot-continuity-contract-design.md` — update implementation status/evidence without changing the approved architecture.
- **Modify after GREEN only:** `docs/media-forge/BENCHMARK_MATRIX_v0.1.0.md` only if the already-added adversarial cases need evidence/status text; do not duplicate the cases already present.

The new production module is intentionally one file for v0.1.0 because all behavior is pure contract semantics. Split only in a later refactor if adapter-specific mapping is introduced.

---

### Task 1: Establish the canonical shot contract and basic validation

**Files:**
- Create: `src/media/shotContinuityContract.ts`
- Create: `src/media/__tests__/shotContinuityContract.test.ts`

**Interfaces:**
- Consumes: no new production interface beyond TypeScript built-ins.
- Produces:
  - `SeamStrategy`
  - `VisualIdentityStrategy`
  - `AudioIdentityStrategy`
  - `EpisodicMemoryStrategy`
  - `DialogueTurn`
  - `ShotReferenceBinding`
  - `ShotContinuityContract`
  - `ShotContractValidationResult`
  - `validateShotContinuityContract(shot: ShotContinuityContract): ShotContractValidationResult`

- [ ] **Step 1: Write the first failing tests before the production file exists**

Create `src/media/__tests__/shotContinuityContract.test.ts` with this initial content:

```ts
import { describe, expect, it } from 'vitest';
import {
  ShotContinuityContract,
  validateShotContinuityContract,
} from '../shotContinuityContract';

const baseShot = (): ShotContinuityContract => ({
  version: '0.1.0',
  shotId: 'shot-001',
  visibleSubjectIds: ['character-a', 'character-b'],
  speakerSubjectIds: ['character-b'],
  dialogueTurns: [
    {
      id: 'turn-001',
      speakerSubjectId: 'character-b',
      startMs: 1200,
      endMs: 3400,
      text: 'Hello.',
    },
  ],
  strategies: {
    seam: 'fresh',
    visualIdentity: 'multi_subject_reference',
    audioIdentity: 'speaker_anchor',
    episodicMemory: 'none',
  },
});

describe('validateShotContinuityContract', () => {
  it('passes a valid two-character shot where only character-b speaks', () => {
    expect(validateShotContinuityContract(baseShot())).toEqual({
      severity: 'PASS',
      issues: [],
    });
  });

  it('rejects an empty shot id', () => {
    const shot = baseShot();
    shot.shotId = '   ';

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'EMPTY_SHOT_ID')).toBe(true);
  });

  it('rejects duplicate subject ids inside a participation list', () => {
    const shot = baseShot();
    shot.visibleSubjectIds = ['character-a', 'character-a'];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DUPLICATE_VISIBLE_SUBJECT')).toBe(true);
  });

  it('rejects invalid dialogue intervals', () => {
    const shot = baseShot();
    shot.dialogueTurns![0].startMs = 4000;
    shot.dialogueTurns![0].endMs = 3000;

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'INVALID_DIALOGUE_INTERVAL')).toBe(true);
  });
});
```

- [ ] **Step 2: Run the new test and verify RED for the missing module**

From the existing isolated Media Forge verification checkout/workspace, run:

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Expected: FAIL because `../shotContinuityContract` does not exist. This is the correct first RED. If failure is caused by environment resolution instead, repair/reuse the already-verified Vitest 2.1.9 environment before continuing; do not count infrastructure failure as semantic RED.

- [ ] **Step 3: Add the minimal production types and validator**

Create `src/media/shotContinuityContract.ts` with:

```ts
export type SeamStrategy = 'fresh' | 'av_extend' | 'audio_extend' | 'video_extend';

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

export type EpisodicMemoryStrategy = 'paired_memory' | 'previous_shot' | 'none';

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

export type ShotContractSeverity = 'PASS' | 'WARN' | 'REJECT';

export interface ShotContractIssue {
  severity: Exclude<ShotContractSeverity, 'PASS'>;
  code: string;
  message: string;
  dialogueTurnId?: string;
}

export interface ShotContractValidationResult {
  severity: ShotContractSeverity;
  issues: ShotContractIssue[];
}

const duplicateValues = (values: string[]): string[] => {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const value of values) {
    if (seen.has(value)) duplicates.add(value);
    seen.add(value);
  }
  return [...duplicates];
};

export function validateShotContinuityContract(
  shot: ShotContinuityContract,
): ShotContractValidationResult {
  const issues: ShotContractIssue[] = [];

  if (!shot.shotId.trim()) {
    issues.push({ severity: 'REJECT', code: 'EMPTY_SHOT_ID', message: 'shotId is empty.' });
  }

  for (const subjectId of duplicateValues(shot.visibleSubjectIds)) {
    issues.push({
      severity: 'REJECT',
      code: 'DUPLICATE_VISIBLE_SUBJECT',
      message: `Duplicate visible subject: ${subjectId}`,
    });
  }

  for (const subjectId of duplicateValues(shot.speakerSubjectIds)) {
    issues.push({
      severity: 'REJECT',
      code: 'DUPLICATE_SPEAKER_SUBJECT',
      message: `Duplicate speaker subject: ${subjectId}`,
    });
  }

  const seenTurnIds = new Set<string>();
  for (const turn of shot.dialogueTurns ?? []) {
    if (!turn.speakerSubjectId.trim()) {
      issues.push({
        severity: 'REJECT',
        code: 'EMPTY_DIALOGUE_SPEAKER',
        message: 'Dialogue turn speakerSubjectId is empty.',
        dialogueTurnId: turn.id,
      });
    }

    if (seenTurnIds.has(turn.id)) {
      issues.push({
        severity: 'REJECT',
        code: 'DUPLICATE_DIALOGUE_TURN_ID',
        message: `Duplicate dialogue turn id: ${turn.id}`,
        dialogueTurnId: turn.id,
      });
    }
    seenTurnIds.add(turn.id);

    const startInvalid = turn.startMs !== undefined && (!Number.isFinite(turn.startMs) || turn.startMs < 0);
    const endInvalid = turn.endMs !== undefined && (!Number.isFinite(turn.endMs) || turn.endMs < 0);
    const inverted =
      turn.startMs !== undefined && turn.endMs !== undefined && turn.endMs < turn.startMs;

    if (startInvalid || endInvalid || inverted) {
      issues.push({
        severity: 'REJECT',
        code: 'INVALID_DIALOGUE_INTERVAL',
        message: `Invalid dialogue interval for turn ${turn.id}.`,
        dialogueTurnId: turn.id,
      });
    }
  }

  const severity: ShotContractSeverity = issues.some((issue) => issue.severity === 'REJECT')
    ? 'REJECT'
    : issues.some((issue) => issue.severity === 'WARN')
      ? 'WARN'
      : 'PASS';

  return { severity, issues };
}
```

Do not add cross-contract logic yet.

- [ ] **Step 4: Run the focused test and verify GREEN**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Expected: 4/4 tests PASS.

- [ ] **Step 5: Run existing MediaReference regression tests**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/mediaReferenceContract.test.ts src/media/__tests__/shotContinuityContract.test.ts
```

Expected: existing MediaReference tests plus the four new tests PASS. No SpotSound behavior has been touched yet.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/media/shotContinuityContract.ts src/media/__tests__/shotContinuityContract.test.ts
git commit -m "feat: add shot continuity contract validation"
```

---

### Task 2: Enforce explicit dialogue-speaker consistency

**Files:**
- Modify: `src/media/__tests__/shotContinuityContract.test.ts`
- Modify: `src/media/shotContinuityContract.ts`

**Interfaces:**
- Consumes: `validateShotContinuityContract(shot)` from Task 1.
- Produces: two additional hard validation codes:
  - `DIALOGUE_SPEAKER_NOT_DECLARED`
  - `DECLARED_SPEAKER_WITHOUT_DIALOGUE`

- [ ] **Step 1: Add failing tests for both directions of the speaker-set invariant**

Append inside the existing `describe` block:

```ts
it('rejects a dialogue speaker that is not declared in speakerSubjectIds', () => {
  const shot = baseShot();
  shot.speakerSubjectIds = ['character-a'];

  const result = validateShotContinuityContract(shot);
  expect(result.severity).toBe('REJECT');
  expect(result.issues.some((issue) => issue.code === 'DIALOGUE_SPEAKER_NOT_DECLARED')).toBe(true);
});

it('rejects a declared speaker that has no dialogue turn when dialogueTurns are present', () => {
  const shot = baseShot();
  shot.speakerSubjectIds = ['character-a', 'character-b'];

  const result = validateShotContinuityContract(shot);
  expect(result.severity).toBe('REJECT');
  expect(result.issues.some((issue) => issue.code === 'DECLARED_SPEAKER_WITHOUT_DIALOGUE')).toBe(true);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Expected: the two new tests FAIL because Task 1 does not compare the dialogue-speaker set with `speakerSubjectIds`.

- [ ] **Step 3: Add the minimal set-equality validation**

Inside `validateShotContinuityContract`, after dialogue-turn structural validation, add:

```ts
if (shot.dialogueTurns !== undefined) {
  const dialogueSpeakers = new Set(
    shot.dialogueTurns
      .map((turn) => turn.speakerSubjectId)
      .filter((subjectId) => subjectId.trim().length > 0),
  );
  const declaredSpeakers = new Set(shot.speakerSubjectIds);

  for (const subjectId of dialogueSpeakers) {
    if (!declaredSpeakers.has(subjectId)) {
      issues.push({
        severity: 'REJECT',
        code: 'DIALOGUE_SPEAKER_NOT_DECLARED',
        message: `Dialogue speaker is not declared in speakerSubjectIds: ${subjectId}`,
      });
    }
  }

  for (const subjectId of declaredSpeakers) {
    if (!dialogueSpeakers.has(subjectId)) {
      issues.push({
        severity: 'REJECT',
        code: 'DECLARED_SPEAKER_WITHOUT_DIALOGUE',
        message: `Declared speaker has no dialogue turn: ${subjectId}`,
      });
    }
  }
}
```

Do not require speakers to be visible; off-screen speech is valid by design.

- [ ] **Step 4: Verify GREEN and regression**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts src/media/__tests__/mediaReferenceContract.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/media/shotContinuityContract.ts src/media/__tests__/shotContinuityContract.test.ts
git commit -m "feat: enforce explicit shot speaker identity"
```

---

### Task 3: Validate canonical reference ownership across contracts

**Files:**
- Modify: `src/media/__tests__/shotContinuityContract.test.ts`
- Modify: `src/media/shotContinuityContract.ts`
- Read-only dependency: `src/media/mediaReferenceContract.ts`

**Interfaces:**
- Consumes:
  - `MediaReferencePackage` from `./mediaReferenceContract`
  - `ShotContinuityContract` from Task 1
- Produces:
  - `validateShotReferenceBindings(shot: ShotContinuityContract, mediaPackage: MediaReferencePackage): ShotContractValidationResult`
  - hard codes `UNKNOWN_REFERENCE_ID` and `REFERENCE_SUBJECT_MISMATCH`

- [ ] **Step 1: Add cross-contract test fixtures and failing tests**

Update imports in the test file:

```ts
import { MediaReferencePackage } from '../mediaReferenceContract';
import {
  ShotContinuityContract,
  validateShotContinuityContract,
  validateShotReferenceBindings,
} from '../shotContinuityContract';
```

Add this fixture below `baseShot`:

```ts
const baseMediaPackage = (): MediaReferencePackage => ({
  version: '0.1.0',
  references: [
    {
      id: 'a-face',
      sourceUri: 'hf://example/a-face.png',
      modality: 'image',
      role: 'identity',
      order: 0,
      subjectId: 'character-a',
    },
    {
      id: 'a-voice',
      sourceUri: 'hf://example/a-voice.wav',
      modality: 'audio',
      role: 'voice',
      order: 1,
      subjectId: 'character-a',
      sampleRateHz: 48000,
    },
    {
      id: 'b-face',
      sourceUri: 'hf://example/b-face.png',
      modality: 'image',
      role: 'identity',
      order: 2,
      subjectId: 'character-b',
    },
    {
      id: 'b-voice',
      sourceUri: 'hf://example/b-voice.wav',
      modality: 'audio',
      role: 'voice',
      order: 3,
      subjectId: 'character-b',
      sampleRateHz: 48000,
    },
    {
      id: 'festival-stage',
      sourceUri: 'hf://example/stage.png',
      modality: 'image',
      role: 'environment',
      order: 4,
    },
  ],
});
```

Append these tests:

```ts
it('rejects a shot binding that references an unknown media id', () => {
  const shot = baseShot();
  shot.referenceBindings = [
    { subjectId: 'character-b', referenceIds: ['missing-ref'], purpose: 'voice' },
  ];

  const result = validateShotReferenceBindings(shot, baseMediaPackage());
  expect(result.severity).toBe('REJECT');
  expect(result.issues.some((issue) => issue.code === 'UNKNOWN_REFERENCE_ID')).toBe(true);
});

it('rejects binding character-b to a reference canonically owned by character-a', () => {
  const shot = baseShot();
  shot.referenceBindings = [
    { subjectId: 'character-b', referenceIds: ['a-voice'], purpose: 'voice' },
  ];

  const result = validateShotReferenceBindings(shot, baseMediaPackage());
  expect(result.severity).toBe('REJECT');
  expect(result.issues.some((issue) => issue.code === 'REFERENCE_SUBJECT_MISMATCH')).toBe(true);
});

it('allows a subjectless environment reference without inventing canonical ownership', () => {
  const shot = baseShot();
  shot.referenceBindings = [
    { referenceIds: ['festival-stage'], purpose: 'environment' },
  ];

  expect(validateShotReferenceBindings(shot, baseMediaPackage())).toEqual({
    severity: 'PASS',
    issues: [],
  });
});
```

- [ ] **Step 2: Run and verify RED**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Expected: FAIL because `validateShotReferenceBindings` does not exist.

- [ ] **Step 3: Import the existing media contract type and implement cross-contract validation**

At the top of `src/media/shotContinuityContract.ts` add:

```ts
import type { MediaReferencePackage } from './mediaReferenceContract';
```

Then add:

```ts
export function validateShotReferenceBindings(
  shot: ShotContinuityContract,
  mediaPackage: MediaReferencePackage,
): ShotContractValidationResult {
  const issues: ShotContractIssue[] = [];
  const referencesById = new Map(mediaPackage.references.map((ref) => [ref.id, ref]));

  for (const binding of shot.referenceBindings ?? []) {
    for (const referenceId of binding.referenceIds) {
      const ref = referencesById.get(referenceId);
      if (!ref) {
        issues.push({
          severity: 'REJECT',
          code: 'UNKNOWN_REFERENCE_ID',
          message: `Unknown reference id: ${referenceId}`,
        });
        continue;
      }

      if (
        binding.subjectId !== undefined &&
        ref.subjectId !== undefined &&
        binding.subjectId !== ref.subjectId
      ) {
        issues.push({
          severity: 'REJECT',
          code: 'REFERENCE_SUBJECT_MISMATCH',
          message: `Reference ${referenceId} belongs to ${ref.subjectId}, not ${binding.subjectId}.`,
        });
      }
    }
  }

  return {
    severity: issues.length > 0 ? 'REJECT' : 'PASS',
    issues,
  };
}
```

Do not mutate `MediaReferencePackage` or infer ownership for references whose canonical `subjectId` is absent.

- [ ] **Step 4: Verify GREEN plus both contract suites**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/mediaReferenceContract.test.ts src/media/__tests__/shotContinuityContract.test.ts
```

Expected: all tests PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/media/shotContinuityContract.ts src/media/__tests__/shotContinuityContract.test.ts
git commit -m "feat: validate shot reference ownership"
```

---

### Task 4: Resolve speaker-owned references without using reference order

**Files:**
- Modify: `src/media/__tests__/shotContinuityContract.test.ts`
- Modify: `src/media/shotContinuityContract.ts`

**Interfaces:**
- Consumes:
  - `ShotContinuityContract`
  - `MediaReferencePackage`
  - explicit `speakerSubjectIds`
- Produces:
  - `SpeakerReferenceResolution`
  - `resolveSpeakerReferenceIds(shot: ShotContinuityContract, mediaPackage: MediaReferencePackage, role?: 'voice' | 'identity'): SpeakerReferenceResolution[]`

The helper is canonical preparation data for later adapters. It never chooses a speaker; it resolves references for speakers the shot already declared.

- [ ] **Step 1: Add the donor-failure regression test first**

Update the shot-module import to include `resolveSpeakerReferenceIds`, then append:

```ts
it('resolves character-b voice references even when character-a references appear first', () => {
  const shot = baseShot();
  shot.referenceBindings = [
    { subjectId: 'character-a', referenceIds: ['a-face', 'a-voice'], purpose: 'identity' },
    { subjectId: 'character-b', referenceIds: ['b-face', 'b-voice'], purpose: 'voice' },
  ];

  expect(resolveSpeakerReferenceIds(shot, baseMediaPackage(), 'voice')).toEqual([
    {
      speakerSubjectId: 'character-b',
      referenceIds: ['b-voice'],
    },
  ]);
});
```

This test deliberately places all A references before B in canonical media order. The expected result must remain B because B is the explicit speaker.

- [ ] **Step 2: Run and verify RED**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Expected: FAIL because `resolveSpeakerReferenceIds` does not exist.

- [ ] **Step 3: Implement the smallest deterministic resolver**

Add to `src/media/shotContinuityContract.ts`:

```ts
export interface SpeakerReferenceResolution {
  speakerSubjectId: string;
  referenceIds: string[];
}

export function resolveSpeakerReferenceIds(
  shot: ShotContinuityContract,
  mediaPackage: MediaReferencePackage,
  role: 'voice' | 'identity' = 'voice',
): SpeakerReferenceResolution[] {
  const boundReferenceIdsBySubject = new Map<string, Set<string>>();

  for (const binding of shot.referenceBindings ?? []) {
    if (!binding.subjectId) continue;
    const ids = boundReferenceIdsBySubject.get(binding.subjectId) ?? new Set<string>();
    for (const referenceId of binding.referenceIds) ids.add(referenceId);
    boundReferenceIdsBySubject.set(binding.subjectId, ids);
  }

  return shot.speakerSubjectIds.map((speakerSubjectId) => {
    const allowedIds = boundReferenceIdsBySubject.get(speakerSubjectId);
    const referenceIds = mediaPackage.references
      .filter(
        (ref) =>
          ref.subjectId === speakerSubjectId &&
          ref.role === role &&
          (allowedIds === undefined || allowedIds.has(ref.id)),
      )
      .map((ref) => ref.id);

    return { speakerSubjectId, referenceIds };
  });
}
```

This implementation intentionally preserves canonical media-package order only *within the already-selected speaker*. It never uses global reference order to decide who speaks.

- [ ] **Step 4: Add one more test proving multi-speaker output follows explicit speaker order**

Append:

```ts
it('resolves each explicit speaker independently in a multi-speaker shot', () => {
  const shot = baseShot();
  shot.speakerSubjectIds = ['character-b', 'character-a'];
  shot.dialogueTurns = [
    { id: 'turn-b', speakerSubjectId: 'character-b', text: 'B' },
    { id: 'turn-a', speakerSubjectId: 'character-a', text: 'A' },
  ];
  shot.referenceBindings = [
    { subjectId: 'character-a', referenceIds: ['a-voice'], purpose: 'voice' },
    { subjectId: 'character-b', referenceIds: ['b-voice'], purpose: 'voice' },
  ];

  expect(resolveSpeakerReferenceIds(shot, baseMediaPackage(), 'voice')).toEqual([
    { speakerSubjectId: 'character-b', referenceIds: ['b-voice'] },
    { speakerSubjectId: 'character-a', referenceIds: ['a-voice'] },
  ]);
});
```

- [ ] **Step 5: Run focused and complete Media Forge tests**

Focused:

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__/shotContinuityContract.test.ts
```

Then all current Media Forge tests:

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__
```

Expected: every Media Forge test passes, including existing SpotSound and MediaReference tests. Record the exact test count; do not predeclare a number in documentation until the fresh run reports it.

- [ ] **Step 6: Commit Task 4**

```bash
git add src/media/shotContinuityContract.ts src/media/__tests__/shotContinuityContract.test.ts
git commit -m "feat: resolve speaker-owned media references"
```

---

### Task 5: Final verification, documentation evidence and promotion boundary

**Files:**
- Modify: `docs/superpowers/specs/2026-08-23-shot-continuity-contract-design.md`
- Inspect: `docs/media-forge/BENCHMARK_MATRIX_v0.1.0.md`
- No production changes unless a test exposed a real defect, in which case return to RED/GREEN before this task.

**Interfaces:**
- Consumes: all green behavior from Tasks 1–4.
- Produces: evidence trail only; no backend support status.

- [ ] **Step 1: Run the complete Media Forge test directory fresh**

```bash
node node_modules/vitest/vitest.mjs run src/media/__tests__
```

Record exact files/tests/pass/fail output.

- [ ] **Step 2: Run TypeScript/Vite validation only as diagnostic, without redefining feature success**

```bash
npm run build
```

If the previously observed unrelated `DynamicBackground`/dependency baseline still fails, record it as `BLOCKED_PREEXISTING` and keep ShotContinuityContract status based on its isolated tests. If the build now passes, record the fresh evidence instead. Do not claim either result before running it.

- [ ] **Step 3: Update the design spec status with exact evidence**

Change the spec header from:

```text
Status: DESIGN_APPROVED_IN_CHAT · SPEC_FOR_REVIEW · NOT_IMPLEMENTED
```

to this shape using the *actual* fresh evidence values:

```text
Status: IMPLEMENTED_ON_FEATURE_BRANCH · TESTED · NOT_MERGED · NOT_BACKEND_SUPPORTED
Implementation evidence: <exact commit(s)> · <exact test command/result>
```

Also add a short `Implementation delta` section stating:

```text
Implemented: canonical ShotContinuityContract types; pure shot validation; explicit dialogue/speaker-set validation; cross-contract reference ownership validation; deterministic speaker-owned reference resolution.
Not implemented: LTX/MSR adapter, JoyLTX/Echo adapter, MiniMax H3 adapter, runtime video generation, backend-specific slot routing, benchmark generation runs.
```

Replace angle-bracket evidence placeholders with actual commit/test values before committing. Do not leave placeholders in the repository.

- [ ] **Step 4: Inspect benchmark documentation for duplication**

Read `docs/media-forge/BENCHMARK_MATRIX_v0.1.0.md`. If the adversarial multi-character cases are already present from the approved design commit, make no content change. If evidence/status needs one sentence, add only the tested contract status; do not mark any backend benchmark as passed.

- [ ] **Step 5: Commit documentation evidence**

```bash
git add docs/superpowers/specs/2026-08-23-shot-continuity-contract-design.md docs/media-forge/BENCHMARK_MATRIX_v0.1.0.md
git commit -m "docs: record shot continuity validation evidence"
```

If the benchmark file was unchanged, omit it from `git add`.

- [ ] **Step 6: Verify branch/PR boundary**

Confirm PR #33 remains draft/open and unmerged. The terminal state for this plan is:

```text
ShotContinuityContract: IMPLEMENTED_ON_FEATURE_BRANCH / TESTED / NOT_MERGED / NOT_PRODUCTION / NOT_BACKEND_SUPPORTED
MediaReferenceContract: unchanged authority semantics
Provider adapters: separate follow-up work
```

Do not promote LTX-2.5, JoyLTX/EchoVid, MSR or MiniMax H3 based on this contract-only plan.

---

## Plan Self-Review Result

- **Spec coverage:** The plan covers canonical types, visibility/speech separation, dialogue speaker ownership, reference-ID composition, canonical subject ownership, no provider slots in canonical state, orthogonal continuity strategies, no silent cross-subject remapping, first donor-failure regression, testing and promotion boundary.
- **Deliberately separate follow-up subsystem:** provider-specific continuity adapters and runtime canaries. They are excluded because they are independently reviewable and require backend-specific evidence after the canonical contract is green.
- **Placeholder scan:** no repository step may retain placeholder evidence; Task 5 explicitly requires replacing evidence tokens with fresh values before commit.
- **Type consistency:** all functions consumed by later tasks are introduced in earlier tasks with exact signatures. `MediaReferencePackage` remains imported one-way from the existing contract, avoiding circular ownership.
