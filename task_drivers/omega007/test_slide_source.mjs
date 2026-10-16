import assert from 'node:assert/strict';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
if (!process.env.FORGE_COHERENCE_HELPER) throw new Error('Supply the verified bound helper path.');
const { verifyLocalExport } = await import(pathToFileURL(resolve(process.env.FORGE_COHERENCE_HELPER)));

if (!process.env.FORGE_PROVIDER_ROOT || !process.env.FORGE_REPORT_PROJECT) throw new Error('Supply verified provider and frozen report paths.');
const providerRoot = resolve(process.env.FORGE_PROVIDER_ROOT), source = resolve(process.env.FORGE_REPORT_PROJECT);
const { readSeparateDataBundle } = await import(pathToFileURL(join(providerRoot, 'scripts/data-app-separate.mjs')));
function copied(t) {
  const root = mkdtempSync(join(tmpdir(), 'kai-slide-export-'));
  t.after(() => rmSync(root, { recursive: true }));
  cpSync(join(source, 'dist'), join(root, 'dist'), { recursive: true });
  mkdirSync(join(root, 'src')); cpSync(join(source, 'src/data.json'), join(root, 'src/data.json'));
  return root;
}
function hashes(root) {
  const result = {};
  for (const entry of readdirSync(root, { withFileTypes: true, recursive: true })) {
    if (entry.isFile()) {
      const path = join(entry.parentPath, entry.name);
      result[path.slice(root.length)] = createHash('sha256').update(readFileSync(path)).digest('hex');
    }
  }
  return result;
}
const check = projectDir => verifyLocalExport({ projectDir, providerRoot });

test('an actual matching split report is accepted without changing any source bytes', async t => {
  const root = copied(t), before = hashes(root);
  const result = await check(root);
  assert.equal(result.status, 'MATCHED_SPLIT_SNAPSHOT');
  assert.equal(result.presentationState, 'NOT_ESTABLISHED_BY_SNAPSHOT_CHECK');
  assert.deepEqual(hashes(root), before);
});
test('a newer source with an older valid build is blocked without implicit rebuild', async t => {
  const root = copied(t), path = join(root, 'src/data.json');
  const data = JSON.parse(readFileSync(path)); data.title += ' changed source'; writeFileSync(path, JSON.stringify(data));
  assert.doesNotThrow(() => readSeparateDataBundle({ projectDir: root }));
  const before = hashes(root);
  await assert.rejects(check(root), /differs from the compiled edition/);
  assert.deepEqual(hashes(root), before);
  t.diagnostic('Existing split verifier validates dist; this additional check covers source/build concordance. No whole provider defect is inferred.');
});
test('an altered compiled sidecar blocks conversion without repair', async t => {
  const root = copied(t), bundle = readSeparateDataBundle({ projectDir: root });
  writeFileSync(bundle.snapshotPath, 'altered'); const before = hashes(root);
  await assert.rejects(check(root), /split build/); assert.deepEqual(hashes(root), before);
});
test('a missing sidecar blocks conversion without recreating files', async t => {
  const root = copied(t), bundle = readSeparateDataBundle({ projectDir: root });
  rmSync(bundle.snapshotPath); const before = hashes(root);
  await assert.rejects(check(root), /split build/); assert.deepEqual(hashes(root), before);
});
test('HTML alone does not become a verified split delivery', async t => {
  const root = copied(t); rmSync(join(root, 'dist/data-app-build.json'));
  await assert.rejects(check(root), /split build/);
  assert.ok(!existsSync(join(root, 'dist/data-app-build.json')));
});
test('a linked source snapshot is refused', async t => {
  const root = copied(t), path = join(root, 'src/data.json');
  rmSync(path); symlinkSync(join(source, 'src/data.json'), path);
  await assert.rejects(check(root), /regular file/);
});
test('byte-different JSON serialization is conservatively blocked without semantic-equivalence claims', async t => {
  const root = copied(t), path = join(root, 'src/data.json');
  writeFileSync(path, readFileSync(path, 'utf8') + '\n ');
  await assert.rejects(check(root), /differs from the compiled edition/);
});
