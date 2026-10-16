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

PIN = '5708f54bd5674d3c92ae96c52c85ea3bd0d42b5699eb12df10e5591945f178b7'


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
        row = rows[5]; root = row['staged_root']
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
        text = text.replace(anchor, '- Before local conversion, follow the [edition and slide export check](references/slides-export-check.md). Verify the compiled edition against the current source snapshot and establish the requested view without modifying the app.\n' + anchor)
        text, count = re.subn(r'- For a local app,[^\n]+', '- For a local app, use its verified compiled output, reviewed `src/data.json`, and the established requested presentation. For split-data output, preserve the full build bundle and check coherence before converting.', text)
        if count != 1:
            raise ValueError('Local route anchor is not unique')
        substitutions = [
            ('For native Google Slides, also confirm Google Drive presentation import or supported native image insertion.',
             'For native Google Slides, confirm the actual presentation import action required by the current canonical contract.'),
            ('If a required capability is unavailable, explain the blocker and retain any verified local PPTX; do not claim delivery to Google Slides.',
             'If a required capability is unavailable, follow the canonical destination contract: explain the blocker, retain verified local work privately, and ask about an alternative without claiming native delivery or silently substituting another destination.'),
            ("3. **Determine a starting style.** If a template or reference wasn't already provided, ask the user if they have a preference on what to base the slides layout and style on. If strong candidates exist in memory or user context, be helpful and suggest them (include a link). If none exist, use the `artifact-template-simple-light-mode` skill from the `openai-templates` plugin.",
             '3. **Determine a starting style.** Follow the current canonical Presentations template-selection policy and honor supplied visual direction. Resolve an actually available template before using it; do not silently depend on a historical named fallback.'),
            ('If import is blocked but native image insertion is supported, use the same PNGs with native slide text as described in the shared workflow. Read back image counts and inspect the rendered slides before returning the link; report an import failure separately from a successful native insertion.',
             "If native import is unavailable or fails, follow the current canonical Presentations destination contract and ask about an alternative; do not silently substitute a local file or native image insertion. Inspect the imported deck's slide count, text, tables, charts, images and layout before returning the link."),
        ]
        for before, after in substitutions:
            if text.count(before) != 1:
                raise ValueError('Canonical presentation instruction anchor is not unique')
            text = text.replace(before, after)
        payload[main] = text.encode()
        here = Path(__file__).parent
        payload['candidates/' + root + '/references/slides-export-check.md'] = inc._regular_bytes(here / 'slides-export-check.md', stop_file)
        helper = rows[4]['staged_root'] + '/scripts/verify-local-export.mjs'
        if helper not in manifest['files']:
            raise ValueError('Verified sibling coherence helper is absent')
        dependencies = sorted({e['path'] for e in rows[4]['provider_resource_files']} | {helper})
        common = [n for n in dependencies if '/skills/' not in n]
        for name in common:
            payload['provider_resources/' + name] = z.read(name)
        payload['RESOURCE_BINDINGS_007.json'] = inc.json_bytes({'format':'kai.skills.provider-bindings/1','bindings':[{'id':5,'files':dependencies}]})
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
    return {'format':'kai.skills.own-evolution/1','base_sha256':pin,'candidate_ids':[5],
            'common_files_resupplied_unchanged':len(common),'dependencies':len(dependencies),
            'files':{n:inc.record(d) for n,d in sorted(payload.items())},
            'reused_sibling_helper':helper,'provider_runtime_modified':False,'active_installation':False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-bundle',type=Path,required=True)
    p.add_argument('--base-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stop-file',type=Path)
    a=p.parse_args()
    print(json.dumps(evolve(a.base_bundle,a.base_sha256,a.output,a.stop_file),indent=2))
