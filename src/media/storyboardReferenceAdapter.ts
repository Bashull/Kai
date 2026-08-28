import type { ShotPlanContract } from './shotPlanContract';

export interface StoryboardDonorShotMeta {
  shotSize: string;
  cameraAngle: string;
  lens: string;
  movement: string;
  transition: string;
}

export interface StoryboardDonorFrame {
  id: string;
  order: number;
  durationS: number;
  shot: StoryboardDonorShotMeta;
}

export function compileStoryboardFramesToShotPlans(
  frames: StoryboardDonorFrame[],
  sceneId: string,
): ShotPlanContract[] {
  let cursorMs = 0;
  return [...frames]
    .sort((a, b) => a.order - b.order)
    .map((frame) => {
      const durationMs = Math.round(frame.durationS * 1000);
      const plan: ShotPlanContract = {
        version: '0.1.0',
        shotId: frame.id,
        sceneId,
        order: frame.order,
        startMs: cursorMs,
        durationMs,
        framing: {
          shotSize: frame.shot.shotSize,
          cameraAngle: frame.shot.cameraAngle,
          lens: frame.shot.lens,
          cameraMotion: frame.shot.movement,
          transition: frame.shot.transition,
        },
      };
      cursorMs += durationMs;
      return plan;
    });
}
