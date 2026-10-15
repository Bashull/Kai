"""Build a partial candidate from a verified bundle and explicit replacement trees.

Reads provider files as data. Never executes providers, installs skills, fetches
dependencies, or promotes evidence claims into functional verification.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import stat
import zipfile

import bundle_io as b
import yaml


MAX_BYTES = 512 * 1024 * 1024
MAX_FILES = 25000
HISTORY = 'HISTORICAL/inherited_v041/'
SECRET_BYTES = re.compile(
    rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|'
    rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b|'
    rb'\bgithub_pat_[A-Za-z0-9_]{40,}\b|'
    rb'\bhf_[A-Za-z0-9]{30,}\b|'
    rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b|'
    rb'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'
)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def record(data):
    return {'bytes': len(data), 'sha256': b.sha(data)}


def _regular_bytes(path, stop_file=None):
    b._check_stop(stop_file)
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise ValueError('Only regular input files are accepted: ' + str(path))
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if ((opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                or not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_BYTES):
            raise ValueError('Input changed or exceeds inspection limit: ' + str(path))
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if (len(data) > MAX_BYTES or (opened.st_size, opened.st_mtime_ns)
            != (after.st_size, after.st_mtime_ns)):
        raise ValueError('Input changed or exceeds inspection limit: ' + str(path))
    return data


def _directory(path):
    path = Path(path).expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Symlink/junction input roots are not accepted')
    if not path.is_dir():
        raise ValueError('Input directory is unavailable: ' + str(path))
    return path.resolve()


def _secret_preflight(name, data):
    # Conservative rejection of recognizable new credentials, not certification
    # that arbitrary binary or textual evidence is free of every possible secret.
    basename = Path(name).name.lower()
    if (basename == '.env' or basename.startswith('.env.')
            or basename in {'credentials.json', 'id_rsa', 'id_ed25519'}
            or basename.endswith(('.pem', '.p12', '.pfx', '.dpapi', '.key'))
            or SECRET_BYTES.search(data)):
        raise ValueError('Possible credential material in new input; value withheld: ' + name)


def snapshot_directory(path, stop_file=None, tools_only=False):
    root = _directory(path)
    snapshot = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        b._check_stop(stop_file)
        for name in dirs:
            item = Path(directory) / name
            if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
                raise ValueError('Input directory contains a symlink/junction')
        for name in sorted(files):
            item = Path(directory) / name
            relative = item.relative_to(root).as_posix()
            if tools_only and (item.parent != root or not (name.endswith('.py') or name == 'README.md')):
                continue
            b.safe_path(relative)
            data = _regular_bytes(item, stop_file)
            _secret_preflight(relative, data)
            snapshot[relative] = data
            total += len(data)
            if len(snapshot) > MAX_FILES or total > MAX_BYTES:
                raise ValueError('Input snapshot exceeds inspection limits')
    b._validate_paths(list(snapshot))
    if tools_only and ('bundle_io.py' not in snapshot or 'README.md' not in snapshot):
        raise ValueError('Current toolkit requires bundle_io.py and README.md')
    return snapshot


class PayloadReader:
    def __init__(self, payload):
        self.payload = payload

    def read(self, path):
        return self.payload[path]


def _manifest(payload, catalog):
    return {'format': 'kai.skills.bundle/1', 'skills': len(catalog),
            'aux_recovered': sum(r['aux_recovered'] for r in catalog),
            'aux_missing': sum(len(r['aux_missing']) for r in catalog),
            'functional_tests': 'NOT_VERIFIED_BY_BUILDER',
            'release_state': 'CANDIDATE_PARTIAL',
            'files': {name: record(data) for name, data in sorted(payload.items())}}


def _csv(catalog):
    stream = io.StringIO(newline='')
    fields = ['id', 'namespace', 'name', 'aux_expected', 'aux_recovered',
              'original_aux_expected', 'captured_aux_expected', 'state', 'functional_tests']
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(catalog)
    return stream.getvalue().encode('utf-8-sig')


def _candidate_header(data, expected_name):
    text = data.decode('utf-8')
    match = re.match(r'^---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValueError('Candidate SKILL.md requires YAML frontmatter')
    try:
        metadata = yaml.safe_load(match[1])
    except yaml.YAMLError as exc:
        raise ValueError('Candidate frontmatter is invalid YAML') from exc
    if (not isinstance(metadata, dict) or metadata.get('name') != expected_name
            or not isinstance(metadata.get('description'), str)
            or not 1 <= len(metadata['description']) <= 1024):
        raise ValueError('Candidate frontmatter name/description does not match its catalog identity')


def build_incremental(base_bundle, candidates, evidence, output, stop_file=None,
                      base_sha256=None, tools_dir=None, expected_skills=None):
    """Create only new paths; return observed integrity and selective dry-run results.

    ``expected_skills`` is an optional input assertion, not a success counter.
    The CLI asserts the original 847-entry baseline by default. Library callers
    may use smaller synthetic catalogs for isolated regression tests.
    """
    b._check_stop(stop_file)
    output = Path(output).expanduser().absolute()
    for part in (output, *output.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Output and its parents must not be links')
    output = output.resolve()
    if any(part.lower() in {'.agents', '.codex', '.claude'} for part in output.parts):
        raise ValueError('Use an isolated output, never an active skills root')
    destination = output.with_name(output.name + '.zip')
    checksum = destination.with_name(destination.name + '.sha256')
    receipt_path = destination.with_name(destination.name + '.build.json')
    dry_target = output.parent / (output.name + '_selective_dry_run')
    for path in (output, destination, checksum, receipt_path, dry_target):
        if path.exists() or path.is_symlink():
            raise ValueError('Output paths must be new: ' + str(path))
    roots = [_directory(candidates), _directory(evidence),
             _directory(tools_dir or Path(__file__).parent)]
    if any(output.is_relative_to(root) for root in roots):
        raise ValueError('Output must be outside all input directory trees')
    base_data = _regular_bytes(Path(base_bundle).expanduser(), stop_file)
    base_digest = b.sha(base_data)
    if base_sha256 is not None:
        if not isinstance(base_sha256, str) or not b.DIGEST_RE.fullmatch(base_sha256):
            raise ValueError('Expected base SHA-256 must be a lowercase digest')
        if base_digest != base_sha256:
            raise ValueError('Base ZIP SHA-256 does not match the supplied pin')
    base_manifest = b.verify_bundle(io.BytesIO(base_data), stop_file)
    with zipfile.ZipFile(io.BytesIO(base_data)) as source:
        base_manifest_bytes = source.read('MANIFEST_SHA256.json')
        by_id = b._catalog_by_id(source, base_manifest)
        if expected_skills is not None:
            if (type(expected_skills) is not int or expected_skills < 1
                    or set(by_id) != set(range(1, expected_skills + 1))):
                raise ValueError('Base catalog does not match the expected original ID scope')
        for row in by_id.values():
            if 'original_path' not in row or 'original_sha256' not in row:
                raise ValueError('Every catalog entry must identify its preserved original')
        original_payload = {}
        for name in base_manifest['files']:
            b._check_stop(stop_file)
            original_payload[name] = source.read(name)
    candidate_files = snapshot_directory(roots[0], stop_file)
    evidence_files = snapshot_directory(roots[1], stop_file)
    tools_files = snapshot_directory(roots[2], stop_file, tools_only=True)
    by_root = {r['staged_root']: r for r in by_id.values()}
    selected = {}
    for name, data in candidate_files.items():
        parts = b.safe_path(name).parts
        if len(parts) < 5 or parts[0] != 'providers' or parts[2] != 'skills':
            raise ValueError('Candidate files must belong to a governed providers tree')
        root = '/'.join(parts[:4])
        if root not in by_root:
            raise ValueError('Unknown candidate provider/name: ' + root)
        selected.setdefault(root, {})[name] = data
    if not selected or any(root + '/SKILL.md' not in files for root, files in selected.items()):
        raise ValueError('Each explicit candidate tree must contain SKILL.md')
    for root, files in selected.items():
        _candidate_header(files[root + '/SKILL.md'], by_root[root]['name'])
    ids = sorted(by_root[root]['id'] for root in selected)
    payload = dict(original_payload)
    changes = []

    def preserve_and_remove(name, historical):
        if name in payload:
            if historical in payload:
                raise ValueError('Historical destination already exists: ' + historical)
            payload[historical] = payload.pop(name)

    # Old test reports are evidence of their own run, never the current result.
    for name in list(payload):
        if name.startswith('reports/'):
            target = ('reports/INHERITED_V041_RESULT.json' if name == 'reports/RESULT.json'
                      else 'reports/HISTORICAL/inherited_v041/' + name[len('reports/'):])
            preserve_and_remove(name, target)
        elif name.startswith('tools/'):
            preserve_and_remove(name, HISTORY + name)
    for name in (b.CATALOG_PATH, 'catalog/847_ESTADO.csv', 'catalog/847_UNA_A_UNA.md',
                 'README.md', 'INFORME_Y_CONTINUIDAD.md'):
        preserve_and_remove(name, HISTORY + name)
    payload[HISTORY + 'MANIFEST_SHA256.json'] = base_manifest_bytes
    catalog = [dict(row) for row in by_id.values()]
    catalog_by_id = {row['id']: row for row in catalog}
    for root, new_files in selected.items():
        row = catalog_by_id[by_root[root]['id']]
        old_files = {n: data for n, data in original_payload.items() if n.startswith(root + '/')}
        for name in old_files:
            preserve_and_remove(name, HISTORY + name)
        payload.update(new_files)
        resources = [{'path': n[len(root) + 1:], **record(data)}
                     for n, data in sorted(new_files.items()) if n != root + '/SKILL.md']
        original_count = row['aux_expected']
        row.setdefault('original_aux_expected', original_count)
        row.setdefault('captured_aux_expected', original_count)
        row.setdefault('captured_aux_recovered', row['aux_recovered'])
        row.setdefault('captured_aux_missing', list(row['aux_missing']))
        row['incremental_base_portable_sha256'] = row['portable_sha256']
        row['portable_sha256'] = row['candidate_sha256'] = b.sha(new_files[root + '/SKILL.md'])
        row.update(aux_expected=len(resources), aux_recovered=len(resources), aux_missing=[],
                   candidate_resource_files=resources, state='CANDIDATE_PARTIAL',
                   candidate_semantic_review='NOT_VERIFIED_BY_BUILDER',
                   functional_tests='NOT_VERIFIED_BY_BUILDER', deployment='NOT_INSTALLED',
                   packaged_auxiliary_scope='ACTUAL_TREE_FILES_NOT_TRANSITIVE_DEPENDENCY_CLOSURE')
        changes.append({'id': row['id'], 'namespace': row['namespace'], 'name': row['name'],
                        'original_sha256': row['original_sha256'],
                        'base_portable_sha256': row['incremental_base_portable_sha256'],
                        'candidate_sha256': row['candidate_sha256'],
                        'before_files': {n[len(root)+1:]: record(d) for n, d in sorted(old_files.items())},
                        'candidate_files': {n[len(root)+1:]: record(d) for n, d in sorted(new_files.items())},
                        'added': sorted(set(new_files) - set(old_files)),
                        'removed': sorted(set(old_files) - set(new_files)),
                        'changed': sorted(n for n in new_files.keys() & old_files.keys()
                                          if new_files[n] != old_files[n]),
                        'unchanged': sorted(n for n in new_files.keys() & old_files.keys()
                                            if new_files[n] == old_files[n]),
                        'functional_validation': 'NOT_VERIFIED_BY_BUILDER'})
    for name, data in tools_files.items():
        payload['tools/' + name] = data
    for name, data in evidence_files.items():
        destination_name = 'batch_001/evidence/' + name
        if destination_name in payload:
            raise ValueError('Batch evidence destination already exists')
        payload[destination_name] = data
    payload[b.CATALOG_PATH] = json_bytes(catalog)
    payload['catalog/847_ESTADO.csv'] = _csv(catalog)
    payload['batch_001/CHANGES.json'] = json_bytes(changes)
    payload['batch_001/CANDIDATE_INPUT_MANIFEST.json'] = json_bytes(
        {name: record(data) for name, data in sorted(candidate_files.items())})
    payload['batch_001/PROVENANCE.json'] = json_bytes({
        'format': 'kai.skills.incremental/1', 'state': 'CANDIDATE_PARTIAL',
        'base_zip_sha256': base_digest,
        'base_sha256_pin': 'MATCHED' if base_sha256 else 'COMPUTED_NOT_EXTERNALLY_PINNED',
        'base_manifest_sha256': b.sha(base_manifest_bytes),
        'candidate_ids': ids, 'historical_prefix': HISTORY,
        'evidence_claims': 'COPIED_AS_EVIDENCE_NOT_PROMOTED_BY_BUILDER',
        'new_secret_preflight': 'HIGH_CONFIDENCE_PATTERNS_ONLY_NOT_CERTIFICATION',
        'provider_code_execution': False, 'active_installation': False})
    summary = ('# KAI Skills Forge — incremental candidate\n\n'
               'State: CANDIDATE_PARTIAL / NOT_INSTALLED / NOT_CANONICAL.\n\n'
               'Originals retain their original bytes. Only explicitly supplied provider trees change. '
               'The base tools, reports, replaced trees and catalog remain historical evidence. '
               'support_files records remain historical capture metadata; candidate_resource_files '
               'and auxiliary counts describe packaged files, not transitive dependency closure.\n\n'
               'Read batch_001/CHANGES.json, batch_001/PROVENANCE.json, the current catalog and '
               'batch_001/evidence/. Copied audit/test receipts retain their original scope. '
               'The builder does not infer manual understanding, upstream currency or provider behavior.\n\n'
               'Run python tools/bundle_io.py ARCHIVE.zip to check payload integrity. '
               'Use --id ID --target NEW_LAB for selective dry-run; --apply is a separate lab copy. '
               'No active installation or provider execution is performed by this build. '
               'The sibling ZIP.build.json records actual post-build verification and dry-run outcomes.\n')
    payload['README.md'] = summary.encode('utf-8')
    payload['INFORME_Y_CONTINUIDAD.md'] = summary.encode('utf-8')
    payload['catalog/847_UNA_A_UNA.md'] = ('# Current candidate catalog\n\n'
        'The number of baseline entries is observed from the verified input catalog. '
        'Inherited reviews retain their earlier scope; current batch evidence is separate.\n\n' +
        '\n'.join(f'- {r["id"]:04d}: {r["namespace"]}/{r["name"]} — {r["state"]}'
                  for r in catalog) + '\n').encode('utf-8')
    result = {'format': 'kai.skills.incremental.result/1', 'state': 'CANDIDATE_PARTIAL',
              'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'observed_catalog_entries': len(catalog), 'candidate_tree_ids': ids,
              'main_changed_ids': sorted(c['id'] for c in changes
                                         if c['candidate_sha256'] != c['base_portable_sha256']),
              'trees_with_file_changes': sorted(c['id'] for c in changes
                                                if c['changed'] or c['added'] or c['removed']),
              'original_files_preserved': sum(n.startswith('originals/') for n in original_payload),
              'candidate_input_files': len(candidate_files), 'evidence_files_copied': len(evidence_files),
              'current_tool_files': len(tools_files), 'base_integrity': 'PASS',
              'manual_review': 'NOT_VERIFIED_BY_BUILDER', 'functional_tests': 'NOT_RUN_BY_BUILDER',
              'provider_execution': False, 'active_installation': False,
              'output_integrity': 'SEE_POST_BUILD_RECEIPT',
              'tests_run': 'NOT_RUN_BY_BUILDER'}
    payload['reports/RESULT.json'] = json_bytes(result)
    b._validate_paths(list(payload) + ['MANIFEST_SHA256.json'])
    if len(payload) + 1 > MAX_FILES or sum(map(len, payload.values())) > MAX_BYTES:
        raise ValueError('Result exceeds documented bundle inspection limits')
    manifest = _manifest(payload, catalog)
    b._catalog_by_id(PayloadReader(payload), manifest)
    for name, data in original_payload.items():
        if name.startswith('originals/') and payload.get(name) != data:
            raise ValueError('An original file would change')
    b._check_stop(stop_file)
    output.mkdir(parents=True, exist_ok=False)
    owner = output.lstat()
    created_files, created_dirs = [], [output]

    def write(path, data, target=output):
        b._check_stop(stop_file)
        current = output.lstat()
        if (current.st_dev, current.st_ino) != (owner.st_dev, owner.st_ino) or output.is_symlink():
            raise ValueError('Output directory was replaced')
        b._write_new_file(path, data, target, created_files, created_dirs)

    try:
        for name, data in sorted(payload.items()):
            write(output / name, data)
        manifest_data = json_bytes(manifest)
        write(output / 'MANIFEST_SHA256.json', manifest_data)
        b._check_stop(stop_file)
        with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
            info = destination.lstat()
            created_files.append((destination, info.st_dev, info.st_ino))
            for name, data in sorted({**payload, 'MANIFEST_SHA256.json': manifest_data}.items()):
                b._check_stop(stop_file)
                archive.writestr(name, data)
        verified = b.verify_bundle(destination, stop_file)
        dry_run = b.stage_selected(destination, ids, dry_target, apply=False, stop_file=stop_file)
        zip_record = record(_regular_bytes(destination, stop_file))
        write(checksum, (zip_record['sha256'] + '  ' + destination.name + '\n').encode(), output.parent)
        receipt = {'format': 'kai.skills.incremental.build/1', 'state': 'CANDIDATE_PARTIAL',
                   'zip': str(destination), **zip_record, 'base_zip_sha256': base_digest,
                   'catalog_entries': len(catalog), 'candidate_ids': ids,
                   'hashed_payload_files': len(verified['files']),
                   'archive_integrity': 'PASS', 'catalog_selective_dry_run': dry_run,
                   'provider_execution': False, 'active_installation': False,
                   'functional_tests': 'NOT_RUN_BY_BUILDER', 'tests_run': 'NOT_RUN_BY_BUILDER'}
        write(receipt_path, json_bytes(receipt), output.parent)
        b._check_stop(stop_file)
    except BaseException as exc:
        failures = b._rollback_new_stage(created_files, created_dirs)
        if failures:
            raise RuntimeError('Build failed; foreign/replaced files preserved; cleanup incomplete: '
                               + ', '.join(failures)) from exc
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-bundle', type=Path, required=True)
    parser.add_argument('--base-sha256', help='Optional externally verified base ZIP digest')
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stop-file', type=Path)
    parser.add_argument('--expected-skills', type=int, default=847)
    args = parser.parse_args()
    result = build_incremental(args.base_bundle, args.candidates, args.evidence,
                               args.output, args.stop_file, args.base_sha256,
                               expected_skills=args.expected_skills)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
