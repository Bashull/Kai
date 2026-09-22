# KAI Media Forge · MediaReferenceContract v0.1.0

Status: DRAFT_IMPLEMENTABLE
Authority target: Bashull/Kai
Purpose: common, backend-agnostic contract for media references used by KAI Studio / kai-media-forge.

## Why this exists
Different video/audio backends interpret references differently. Some depend on ordering, modality, FPS or sample rate. KAI must preserve that semantics instead of reducing every reference to a path or URL.

## Core principles
- CONTENT_OBJECT != CAPTURE_EVENT.
- Reference order is explicit and preserved.
- Modality is explicit: image, video, audio, text, mask, depth, normals, pose, segmentation, identity-anchor.
- Timing metadata is first-class: fps, sample_rate, duration, start/end offsets.
- Role is explicit and independent from person identity.
- Provenance and authority are recorded without copying secrets.
- A backend adapter may transform the contract, but may not silently discard required semantics.

## Type sketch
```ts
export type MediaModality =
  | 'image' | 'video' | 'audio' | 'text'
  | 'mask' | 'depth' | 'normals' | 'pose'
  | 'segmentation' | 'identity_anchor';

export type ReferenceRole =
  | 'identity' | 'appearance' | 'wardrobe' | 'environment'
  | 'motion' | 'camera' | 'voice' | 'music' | 'timing'
  | 'structure' | 'style' | 'negative' | 'other';

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
```

## Validation gates
1. `order` must be unique and deterministic.
2. Video references requiring temporal fidelity must carry FPS.
3. Audio references requiring waveform/timing fidelity must carry sample rate.
4. `subjectId` and `role` are separate dimensions.
5. Backend adapters must declare which fields they consume, ignore or transform.
6. If a required field would be dropped, adapter returns WARN/REJECT instead of silently continuing.
7. Identity-critical references can require pre/post QA.

## Backend adapter examples
### LTX-2.5
Consumes image/video/audio references; adapter maps supported references into the LTX conditioning API. Multishot continuity remains model-native where available, while KAI continuity QA remains external.

### MiniMax H3
Order-sensitive multimodal conditioning. Adapter must preserve reference sequence, FPS and sample rate metadata.

### Wan2.2 Animate
Consumes subject image + driving video for character animation. Adapter maps `identity` and `motion` roles explicitly.

## Terminal state for this document
DRAFT_IMPLEMENTABLE. It is not RUNNING until TypeScript types, validators and adapter tests exist and pass.
