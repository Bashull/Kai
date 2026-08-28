export type SeamStrategy = 'fresh' | 'av_extend' | 'audio_extend' | 'video_extend';
export type VisualIdentityStrategy =
  | 'reference_conditioning'
  | 'multi_subject_reference'
  | 'previous_frame'
  | 'none';
export type AudioIdentityStrategy = 'speaker_anchor' | 'previous_tail' | 'reference_audio' | 'none';
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
}
export interface ShotContractValidationResult {
  severity: ShotContractSeverity;
  issues: ShotContractIssue[];
}

const sameStringSet = (a: string[], b: string[]): boolean => {
  if (a.length !== b.length) return false;
  const right = new Set(b);
  return a.every((value) => right.has(value));
};
export function validateShotContinuityContract(
  shot: ShotContinuityContract,
): ShotContractValidationResult {
  const issues: ShotContractIssue[] = [];

  if (!shot.shotId.trim()) {
    issues.push({ severity: 'REJECT', code: 'EMPTY_SHOT_ID', message: 'shotId is empty.' });
  }

  if (new Set(shot.visibleSubjectIds).size !== shot.visibleSubjectIds.length) {
    issues.push({
      severity: 'REJECT',
      code: 'DUPLICATE_VISIBLE_SUBJECT',
      message: 'visibleSubjectIds contains duplicates.',
    });
  }

  if (new Set(shot.speakerSubjectIds).size !== shot.speakerSubjectIds.length) {
    issues.push({
      severity: 'REJECT',
      code: 'DUPLICATE_SPEAKER_SUBJECT',
      message: 'speakerSubjectIds contains duplicates.',
    });
  }

  const seenDialogueTurnIds = new Set<string>();
  for (const turn of shot.dialogueTurns ?? []) {
    if (seenDialogueTurnIds.has(turn.id)) {
      issues.push({
        severity: 'REJECT',
        code: 'DUPLICATE_DIALOGUE_TURN',
        message: `Duplicate dialogue turn id: ${turn.id}.`,
      });
    }
    seenDialogueTurnIds.add(turn.id);

    const invalidStart = turn.startMs !== undefined && turn.startMs < 0;
    const invalidEnd = turn.endMs !== undefined && turn.endMs < 0;
    const inverted =
      turn.startMs !== undefined && turn.endMs !== undefined && turn.endMs < turn.startMs;
    if (invalidStart || invalidEnd || inverted) {
      issues.push({
        severity: 'REJECT',
        code: 'INVALID_DIALOGUE_INTERVAL',
        message: `Invalid dialogue interval for turn ${turn.id}.`,
      });
    }
  }

  const dialogueSpeakers = [
    ...new Set((shot.dialogueTurns ?? []).map((turn) => turn.speakerSubjectId)),
  ];

  if (shot.dialogueTurns?.length && !sameStringSet(dialogueSpeakers, shot.speakerSubjectIds)) {
    issues.push({
      severity: 'REJECT',
      code: 'DIALOGUE_SPEAKER_MISMATCH',
      message: 'speakerSubjectIds must equal the unique speakers declared by dialogueTurns.',
    });
  }

  return {
    severity: issues.length ? 'REJECT' : 'PASS',
    issues,
  };
}
export function validateShotReferenceBindings(
  shot: ShotContinuityContract,
  mediaPackage: import('./mediaReferenceContract').MediaReferencePackage,
): ShotContractValidationResult {
  const issues: ShotContractIssue[] = [];
  const refs = new Map(mediaPackage.references.map((ref) => [ref.id, ref]));

  for (const binding of shot.referenceBindings ?? []) {
    for (const referenceId of binding.referenceIds) {
      const ref = refs.get(referenceId);
      if (!ref) {
        issues.push({
          severity: 'REJECT',
          code: 'UNKNOWN_REFERENCE',
          message: `Unknown reference id: ${referenceId}`,
        });
      } else if (binding.subjectId && ref.subjectId && binding.subjectId !== ref.subjectId) {
        issues.push({
          severity: 'REJECT',
          code: 'SUBJECT_REFERENCE_MISMATCH',
          message: `Binding subject ${binding.subjectId} conflicts with reference owner ${ref.subjectId}.`,
        });
      }
    }
  }

  return { severity: issues.length ? 'REJECT' : 'PASS', issues };
}
