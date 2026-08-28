import { describe, expect, it } from 'vitest';
import { createFfmpegRuntime } from '../ffmpegRuntime';

describe('createFfmpegRuntime', () => {
  it('probes media through an injected executor', async () => {
    const calls: Array<[string, string[]]> = [];
    const runtime = createFfmpegRuntime(
      { ffmpeg: 'ffmpeg', ffprobe: 'ffprobe', nullSink: '/dev/null' },
      async (bin, args) => {
        calls.push([bin, args]);
        return {
          code: 0,
          stdout: JSON.stringify({
            streams: [{ codec_type: 'video', width: 640, height: 360, avg_frame_rate: '30/1' }],
            format: { duration: '3' },
          }),
          stderr: '',
        };
      },
    );
    expect(await runtime.probe('clip.mp4')).toEqual({
      width: 640, height: 360, durationMs: 3000, fps: 30,
    });
    expect(calls[0][0]).toBe('ffprobe');
    expect(calls[0][1].at(-1)).toBe('clip.mp4');
  });
});
  it('detects scenes through ffmpeg and parses absolute source times', async () => {
    const runtime = createFfmpegRuntime(
      { ffmpeg: 'ffmpeg', ffprobe: 'ffprobe', nullSink: '/dev/null' },
      async () => ({ code: 0, stdout: '', stderr: 'pts_time:1.5\npts_time:4.25' }),
    );
    expect(await runtime.detectScenes('clip.mp4', 1, 5, 0.2)).toEqual([1, 1.5, 4.25]);
  });

  it('reports frame extraction failure without throwing away stderr', async () => {
    const runtime = createFfmpegRuntime(
      { ffmpeg: 'ffmpeg', ffprobe: 'ffprobe', nullSink: '/dev/null' },
      async () => ({ code: 1, stdout: '', stderr: 'decoder exploded' }),
    );
    expect(await runtime.extractFrame('clip.mp4', 2, 'frame.png')).toEqual({
      ok: false,
      error: 'decoder exploded',
      path: 'frame.png',
    });
  });
