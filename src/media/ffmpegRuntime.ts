import {
  buildFrameExtractionArgs,
  buildProbeArgs,
  buildSceneDetectionArgs,
  parseFfprobeJson,
  parseSceneTimes,
  type MediaProbe,
} from './ffmpegMediaKernel';

export interface ProcessResult {
  code: number | null;
  stdout: string;
  stderr: string;
}

export type ProcessExecutor = (
  bin: string,
  args: string[],
) => Promise<ProcessResult>;

export interface FfmpegBinaries {
  ffmpeg: string;
  ffprobe?: string;
  nullSink: string;
}

export interface FrameExtractionResult {
  ok: boolean;
  error?: string;
  path: string;
}
export interface FfmpegRuntime {
  probe(filePath: string): Promise<MediaProbe>;
  detectScenes(filePath: string, startS: number, endS: number, threshold: number): Promise<number[]>;
  extractFrame(filePath: string, timeS: number, outPng: string): Promise<FrameExtractionResult>;
}

export function createFfmpegRuntime(
  binaries: FfmpegBinaries,
  execute: ProcessExecutor,
): FfmpegRuntime {
  return {
    async probe(filePath) {
      if (!binaries.ffprobe) throw new Error('FFPROBE_UNAVAILABLE');
      const result = await execute(binaries.ffprobe, buildProbeArgs(filePath));
      if (result.code !== 0) throw new Error(`FFPROBE_FAILED:${result.code}`);
      return parseFfprobeJson(result.stdout);
    },

    async detectScenes(filePath, startS, endS, threshold) {
      const args = buildSceneDetectionArgs(filePath, threshold, binaries.nullSink);
      const result = await execute(binaries.ffmpeg, args);
      return parseSceneTimes(result.stderr, startS, endS, 40);
    },
    async extractFrame(filePath, timeS, outPng) {
      const result = await execute(
        binaries.ffmpeg,
        buildFrameExtractionArgs(filePath, timeS, outPng),
      );
      if (result.code !== 0) {
        return {
          ok: false,
          error: result.stderr.slice(-400),
          path: outPng,
        };
      }
      return { ok: true, path: outPng };
    },
  };
}
