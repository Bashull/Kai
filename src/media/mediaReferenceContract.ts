export type MediaModality =
  | 'image'
  | 'video'
  | 'audio'
  | 'text'
  | 'mask'
  | 'depth'
  | 'normals'
  | 'pose'
  | 'segmentation'
  | 'identity_anchor';

export type ReferenceRole =
  | 'identity'
  | 'appearance'
  | 'wardrobe'
  | 'environment'
  | 'motion'
  | 'camera'
  | 'voice'
  | 'music'
  | 'timing'
  | 'structure'
  | 'style'
  | 'negative'
  | 'other';

export type ContractSeverity = 'PASS' | 'WARN' | 'REJECT';

export interface MediaReference {
  id: string;
  sourceUri: string;
  modality: MediaModality;
  role: ReferenceRole;
  order: number;
  subjectId?: string;
  mimeType?: string;
  fps?: number;
  sampleRateHz?: number;
  durationMs?: number;
  startMs?: number;
  endMs?: number;
  frameIndex?: number;
  weight?: number;
  provenance?: {
    source: string;
    sourceId?: string;
    captureEventId?: string;
    sha256?: string;
  };
  constraints?: {
    preserveIdentity?: boolean;
    preserveGeometry?: boolean;
    preserveTiming?: boolean;
    preserveAudioPitch?: boolean;
  };
  metadata?: Record<string, unknown>;
}

export interface MediaReferencePackage {
  version: '0.1.0';
  references: MediaReference[];
  primarySubjectIds?: string[];
  target?: {
    width?: number;
    height?: number;
    fps?: number;
    sampleRateHz?: number;
    durationMs?: number;
  };
  policy?: {
    strictOrder?: boolean;
    rejectMetadataLoss?: boolean;
    identityGuardRequired?: boolean;
  };
}

export interface ContractIssue {
  severity: Exclude<ContractSeverity, 'PASS'>;
  code: string;
  message: string;
  referenceId?: string;
}

export interface ContractValidationResult {
  severity: ContractSeverity;
  issues: ContractIssue[];
}

const isPositiveFinite = (value: number | undefined): boolean =>
  value === undefined || (Number.isFinite(value) && value > 0);

export function validateMediaReferencePackage(
  pkg: MediaReferencePackage,
): ContractValidationResult {
  const issues: ContractIssue[] = [];

  if (pkg.version !== '0.1.0') {
    issues.push({
      severity: 'REJECT',
      code: 'UNSUPPORTED_VERSION',
      message: `Unsupported MediaReferencePackage version: ${pkg.version}`,
    });
  }

  const seenIds = new Set<string>();
  const seenOrder = new Set<number>();

  for (const ref of pkg.references) {
    if (!ref.id.trim()) {
      issues.push({ severity: 'REJECT', code: 'EMPTY_ID', message: 'Reference id is empty.' });
    } else if (seenIds.has(ref.id)) {
      issues.push({
        severity: 'REJECT',
        code: 'DUPLICATE_ID',
        message: `Duplicate reference id: ${ref.id}`,
        referenceId: ref.id,
      });
    }
    seenIds.add(ref.id);

    if (!Number.isInteger(ref.order) || ref.order < 0) {
      issues.push({
        severity: 'REJECT',
        code: 'INVALID_ORDER',
        message: 'Reference order must be a non-negative integer.',
        referenceId: ref.id,
      });
    } else if (seenOrder.has(ref.order)) {
      issues.push({
        severity: 'REJECT',
        code: 'DUPLICATE_ORDER',
        message: `Duplicate reference order: ${ref.order}`,
        referenceId: ref.id,
      });
    }
    seenOrder.add(ref.order);

    if (!isPositiveFinite(ref.fps)) {
      issues.push({
        severity: 'REJECT',
        code: 'INVALID_FPS',
        message: 'fps must be a positive finite number.',
        referenceId: ref.id,
      });
    }

    if (!isPositiveFinite(ref.sampleRateHz)) {
      issues.push({
        severity: 'REJECT',
        code: 'INVALID_SAMPLE_RATE',
        message: 'sampleRateHz must be a positive finite number.',
        referenceId: ref.id,
      });
    }

    if (ref.modality === 'video' && ref.constraints?.preserveTiming && ref.fps === undefined) {
      issues.push({
        severity: pkg.policy?.rejectMetadataLoss ? 'REJECT' : 'WARN',
        code: 'VIDEO_FPS_REQUIRED',
        message: 'Timing-critical video reference is missing fps.',
        referenceId: ref.id,
      });
    }

    if (ref.modality === 'audio' && ref.constraints?.preserveTiming && ref.sampleRateHz === undefined) {
      issues.push({
        severity: pkg.policy?.rejectMetadataLoss ? 'REJECT' : 'WARN',
        code: 'AUDIO_SAMPLE_RATE_REQUIRED',
        message: 'Timing-critical audio reference is missing sampleRateHz.',
        referenceId: ref.id,
      });
    }
  }

  const severity: ContractSeverity = issues.some((issue) => issue.severity === 'REJECT')
    ? 'REJECT'
    : issues.some((issue) => issue.severity === 'WARN')
      ? 'WARN'
      : 'PASS';

  return { severity, issues };
}
