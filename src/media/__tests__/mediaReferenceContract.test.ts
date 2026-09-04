import { describe, expect, it } from 'vitest';
import {
  MediaReferencePackage,
  validateMediaReferencePackage,
} from '../mediaReferenceContract';

const basePackage = (): MediaReferencePackage => ({
  version: '0.1.0',
  references: [
    {
      id: 'subject-image',
      sourceUri: 'hf://example/subject.png',
      modality: 'image',
      role: 'identity',
      order: 0,
      subjectId: 'character-a',
      constraints: { preserveIdentity: true },
    },
  ],
  policy: {
    strictOrder: true,
    rejectMetadataLoss: true,
    identityGuardRequired: true,
  },
});

describe('validateMediaReferencePackage', () => {
  it('passes a valid package', () => {
    expect(validateMediaReferencePackage(basePackage())).toEqual({
      severity: 'PASS',
      issues: [],
    });
  });

  it('rejects duplicate order values', () => {
    const pkg = basePackage();
    pkg.references.push({
      id: 'second',
      sourceUri: 'hf://example/second.png',
      modality: 'image',
      role: 'wardrobe',
      order: 0,
    });

    const result = validateMediaReferencePackage(pkg);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'DUPLICATE_ORDER')).toBe(true);
  });

  it('rejects missing fps for timing-critical video when metadata loss is forbidden', () => {
    const pkg = basePackage();
    pkg.references.push({
      id: 'drive-video',
      sourceUri: 'hf://example/drive.mp4',
      modality: 'video',
      role: 'motion',
      order: 1,
      constraints: { preserveTiming: true },
    });

    const result = validateMediaReferencePackage(pkg);
    expect(result.severity).toBe('REJECT');
    expect(result.issues.some((issue) => issue.code === 'VIDEO_FPS_REQUIRED')).toBe(true);
  });

  it('warns instead of rejecting metadata loss when policy allows it', () => {
    const pkg = basePackage();
    pkg.policy = { rejectMetadataLoss: false };
    pkg.references.push({
      id: 'voice',
      sourceUri: 'hf://example/voice.wav',
      modality: 'audio',
      role: 'voice',
      order: 1,
      constraints: { preserveTiming: true },
    });

    const result = validateMediaReferencePackage(pkg);
    expect(result.severity).toBe('WARN');
    expect(result.issues.some((issue) => issue.code === 'AUDIO_SAMPLE_RATE_REQUIRED')).toBe(true);
  });
});
