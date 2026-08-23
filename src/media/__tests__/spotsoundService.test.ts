import { describe, expect, it } from 'vitest';
import {
  analyzeSpotSound,
  buildSpotSoundRequest,
  constrainSpotSoundRequest,
  normalizeSpotSoundAnswer,
  SPOTSOUND_BACKEND_LIMITS,
  SPOTSOUND_KAI_DEFAULTS,
  type SpotSoundTransport,
  type SpotSoundTransportResult,
} from '../services/spotsoundService';

describe('SpotSound service contract', () => {
  it('keeps verified backend limits separate from KAI request defaults', () => {
    expect(SPOTSOUND_BACKEND_LIMITS).toEqual({
      minAudioSeconds: 30,
      maxAudioSeconds: 600,
      minNewTokens: 16,
      maxNewTokens: 512,
    });
    expect(SPOTSOUND_KAI_DEFAULTS).toEqual({
      maxAudioSeconds: 300,
      maxNewTokens: 128,
    });
  });

  it('clamps out-of-range request controls and reports every adjustment', () => {
    const result = constrainSpotSoundRequest({
      audioPath: '/tmp/audio.wav',
      query: 'door slam',
      task: 'Temporal grounding (when?)',
      maxAudioSeconds: 999,
      maxNewTokens: 4,
    });

    expect(result).toEqual({
      request: {
        audioPath: '/tmp/audio.wav',
        query: 'door slam',
        task: 'Temporal grounding (when?)',
        maxAudioSeconds: 600,
        maxNewTokens: 16,
      },
      adjustments: [
        { field: 'maxAudioSeconds', from: 999, to: 600 },
        { field: 'maxNewTokens', from: 4, to: 16 },
      ],
    });
  });

  it('builds the verified /spot payload without losing task semantics', () => {
    expect(buildSpotSoundRequest('/tmp/audio.wav', 'dog barking')).toEqual({
      audioPath: '/tmp/audio.wav',
      query: 'dog barking',
      task: 'Temporal grounding (when?)',
      maxAudioSeconds: 300,
      maxNewTokens: 128,
    });
  });

  it('normalizes a present temporal window from the model answer', () => {
    const transport: SpotSoundTransportResult = {
      modelAnswer: '[[11.2, 20.3]]',
      predictedWindowsUri: 'file:///tmp/windows.png',
      spottedAudioUri: 'file:///tmp/spotted.wav',
    };

    expect(normalizeSpotSoundAnswer(transport)).toMatchObject({
      present: true,
      intervals: [{ startSeconds: 11.2, endSeconds: 20.3 }],
    });
  });

  it('normalizes the interval dialect used by SpotSound training, including multiple windows', () => {
    const transport: SpotSoundTransportResult = {
      modelAnswer: 'from 8.10s to 10.90s, from 21.25s to 22.00s',
    };

    expect(normalizeSpotSoundAnswer(transport)).toMatchObject({
      present: true,
      intervals: [
        { startSeconds: 8.1, endSeconds: 10.9 },
        { startSeconds: 21.25, endSeconds: 22 },
      ],
    });
  });

  it('extracts the model answer from the live Space report without losing the report', () => {
    const report =
      'Answer: from 8.010s to 11.010s\n' +
      'Windows: [8.01s → 11.01s]\n' +
      'Audio: 57.0s  ·  inference: 1.3s';
    const transport: SpotSoundTransportResult = { report };

    expect(normalizeSpotSoundAnswer(transport)).toMatchObject({
      present: true,
      intervals: [{ startSeconds: 8.01, endSeconds: 11.01 }],
      rawAnswer: 'from 8.010s to 11.010s',
      rawReport: report,
    });
  });

  it('does not invent timestamps when the answer says the event is absent', () => {
    const transport: SpotSoundTransportResult = {
      modelAnswer: 'No, the queried event does not occur in the audio.',
    };

    expect(normalizeSpotSoundAnswer(transport)).toEqual({
      present: false,
      intervals: [],
      rawAnswer: transport.modelAnswer,
      predictedWindowsUri: undefined,
      spottedAudioUri: undefined,
    });
  });

  it('runs analysis through an injected transport and preserves the verified request', async () => {
    const seen = [] as unknown[];
    const transport: SpotSoundTransport = {
      async spot(request) {
        seen.push(request);
        return { modelAnswer: '[(1.5, 2.75)]' };
      },
    };

    const result = await analyzeSpotSound(transport, '/tmp/audio.wav', 'door slam');

    expect(seen).toEqual([buildSpotSoundRequest('/tmp/audio.wav', 'door slam')]);
    expect(result).toMatchObject({
      present: true,
      intervals: [{ startSeconds: 1.5, endSeconds: 2.75 }],
    });
  });
});
