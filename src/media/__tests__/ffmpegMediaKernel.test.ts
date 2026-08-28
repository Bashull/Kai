import { describe, expect, it } from 'vitest';
import {
  parseFfprobeJson,
  planRangeSampling,
  parseSceneTimes,
} from '../ffmpegMediaKernel';

describe('parseFfprobeJson', () => {
  it('extracts video geometry, duration and rational fps', () => {
    const result = parseFfprobeJson(JSON.stringify({
      streams: [{ codec_type: 'video', width: 1920, height: 1080, avg_frame_rate: '24000/1001' }],
      format: { duration: '12.5' },
    }));
    expect(result.width).toBe(1920);
    expect(result.height).toBe(1080);
    expect(result.durationMs).toBe(12500);
    expect(result.fps).toBeCloseTo(23.976, 3);
  });
});

describe('planRangeSampling', () => {
  it('plans deterministic evenly spaced count samples', () => {
    expect(planRangeSampling(2, 8, { kind: 'count', n: 4 })).toEqual([2, 4, 6, 8]);
  });
});
describe('parseSceneTimes', () => {
  it('keeps scene cuts in range and prepends the requested start', () => {
    const stderr = [
      'showinfo pts_time:1.000',
      'showinfo pts_time:3.250',
      'showinfo pts_time:6.000',
    ].join('\n');
    expect(parseSceneTimes(stderr, 2, 5, 40)).toEqual([2, 3.25]);
  });
});

import {
  buildFrameExtractionArgs,
  buildProbeArgs,
  buildSceneDetectionArgs,
} from '../ffmpegMediaKernel';

describe('ffmpeg argv planning', () => {
  it('builds probe args without shell interpolation', () => {
    expect(buildProbeArgs('/tmp/a weird name.mp4')).toContain('/tmp/a weird name.mp4');
  });

  it('clamps frame seek time to zero', () => {
    expect(buildFrameExtractionArgs('in.mp4', -4, 'out.png').slice(0, 4)).toEqual([
      '-y', '-ss', '0', '-i',
    ]);
  });

  it('clamps scene threshold and keeps a platform null sink explicit', () => {
    const args = buildSceneDetectionArgs('in.mp4', 4, 'NUL');
    expect(args.join(' ')).toContain('0.99');
    expect(args.at(-1)).toBe('NUL');
  });
});
