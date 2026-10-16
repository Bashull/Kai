"""Adapt exact private context instructions in a new isolated candidate overlay."""
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

PIN = 'dd46e2acf43bf3fd0e7290ddee9ed4f4b97eea23c27a7f031af225a1c71c88e8'


def replace_line(text, prefix, replacement):
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError('Instruction anchor is not unique: ' + prefix)
    lines[matches[0]] = replacement + '\n'
    return ''.join(lines)


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
        row = rows[6]; root = row['staged_root']
        if row['namespace'] != 'data-analytics' or b.sha(z.read(root + '/SKILL.md')) != PIN:
            raise ValueError('Exact private skill baseline differs')
        for name in manifest['files']:
            if name.startswith(root + '/'):
                payload['candidates/' + name] = z.read(name)
        if len(payload) != 4:
            raise ValueError('Expected main and three complete references')
        main = 'candidates/' + root + '/SKILL.md'
        text = payload[main].decode()
        prefix = 'When: the user requests installation, packaging,'
        lines = text.splitlines()
        found = [s for s in lines if s.startswith(prefix)]
        if len(found) != 1:
            raise ValueError('Finalization routing anchor differs')
        text = replace_line(text, prefix, found[0] + ' Before choosing a plugin layout, read [context package formats](references/portable-context-manifests.md); preserve an approved Codex layout unless conversion was requested.')
        payload[main] = text.encode()
        guide = 'candidates/' + root + '/references/packaging-and-sharing.md'
        text = payload[guide].decode()
        anchor = '## Portable package shape\n'
        if text.count(anchor) != 1:
            raise ValueError('Package shape anchor differs')
        text = text.replace(anchor, anchor + '\nChoose the requested manifest contract using [context package formats](portable-context-manifests.md). Keep approved existing layouts; use root `plugin.json` for a new portable Agent Plugins package.\n')
        example = '  .codex-plugin/plugin.json\n'
        if text.count(example) != 1:
            raise ValueError('Directory example anchor differs')
        text = text.replace(example, '  plugin.json             # portable Agent Plugins manifest\n')
        blocks = list(re.finditer(r'```json\n(.*?)\n```', text, re.S))
        match = blocks[0]
        old = b.read_json(match.group(1).encode())
        if old.get('name') != 'context-acme-product-analytics' or old.get('skills') != './skills/':
            raise ValueError('Minimal Codex example differs')
        portable = {'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', **old}
        portable.pop('skills')
        text = text[:match.start()] + '```json\n' + json.dumps(portable, indent=2) + '\n```' + text[match.end():]
        replacements = [
            ('Use truthful creator and purpose metadata.', 'Use truthful creator and purpose metadata. Preserve the complete approved publisher and UI configuration, including author, developerName, category and capabilities; an audience is not a publisher. Locate UI settings according to the selected format: portable OpenAI settings belong under extensions["com.openai"], while a standalone Codex manifest retains its supported fields. Do not migrate or discard approved settings merely to match this example. A minimal new portable manifest can use:'),
            ('For a plugin with UI metadata, set', 'For a plugin with UI metadata, place defaultPrompt under extensions["com.openai"].interface in the portable manifest, or interface in a standalone Codex compatibility manifest. Include one usable starter per actual skill, up to three. For the minimal manifest above, use the skills\' agents/openai.yaml prompts. Keep each UI starter within 128 normalized characters and omit raw $skill-name invocation text. README and chat starters should be natural tasks within the saved applicability; do not call them behaviorally tested without an observed run.'),
            ('For a workspace-ready ZIP, place', 'For a workspace-ready portable ZIP, place plugin.json, skills/ and approved README/assets directly at the archive root. For an approved Codex-only package, retain .codex-plugin/plugin.json at that root instead. Preserve the named editable source folder outside the ZIP. Check integrity, size below 100 MB, exact approved bytes, the selected manifest contract, prompts and bundled references. Reject duplicate members, absolute/traversal paths, symlinks and escaped files.'),
        ]
        for prefix, replacement in replacements:
            text = replace_line(text, prefix, replacement)
        prefix = 'If the runtime exposes canonical plugin scaffolding,'
        old_line = next(s for s in text.splitlines() if s.startswith(prefix))
        text = replace_line(text, prefix, old_line + ' Determine whether the resolved scaffold emits portable or Codex compatibility files; a supported Codex scaffold is not a portable-format conversion. Do not rename its manifest without adapting its contract.')
        prefix = '2. Validate the whole plugin'
        old_line = next(s for s in text.splitlines() if s.startswith(prefix))
        text = replace_line(text, prefix, old_line + ' For portable output, check the declared schema and fixed skills/ discovery; do not place Codex-only fields at the portable root. Resolve the effective OpenAI settings without merging an inline object with its compatibility fallback. Preserve accepted Codex-only packages under their own contract.')
        payload[guide] = text.encode()
        here = Path(__file__).parent
        reference = inc._regular_bytes(here / 'portable-context-manifests.md', stop_file)
        payload['candidates/' + root + '/references/portable-context-manifests.md'] = reference
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
    return {'format':'kai.skills.own-evolution/1','base_sha256':pin,'candidate_ids':[6],
            'files':{n:inc.record(d) for n,d in sorted(payload.items())},
            'provider_runtime_modified':False,'active_installation':False,
            'existing_tooling_reused':['bundle_io','build_incremental'],
            'new_runtime_helper':False,'new_provider_resources':0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-bundle',type=Path,required=True)
    p.add_argument('--base-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stop-file',type=Path)
    a=p.parse_args()
    print(json.dumps(evolve(a.base_bundle,a.base_sha256,a.output,a.stop_file),indent=2))
