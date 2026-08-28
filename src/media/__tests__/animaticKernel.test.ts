import { describe, expect, it } from 'vitest';
import {
  buildAnimaticConcatArgs,
  buildAnimaticSegmentArgs,
  buildCropFilter,
} from '../animaticKernel';

describe('buildCropFilter', () => {
  it('converts normalized crop to bounded even pixel geometry', () => {
    expect(buildCropFilter({ x: 0.1, y: 0.2, w: 0.5, h: 0.5 }, 1920, 1080))
      .toBe('crop=960:540:192:216');
  });
});

describe('buildAnimaticSegmentArgs', () => {
  it('clamps hold duration and produces deterministic h264 framing', () => {
    const args = buildAnimaticSegmentArgs({
      sourcePng: 'frame.png', durationMs: 10, label: '', crop: null,
      sourceWidth: 1920, sourceHeight: 1080,
    }, 'seg.mp4');
    expect(args).toContain('0.250');
    expect(args).toContain('24');
    expect(args).toContain('yuv420p');
  });
});
describe('buildAnimaticConcatArgs', () => {
  it('muxes optional scratch audio with shortest semantics', () => {
    expect(buildAnimaticConcatArgs('list.txt', 'out.mp4', 'scratch.wav')).toEqual([
      '-y', '-f', 'concat', '-safe', '0', '-i', 'list.txt',
      '-i', 'scratch.wav', '-map', '0:v', '-map', '1:a',
      '-c:v', 'copy', '-c:a', 'aac', '-shortest', 'out.mp4',
    ]);
  });
});
