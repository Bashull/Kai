// Own offline integration harness. Provider source is supplied separately and never vendored here.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

if (!process.env.FORGE_PROVIDER_ROOT) throw new Error('Set FORGE_PROVIDER_ROOT to an already verified support pack.');
const root = resolve(process.env.FORGE_PROVIDER_ROOT);
const prep = await import(pathToFileURL(join(root, 'scripts/prepare-data-app.mjs')));
const runtime = await import(pathToFileURL(join(root, 'scripts/data-app-runtime.mjs')));

function temporary(t) {
  const dir = mkdtempSync(join(tmpdir(), 'kai-dashboard-portability-'));
  t.after(() => rmSync(dir, { recursive: true }));
  return dir;
}
function snapshot(dir, value = { title: 'Synthetic integration evidence', status: 'fixture',
  queries: { supplied: { rows: [{ marker: 'own-reviewed-input', value: 42 }],
    source: { label: 'Own synthetic fixture; no business observations' } } } }) {
  const file = join(dir, 'reviewed.json');
  writeFileSync(file, JSON.stringify(value));
  return file;
}

test('captured prebuilt runtime verifies its own release artifacts without dependency installation', async () => {
  const manifest = await runtime.readPrebuiltManifest(root);
  assert.ok(Object.keys(manifest.artifacts).length > 0);
  const compiler = await runtime.loadPrebuiltCompiler({ pluginRoot: root, manifest });
  assert.equal(typeof compiler.transform, 'function');
});

test('all approved dashboard references retain supplied evidence and generate fresh identities', async t => {
  const dir = temporary(t), input = snapshot(dir);
  const original = readFileSync(input);
  const entries = prep.readCatalog().examples.filter(e => e.status === 'golden' && (e.kind ?? 'dashboard') === 'dashboard');
  assert.ok(entries.length > 0);
  const ids = new Set();
  for (const entry of entries) {
    const output = join(dir, entry.id);
    const result = await prep.prepareDataApp({ output, fromReference: entry.id, snapshot: input });
    const data = JSON.parse(readFileSync(join(output, 'src/data.json')));
    assert.deepEqual(data.queries, JSON.parse(original).queries);
    assert.equal(data.status, 'fixture');
    assert.equal(result.built, false);
    assert.equal(data.surface, 'dashboard');
    assert.ok(!ids.has(data.id)); ids.add(data.id);
    assert.ok(existsSync(join(output, 'AGENTS.md')));
    assert.ok(existsSync(result.documentation.entryPoint));
    assert.ok(!existsSync(join(output, 'node_modules')));
  }
  assert.deepEqual(readFileSync(input), original);
  t.diagnostic(`approved reference preparations: ${entries.length}; this is one integration test, not ${entries.length} whole dashboards verified`);
});

test('invalid snapshots and missing reference snapshots fail before creating output', async t => {
  const dir = temporary(t);
  const output = join(dir, 'must-not-exist');
  await assert.rejects(prep.prepareDataApp({ output, snapshot: snapshot(dir, []) }), /queries/);
  assert.ok(!existsSync(output));
  const entry = prep.readCatalog().examples.find(e => e.status === 'golden' && (e.kind ?? 'dashboard') === 'dashboard');
  await assert.rejects(prep.prepareDataApp({ output, fromReference: entry.id }), /requires/);
  assert.ok(!existsSync(output));
});

test('existing projects and their witness file are not overwritten', async t => {
  const dir = temporary(t), witness = join(dir, 'witness.txt');
  writeFileSync(witness, 'keep user work');
  await assert.rejects(prep.prepareDataApp({ output: dir }), /exists/);
  assert.equal(readFileSync(witness, 'utf8'), 'keep user work');
});

test('absolute helper paths work from an unrelated cwd and reference preparation is read-only', async t => {
  const dir = temporary(t), project = join(dir, 'app'), input = snapshot(dir);
  const create = spawnSync(process.execPath, [join(root, 'scripts/prepare-data-app.mjs'),
    '--surface', 'dashboard', '--snapshot', input, '--output', project], { cwd: dir, encoding: 'utf8' });
  assert.equal(create.status, 0, create.stderr);
  const before = readFileSync(join(project, 'src/data.json'));
  const lookup = spawnSync(process.execPath, [join(root, 'scripts/data-app.mjs'),
    'prepare', '--project-dir', project], { cwd: dir, encoding: 'utf8' });
  assert.equal(lookup.status, 0, lookup.stderr);
  const result = JSON.parse(lookup.stdout);
  assert.equal(result.documentation.source, 'installed-plugin');
  assert.deepEqual(readFileSync(join(project, 'src/data.json')), before);
  assert.ok(!existsSync(join(project, 'node_modules')));
  assert.ok(!existsSync(join(project, 'dist')));
});

test('a corrupted support-pack artifact is rejected before compiler evaluation', async t => {
  const dir = temporary(t), copy = join(dir, 'provider');
  cpSync(root, copy, { recursive: true });
  const manifest = JSON.parse(readFileSync(join(copy, 'assets/data-app-runtime/manifest.json')));
  const path = join(copy, 'assets/data-app-runtime', manifest.artifacts.compiler.path);
  const bytes = readFileSync(path); bytes[0] ^= 1; writeFileSync(path, bytes);
  await assert.rejects(runtime.readPrebuiltManifest(copy));
});

test('the actual captured Node compatibility gate rejects unsupported majors and minor boundaries', () => {
  for (const version of ['18.20.0', '20.18.9', '21.9.0', '22.11.9']) {
    assert.throws(() => runtime.assertSupportedDataNode(version));
  }
  for (const version of ['20.19.0', '22.12.0', '24.19.0']) {
    assert.doesNotThrow(() => runtime.assertSupportedDataNode(version));
  }
});
