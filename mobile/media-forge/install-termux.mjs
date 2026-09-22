#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
if (process.platform !== 'android') throw new Error('TERMUX_ANDROID_REQUIRED');
const target = fileURLToPath(new URL('./kai-media.mjs', import.meta.url));
const bin = path.dirname(process.execPath);
const launcher = path.join(bin, 'kai-media');
const quote = (s) => "'" + s.replaceAll("'", "'\\''") + "'";
const content = '#!' + path.join(path.dirname(process.execPath), 'sh') +
  '\n# KAI Media Forge Termux launcher v0.1.0\nexec ' + quote(process.execPath) + ' ' + quote(target) + ' "$@"\n';
fs.mkdirSync(bin, { recursive: true });
if (fs.existsSync(launcher)) {
  if (fs.readFileSync(launcher, 'utf8') !== content) throw new Error('EXISTING_LAUNCHER_PRESERVED: ' + launcher);
} else {
  fs.writeFileSync(launcher, content, { flag: 'wx', mode: 0o700 });
}
console.log(JSON.stringify({ installed: launcher, target, onPath: (process.env.PATH || '').split(path.delimiter).includes(bin) }));
