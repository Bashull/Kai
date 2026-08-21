import { describe, expect, it } from 'vitest';
import {
  analyzeSpotSound,
  buildSpotSoundRequest,
  normalizeSpotSoundAnswer,
  type SpotSoundTransport,
  type SpotSoundTransportResult,
} from '../services/spotsoundService';

describe('SpotSound service contract', () => {
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
