export interface MediaProbe {
  width: number;
  height: number;
  durationMs?: number;
  fps?: number;
}

export type SamplingMode =
  | { kind: 'interval'; everyS: number }
  | { kind: 'count'; n: number };

function parseRational(value: unknown): number | undefined {
  if (typeof value !== 'string') return undefined;
  const [a, b] = value.split('/').map(Number);
  if (!Number.isFinite(a)) return undefined;
  if (!b) return a || undefined;
  const result = a! / b;
  return Number.isFinite(result) ? result : undefined;
}

export function parseFfprobeJson(text: string): MediaProbe {
  const data = JSON.parse(text) as any;
  const video = (data.streams ?? []).find((stream: any) => stream.codec_type === 'video');
  if (!video) return { width: 0, height: 0 };
  const durationS = Number(data.format?.duration) || Number(video.duration) || undefined;
  const fps = parseRational(video.avg_frame_rate) ?? parseRational(video.r_frame_rate);
  return {
    width: Number(video.width) || 0,
    height: Number(video.height) || 0,
    durationMs: durationS && Number.isFinite(durationS) ? Math.round(durationS * 1000) : undefined,
    fps,
  };
}
export function planRangeSampling(
  startS: number,
  endS: number,
  mode: SamplingMode,
): number[] {
  const start = Math.max(0, startS);
  const end = Math.max(start, endS);
  const span = end - start;
  if (mode.kind === 'interval') {
    const step = Math.max(0.05, mode.everyS);
    const times: number[] = [];
    for (let t = start; t <= end + 1e-6 && times.length < 300; t += step) {
      times.push(Number(t.toFixed(6)));
    }
    return times;
  }
  const n = Math.max(1, Math.floor(mode.n));
  if (n === 1) return [start + span / 2];
  return Array.from({ length: n }, (_, i) => start + (span * i) / (n - 1));
}

export function parseSceneTimes(
  stderr: string,
  startS: number,
  endS: number,
  cap = 40,
): number[] {
  const times: number[] = [];
  const re = /pts_time:([\d.]+)/g;
  let match: RegExpExecArray | null;
  const windowed = endS > startS;
  while ((match = re.exec(stderr)) !== null && times.length < cap) {
    const t = Number(match[1]);
    if (!Number.isFinite(t)) continue;
    if (windowed && (t < startS - 1e-3 || t > endS + 1e-3)) continue;
    times.push(t);
  }
  if (times.length === 0 || times[0]! - startS > 0.25) {
    times.unshift(startS);
  }
  return times.slice(0, cap);
}

export function buildProbeArgs(filePath: string): string[] {
  return ['-v', 'quiet', '-print_format', 'json', '-show_streams', '-show_format', filePath];
}

export function buildFrameExtractionArgs(
  mediaPath: string,
  timeS: number,
  outPng: string,
): string[] {
  return [
    '-y', '-ss', String(Math.max(0, timeS)), '-i', mediaPath,
    '-frames:v', '1', outPng,
  ];
}

export function buildSceneDetectionArgs(
  mediaPath: string,
  threshold: number,
  nullSink: string,
): string[] {
  const clamped = Math.min(0.99, Math.max(0.01, threshold));
  return [
    '-i', mediaPath,
    '-vf', `select='gt(scene\\,${clamped})',showinfo`,
    '-vsync', 'vfr', '-f', 'null', nullSink,
  ];
}
