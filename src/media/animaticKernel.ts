export interface NormalizedCrop {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface AnimaticFrameInput {
  sourcePng: string;
  durationMs: number;
  label: string;
  crop: NormalizedCrop | null;
  sourceWidth: number;
  sourceHeight: number;
}

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const even = (value: number): number => Math.max(2, Math.round(value / 2) * 2);
const evenFloor = (value: number): number => Math.max(2, Math.floor(value / 2) * 2);

export function buildCropFilter(
  crop: NormalizedCrop | null,
  width: number,
  height: number,
): string | null {
  if (!crop) return null;
  if (crop.x === 0 && crop.y === 0 && crop.w === 1 && crop.h === 1) return null;
  const cx = clamp(even(crop.x * width), 0, Math.max(0, width - 2));
  const cy = clamp(even(crop.y * height), 0, Math.max(0, height - 2));
  const maxW = evenFloor(Math.max(2, width - cx));
  const maxH = evenFloor(Math.max(2, height - cy));
  const cw = clamp(even(crop.w * width), 2, maxW);
  const ch = clamp(even(crop.h * height), 2, maxH);
  return `crop=${cw}:${ch}:${cx}:${cy}`;
}

export function buildAnimaticSegmentArgs(
  frame: AnimaticFrameInput,
  outSegment: string,
  width = 1920,
  height = 1080,
  fps = 24,
): string[] {
  const durationS = clamp(frame.durationMs / 1000, 0.25, 30);
  const filters: string[] = [];
  const crop = buildCropFilter(frame.crop, frame.sourceWidth, frame.sourceHeight);
  if (crop) filters.push(crop);
  filters.push(`scale=${width}:${height}:force_original_aspect_ratio=decrease`);
  filters.push(`pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=black`);
  return [
    '-y', '-loop', '1', '-i', frame.sourcePng,
    '-t', durationS.toFixed(3), '-vf', filters.join(','),
    '-r', String(fps), '-pix_fmt', 'yuv420p', '-c:v', 'libx264', outSegment,
  ];
}
export function buildAnimaticConcatArgs(
  listPath: string,
  videoPath: string,
  audioPath?: string | null,
): string[] {
  const args = ['-y', '-f', 'concat', '-safe', '0', '-i', listPath];
  if (audioPath) {
    args.push(
      '-i', audioPath,
      '-map', '0:v', '-map', '1:a',
      '-c:v', 'copy', '-c:a', 'aac', '-shortest',
    );
  } else {
    args.push('-c', 'copy');
  }
  args.push(videoPath);
  return args;
}
