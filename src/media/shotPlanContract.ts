export interface ShotFraming {
  shotSize: string;
  cameraAngle: string;
  lens: string;
  cameraMotion: string;
  transition: string;
}

export interface ShotPlanContract {
  version: '0.1.0';
  shotId: string;
  sceneId: string;
  order: number;
  startMs: number;
  durationMs: number;
  framing: ShotFraming;
}

export type ShotPlanSeverity = 'PASS' | 'WARN' | 'REJECT';
export interface ShotPlanIssue {
  severity: Exclude<ShotPlanSeverity, 'PASS'>;
  code: string;
  message: string;
}

export interface ShotPlanValidationResult {
  severity: ShotPlanSeverity;
  issues: ShotPlanIssue[];
}
export function validateShotPlanContract(
  plan: ShotPlanContract,
): ShotPlanValidationResult {
  const issues: ShotPlanIssue[] = [];

  if (!plan.shotId.trim()) {
    issues.push({ severity: 'REJECT', code: 'EMPTY_SHOT_ID', message: 'shotId is empty.' });
  }

  if (!plan.sceneId.trim()) {
    issues.push({ severity: 'REJECT', code: 'EMPTY_SCENE_ID', message: 'sceneId is empty.' });
  }

  if (!Number.isFinite(plan.durationMs) || plan.durationMs <= 0) {
    issues.push({
      severity: 'REJECT',
      code: 'INVALID_DURATION',
      message: 'durationMs must be a positive finite number.',
    });
  }

  if (!Number.isFinite(plan.startMs) || plan.startMs < 0) {
    issues.push({
      severity: 'REJECT',
      code: 'INVALID_START',
      message: 'startMs must be a non-negative finite number.',
    });
  }

  if (!Number.isInteger(plan.order) || plan.order < 0) {
    issues.push({
      severity: 'REJECT',
      code: 'INVALID_ORDER',
      message: 'order must be a non-negative integer.',
    });
  }

  return {
    severity: issues.length ? 'REJECT' : 'PASS',
    issues,
  };
}

export function validateShotPlanContinuityAlignment(
  plan: ShotPlanContract,
  continuity: import('./shotContinuityContract').ShotContinuityContract,
): ShotPlanValidationResult {
  if (plan.shotId !== continuity.shotId) {
    return {
      severity: 'REJECT',
      issues: [{
        severity: 'REJECT',
        code: 'SHOT_ID_MISMATCH',
        message: `Shot plan ${plan.shotId} does not match continuity ${continuity.shotId}.`,
      }],
    };
  }

  return { severity: 'PASS', issues: [] };
}
