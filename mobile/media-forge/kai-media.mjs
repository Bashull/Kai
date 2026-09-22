#!/usr/bin/env node
// Termux front end for KAI Media Forge Omega. No provider calls or credentials.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildAnimaticSegmentArgs, buildAnimaticConcatArgs } from '../../src/media/animaticKernel.ts';

export const VERSION = '0.1.0';
export const PROFILES = Object.freeze({
  preview: { width: 1280, height: 720, fps: 24, threads: 2, preset: 'veryfast', crf: 23 },
  small: { width: 640, height: 360, fps: 24, threads: 2, preset: 'veryfast', crf: 25 },
  master: { width: 1920, height: 1080, fps: 24, threads: 2, preset: 'veryfast', crf: 20 },
});
const root = process.env.KAI_MEDIA_STATE_DIR || path.join(os.homedir(), '.local/share/kai/media-forge');
const kernel = fileURLToPath(new URL('../../src/media/animaticKernel.ts', import.meta.url));
const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const ensure = (ok, reason) => { if (!ok) throw new Error(reason); };
const emit = (value) => console.log(JSON.stringify(value));
const exists = (p) => fs.existsSync(p);
const hashFile = (p) => {
  const h = crypto.createHash('sha256'), fd = fs.openSync(p, 'r'), buf = Buffer.alloc(1024 * 1024);
  try { let n; while ((n = fs.readSync(fd, buf)) > 0) h.update(buf.subarray(0, n)); }
  finally { fs.closeSync(fd); }
  return h.digest('hex');
};
function writeJson(p, value) {
  const tmp = p + '.tmp-' + process.pid;
  fs.writeFileSync(tmp, JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
  fs.renameSync(tmp, p);
}
export function run(bin, args, timeout = 120000) {
  const r = spawnSync(bin, args, { encoding: 'utf8', timeout, killSignal: 'SIGKILL',
    maxBuffer: 2 * 1024 * 1024, windowsHide: true, shell: false });
  if (r.error || r.status !== 0)
    throw new Error(bin + ': ' + (r.error?.code || r.status) + ' ' + (r.stderr || '').slice(-1500));
  return r.stdout;
}
export function probe(source) {
  ensure(path.isAbsolute(source) && fs.statSync(source).isFile(), 'SOURCE_MUST_BE_LOCAL_FILE');
  return JSON.parse(run('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', source], 15000));
}
function finite(n, lo, hi, name) {
  ensure(typeof n === 'number' && Number.isFinite(n) && n >= lo && n <= hi, 'INVALID_' + name);
}
export function validatePlan(p) {
  ensure(p?.schemaVersion === 1 && Array.isArray(p.shots) && p.shots.length > 0 && p.shots.length <= 500, 'INVALID_PLAN');
  ensure(Object.hasOwn(PROFILES, p.profile || 'preview'), 'INVALID_PROFILE');
  const ids = new Set();
  for (const s of p.shots) {
    ensure(typeof s.id === 'string' && /^[a-zA-Z0-9_-]{1,64}$/.test(s.id) && !ids.has(s.id), 'INVALID_OR_DUPLICATE_SHOT_ID');
    ids.add(s.id);
    ensure(typeof s.source === 'string' && path.isAbsolute(s.source) && !s.source.includes('\0'), 'INVALID_SOURCE_PATH');
    ensure(s.kind === 'still' || s.kind === 'video', 'INVALID_SHOT_KIND');
    finite(s.durationSeconds, 0.25, 30, 'DURATION');
    finite(s.startSeconds ?? 0, 0, 86400, 'START');
    ensure(['hold', 'push'].includes(s.motion || 'hold'), 'INVALID_MOTION');
    ensure(s.kind === 'still' || (s.motion || 'hold') === 'hold', 'VIDEO_MOTION_NOT_SUPPORTED');
    if (s.crop != null) {
      for (const k of ['x', 'y', 'w', 'h']) finite(s.crop[k], 0, 1, 'CROP_' + k);
      ensure(s.crop.w > 0 && s.crop.h > 0 && s.crop.x + s.crop.w <= 1.000001 && s.crop.y + s.crop.h <= 1.000001, 'CROP_OUTSIDE_SOURCE');
    }
  }
  if (p.audio) {
    ensure(typeof p.audio.source === 'string' && path.isAbsolute(p.audio.source), 'INVALID_AUDIO_SOURCE');
    finite(p.audio.startSeconds ?? 0, 0, 86400, 'AUDIO_START');
  }
  return p;
}
export function segmentArgs(s, info, out, profile) {
  const v = info.streams.find((x) => x.codec_type === 'video');
  ensure(v?.width > 0 && v.height > 0, 'VIDEO_STREAM_REQUIRED');
  const frames = Math.round(s.durationSeconds * profile.fps);
  const args = buildAnimaticSegmentArgs({ sourcePng: s.source, durationMs: frames / profile.fps * 1000,
    label: s.id, crop: s.crop || null, sourceWidth: v.width, sourceHeight: v.height },
    out, profile.width, profile.height, profile.fps);
  if (s.kind === 'video') {
    args.splice(args.indexOf('-loop'), 2);
    args.splice(args.indexOf('-i'), 0, '-ss', String(s.startSeconds || 0));
  }
  const fi = args.indexOf('-vf') + 1;
  args[fi] += ',setsar=1';
  if (s.motion === 'push') {
    args[fi] += ",zoompan=z='1+0.035*min(on/" + Math.max(1, frames - 1) +
      ",1)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:fps=" + profile.fps +
      ':s=' + profile.width + 'x' + profile.height;
  }
  args.splice(1, 0, '-hide_banner', '-loglevel', 'error', '-nostdin', '-filter_threads', '1', '-threads', '2');
  args.splice(-1, 0, '-an', '-frames:v', String(frames), '-preset', profile.preset, '-crf',
    String(profile.crf), '-threads', String(profile.threads), '-movflags', '+faststart');
  return args;
}
function verifyClip(p, profile, duration) {
  const data = probe(p), v = data.streams.find((s) => s.codec_type === 'video');
  ensure(v && v.codec_name === 'h264' && v.width === profile.width && v.height === profile.height, 'OUTPUT_FORMAT_MISMATCH');
  const [a, b] = String(v.avg_frame_rate).split('/').map(Number);
  ensure(Math.abs(a / (b || 1) - profile.fps) < 0.01, 'OUTPUT_FPS_MISMATCH');
  ensure(Math.abs(Number(data.format.duration) - duration) <= 0.15, 'OUTPUT_DURATION_MISMATCH');
  run('ffmpeg', ['-v', 'error', '-nostdin', '-threads', '2', '-i', p, '-f', 'null', '-'], Math.max(30000, duration * 3000));
  return { bytes: fs.statSync(p).size, sha256: hashFile(p), duration: Number(data.format.duration) };
}
export function doctor(benchmark = false) {
  const report = { version: VERSION, platform: process.platform, arch: process.arch, node: process.version,
    memoryAvailableMiB: Math.round(os.freemem() / 1048576), stateDirectory: root,
    timestamp: new Date().toISOString(), generation: 'NO_LOCAL_AI_MODEL_INSTALLED_BY_THIS_TOOL' };
  try { const v = fs.statfsSync(os.homedir()); report.freeGiB = +(v.bavail * v.bsize / 1073741824).toFixed(2); } catch {}
  try {
    report.ffmpeg = run('ffmpeg', ['-version'], 10000).split('\n')[0];
    const enc = run('ffmpeg', ['-hide_banner', '-encoders'], 10000);
    report.encodersAdvertised = ['libx264', 'h264_mediacodec'].filter((x) => enc.includes(x));
    const filters = run('ffmpeg', ['-hide_banner', '-filters'], 10000);
    report.filters = ['scale', 'pad', 'zoompan', 'concat', 'loudnorm'].filter((x) => new RegExp('\\b' + x + '\\b').test(filters));
    report.ready = report.encodersAdvertised.includes('libx264') && report.filters.length === 5;
  } catch (e) { report.ready = false; report.error = e.message; }
  if (benchmark && report.ready) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-media-bench-'));
    report.benchmarks = [];
    try {
      for (const encoder of report.encodersAdvertised) {
        const out = path.join(dir, encoder + '.mp4'), t = Date.now();
        try {
          const args = ['-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=24',
            '-frames:v', '24', '-an', '-c:v', encoder, '-threads', '2'];
          if (encoder === 'libx264') args.push('-preset', 'veryfast');
          else args.push('-b:v', '1000k');
          args.push('-pix_fmt', 'yuv420p', '-y', out);
          run('ffmpeg', args, 15000);
          const result = verifyClip(out, { width: 320, height: 180, fps: 24 }, 1);
          report.benchmarks.push({ encoder, ok: true, elapsedMs: Date.now() - t, ...result });
        } catch (e) { report.benchmarks.push({ encoder, ok: false, elapsedMs: Date.now() - t, error: e.message }); }
      }
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
  return report;
}
export function render(planFile, output) {
  const plan = validatePlan(readJson(planFile)), profile = PROFILES[plan.profile || 'preview'];
  ensure(path.isAbsolute(output) && path.extname(output).toLowerCase() === '.mp4', 'ABSOLUTE_MP4_OUTPUT_REQUIRED');
  ensure(fs.existsSync(path.dirname(output)), 'OUTPUT_DIRECTORY_MISSING');
  const records = plan.shots.map((s) => {
    ensure(path.resolve(s.source) !== path.resolve(output), 'OUTPUT_EQUALS_SOURCE');
    const info = probe(s.source), duration = Number(info.format?.duration);
    if (s.kind === 'video') ensure(duration >= (s.startSeconds || 0) + s.durationSeconds - 0.05, 'VIDEO_TOO_SHORT:' + s.id);
    return { shot: s, info, sha256: hashFile(s.source) };
  });
  const total = plan.shots.reduce((n, s) => n + Math.round(s.durationSeconds * profile.fps) / profile.fps, 0);
  let audioHash = null;
  if (plan.audio) {
    const audioInfo = probe(plan.audio.source);
    ensure(audioInfo.streams.some((s) => s.codec_type === 'audio'), 'AUDIO_STREAM_REQUIRED');
    ensure(Number(audioInfo.format.duration) >= (plan.audio.startSeconds || 0) + total - 0.05, 'AUDIO_TOO_SHORT');
    ensure(path.resolve(plan.audio.source) !== path.resolve(output), 'OUTPUT_EQUALS_SOURCE');
    audioHash = hashFile(plan.audio.source);
  }
  const key = sha(JSON.stringify({ version: VERSION, implementation: hashFile(fileURLToPath(import.meta.url)), kernel: hashFile(kernel), plan, profile,
    inputs: records.map((r) => r.sha256), audioHash, ffmpeg: run('ffmpeg', ['-version']).split('\n')[0] })).slice(0,24);
  const job = path.join(root, 'jobs', key);
  fs.mkdirSync(job, { recursive: true, mode: 0o700 });
  const receipt = output + '.kai.json';
  if (exists(output)) {
    if (exists(receipt)) {
      const previous = readJson(receipt);
      if (previous.job === key && previous.output?.sha256 === hashFile(output)) return { ...previous, reused: true };
    }
    throw new Error('OUTPUT_EXISTS_PRESERVED: ' + output);
  }
  const lock = path.join(job, 'render.lock');
  let fd;
  try { fd = fs.openSync(lock, 'wx', 0o600); fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, started: new Date().toISOString() })); }
  catch { throw new Error('JOB_LOCKED: ' + lock + ' (see runbook; do not remove a live render lock)'); }
  const started = Date.now();
  try {
    const cached = [];
    for (let i = 0; i < records.length; i++) {
      const r = records[i], segment = path.join(job, String(i).padStart(4,'0') + '.mp4'), meta = segment + '.json';
      const duration = Math.round(r.shot.durationSeconds * profile.fps) / profile.fps;
      if (exists(segment) && exists(meta) && readJson(meta).sha256 === hashFile(segment)) {
        cached.push(r.shot.id); emit({ event: 'segment_cached', shot: r.shot.id }); continue;
      }
      emit({ event: 'rendering', shot: r.shot.id, index: i + 1, total: records.length });
      run('ffmpeg', segmentArgs(r.shot, r.info, segment, profile), Math.max(120000, duration * 15000));
      const verified = verifyClip(segment, profile, duration);
      ensure(hashFile(r.shot.source) === r.sha256, 'SOURCE_CHANGED_DURING_RENDER');
      writeJson(meta, verified);
    }
    // Fixed basenames + safe concat avoid interpretation of untrusted asset paths.
    const list = path.join(job, 'concat.txt');
    fs.writeFileSync(list, records.map((_, i) => "file '" + String(i).padStart(4,'0') + ".mp4'").join('\n') + '\n');
    const staged = path.join(job, 'assembled.mp4');
    const args = buildAnimaticConcatArgs(list, staged, plan.audio?.source);
    args[args.indexOf('-safe') + 1] = '1';
    if (plan.audio) {
      const secondInput = args.indexOf('-i', args.indexOf('-i') + 1);
      args.splice(secondInput, 0, '-ss', String(plan.audio.startSeconds || 0));
    }
    args.splice(1, 0, '-hide_banner', '-loglevel', 'error', '-nostdin');
    args.splice(-1, 0, '-t', String(total), '-movflags', '+faststart');
    run('ffmpeg', args, Math.max(120000, total * 3000));
    const verified = verifyClip(staged, profile, total);
    if (plan.audio) {
      ensure(hashFile(plan.audio.source) === audioHash, 'AUDIO_CHANGED_DURING_RENDER');
      ensure(probe(staged).streams.some((s) => s.codec_type === 'audio'), 'OUTPUT_AUDIO_MISSING');
    }
    for (const r of records) ensure(hashFile(r.shot.source) === r.sha256, 'SOURCE_CHANGED_DURING_RENDER');
    fs.copyFileSync(staged, output, fs.constants.COPYFILE_EXCL);
    const result = { version: VERSION, status: 'RENDER_VERIFIED', job: key, type: 'ANIMATIC_NOT_GENERATIVE_VIDEO',
      timestamp: new Date().toISOString(), elapsedSeconds: (Date.now() - started) / 1000,
      profile, shots: records.map((r) => ({ id: r.shot.id, source: r.shot.source, sha256: r.sha256 })),
      audioHash, cachedSegments: cached, output: { path: output, ...verified } };
    writeJson(receipt, result);
    writeJson(path.join(job, 'receipt.json'), result);
    return result;
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    fs.rmSync(lock, { force: true });
  }
}
function main(args) {
  const [cmd, a, b] = args;
  if (cmd === 'doctor') return emit(doctor(a === '--benchmark'));
  if (cmd === 'probe') return emit(probe(path.resolve(a)));
  if (cmd === 'render' && a && b) return emit(render(path.resolve(a), path.resolve(b)));
  if (cmd === 'validate' && a) return emit({ valid: !!validatePlan(readJson(a)) });
  console.log('KAI Media Forge / Termux ' + VERSION + '\n' +
    'kai-media doctor [--benchmark]\n' +
    'kai-media probe /ruta/video.mp4\n' +
    'kai-media validate plan.json\n' +
    'kai-media render plan.json /ruta/salida.mp4\n' +
    'Reutiliza Animatic Kernel. Planes locales; sin servicios de pago ni claves.');
}
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(process.argv.slice(2)); } catch (e) { console.error(e.message); process.exitCode = 1; }
}
