export type SpotSoundTask =
  | 'Temporal grounding (when?)'
  | 'Event detection (does it occur?)';

export const SPOTSOUND_BACKEND_LIMITS = Object.freeze({
  minAudioSeconds: 30,
  maxAudioSeconds: 600,
  minNewTokens: 16,
  maxNewTokens: 512,
});

export const SPOTSOUND_KAI_DEFAULTS = Object.freeze({
  maxAudioSeconds: 300,
  maxNewTokens: 128,
});

export interface SpotSoundRequest {
  audioPath: string;
  query: string;
  task: SpotSoundTask;
  maxAudioSeconds: number;
  maxNewTokens: number;
}

interface SpotSoundTransportArtifacts {
  predictedWindowsUri?: string;
  spottedAudioUri?: string;
}

export type SpotSoundTransportResult = SpotSoundTransportArtifacts &
  (
    | { modelAnswer: string; report?: string }
    | { report: string; modelAnswer?: string }
  );

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
  rawReport?: string;
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
    ...SPOTSOUND_KAI_DEFAULTS,
  };
}

const ABSENT_PATTERN = /\b(no|not present|does not occur|doesn't occur|absent)\b/i;
const INTERVAL_PATTERN = /[\[(]\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*[\])]/g;
const FROM_TO_PATTERN = /\bfrom\s+(-?\d+(?:\.\d+)?)\s*s?\s+to\s+(-?\d+(?:\.\d+)?)\s*s?\b/gi;
const REPORT_ANSWER_PATTERN = /^Answer:\s*(.*)$/m;

function extractModelAnswer(report: string): string {
  const match = REPORT_ANSWER_PATTERN.exec(report);
  return match ? match[1].trim() : report.trim();
}

function appendInterval(
  intervals: SpotSoundInterval[],
  startRaw: string,
  endRaw: string,
): void {
  const startSeconds = Number(startRaw);
  const endSeconds = Number(endRaw);
  if (
    Number.isFinite(startSeconds) &&
    Number.isFinite(endSeconds) &&
    startSeconds >= 0 &&
    endSeconds >= startSeconds
  ) {
    intervals.push({ startSeconds, endSeconds });
  }
}

export function normalizeSpotSoundAnswer(
  transport: SpotSoundTransportResult,
): SpotSoundResult {
  const rawAnswer = transport.modelAnswer ?? extractModelAnswer(transport.report);
  const answerForParsing = rawAnswer.trim();
  const reportFields = transport.report ? { rawReport: transport.report } : {};

  if (ABSENT_PATTERN.test(answerForParsing)) {
    return {
      present: false,
      intervals: [],
      rawAnswer,
      ...reportFields,
      predictedWindowsUri: transport.predictedWindowsUri,
      spottedAudioUri: transport.spottedAudioUri,
    };
  }

  const intervals: SpotSoundInterval[] = [];
  for (const match of answerForParsing.matchAll(INTERVAL_PATTERN)) {
    appendInterval(intervals, match[1], match[2]);
  }
  for (const match of answerForParsing.matchAll(FROM_TO_PATTERN)) {
    appendInterval(intervals, match[1], match[2]);
  }

  return {
    present: intervals.length > 0,
    intervals,
    rawAnswer,
    ...reportFields,
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
