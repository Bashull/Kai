"""Evolve two exact private inputs using own additions; no provider text vendored.

Reads a pinned verified ZIP, creates a new lab overlay, and preserves input bytes.
No provider execution, installation, dependency fetch, or canonical promotion.
"""
import argparse
import io
import json
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import build_incremental as inc
import bundle_io as b

PINS = {2: '1bd897886c71dcefcdedfdb76f1714edbe73cb47e3de3f087f736d6e04aaa489',
        3: 'a464dc6bcda8bf5659ba951a9ccba52020cf9c5d6f5f40e05d0e6a42149b51cf'}
SHARED = 'providers/data-analytics/shared/forge-portable-authoring.md'
PORTABLE = ('- For a portable or selectively staged copy, follow the '
            '[portable authoring check](../../shared/forge-portable-authoring.md) '
            'before preparation. Keep its provider-relative resources and verify '
            'the requested runtime path; a copied policy does not establish closure.\n')
CLAIMS = ('Keep a concise [claim and refresh check](references/claim-evidence.md) '
          'for consequential titles, findings, comparisons, and recommendations. '
          'Reconcile affected claims with the current reviewed rows and source scopes '
          'when revising; do not equate a rebuild or preparation timestamp with '
          'new evidence.\n')
BUILD = ('Keep the shared runtime and stable app identity. Follow the copied build '
         'guide for the output format. A build with `--separate-data` needs the '
         'complete `dist` directory: HTML, the content-addressed JSON sidecar, and '
         'the build manifest. Use the documented offline export when the user '
         'requests a standalone HTML file. Preserve the protected shell infrastructure.')


def evolve(base_bundle, pin, output, stop_file=None):
    b._check_stop(stop_file)
    output = Path(output).expanduser().absolute()
    for part in (output, *output.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Output ancestors must not be links')
    if output.exists() or any(p.lower() in {'.codex', '.agents', '.claude'} for p in output.parts):
        raise ValueError('Output must be a new isolated lab')
    raw = inc._regular_bytes(base_bundle, stop_file)
    if not isinstance(pin, str) or not b.DIGEST_RE.fullmatch(pin) or b.sha(raw) != pin:
        raise ValueError('Pinned base SHA-256 mismatch')
    source_root = Path(__file__).parent
    own_shared = inc._regular_bytes(source_root / 'forge-portable-authoring.md', stop_file)
    own_claims = inc._regular_bytes(source_root / 'claim-evidence.md', stop_file)
    payload = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as source:
        manifest = b._verify_open_zip(source, stop_file)
        rows = b._catalog_by_id(source, manifest)
        roots = {}
        for skill_id, expected in PINS.items():
            row = rows[skill_id]
            root = row['staged_root']; roots[skill_id] = root
            if row['namespace'] != 'data-analytics' or b.sha(source.read(root + '/SKILL.md')) != expected:
                raise ValueError('Expected exact private skill input does not match')
            for name in manifest['files']:
                if name.startswith(root + '/'):
                    payload['candidates/' + name] = source.read(name)
        old_ref = 'candidates/' + roots[2] + '/references/portable-runtime.md'
        if old_ref not in payload:
            raise ValueError('Prior portable reference is absent')
        old_ref_sha = b.sha(payload.pop(old_ref))
        main = 'candidates/' + roots[2] + '/SKILL.md'
        text = payload[main].decode()
        old_link = '(references/portable-runtime.md)'
        if text.count(old_link) != 1:
            raise ValueError('Dashboard portable link is not unique')
        payload[main] = text.replace(old_link, '(../../shared/forge-portable-authoring.md)').encode()
        main = 'candidates/' + roots[3] + '/SKILL.md'
        text = payload[main].decode()
        if text.count('\n## Dependencies\n') != 1 or text.count('\n## 1. Understand') != 1:
            raise ValueError('Report insertion anchors are not unique')
        text = text.replace('\n## Dependencies\n', PORTABLE + '\n## Dependencies\n')
        text = text.replace('\n## 1. Understand', '\n' + CLAIMS + '\n## 1. Understand')
        text, replacements = re.subn(r'Keep one shared runtime[^\n]+', BUILD, text)
        if replacements != 1:
            raise ValueError('Report build-format anchor is not unique')
        payload[main] = text.encode()
        payload['candidates/' + roots[3] + '/references/claim-evidence.md'] = own_claims
        common = [e['path'] for e in rows[2]['provider_resource_files'] if '/skills/' not in e['path']]
        dependencies = sorted({e['path'] for e in rows[2]['provider_resource_files']} | {SHARED})
        for name in common:
            payload['provider_resources/' + name] = source.read(name)
        payload['provider_resources/' + SHARED] = own_shared
        bindings = {'format': 'kai.skills.provider-bindings/1',
                    'bindings': [{'id': i, 'files': dependencies} for i in [2, 3]]}
        payload['RESOURCE_BINDINGS_005.json'] = inc.json_bytes(bindings)
        for skill_id in PINS:
            root = 'candidates/' + roots[skill_id]
            inc._candidate_header(payload[root + '/SKILL.md'], rows[skill_id]['name'])
    for name, data in payload.items():
        inc._secret_preflight(name, data)
    b._validate_paths(list(payload))
    b._check_stop(stop_file)
    output.mkdir(parents=True, exist_ok=False)
    created_files, created_dirs = [], [output]
    try:
        for name, data in sorted(payload.items()):
            b._check_stop(stop_file)
            b._write_new_file(output / name, data, output, created_files, created_dirs)
    except BaseException as exc:
        failures = b._rollback_new_stage(created_files, created_dirs)
        if failures:
            raise RuntimeError('Incomplete cleanup; foreign data preserved') from exc
        raise
    return {'format': 'kai.skills.own-evolution/1', 'base_sha256': pin,
            'candidate_ids': [2, 3], 'old_portable_reference_sha256': old_ref_sha,
            'shared_reference': SHARED, 'common_files_resupplied_unchanged': len(common),
            'own_common_files_added': 1, 'dependencies_per_skill': len(dependencies),
            'files': {name: inc.record(data) for name, data in sorted(payload.items())},
            'active_installation': False, 'functional_verification': 'NOT_RUN_BY_GENERATOR'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-bundle', type=Path, required=True)
    p.add_argument('--base-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stop-file', type=Path)
    a = p.parse_args()
    print(json.dumps(evolve(a.base_bundle, a.base_sha256, a.output, a.stop_file), indent=2))
