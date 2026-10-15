"""Verify a governed archive and optionally copy selected IDs into a NEW lab.

This module never executes bundled code or installs into active skill paths.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError('Duplicate JSON key: ' + key)
        out[key] = value
    return out


def read_json(data):
    return json.loads(data, object_pairs_hook=unique_object)


def safe_path(name):
    p = PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or ':' in name
            or any(ord(c) < 32 for c in name) or any(x in ('', '.', '..') for x in name.split('/'))
            or p.as_posix() != name):
        raise ValueError('Unsafe archive path: ' + repr(name))
    return p


def verify_bundle(path):
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [x.filename for x in infos]
        if len(infos) > 25000 or sum(x.file_size for x in infos) > 512 * 1024 * 1024:
            raise ValueError('Archive exceeds documented inspection limits')
        if len(set(x.casefold() for x in names)) != len(names):
            raise ValueError('Duplicate or case-colliding archive paths')
        for x in infos:
            safe_path(x.filename)
            if x.is_dir() or stat.S_ISLNK(x.external_attr >> 16):
                raise ValueError('Only regular archive members are allowed')
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failure')
        manifest = read_json(z.read('MANIFEST_SHA256.json'))
        if manifest.get('format') != 'kai.skills.bundle/1':
            raise ValueError('Unsupported manifest format')
        files = manifest['files']
        if set(files) != set(names) - {'MANIFEST_SHA256.json'}:
            raise ValueError('Manifest does not cover every payload file exactly')
        for name, info in files.items():
            data = z.read(name)
            if info['bytes'] != len(data) or info['sha256'] != sha(data):
                raise ValueError('Manifest mismatch: ' + name)
        return manifest


def stage_selected(path, ids, target, apply=False):
    manifest = verify_bundle(path)
    target = Path(target).expanduser().resolve()
    if any(x.lower() in ('.agents', '.claude', '.codex') for x in target.parts):
        raise ValueError('Use a new isolated lab, never an active skills directory')
    if target.exists():
        raise ValueError('Target must not exist; existing work is never overwritten')
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise ValueError('Select at least one explicit skill ID')
    with zipfile.ZipFile(path) as z:
        catalog = read_json(z.read('catalog/INDEX_847_RECONCILED.json'))
        by_id = {r['id']: r for r in catalog}
        if any(i not in by_id for i in ids):
            raise ValueError('Unknown skill ID')
        selected = [by_id[i] for i in ids]
        names = [r['name'] for r in selected]
        if len(set(names)) != len(names):
            raise ValueError('Selected skills have conflicting names; test separate provider scopes')
        plan = []
        for r in selected:
            if r['aux_missing']:
                raise ValueError(f'Skill {r["id"]} still has missing declared resources')
            prefix = r['staged_root'] + '/'
            plan += [(n, r['name'] + '/' + n[len(prefix):]) for n in manifest['files'] if n.startswith(prefix)]
        if apply:
            target.mkdir(parents=True, exist_ok=False)
            for source, relative in plan:
                dest = target / safe_path(relative)
                if not dest.resolve().is_relative_to(target):
                    raise ValueError('Target escape')
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as out:
                    out.write(z.read(source))
        return {'mode': 'ISOLATED_STAGE' if apply else 'DRY_RUN', 'ids': ids,
                'files': len(plan), 'target': str(target), 'executed_bundled_code': False,
                'functional_validation': 'NOT_RUN', 'active_installation': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--id', type=int, action='append', default=[])
    p.add_argument('--target', type=Path)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    if args.target:
        result = stage_selected(args.bundle, args.id, args.target, args.apply)
    else:
        if args.apply or args.id:
            p.error('--apply/--id require --target')
        m = verify_bundle(args.bundle)
        result = {'status': 'PASS', 'hashed_payload_files': len(m['files']),
                  'skills': m['skills'], 'aux_recovered': m['aux_recovered'],
                  'aux_missing': m['aux_missing'], 'functional_validation': 'NOT_RUN'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
