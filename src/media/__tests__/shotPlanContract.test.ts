import { describe, expect, it } from 'vitest';
import { ShotContinuityContract } from '../shotContinuityContract';
import {
  ShotPlanContract,
  validateShotPlanContract,
  validateShotPlanContinuityAlignment,
} from '../shotPlanContract';

const basePlan = (): ShotPlanContract => ({
  version: '0.1.0',
  shotId: 'shot-001',
  sceneId: 'scene-001',
  order: 0,
  startMs: 0,
  durationMs: 2000,
  framing: {
    shotSize: 'medium shot',
    cameraAngle: 'eye level',
    lens: '50mm',
    cameraMotion: 'Static',
    transition: 'Cut',
  },
});

describe('validateShotPlanContract', () => {
  it('rejects zero duration', () => {
    const plan = basePlan();
    plan.durationMs = 0;
    const result = validateShotPlanContract(plan);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'INVALID_DURATION')).toBe(true);
  });
});

describe('shot plan timing invariants', () => {
  it('rejects negative start time', () => {
    const plan = basePlan();
    plan.startMs = -1;
    const result = validateShotPlanContract(plan);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'INVALID_START')).toBe(true);
  });
});

describe('shot plan ordering invariants', () => {
  it('rejects negative or fractional order', () => {
    const plan = basePlan();
    plan.order = 1.5;
    const result = validateShotPlanContract(plan);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'INVALID_ORDER')).toBe(true);
  });
});

describe('shot plan identity invariants', () => {
  it('rejects empty shotId', () => {
    const plan = basePlan();
    plan.shotId = '   ';
    const result = validateShotPlanContract(plan);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'EMPTY_SHOT_ID')).toBe(true);
  });
});

describe('shot plan scene invariants', () => {
  it('rejects empty sceneId', () => {
    const plan = basePlan();
    plan.sceneId = '';
    const result = validateShotPlanContract(plan);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'EMPTY_SCENE_ID')).toBe(true);
  });
});

describe('shot plan continuity alignment', () => {
  it('rejects mismatched shot ids', () => {
    const plan = basePlan();
    const continuity: ShotContinuityContract = {
      version: '0.1.0',
      shotId: 'shot-999',
      visibleSubjectIds: [],
      speakerSubjectIds: [],
      strategies: {
        seam: 'fresh',
        visualIdentity: 'none',
        audioIdentity: 'none',
        episodicMemory: 'none',
      },
    };
    const result = validateShotPlanContinuityAlignment(plan, continuity);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'SHOT_ID_MISMATCH')).toBe(true);
  });
});
