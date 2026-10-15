// Own read-only coherence check. Provider implementations are supplied separately.
import { lstatSync, realpathSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

export async function verifyLocalExport({ projectDir, providerRoot = fileURLToPath(new URL('../../../', import.meta.url)) }) {
  if (!projectDir) throw new Error('Supply the existing project directory.');
  const root = realpathSync(projectDir);
  for (const [path, directory] of [[join(root, 'src'), true], [join(root, 'src/data.json'), false]]) {
    const info = lstatSync(path);
    if (info.isSymbolicLink() || (directory ? !info.isDirectory() : !info.isFile())) {
      throw new Error('The source snapshot must be a regular file inside the project.');
    }
  }
  const runtime = await import(pathToFileURL(join(resolve(providerRoot), 'scripts/data-app-separate.mjs')));
  let bundle;
  try { bundle = runtime.readSeparateDataBundle({ projectDir: root }); }
  catch { throw new Error('The split build is missing, invalid or changed. Conversion is blocked; this check never rebuilds the source.'); }
  const source = runtime.fingerprintDataFile(join(root, 'src/data.json'));
  if (source.sha256 !== bundle.manifest.snapshot.sha256 || source.bytes !== bundle.manifest.snapshot.bytes) {
    throw new Error('Current source snapshot differs from the compiled edition. Resolve the intended edition before conversion; do not rebuild implicitly.');
  }
  return {
    format: 'kai.skills.local-export-coherence/1', status: 'MATCHED_SPLIT_SNAPSHOT',
    snapshot: source, html: bundle.manifest.html, runtimeSha256: bundle.manifest.runtimeSha256,
    sourceModified: false, providerCodeExecuted: 'existing read-only split verifier only',
    presentationState: 'NOT_ESTABLISHED_BY_SNAPSHOT_CHECK',
    claimAccuracy: 'NOT_REVIEWED_BY_HELPER', browserRendering: 'NOT_CHECKED',
    documentConversion: 'NOT_RUN_BY_HELPER', concurrentMutationGuarantee: 'NONE; recheck immediately before export if files may change',
  };
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  try {
    const { values } = parseArgs({ options: { 'project-dir': { type: 'string' } }, allowPositionals: false });
    process.stdout.write(JSON.stringify(await verifyLocalExport({ projectDir: values['project-dir'] })) + '\n');
  } catch (error) {
    process.stderr.write(JSON.stringify({ status: 'BLOCKED', message: error.message, sourceModified: false }) + '\n');
    process.exitCode = 1;
  }
}
