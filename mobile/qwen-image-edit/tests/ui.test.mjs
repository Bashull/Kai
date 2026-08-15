import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const app = fs.existsSync(new URL('../app.mjs', import.meta.url))
  ? fs.readFileSync(new URL('../app.mjs', import.meta.url), 'utf8')
  : '';
const manifest = fs.existsSync(new URL('../manifest.webmanifest', import.meta.url))
  ? fs.readFileSync(new URL('../manifest.webmanifest', import.meta.url), 'utf8')
  : '';

for (const marker of [
  'webkitdirectory',
  'id="candidateA"',
  'id="candidateB"',
  '❤️ Elegir A',
  '❤️ Elegir B',
  '📌 A + ancla',
  '📌 B + ancla',
  '🔁 Reintentar',
]) assert.ok(html.includes(marker), `missing HTML marker: ${marker}`);

for (const marker of [
  'Bashull/Qwen-Image-Edit-2511-LoRAs-Fast',
  '/studio_pair',
  '/kai_edit_pair',
  '/kai_edit',
  '/studio_choose',
  'serverRecorded',
  'identityRefs',
  'showDirectoryPicker',
]) assert.ok(app.includes(marker), `missing app marker: ${marker}`);

assert.ok(manifest.includes('"display": "standalone"'));
console.log('ui contract OK');

const installer = fs.readFileSync(new URL('../install.sh', import.meta.url), 'utf8');
for (const asset of ['app.mjs', 'state.mjs', 'manifest.webmanifest', 'sw.js', 'icon.svg']) {
  assert.ok(installer.includes(asset), `installer missing ${asset}`);
}
console.log('installer contract OK');
