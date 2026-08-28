import { describe, expect, it } from 'vitest';
import { compileStoryboardFramesToShotPlans } from '../storyboardReferenceAdapter';

describe('compileStoryboardFramesToShotPlans', () => {
  it('converts donor frame order, duration and shot metadata into a deterministic timeline', () => {
    const plans = compileStoryboardFramesToShotPlans([
      {
        id: 'frame-b', order: 1, durationS: 2,
        shot: {
          shotSize: 'close-up', cameraAngle: 'low angle', lens: '85mm',
          movement: 'Dolly in', transition: 'Cut',
        },
      },
      {
        id: 'frame-a', order: 0, durationS: 1.5,
        shot: {
          shotSize: 'wide shot', cameraAngle: 'eye level', lens: '35mm',
          movement: 'Static', transition: 'Fade in',
        },
      },
    ], 'scene-001');

    expect(plans.map((plan) => [plan.shotId, plan.startMs, plan.durationMs])).toEqual([
      ['frame-a', 0, 1500],
      ['frame-b', 1500, 2000],
    ]);
    expect(plans[1].framing.cameraMotion).toBe('Dolly in');
    expect(plans[1].framing.lens).toBe('85mm');
  });
});
