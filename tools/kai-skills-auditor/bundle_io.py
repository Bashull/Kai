"""Verify a governed archive and optionally copy selected IDs into a NEW lab.

This module never executes bundled code or installs into active skill paths.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import zipfile

NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
DIGEST_RE = re.compile(r'^[0-9a-f]{64}$')
CATALOG_PATH = 'catalog/INDEX_847_RECONCILED.json'
RECEIPT_NAME = 'STAGE_RECEIPT.json'


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
    if not isinstance(name, str):
        raise ValueError('Archive paths must be strings')
    p = PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or ':' in name
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>"|?*' for c in name)
            or any(x in ('', '.', '..') for x in name.split('/'))
            or p.as_posix() != name):
        raise ValueError('Unsafe archive path: ' + repr(name))
    for part in p.parts:
        device = part.split('.')[0].upper()
        if (part != part.rstrip(' .') or device in {'CON', 'PRN', 'AUX', 'NUL'}
                or re.fullmatch(r'(?:COM|LPT)[1-9¹²³]', device)):
            raise ValueError('Nonportable archive path: ' + repr(name))
    return p


def _path_key(name):
    return unicodedata.normalize('NFC', name).casefold()


def _validate_paths(names):
    files = set()
    for name in names:
        safe_path(name)
        key = _path_key(name)
        if key in files:
            raise ValueError('Duplicate or case/normalization-colliding paths')
        files.add(key)
    for name in names:
        if any(_path_key(str(parent)) in files for parent in PurePosixPath(name).parents):
            raise ValueError('File/directory path collision: ' + name)


def _check_stop(stop_file):
    # Treat dangling symlinks as STOP too; no contents or credentials are read.
    if stop_file is not None:
        flag = Path(stop_file).expanduser()
        if flag.exists() or flag.is_symlink():
            raise RuntimeError('STOP requested; no further staging writes are allowed')


def _check_record(name, record, data):
    if (not isinstance(record, dict) or type(record.get('bytes')) is not int
            or record['bytes'] < 0 or not isinstance(record.get('sha256'), str)
            or not DIGEST_RE.fullmatch(record['sha256'])):
        raise ValueError('Invalid file manifest record: ' + name)
    if record['bytes'] != len(data) or record['sha256'] != sha(data):
        raise ValueError('Manifest mismatch: ' + name)


def _verify_open_zip(z, stop_file=None):
    """Validate the handle the caller will use; never reopen its pathname."""
    _check_stop(stop_file)
    infos = z.infolist()
    names = [x.filename for x in infos]
    if len(infos) > 25000 or sum(x.file_size for x in infos) > 512 * 1024 * 1024:
        raise ValueError('Archive exceeds documented inspection limits')
    _validate_paths(names)
    for x in infos:
        kind = stat.S_IFMT(x.external_attr >> 16)
        if x.is_dir() or kind not in (0, stat.S_IFREG):
            raise ValueError('Only regular archive members are allowed')
    # ZipFile.read checks each member CRC, avoiding a redundant testzip pass.
    manifest = read_json(z.read('MANIFEST_SHA256.json'))
    if not isinstance(manifest, dict) or manifest.get('format') != 'kai.skills.bundle/1':
        raise ValueError('Unsupported manifest format')
    files = manifest.get('files')
    if not isinstance(files, dict) or set(files) != set(names) - {'MANIFEST_SHA256.json'}:
        raise ValueError('Manifest does not cover every payload file exactly')
    for name, record in files.items():
        _check_stop(stop_file)
        _check_record(name, record, z.read(name))
    return manifest


def verify_bundle(path, stop_file=None):
    """Check payload integrity/paths; stage_selected also validates catalog semantics."""
    _check_stop(stop_file)
    with zipfile.ZipFile(path) as z:
        return _verify_open_zip(z, stop_file)


def _catalog_by_id(z, manifest):
    if CATALOG_PATH not in manifest['files']:
        raise ValueError('Governed catalog is required for selective staging')
    data = z.read(CATALOG_PATH)
    _check_record(CATALOG_PATH, manifest['files'][CATALOG_PATH], data)
    catalog = read_json(data)
    if (not isinstance(catalog, list) or type(manifest.get('skills')) is not int
            or manifest['skills'] < 1 or len(catalog) != manifest['skills']):
        raise ValueError('Catalog length does not match the manifest skills count')
    by_id = {}
    roots = set()
    known_skill_roots = {r.get('staged_root') for r in catalog if isinstance(r, dict)
                         and isinstance(r.get('staged_root'), str)}
    auxiliary_roots = manifest.get('auxiliary_source_roots', [])
    if not isinstance(auxiliary_roots, list):
        raise ValueError('Auxiliary source roots must be an explicit list')
    _validate_paths(auxiliary_roots)
    namespaces = {r.get('namespace') for r in catalog if isinstance(r, dict)
                  and isinstance(r.get('namespace'), str)}
    for auxiliary_root in auxiliary_roots:
        parts = safe_path(auxiliary_root).parts
        if (len(parts) != 4 or parts[0] != 'providers' or parts[2] != 'skills'
                or parts[1] not in namespaces or not NAME_RE.fullmatch(parts[3])):
            raise ValueError('Invalid auxiliary source root')
    known_skill_roots.update(auxiliary_roots)
    for r in catalog:
        if not isinstance(r, dict) or type(r.get('id')) is not int or r['id'] < 1 or r['id'] in by_id:
            raise ValueError('Catalog IDs must be positive, unique integers')
        name, namespace = r.get('name'), r.get('namespace')
        if not isinstance(name, str) or len(name) > 64 or not NAME_RE.fullmatch(name):
            raise ValueError('Invalid catalog skill name')
        if not isinstance(namespace, str) or len(safe_path(namespace).parts) != 1:
            raise ValueError('Invalid catalog provider namespace')
        safe_path(name)
        uri = r.get('uri')
        identity = re.fullmatch(r'skills?://plugins/([^/\s]+)/([^/\s]+)', uri) if isinstance(uri, str) else None
        if not identity or identity.groups() != (namespace, name):
            raise ValueError('Catalog URI, provider and skill name disagree')
        root = r.get('staged_root')
        if root != f'providers/{namespace}/skills/{name}' or _path_key(root) in roots:
            raise ValueError('Catalog staged roots must be unique and match provider/name')
        roots.add(_path_key(root))
        skill = root + '/SKILL.md'
        if skill not in manifest['files'] or r.get('portable_sha256') != manifest['files'][skill]['sha256']:
            raise ValueError('Catalog SKILL.md is missing or its hash disagrees')
        missing = r.get('aux_missing')
        expected, recovered = r.get('aux_expected'), r.get('aux_recovered')
        actual = sum(n.startswith(root + '/') for n in manifest['files']) - 1
        if (not isinstance(missing, list) or any(not isinstance(x, str) for x in missing)
                or type(expected) is not int or type(recovered) is not int
                or recovered < 0 or expected != recovered + len(missing) or actual != recovered):
            raise ValueError('Catalog auxiliary counts do not match the payload')
        if 'original_path' in r or 'original_sha256' in r:
            original = f'originals/{namespace}/{name}/SKILL.md'
            if (r.get('original_path') != original or original not in manifest['files']
                    or r.get('original_sha256') != manifest['files'][original]['sha256']):
                raise ValueError('Catalog original root/hash disagrees with the manifest')
        resources = r.get('provider_resource_files', [])
        if not isinstance(resources, list):
            raise ValueError('Provider resources must be an explicit list')
        resource_names = []
        for entry in resources:
            if not isinstance(entry, dict):
                raise ValueError('Invalid provider resource record')
            path = entry.get('path')
            _provider_resource_path(path, namespace, known_skill_roots)
            if (path not in manifest['files'] or
                    {k: entry.get(k) for k in ('bytes', 'sha256')} != manifest['files'][path]):
                raise ValueError('Provider resource is missing or disagrees with the manifest')
            resource_names.append(path)
        _validate_paths(resource_names)
        by_id[r['id']] = r
    for key, total in (('aux_recovered', sum(r['aux_recovered'] for r in catalog)),
                       ('aux_missing', sum(len(r['aux_missing']) for r in catalog))):
        if type(manifest.get(key)) is not int or manifest[key] != total:
            raise ValueError('Catalog auxiliary totals disagree with the manifest')
    return by_id


def _provider_resource_path(path, namespace, known_skill_roots=None):
    """Allow common files and explicitly referenced auxiliaries of known sibling skills.

    SKILL.md is always excluded: copying an auxiliary does not select another skill.
    """
    parts = safe_path(path).parts
    if (len(parts) < 3 or parts[:2] != ('providers', namespace)
            or _path_key(parts[-1]) == 'skill.md'):
        raise ValueError('Provider resource must stay in its own provider and exclude skill entrypoints')
    if _path_key(parts[2]) == 'skills':
        if (parts[2] != 'skills' or len(parts) < 5 or known_skill_roots is None
                or '/'.join(parts[:4]) not in known_skill_roots):
            raise ValueError('Sibling auxiliary requires an explicit known skill root')
    return path


def _write_new_file(path, data, target, created_files, created_dirs):
    current = target
    for part in path.parent.relative_to(target).parts:
        current = current / part
        if not current.exists():
            current.mkdir()
            created_dirs.append(current)
        elif current.is_symlink() or not current.is_dir():
            raise ValueError('Staging directory was replaced or is not a directory')
    with path.open('xb') as out:
        owner = path.lstat()
        created_files.append((path, owner.st_dev, owner.st_ino))
        if out.write(data) != len(data):
            raise OSError('Incomplete staging write')


def _rollback_new_stage(created_files, created_dirs):
    """Remove only files we created and empty directories; preserve foreign data."""
    failures = []
    for path, device, inode in reversed(created_files):
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) != (device, inode):
                raise OSError('Staging path was replaced; preserving it')
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            failures.append(str(path))
    for directory in reversed(created_dirs):
        try:
            directory.rmdir()
        except FileNotFoundError:
            pass
        except OSError:
            failures.append(str(directory))
    return failures


def stage_selected(path, ids, target, apply=False, stop_file=None):
    _check_stop(stop_file)
    target = Path(target).expanduser().resolve()
    if any(x.lower() in ('.agents', '.claude', '.codex') for x in target.parts):
        raise ValueError('Use a new isolated lab, never an active skills directory')
    if target.exists():
        raise ValueError('Target must not exist; existing work is never overwritten')
    ids = list(ids)
    if not ids or any(type(i) is not int or i < 1 for i in ids):
        raise ValueError('Select at least one explicit skill ID')
    ids = list(dict.fromkeys(ids))
    with zipfile.ZipFile(path) as z:
        manifest = _verify_open_zip(z, stop_file)
        by_id = _catalog_by_id(z, manifest)
        if any(i not in by_id for i in ids):
            raise ValueError('Unknown skill ID')
        selected = [by_id[i] for i in ids]
        names = [r['name'] for r in selected]
        if len({_path_key(n) for n in names}) != len(names):
            raise ValueError('Selected skills have conflicting names; test separate provider scopes')
        provider_layout = any(r.get('provider_resource_files') for r in selected)
        sources = set()
        for r in selected:
            if r['aux_missing']:
                raise ValueError(f'Skill {r["id"]} still has missing declared resources')
            prefix = r['staged_root'] + '/'
            sources.update(n for n in manifest['files'] if n.startswith(prefix))
            sources.update(e['path'] for e in r.get('provider_resource_files', []))
        if provider_layout:
            plan = [(n, n) for n in sorted(sources)]
        else:
            plan = []
            for r in selected:
                prefix = r['staged_root'] + '/'
                plan += [(n, r['name'] + '/' + n[len(prefix):])
                         for n in sorted(sources) if n.startswith(prefix)]
        _validate_paths([relative for _, relative in plan])
        _check_stop(stop_file)
        if apply:
            # New target is exclusively ours. Visibility during copy is not atomic;
            # STAGE_RECEIPT.json is written only after every payload file succeeds.
            target.mkdir(parents=True, exist_ok=False)
            created_files, created_dirs = [], [target]
            try:
                for source, relative in plan:
                    _check_stop(stop_file)
                    data = z.read(source)
                    _check_record(source, manifest['files'][source], data)
                    _write_new_file(target / relative, data, target, created_files, created_dirs)
                _check_stop(stop_file)
                receipt = {'format': 'kai.skills.stage/2' if provider_layout else 'kai.skills.stage/1', 'ids': ids,
                           **({'layout': 'PROVIDER_SCOPED',
                               'selected_roots': [r['staged_root'] for r in selected],
                               'resource_paths': sorted({e['path'] for r in selected
                                                         for e in r.get('provider_resource_files', [])})}
                              if provider_layout else {}),
                           'bundle_manifest_sha256': sha(z.read('MANIFEST_SHA256.json')),
                           'files': [{'path': relative, 'source': source, **manifest['files'][source]}
                                     for source, relative in plan],
                           'executed_bundled_code': False, 'functional_validation': 'NOT_RUN',
                           'active_installation': False, 'atomic_visibility': False,
                           'failure_rollback': 'OWN_CREATED_FILES_AND_EMPTY_DIRECTORIES_ONLY'}
                _write_new_file(target / RECEIPT_NAME,
                                (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
                                target, created_files, created_dirs)
                _check_stop(stop_file)
            except BaseException as exc:
                failures = _rollback_new_stage(created_files, created_dirs)
                if failures:
                    raise RuntimeError('Stage failed; foreign/replaced paths preserved; cleanup incomplete: '
                                       + ', '.join(failures)) from exc
                raise
        return {'mode': 'ISOLATED_STAGE' if apply else 'DRY_RUN', 'ids': ids,
                'layout': 'PROVIDER_SCOPED' if provider_layout else 'FLAT_SKILL_LEGACY',
                'files': len(plan), 'target': str(target), 'executed_bundled_code': False,
                'functional_validation': 'NOT_RUN', 'active_installation': False,
                'receipt': str(target / RECEIPT_NAME) if apply else None}


def _rollback_plan(target, stop_file):
    _check_stop(stop_file)
    requested = Path(target).expanduser().absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('Rollback does not follow symlink targets or ancestors')
    target = requested.resolve()
    if target == Path(target.anchor) or any(p.lower() in ('.agents', '.claude', '.codex') for p in target.parts):
        raise ValueError('Rollback requires an isolated lab, never a filesystem root or active tree')
    if not target.is_dir():
        raise ValueError('Rollback target must be an existing lab directory')
    actual_files, actual_dirs = set(), set()
    for path in target.rglob('*'):
        relative = path.relative_to(target).as_posix()
        safe_path(relative)
        kind = stat.S_IFMT(path.lstat().st_mode)
        if kind == stat.S_IFREG:
            actual_files.add(relative)
        elif kind == stat.S_IFDIR:
            actual_dirs.add(relative)
        else:
            raise ValueError('Rollback target contains a symlink or nonregular member')
    if RECEIPT_NAME not in actual_files:
        raise ValueError('Completed staging receipt is required for rollback')
    receipt_data = (target / RECEIPT_NAME).read_bytes()
    receipt = read_json(receipt_data)
    if (not isinstance(receipt, dict) or receipt.get('format') not in {'kai.skills.stage/1', 'kai.skills.stage/2'}
            or receipt.get('active_installation') is not False
            or receipt.get('executed_bundled_code') is not False
            or not isinstance(receipt.get('bundle_manifest_sha256'), str)
            or not DIGEST_RE.fullmatch(receipt['bundle_manifest_sha256'])):
        raise ValueError('Unsupported or invalid staging receipt')
    ids, entries = receipt.get('ids'), receipt.get('files')
    if (not isinstance(ids, list) or not ids or any(type(i) is not int or i < 1 for i in ids)
            or len(set(ids)) != len(ids) or not isinstance(entries, list) or not entries
            or any(not isinstance(e, dict) for e in entries)):
        raise ValueError('Invalid staging receipt selection or file records')
    paths = [e.get('path') for e in entries]
    _validate_paths(paths)
    provider_layout = receipt['format'] == 'kai.skills.stage/2'
    selected_roots = receipt.get('selected_roots', [])
    resource_paths = receipt.get('resource_paths', [])
    if provider_layout:
        if (receipt.get('layout') != 'PROVIDER_SCOPED' or not isinstance(selected_roots, list)
                or len(selected_roots) != len(ids) or not isinstance(resource_paths, list)):
            raise ValueError('Invalid provider-scoped staging selection')
        _validate_paths(selected_roots)
        _validate_paths(resource_paths)
        if not set(resource_paths).issubset(paths):
            raise ValueError('Staging resource declaration names missing files')
        for root in selected_roots:
            parts = safe_path(root).parts
            if (len(parts) != 4 or parts[0] != 'providers' or parts[2] != 'skills'
                    or not NAME_RE.fullmatch(parts[3])):
                raise ValueError('Invalid provider-scoped selected root')
    expected_dirs, roots = set(), set()
    plan = []
    for entry in entries:
        relative = safe_path(entry['path'])
        source = safe_path(entry.get('source'))
        if provider_layout:
            if source != relative or len(source.parts) < 3:
                raise ValueError('Invalid provider-scoped receipt path')
            containing = [root for root in selected_roots if entry['path'].startswith(root + '/')]
            if containing:
                roots.update(containing)
            else:
                namespaces = {safe_path(root).parts[1] for root in selected_roots}
                if source.parts[1] not in namespaces:
                    raise ValueError('Resource belongs to an unselected provider')
                known_aux_roots = ({'/'.join(source.parts[:4])}
                                   if entry['source'] in resource_paths else None)
                _provider_resource_path(entry['source'], source.parts[1], known_aux_roots)
        elif (len(relative.parts) < 2 or not NAME_RE.fullmatch(relative.parts[0])
                or len(source.parts) < 5 or source.parts[0] != 'providers' or source.parts[2] != 'skills'
                or source.parts[3:] != relative.parts):
            raise ValueError('Staging receipt contains an invalid scoped file path')
        else:
            roots.add(relative.parts[0])
        expected_dirs.update(str(p) for p in relative.parents if str(p) != '.')
        if entry['path'] not in actual_files:
            raise ValueError('Rollback payload file is missing')
        _check_stop(stop_file)
        path = target / relative
        _check_record(entry['path'], entry, path.read_bytes())
        owner = path.lstat()
        plan.append((path, entry, (owner.st_dev, owner.st_ino)))
    if (len(roots) != len(ids) or any(root + '/SKILL.md' not in paths for root in roots)
            or actual_files != set(paths) | {RECEIPT_NAME} or actual_dirs != expected_dirs):
        raise ValueError('Rollback blocked: missing files or additional/foreign material')
    receipt_path = target / RECEIPT_NAME
    owner = receipt_path.lstat()
    plan.append((receipt_path, {'bytes': len(receipt_data), 'sha256': sha(receipt_data)},
                 (owner.st_dev, owner.st_ino)))
    return target, plan, actual_dirs


def rollback_stage(target, apply=False, stop_file=None):
    """Preview or remove an unchanged isolated copy; never remove foreign material."""
    target, plan, directories = _rollback_plan(target, stop_file)
    if apply:
        # The entire inventory/hash gate passed before the first deletion.
        # Individual records are rechecked before unlink; this is not atomic.
        for path, entry, identity in plan[:-1]:
            _check_stop(stop_file)
            current = path.lstat()
            if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity:
                raise ValueError('Rollback member was replaced; preserving it')
            _check_record(str(path), entry, path.read_bytes())
            path.unlink()
        for directory in sorted(directories, key=lambda p: len(PurePosixPath(p).parts), reverse=True):
            _check_stop(stop_file)
            (target / directory).rmdir()
        path, entry, identity = plan[-1]
        _check_stop(stop_file)
        current = path.lstat()
        if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino) != identity:
            raise ValueError('Staging receipt was replaced; preserving it')
        _check_record(RECEIPT_NAME, entry, path.read_bytes())
        path.unlink()
        target.rmdir()
    return {'mode': 'ROLLED_BACK' if apply else 'ROLLBACK_DRY_RUN', 'target': str(target),
            'files': len(plan) - 1, 'active_installation': False, 'atomic_visibility': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path, nargs='?')
    p.add_argument('--id', type=int, action='append', default=[])
    p.add_argument('--target', type=Path)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--stop-file', type=Path, help='Abort when this flag exists; contents are never read')
    p.add_argument('--rollback-target', type=Path, help='Preview removal of an unchanged isolated staging copy')
    args = p.parse_args()
    if args.rollback_target:
        if args.bundle or args.id or args.target:
            p.error('--rollback-target cannot be combined with bundle/--id/--target')
        result = rollback_stage(args.rollback_target, args.apply, args.stop_file)
    elif args.bundle is None:
        p.error('Provide a bundle or an explicit --rollback-target')
    elif args.target:
        result = stage_selected(args.bundle, args.id, args.target, args.apply, args.stop_file)
    else:
        if args.apply or args.id:
            p.error('--apply/--id require --target')
        m = verify_bundle(args.bundle, args.stop_file)
        result = {'status': 'PASS', 'hashed_payload_files': len(m['files']),
                  'skills': m['skills'], 'aux_recovered': m['aux_recovered'],
                  'aux_missing': m['aux_missing'], 'functional_validation': 'NOT_RUN',
                  'catalog_semantics': 'NOT_CHECKED_USE_SELECTIVE_STAGE_DRY_RUN'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
