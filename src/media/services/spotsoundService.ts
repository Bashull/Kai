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

export interface SpotSoundRequestAdjustment {
  field: 'maxAudioSeconds' | 'maxNewTokens';
  from: number;
  to: number;
}

export interface ConstrainedSpotSoundRequest {
  request: SpotSoundRequest;
  adjustments: SpotSoundRequestAdjustment[];
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

export interface SpotSoundPresenceGateResult extends SpotSoundResult {
  detectionAnswer: string;
  groundingAttempted: boolean;
}

function assertFiniteRequestControl(
  field: 'maxAudioSeconds' | 'maxNewTokens',
  value: number,
): void {
  if (!Number.isFinite(value)) {
    throw new RangeError(`${field} must be finite`);
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function constrainSpotSoundRequest(
  request: SpotSoundRequest,
): ConstrainedSpotSoundRequest {
  assertFiniteRequestControl('maxAudioSeconds', request.maxAudioSeconds);
  assertFiniteRequestControl('maxNewTokens', request.maxNewTokens);

  const constrainedAudioSeconds = clamp(
    request.maxAudioSeconds,
    SPOTSOUND_BACKEND_LIMITS.minAudioSeconds,
    SPOTSOUND_BACKEND_LIMITS.maxAudioSeconds,
  );
  const constrainedNewTokens = clamp(
    request.maxNewTokens,
    SPOTSOUND_BACKEND_LIMITS.minNewTokens,
    SPOTSOUND_BACKEND_LIMITS.maxNewTokens,
  );

  const adjustments: SpotSoundRequestAdjustment[] = [];
  if (constrainedAudioSeconds !== request.maxAudioSeconds) {
    adjustments.push({ field: 'maxAudioSeconds', from: request.maxAudioSeconds, to: constrainedAudioSeconds });
  }
  if (constrainedNewTokens !== request.maxNewTokens) {
    adjustments.push({ field: 'maxNewTokens', from: request.maxNewTokens, to: constrainedNewTokens });
  }

  return {
    request: { ...request, maxAudioSeconds: constrainedAudioSeconds, maxNewTokens: constrainedNewTokens },
    adjustments,
  };
}

export function buildSpotSoundRequest(
  audioPath: string,
  query: string,
  task: SpotSoundTask = 'Temporal grounding (when?)',
): SpotSoundRequest {
  return { audioPath, query, task, ...SPOTSOUND_KAI_DEFAULTS };
}

const ABSENT_PATTERN = /\b(no|not present|does not occur|doesn't occur|absent)\b/i;
const INTERVAL_PATTERN = /[\[(]\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*[\])]/g;
const FROM_TO_PATTERN = /\bfrom\s+(-?\d+(?:\.\d+)?)\s*s?\s+to\s+(-?\d+(?:\.\d+)?)\s*s?\b/gi;
const REPORT_ANSWER_PATTERN = /^Answer:\s*(.*)$/m;

function extractModelAnswer(report: string): string {
  const match = REPORT_ANSWER_PATTERN.exec(report);
  return match ? match[1].trim() : report.trim();
}

function answerFromTransport(transport: SpotSoundTransportResult): string {
  return transport.modelAnswer ?? extractModelAnswer(transport.report);
}

function appendInterval(intervals: SpotSoundInterval[], startRaw: string, endRaw: string): void {
  const startSeconds = Number(startRaw);
  const endSeconds = Number(endRaw);
  if (Number.isFinite(startSeconds) && Number.isFinite(endSeconds) && startSeconds >= 0 && endSeconds >= startSeconds) {
    intervals.push({ startSeconds, endSeconds });
  }
}

export function normalizeSpotSoundAnswer(transport: SpotSoundTransportResult): SpotSoundResult {
  const rawAnswer = answerFromTransport(transport);
  const answerForParsing = rawAnswer.trim();
  const reportFields = transport.report ? { rawReport: transport.report } : {};

  if (ABSENT_PATTERN.test(answerForParsing)) {
    return { present: false, intervals: [], rawAnswer, ...reportFields, predictedWindowsUri: transport.predictedWindowsUri, spottedAudioUri: transport.spottedAudioUri };
  }

  const intervals: SpotSoundInterval[] = [];
  for (const match of answerForParsing.matchAll(INTERVAL_PATTERN)) appendInterval(intervals, match[1], match[2]);
  for (const match of answerForParsing.matchAll(FROM_TO_PATTERN)) appendInterval(intervals, match[1], match[2]);

  return { present: intervals.length > 0, intervals, rawAnswer, ...reportFields, predictedWindowsUri: transport.predictedWindowsUri, spottedAudioUri: transport.spottedAudioUri };
}

export async function analyzeSpotSound(
  transport: SpotSoundTransport,
  audioPath: string,
  query: string,
): Promise<SpotSoundResult> {
  const response = await transport.spot(buildSpotSoundRequest(audioPath, query));
  return normalizeSpotSoundAnswer(response);
}

export async function analyzeSpotSoundWithPresenceGate(
  transport: SpotSoundTransport,
  audioPath: string,
  query: string,
): Promise<SpotSoundPresenceGateResult> {
  const detection = await transport.spot(
    buildSpotSoundRequest(audioPath, query, 'Event detection (does it occur?)'),
  );
  const detectionAnswer = answerFromTransport(detection).trim();

  if (ABSENT_PATTERN.test(detectionAnswer)) {
    return {
      present: false,
      intervals: [],
      rawAnswer: detectionAnswer,
      rawReport: detection.report,
      predictedWindowsUri: detection.predictedWindowsUri,
      spottedAudioUri: detection.spottedAudioUri,
      detectionAnswer,
      groundingAttempted: false,
    };
  }

  const grounding = await transport.spot(buildSpotSoundRequest(audioPath, query));
  return {
    ...normalizeSpotSoundAnswer(grounding),
    detectionAnswer,
    groundingAttempted: true,
  };
}
