import { describe, expect, it } from 'vitest';
import {
  buildSpotSoundRequest,
  normalizeSpotSoundAnswer,
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
});
