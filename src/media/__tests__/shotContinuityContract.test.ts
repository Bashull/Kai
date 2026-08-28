import { describe, expect, it } from 'vitest';
import { MediaReferencePackage } from '../mediaReferenceContract';
import {
  ShotContinuityContract,
  validateShotContinuityContract,
  validateShotReferenceBindings,
} from '../shotContinuityContract';

const baseShot = (): ShotContinuityContract => ({
  version: '0.1.0',
  shotId: 'shot-001',
  visibleSubjectIds: ['subject-a', 'subject-b'],
  speakerSubjectIds: ['subject-b'],
  dialogueTurns: [
    { id: 'turn-1', speakerSubjectId: 'subject-b', startMs: 1200, endMs: 3400 },
  ],
  referenceBindings: [
    { subjectId: 'subject-a', referenceIds: ['ref-a'], purpose: 'identity' },
    { subjectId: 'subject-b', referenceIds: ['ref-b'], purpose: 'identity' },
  ],
  strategies: {
    seam: 'fresh',
    visualIdentity: 'multi_subject_reference',
    audioIdentity: 'speaker_anchor',
    episodicMemory: 'none',
  },
});
const mediaPackage = (): MediaReferencePackage => ({
  version: '0.1.0',
  references: [
    {
      id: 'ref-a',
      sourceUri: 'hf://example/a.png',
      modality: 'image',
      role: 'identity',
      order: 0,
      subjectId: 'subject-a',
    },
    {
      id: 'ref-b',
      sourceUri: 'hf://example/b.png',
      modality: 'image',
      role: 'identity',
      order: 1,
      subjectId: 'subject-b',
    },
  ],
});

describe('validateShotContinuityContract', () => {
  it('accepts explicit speaker B even when reference A comes first', () => {
    const shot = baseShot();
    expect(validateShotContinuityContract(shot).severity).toBe('PASS');
    expect(shot.speakerSubjectIds).toEqual(['subject-b']);
  });
  it('rejects when dialogue speakers contradict speakerSubjectIds', () => {
    const shot = baseShot();
    shot.speakerSubjectIds = ['subject-a'];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DIALOGUE_SPEAKER_MISMATCH')).toBe(true);
  });
});

describe('validateShotReferenceBindings', () => {
  it('passes when bindings preserve canonical subject ownership', () => {
    expect(validateShotReferenceBindings(baseShot(), mediaPackage())).toEqual({
      severity: 'PASS',
      issues: [],
    });
  });

  it('rejects subject/reference leakage', () => {
    const shot = baseShot();
    shot.referenceBindings = [
      { subjectId: 'subject-b', referenceIds: ['ref-a'], purpose: 'identity' },
    ];

    const result = validateShotReferenceBindings(shot, mediaPackage());
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'SUBJECT_REFERENCE_MISMATCH')).toBe(true);
  });
});

describe('shot continuity hard invariants', () => {
  it('rejects an empty shotId', () => {
    const shot = baseShot();
    shot.shotId = '   ';

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'EMPTY_SHOT_ID')).toBe(true);
  });
});

describe('shot continuity subject identity invariants', () => {
  it('rejects duplicate visible subject ids', () => {
    const shot = baseShot();
    shot.visibleSubjectIds = ['subject-a', 'subject-a'];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DUPLICATE_VISIBLE_SUBJECT')).toBe(true);
  });
});

describe('shot continuity speaker identity invariants', () => {
  it('rejects duplicate speaker subject ids', () => {
    const shot = baseShot();
    shot.speakerSubjectIds = ['subject-b', 'subject-b'];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DUPLICATE_SPEAKER_SUBJECT')).toBe(true);
  });
});

describe('shot continuity dialogue interval invariants', () => {
  it('rejects an inverted dialogue interval', () => {
    const shot = baseShot();
    shot.dialogueTurns = [
      { id: 'turn-1', speakerSubjectId: 'subject-b', startMs: 3400, endMs: 1200 },
    ];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'INVALID_DIALOGUE_INTERVAL')).toBe(true);
  });
});

describe('shot continuity dialogue identity invariants', () => {
  it('rejects duplicate dialogue turn ids', () => {
    const shot = baseShot();
    shot.dialogueTurns = [
      { id: 'turn-1', speakerSubjectId: 'subject-b', startMs: 0, endMs: 1000 },
      { id: 'turn-1', speakerSubjectId: 'subject-b', startMs: 1000, endMs: 2000 },
    ];

    const result = validateShotContinuityContract(shot);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DUPLICATE_DIALOGUE_TURN')).toBe(true);
  });
});

describe('shot continuity reference existence invariants', () => {
  it('rejects a binding to an unknown reference id', () => {
    const shot = baseShot();
    shot.referenceBindings = [
      { subjectId: 'subject-b', referenceIds: ['missing-ref'], purpose: 'identity' },
    ];

    const result = validateShotReferenceBindings(shot, mediaPackage());
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'UNKNOWN_REFERENCE')).toBe(true);
  });
});
