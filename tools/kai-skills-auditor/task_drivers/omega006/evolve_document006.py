"""Apply own additions to an exact private baseline in a new isolated overlay."""
import argparse
import io
import json
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bundle_io as b
import build_incremental as inc

PIN = '71a4616d6e111c4e8e570b0c986ad62631fb39aff26ba08837961eedff4fe2a2'


def evolve(base, pin, output, stop_file=None):
    b._check_stop(stop_file)
    output = Path(output).absolute()
    if output.exists() or any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in [output, *output.parents]):
        raise ValueError('Output must be a new isolated directory without links')
    if any(p.lower() in {'.codex', '.claude', '.agents'} for p in output.parts):
        raise ValueError('Active installation paths are not allowed')
    raw = inc._regular_bytes(base, stop_file)
    if not isinstance(pin, str) or not b.DIGEST_RE.fullmatch(pin) or b.sha(raw) != pin:
        raise ValueError('Base SHA mismatch')
    payload = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        manifest = b._verify_open_zip(z, stop_file)
        rows = b._catalog_by_id(z, manifest)
        row = rows[4]; root = row['staged_root']
        if row['namespace'] != 'data-analytics' or b.sha(z.read(root + '/SKILL.md')) != PIN:
            raise ValueError('Exact private skill baseline differs')
        for name in manifest['files']:
            if name.startswith(root + '/'):
                payload['candidates/' + name] = z.read(name)
        main = 'candidates/' + root + '/SKILL.md'
        text = payload[main].decode()
        anchor = '\n## Dependencies\n'
        if text.count(anchor) != 1:
            raise ValueError('Instruction anchor is not unique')
        text = text.replace(anchor, '- Before local conversion, follow the [edition and document export check](references/document-export-check.md). Verify the compiled edition against the current source snapshot and establish the requested view without modifying the app.\n' + anchor)
        text, count = re.subn(r'- For a local app,[^\n]+', '- For a local app, use its verified compiled output, reviewed `src/data.json`, and the established requested presentation. For split-data output, preserve the full build bundle and check coherence before converting.', text)
        if count != 1:
            raise ValueError('Local route anchor is not unique')
        text, count = re.subn(r'If import is blocked but native image insertion is supported,[^.]+\.', 'Follow the current canonical Documents import contract; use a native insertion fallback only when that contract and the task explicitly permit it. Retain the verified DOCX and report native delivery as blocked when those conditions are absent.', text)
        if count != 1:
            raise ValueError('Native delivery anchor is not unique')
        payload[main] = text.encode()
        here = Path(__file__).parent
        for name, destination in [('document-export-check.md', 'references/document-export-check.md'), ('verify-local-export.mjs', 'scripts/verify-local-export.mjs')]:
            payload['candidates/' + root + '/' + destination] = inc._regular_bytes(here / name, stop_file)
        dependencies = sorted(e['path'] for e in rows[3]['provider_resource_files'])
        common = [n for n in dependencies if '/skills/' not in n]
        for name in common:
            payload['provider_resources/' + name] = z.read(name)
        payload['RESOURCE_BINDINGS_006.json'] = inc.json_bytes({'format':'kai.skills.provider-bindings/1','bindings':[{'id':4,'files':dependencies}]})
        inc._candidate_header(payload[main], row['name'])
    b._validate_paths(list(payload))
    for name, data in payload.items():
        inc._secret_preflight(name, data)
    output.mkdir(parents=True)
    created_files, created_dirs = [], [output]
    try:
        for name, data in sorted(payload.items()):
            b._check_stop(stop_file)
            b._write_new_file(output / name, data, output, created_files, created_dirs)
    except BaseException as error:
        if b._rollback_new_stage(created_files, created_dirs):
            raise RuntimeError('Incomplete cleanup; foreign data retained') from error
        raise
    return {'format':'kai.skills.own-evolution/1','base_sha256':pin,'candidate_ids':[4],
            'common_files_resupplied_unchanged':len(common),'dependencies':len(dependencies),
            'files':{n:inc.record(d) for n,d in sorted(payload.items())},
            'provider_runtime_modified':False,'active_installation':False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-bundle',type=Path,required=True)
    p.add_argument('--base-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stop-file',type=Path)
    a=p.parse_args()
    print(json.dumps(evolve(a.base_bundle,a.base_sha256,a.output,a.stop_file),indent=2))
