export type SpotSoundTask =
  | 'Temporal grounding (when?)'
  | 'Event detection (does it occur?)';

export interface SpotSoundRequest {
  audioPath: string;
  query: string;
  task: SpotSoundTask;
  maxAudioSeconds: number;
  maxNewTokens: number;
}

export interface SpotSoundTransportResult {
  modelAnswer: string;
  predictedWindowsUri?: string;
  spottedAudioUri?: string;
}

export interface SpotSoundTransport {
  spot(request: SpotSoundRequest): Promise<SpotSoundTransportResult>;
}

export interface SpotSoundInterval {
  startSeconds: number;
  endSeconds: number;
}

export interface SpotSoundResult {
  present: boolean;
  intervals: SpotSoundInterval[];
  rawAnswer: string;
  predictedWindowsUri?: string;
  spottedAudioUri?: string;
}

export function buildSpotSoundRequest(
  audioPath: string,
  query: string,
): SpotSoundRequest {
  return {
    audioPath,
    query,
    task: 'Temporal grounding (when?)',
    maxAudioSeconds: 300,
    maxNewTokens: 128,
  };
}

const ABSENT_PATTERN = /\b(no|not present|does not occur|doesn't occur|absent)\b/i;
const INTERVAL_PATTERN = /[\[(]\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*[\])]/g;

export function normalizeSpotSoundAnswer(
  transport: SpotSoundTransportResult,
): SpotSoundResult {
  const rawAnswer = transport.modelAnswer.trim();

  if (ABSENT_PATTERN.test(rawAnswer)) {
    return {
      present: false,
      intervals: [],
      rawAnswer: transport.modelAnswer,
      predictedWindowsUri: transport.predictedWindowsUri,
      spottedAudioUri: transport.spottedAudioUri,
    };
  }

  const intervals: SpotSoundInterval[] = [];
  for (const match of rawAnswer.matchAll(INTERVAL_PATTERN)) {
    const startSeconds = Number(match[1]);
    const endSeconds = Number(match[2]);
    if (
      Number.isFinite(startSeconds) &&
      Number.isFinite(endSeconds) &&
      startSeconds >= 0 &&
      endSeconds >= startSeconds
    ) {
      intervals.push({ startSeconds, endSeconds });
    }
  }

  return {
    present: intervals.length > 0,
    intervals,
    rawAnswer: transport.modelAnswer,
    predictedWindowsUri: transport.predictedWindowsUri,
    spottedAudioUri: transport.spottedAudioUri,
  };
}

export async function analyzeSpotSound(
  transport: SpotSoundTransport,
  audioPath: string,
  query: string,
): Promise<SpotSoundResult> {
  const request = buildSpotSoundRequest(audioPath, query);
  const response = await transport.spot(request);
  return normalizeSpotSoundAnswer(response);
}
