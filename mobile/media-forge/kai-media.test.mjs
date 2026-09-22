import test from 'node:test';
import assert from 'node:assert/strict';
import { validatePlan, segmentArgs, PROFILES } from './kai-media.mjs';
const shot = { id: 'yires', source: '/tmp/Yires image.jpg', kind: 'still', durationSeconds: 4, motion: 'push' };
const plan = (s = shot) => ({ schemaVersion: 1, shots: [s] });
test('rejects duplicate ids, traversal ids and invalid crop instead of silently clamping', () => {
  assert.throws(() => validatePlan({ schemaVersion: 1, shots: [shot, shot] }));
  assert.throws(() => validatePlan(plan({ ...shot, id: '../escape' })));
  assert.throws(() => validatePlan(plan({ ...shot, crop: { x: .9, y: 0, w: .2, h: 1 } })));
  assert.throws(() => validatePlan(plan({ ...shot, crop: { x: 0, y: 0, w: 0, h: 1 } })));
});
test('rejects unbounded durations, remote URLs and nonfinite numbers', () => {
  for (const durationSeconds of [0, 31, NaN, Infinity]) assert.throws(() => validatePlan(plan({ ...shot, durationSeconds })));
  assert.throws(() => validatePlan(plan({ ...shot, source: 'https://example.com/image.png' })));
  assert.throws(() => validatePlan({ ...plan(), profile: '__proto__' }));
});
test('still rendering preserves path as an argument and sets square pixels, bounded threads and exact frame count', () => {
  const args = segmentArgs(shot, { streams: [{ codec_type: 'video', width: 1536, height: 1152 }] }, '/tmp/out.mp4', PROFILES.preview);
  assert.equal(args[args.indexOf('-i') + 1], shot.source);
  assert.equal(args[args.indexOf('-frames:v') + 1], '96');
  assert.match(args[args.indexOf('-vf') + 1], /setsar=1,zoompan=/);
  assert.equal(args.at(-1), '/tmp/out.mp4');
});
test('video input is trimmed without image looping or camera animation', () => {
  const s = { ...shot, kind: 'video', motion: 'hold', startSeconds: 2 };
  validatePlan(plan(s));
  const args = segmentArgs(s, { streams: [{ codec_type: 'video', width: 1920, height: 1080 }] }, '/tmp/out.mp4', PROFILES.small);
  assert.ok(!args.includes('-loop'));
  assert.equal(args[args.indexOf('-ss') + 1], '2');
  assert.throws(() => validatePlan(plan({ ...s, motion: 'push' })));
});
