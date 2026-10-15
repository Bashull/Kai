// Own output-contract checks; the separately supplied provider stays private.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

for (const key of ['FORGE_PROVIDER_ROOT', 'FORGE_REPORT_PROJECT']) {
  if (!process.env[key]) throw new Error(`Set ${key} to the already verified local input.`);
}
const root = resolve(process.env.FORGE_PROVIDER_ROOT);
const project = resolve(process.env.FORGE_REPORT_PROJECT);
const { readSeparateDataBundle, exportOfflineDataApp } = await import(pathToFileURL(join(root, 'scripts/data-app-separate.mjs')));
const { inspectDataAppDocument } = await import(pathToFileURL(join(root, 'skills/publish-artifact-to-sites/scripts/publication-assets.mjs')));
const reviewed = JSON.parse(readFileSync(join(project, 'src/data.json'), 'utf8'));

function temporary(t, copyDist = true) {
  const dir = mkdtempSync(join(tmpdir(), 'kai-report-delivery-'));
  t.after(() => rmSync(dir, { recursive: true }));
  if (copyDist) cpSync(join(project, 'dist'), join(dir, 'dist'), { recursive: true });
  return dir;
}

test('the complete split bundle contains the exact reviewed report snapshot', () => {
  const bundle = readSeparateDataBundle({ projectDir: project });
  assert.deepEqual(JSON.parse(readFileSync(bundle.snapshotPath, 'utf8')), reviewed);
  assert.ok(Object.keys(reviewed.queries).length > 0);
});

test('HTML alone is rejected as an incomplete split delivery', t => {
  const dir = temporary(t, false);
  cpSync(join(project, 'dist/index.html'), join(dir, 'index.html'));
  assert.throws(() => readSeparateDataBundle({ projectDir: dir }));
});

test('a missing sidecar is rejected and produces no offline export', async t => {
  const dir = temporary(t);
  const valid = readSeparateDataBundle({ projectDir: dir });
  rmSync(valid.snapshotPath);
  assert.throws(() => readSeparateDataBundle({ projectDir: dir }));
  await assert.rejects(exportOfflineDataApp({ projectDir: dir }));
  assert.ok(!existsSync(join(dir, '.data-app-offline/exports/data-app-offline.html')));
});

test('an altered sidecar is rejected and produces no offline export', async t => {
  const dir = temporary(t);
  const valid = readSeparateDataBundle({ projectDir: dir });
  const bytes = readFileSync(valid.snapshotPath); bytes[0] ^= 1;
  writeFileSync(valid.snapshotPath, bytes);
  assert.throws(() => readSeparateDataBundle({ projectDir: dir }));
  await assert.rejects(exportOfflineDataApp({ projectDir: dir }));
  assert.ok(!existsSync(join(dir, '.data-app-offline/exports/data-app-offline.html')));
});

test('the supported offline export embeds the entire reviewed snapshot', async t => {
  const dir = temporary(t);
  const output = await exportOfflineDataApp({ projectDir: dir });
  assert.equal(output.offline, true);
  const html = readFileSync(output.htmlPath, 'utf8');
  const parsed = inspectDataAppDocument(html);
  const fragments = [parsed.snapshotElement, ...parsed.snapshotContinuations];
  assert.ok(fragments.every(Boolean));
  const embedded = fragments.map(({ contentStart, contentEnd }) => html.slice(contentStart, contentEnd)).join('');
  assert.deepEqual(JSON.parse(embedded), reviewed);
  const names = parsed.metadata.flatMap(meta => meta.names);
  assert.ok(!names.includes('data-app-build-layout'));
  assert.ok(!names.includes('data-app-local-snapshot'));
  t.diagnostic('HTML parsing and byte checks only; no browser rendering, keyboard or accessibility acceptance.');
});

test('an explicit evidence cutoff stays the same across distinct host time zones', () => {
  const moduleUrl = pathToFileURL(join(root, 'templates/data-app/base/src/report-date.js')).href;
  const source = `import { reportDateMetadata } from ${JSON.stringify(moduleUrl)};
    const d = reportDateMetadata({asOf:'2026-09-30',generatedAt:'2026-10-16T00:10:00Z'});
    process.stdout.write(JSON.stringify({label:d.label,value:d.value,timeZone:d.timeZone,
      displayed:new Intl.DateTimeFormat('en-CA',{timeZone:d.timeZone,year:'numeric',month:'2-digit',day:'2-digit'}).format(d.date)}));`;
  const observations = ['Europe/Madrid', 'Pacific/Honolulu'].map(TZ => {
    const child = spawnSync(process.execPath, ['--input-type=module', '-e', source], { env: { ...process.env, TZ }, encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr);
    return JSON.parse(child.stdout);
  });
  assert.deepEqual(observations[0], observations[1]);
  assert.deepEqual(observations[0], { label: 'As of', value: '2026-09-30', timeZone: 'UTC', displayed: '2026-09-30' });
});
