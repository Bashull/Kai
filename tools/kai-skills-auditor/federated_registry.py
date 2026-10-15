"""Federate preserved occurrences without certifying functional equivalence.

Extends the existing Forge toolkit. Inputs are pinned capture ZIPs and an
already verified original bundle tree. No captured instructions are executed.
"""
import argparse
import collections
import datetime as dt
import io
import json
from pathlib import Path
import re
import stat
import zipfile

import yaml

from bundle_io import (sha, read_json, _validate_paths, _check_record,
                       _check_stop, DIGEST_RE)
from capture_skills import read_regular


COLLECTIONS = {'pc-asier': ('PC', 723), 'termux': ('TMX', 3659)}


def inspect_text(data):
    result = {'name': None, 'description': None, 'declared_license': None,
              'version': None, 'frontmatter': 'ABSENT', 'issues': []}
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        result['issues'].append('NON_UTF8'); return result
    normalized = '\n'.join(line.rstrip(' \t') for line in
                            text.replace('\r\n', '\n').replace('\r', '\n').split('\n')).strip('\n') + '\n'
    result['normalized_text_sha256'] = sha(normalized.encode('utf-8'))
    result['normalization_scope'] = 'LINE_ENDINGS_TRAILING_HORIZONTAL_SPACE_FINAL_NEWLINE_ONLY'
    result['local_link_hints'] = sorted(set(re.findall(r'\]\(([^)]+)\)', text)))
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)', text, re.S)
    if not match:
        return result
    if len(match[1]) > 128 * 1024:
        result['issues'].append('FRONTMATTER_TOO_LARGE'); return result
    try:
        header = yaml.safe_load(match[1])
    except (yaml.YAMLError, RecursionError):
        result['frontmatter'] = 'INVALID_YAML'; return result
    if not isinstance(header, dict):
        result['frontmatter'] = 'NOT_A_MAPPING'; return result
    result['frontmatter'] = 'PARSED_NOT_SCHEMA_CERTIFIED'
    for source, target in [('name', 'name'), ('description', 'description'),
                           ('license', 'declared_license'), ('version', 'version')]:
        value = header.get(source)
        if isinstance(value, str):
            result[target] = value
        elif value is not None:
            result['issues'].append('NON_STRING_' + source.upper())
    return result


def read_capture(path, expected_sha256, source, expected_count=None, stop=None):
    """Check the exact archive handle, every byte object, census and occurrence."""
    _check_stop(stop)
    if source not in COLLECTIONS or not isinstance(expected_sha256, str) or not DIGEST_RE.fullmatch(expected_sha256):
        raise ValueError('Known source and explicit SHA-256 pin required')
    count = COLLECTIONS[source][1] if expected_count is None else expected_count
    if type(count) is not int or count < 1:
        raise ValueError('Expected count must be a positive integer')
    raw = read_regular(path, 32 * 1024 * 1024)
    if sha(raw) != expected_sha256:
        raise ValueError('Capture SHA-256 does not match pin')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos = z.infolist(); names = [i.filename for i in infos]
        if len(names) > 20000 or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
            raise ValueError('Capture exceeds inspection limits')
        _validate_paths(names)
        if any(i.is_dir() or stat.S_IFMT(i.external_attr >> 16) not in (0, stat.S_IFREG) for i in infos):
            raise ValueError('Capture members must be regular files')
        integrity = read_json(z.read('CAPTURE_INTEGRITY.json'))
        if integrity.get('format') != 'kai.capture.integrity/1' or set(integrity.get('files', {})) != set(names) - {'CAPTURE_INTEGRITY.json'}:
            raise ValueError('Capture integrity coverage mismatch')
        objects = {}
        for name, record in integrity['files'].items():
            _check_stop(stop)
            data = z.read(name); _check_record(name, record, data)
            objects[name] = data
        manifest = read_json(objects['CAPTURE_MANIFEST.json'])
        census_bytes = objects['SOURCE_CENSUS.json']; census = read_json(census_bytes)
        if (manifest.get('format') != 'kai.skill_capture/1' or manifest.get('source') != source
                or manifest.get('expected_count') != count or manifest.get('census_sha256') != sha(census_bytes)):
            raise ValueError('Capture identity/count/census mismatch')
        rows = manifest.get('rows'); old_rows = census.get('skills')
        if not isinstance(rows, list) or not isinstance(old_rows, list) or len(rows) != count or len(old_rows) != count:
            raise ValueError('Occurrence coverage mismatch')
        paths = set(); counts = collections.Counter()
        for index, (row, old) in enumerate(zip(rows, old_rows), 1):
            if (type(row.get('index')) is not int or row['index'] != index
                    or row.get('path') != old.get('path')
                    or row.get('expected_sha256') != old.get('sha256')
                    or row.get('expected_bytes') != old.get('bytes')
                    or row.get('occurrence_id') != source + ':' + str(index).zfill(4)):
                raise ValueError('Historical occurrence was renumbered or mismatched')
            path_key = row['path'].replace('\\', '/')
            uid = 'occ:' + source + ':' + sha(path_key.encode())[:24]
            if row.get('occurrence_uid') != uid:
                raise ValueError('Occurrence UID mismatch')
            path_key = path_key.casefold() if source == 'pc-asier' else path_key
            if path_key in paths:
                raise ValueError('Duplicate source occurrence path')
            paths.add(path_key)
            state = row.get('state'); counts[state] += 1
            if state not in {'CAPTURED', 'CHANGED_SINCE_CENSUS', 'BLOCKED'}:
                raise ValueError('Unknown capture state')
            if state != 'BLOCKED':
                data = objects.get(row.get('object_path'))
                if data is None or sha(data) != row.get('sha256') or len(data) != row.get('bytes'):
                    raise ValueError('Occurrence object missing or corrupt')
                same = row['sha256'] == old['sha256'] and len(data) == old['bytes']
                if row.get('matches_census') is not same or (state == 'CAPTURED') is not same:
                    raise ValueError('Changed source incorrectly presented as unchanged')
        expected_counts = {s: counts[s] for s in ('CAPTURED', 'CHANGED_SINCE_CENSUS', 'BLOCKED')}
        if manifest.get('counts') != expected_counts:
            raise ValueError('Capture counts disagree with row evidence')
        return manifest, objects


def record_base(historical_id, uid, source, path, data, evidence, previous=None):
    info = inspect_text(data) if data is not None else {}
    digest = sha(data) if data is not None else None
    return {'historical_id': historical_id, 'global_occurrence_id': uid,
        'source': source, 'path': path, 'bytes': len(data) if data is not None else None,
        'sha256': digest, 'text_profile': info,
        'logical_global_id': None, 'logical_identity_status': 'NOT_FUNCTIONALLY_RECONCILED',
        'content_group_id': 'sha256:' + digest if digest else None,
        'author_provider': (previous or {}).get('namespace', 'NOT_REVIEWED'),
        'license': {'declared': info.get('declared_license'), 'clearance': 'NOT_CERTIFIED_FOR_REDISTRIBUTION'},
        'version': info.get('version'), 'modified_at': None, 'format': 'SKILL.md',
        'resources': {'capture_scope': 'SKILL_MAIN_TEXT', 'transitive_closure': 'NOT_VERIFIED'},
        'dependencies': 'PENDING_INDIVIDUAL_REVIEW', 'repository': None,
        'document_state': 'EVIDENCE', 'access_state': 'BYTES_CAPTURED' if data is not None else 'BLOCKED',
        'understanding_level': 'L1_INVENTORIED', 'functional_test_state': 'NOT_TESTED',
        'deep_audit_state': 'PENDING', 'evidence': evidence,
        'historical_catalog': previous, 'whole_capability_verified': False}


def federate(original_root, catalog, captures, stop=None):
    _check_stop(stop)
    if not isinstance(catalog, list) or [r.get('id') for r in catalog] != list(range(1, len(catalog) + 1)) or not catalog:
        raise ValueError('Original catalog must retain contiguous ordered integer IDs')
    if any(type(r['id']) is not int for r in catalog):
        raise ValueError('Boolean/noninteger original ID')
    identities = [(r.get('namespace'), r.get('name')) for r in catalog]
    if len(set(identities)) != len(catalog) or any(not all(isinstance(s, str) and s for s in pair) for pair in identities):
        raise ValueError('Original provider identities must be unique')
    records = []; content = {}; normalized = {}; named = {}
    for row in catalog:
        _check_stop(stop)
        from bundle_io import safe_path
        safe_path(row['original_path'])
        data = read_regular(Path(original_root) / row['original_path'])
        if sha(data) != row['original_sha256']:
            raise ValueError('Original source hash mismatch')
        rid = 'ORI-' + str(row['id']).zfill(4)
        rec = record_base(rid, 'ori:' + row['namespace'] + ':' + row['name'], 'originals',
                          row['original_path'], data,
                          {'basis': 'PINNED_BATCH002_ORIGINAL', 'prior_numeric_id': row['id']}, row)
        records.append(rec)
    seen_sources = set()
    for manifest, objects in captures:
        source = manifest['source']
        if source in seen_sources:
            raise ValueError('A collection cannot be federated twice')
        seen_sources.add(source); prefix = COLLECTIONS[source][0]
        for row in manifest['rows']:
            _check_stop(stop)
            rid = prefix + '-' + str(row['index']).zfill(4)
            rec = record_base(rid, row['occurrence_uid'], source, row['path'],
                              objects.get(row.get('object_path')),
                              {'capture_alias': row['occurrence_id'], 'capture_utc': manifest['utc'],
                               'census_sha256': manifest['census_sha256'], 'capture_state': row['state'],
                               'historical_label_basis': 'PRESERVED_CENSUS_ORDER_NOT_A_REASSIGNED_ID'})
            if row['state'] == 'BLOCKED': rec['block_reason'] = row.get('error')
            records.append(rec)
    for rec in records:
        rid = rec['historical_id']; info = rec['text_profile']
        if rec['sha256']: content.setdefault(rec['sha256'], []).append(rid)
        if info.get('normalized_text_sha256'): normalized.setdefault(info['normalized_text_sha256'], []).append(rid)
        if info.get('name'): named.setdefault(info['name'], []).append(rid)
    by_id = {r['historical_id']: r for r in records}
    if len(by_id) != len(records): raise ValueError('Historical ID collision')
    edges = []
    for digest, ids in content.items():
        for rid in ids[1:]:
            edges.append({'from': rid, 'to': ids[0], 'relation': 'DUPLICATE_OF',
                          'scope': 'DOCUMENT_BYTES_ONLY', 'sha256': digest,
                          'functional_equivalence': 'NOT_REVIEWED'})
    variants = []
    for digest, ids in normalized.items():
        if len({by_id[i]['sha256'] for i in ids}) > 1:
            variants.append({'normalized_sha256': digest, 'ids': ids,
                             'scope': 'TEXT_NORMALIZATION_ONLY_NOT_SEMANTIC_EQUIVALENCE'})
    summary = {'scope': 'VERIFIED_SCOPE_FIXED_HISTORICAL_CENSUSES_NOT_FULL_DEVICE_INVENTORY',
        'records': len(records), 'collections': dict(collections.Counter(r['source'] for r in records)),
        'hash_verified_records': sum(r['sha256'] is not None for r in records),
        'distinct_main_text_hashes': len(content),
        'duplicate_occurrences_beyond_first': sum(len(v) - 1 for v in content.values()),
        'exact_duplicate_groups': sum(len(v) > 1 for v in content.values()),
        'normalized_variant_groups': len(variants), 'unique_functional_capabilities': None,
        'new_deep_audits_completed_by_this_automation': 0, 'whole_capabilities_verified': 0}
    return {'format': 'kai.skills.federation/1', 'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'summary': summary, 'records': records, 'edges': edges,
            'normalized_variants': variants,
            'name_candidates': {k:v for k,v in named.items() if len(v)>1}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original-root', type=Path, required=True)
    p.add_argument('--pc', type=Path, required=True); p.add_argument('--pc-sha256', required=True)
    p.add_argument('--termux', type=Path, required=True); p.add_argument('--termux-sha256', required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--stop-file', type=Path)
    a = p.parse_args(); _check_stop(a.stop_file)
    if a.output.exists() or a.output.is_symlink(): raise ValueError('Federation output must be new')
    catalog = read_json((a.original_root / 'catalog/INDEX_847_RECONCILED.json').read_bytes())
    if len(catalog) != 847: raise ValueError('Historical original count must be 847')
    captures = [read_capture(a.pc, a.pc_sha256, 'pc-asier', stop=a.stop_file),
                read_capture(a.termux, a.termux_sha256, 'termux', stop=a.stop_file)]
    result = federate(a.original_root, catalog, captures, a.stop_file)
    _check_stop(a.stop_file); a.output.mkdir(parents=True, exist_ok=False)
    # New-directory publication is recoverable, not a claim of filesystem-wide atomicity.
    for name, data in [('FEDERATED_REGISTRY.json', result), ('COVERAGE.json', result['summary'])]:
        _check_stop(a.stop_file)
        with (a.output/name).open('x', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__': main()
