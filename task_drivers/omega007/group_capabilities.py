"""Add navigable views to the existing federation; never merge or execute sources."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bundle_io as b
import build_incremental as inc


def build_groups(registry, audit, spec, expected=None):
    expected = expected or {'originals': 847, 'pc-asier': 723, 'termux': 3659}
    if registry.get('format') != 'kai.skills.federation/1':
        raise ValueError('Existing federation format required')
    records = registry.get('records')
    if not isinstance(records, list) or dict(Counter(r.get('source') for r in records)) != expected:
        raise ValueError('Fixed census collection coverage differs')
    by_id = {}
    collections, hashes, names, providers = (defaultdict(list) for _ in range(4))
    prefixes = {'originals': 'ORI', 'pc-asier': 'PC', 'termux': 'TMX'}
    for r in records:
        rid, digest = r.get('historical_id'), r.get('sha256')
        if (not isinstance(rid, str) or not re.fullmatch(prefixes[r['source']] + r'-\d{4}', rid)
                or rid in by_id or not isinstance(digest, str) or not b.DIGEST_RE.fullmatch(digest)):
            raise ValueError('Missing/duplicate historical identity or unverified document hash')
        by_id[rid] = r
        collections[r['source']].append(rid)
        hashes[digest].append(rid)
        name = r.get('text_profile', {}).get('name')
        if isinstance(name, str) and name:
            names[name].append(rid)
        if r['source'] == 'originals':
            namespace = r.get('author_provider')
            if not isinstance(namespace, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', namespace):
                raise ValueError('Invalid original provider namespace')
            providers[namespace].append(rid)
    for source, count in expected.items():
        if set(collections[source]) != {prefixes[source] + '-' + str(i).zfill(4) for i in range(1, count + 1)}:
            raise ValueError('Historical occurrence IDs were reassigned')
    rows = audit.get('rows')
    if not isinstance(rows, list) or len(rows) != expected['originals']:
        raise ValueError('Original audit coverage differs')
    ids = [r.get('id') for r in rows]
    if any(type(i) is not int for i in ids) or sorted(ids) != list(range(1, expected['originals'] + 1)):
        raise ValueError('Audit IDs were reassigned or duplicated')
    reviewed = {'ORI-' + str(r['id']).zfill(4) for r in rows if r.get('manual_instruction_review') is True}
    if spec.get('format') != 'kai.skills.reviewed-families/1' or not isinstance(spec.get('families'), list):
        raise ValueError('Explicit reviewed family specification required')
    candidate_ids = spec.get('candidate_ids')
    if (not isinstance(candidate_ids, list) or any(type(i) is not int for i in candidate_ids)
            or len(set(candidate_ids)) != len(candidate_ids)
            or any('ORI-' + str(i).zfill(4) not in reviewed for i in candidate_ids)):
        raise ValueError('Candidate IDs must be unique individually reviewed originals')
    candidates = {'ORI-' + str(i).zfill(4) for i in candidate_ids}
    families, assigned, family_ids = [], set(), set()
    for f in spec['families']:
        key, members = f.get('id'), f.get('members')
        if (not isinstance(key, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', key)
                or key in family_ids or not isinstance(members, list) or not members):
            raise ValueError('Invalid or duplicate family')
        family_ids.add(key)
        for rid in members:
            if rid not in reviewed or rid not in by_id:
                raise ValueError('Unreviewed or unknown entry cannot acquire a reviewed family')
            if rid in assigned:
                raise ValueError('Reviewed family membership must be exclusive')
            assigned.add(rid)
        families.append({**f, 'scope': 'MANUAL_INSTRUCTION_REVIEW_NOT_WHOLE_CAPABILITY_CERTIFICATION',
                         'members': sorted(members), 'candidate_members': sorted(set(members) & candidates),
                         'whole_capability_verified': False})
    if assigned != reviewed:
        raise ValueError('Every individually reviewed original needs an explicit family')
    exact = [{'sha256': h, 'members': sorted(v), 'scope': 'DOCUMENT_BYTES_ONLY',
              'functional_equivalence': 'NOT_INFERRED'} for h, v in sorted(hashes.items())]
    return {'format': 'kai.skills.grouping/1', 'extends': 'kai.skills.federation/1',
            'scope': 'FIXED_CAPTURE_NAVIGATION_NOT_MERGE_NOT_INSTALLATION',
            'summary': {'occurrences': len(records), 'collections': expected,
                        'document_byte_groups': len(exact),
                        'duplicate_document_groups': sum(len(x['members']) > 1 for x in exact),
                        'original_provider_groups': len(providers), 'declared_name_groups': len(names),
                        'reviewed_originals': len(reviewed), 'reviewed_families': len(families),
                        'pending_original_manual_reviews': expected['originals'] - len(reviewed),
                        'pending_occurrence_deep_reviews_in_OMEGA': len(records) - len(reviewed),
                        'candidate_trees': len(candidates), 'unique_functional_capabilities': None},
            'reviewed_families': families,
            'collection_groups': dict(sorted((k, sorted(v)) for k, v in collections.items())),
            'original_provider_groups': dict(sorted((k, sorted(v)) for k, v in providers.items())),
            'document_byte_groups': exact,
            'declared_name_groups': {k: {'members': sorted(v), 'scope': 'METADATA_NAME_ONLY_NOT_FUNCTIONAL_EQUIVALENCE'}
                                     for k, v in sorted(names.items())},
            'unnamed_main_ids': sorted(rid for rid, r in by_id.items() if not r.get('text_profile', {}).get('name')),
            'pending_deep_review_ids': sorted(set(by_id) - reviewed),
            'whole_capabilities_verified': 0, 'originals_modified': False, 'active_installation': False}


def markdown(result, registry):
    by_id = {r['historical_id']: r for r in registry['records']}
    s = result['summary']
    text = '# Agrupación de skills · OMEGA007\n\n'
    text += ('Vista del registro federado existente. Conserva cada original, su ID y su ubicación; no mueve, borra, '
             'fusiona ni instala archivos. Una familia expresa relación de trabajo, no funciones intercambiables.\n\n')
    text += (f"**{s['occurrences']:,} ocurrencias históricas**, {s['document_byte_groups']:,} grupos de bytes, "
             f"{s['original_provider_groups']} proveedores originales y {s['reviewed_originals']} originales revisados "
             f"en {s['reviewed_families']} familias. {s['pending_original_manual_reviews']} originales pendientes. "
             'El número de capacidades funcionales únicas sigue desconocido.\n\n')
    text += '| Familia revisada | Entradas | Candidatas |\n| --- | --- | --- |\n'
    for f in result['reviewed_families']:
        labels = ', '.join(rid + ' ' + by_id[rid]['text_profile']['name'] for rid in f['members'])
        text += '| ' + f['title'] + ' | ' + labels + ' | ' + ', '.join(f['candidate_members']) + ' |\n'
    text += (f"\nLos {s['document_byte_groups']:,} grupos por SHA256 identifican documentos de contenido idéntico en este corte; "
             'no certifican sus dependencias, permisos, equivalencia funcional ni compatibilidad de instalación. '
             'Las coincidencias por nombre son pistas y pueden contener proveedores distintos. '
             'PC y Termux conservan sus colecciones e IDs; no se les propaga la revisión manual de un clon.\n\n')
    text += ('La exportación0005 reutiliza un único auxiliar propio de0004: '
             '`providers/data-analytics/skills/convert-to-doc/scripts/verify-local-export.mjs`. '
             'La selección005 incluye ese archivo explícitamente sin seleccionar el main004. '
             'Los recursos comunes Data se deduplican por ruta/hash en el paquete; Documents y Presentations '
             'siguen siendo capacidades externas del host.\n\n')
    text += ('El JSON adjunto contiene todos los miembros y las vistas por colección, proveedor original, '
             'nombre declarado y bytes. Su fuente preservada está en '
             '`batch_003/evidence/federation/FEDERATED_REGISTRY.json` del payload acumulado. '
             'Las métricas de la rama UNION requieren reconciliación separada.\n\n')
    text += '| Proveedor original (metadata) | Entradas ORI |\n| --- | ---: |\n'
    for name, members in result['original_provider_groups'].items():
        text += f'| `{name}` | {len(members)} |\n'
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', type=Path, required=True)
    p.add_argument('--registry-sha256', required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--families', type=Path, default=Path(__file__).with_name('reviewed_families.json'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--stop-file', type=Path)
    a = p.parse_args(); b._check_stop(a.stop_file)
    out = a.output.absolute()
    if out.exists() or any(x.is_symlink() for x in [out, *out.parents]):
        raise ValueError('Grouping output must be a new isolated directory')
    if any(x.lower() in {'.codex', '.agents', '.claude'} for x in out.parts):
        raise ValueError('Active installation paths are not allowed')
    raw = inc._regular_bytes(a.registry, a.stop_file)
    if not b.DIGEST_RE.fullmatch(a.registry_sha256) or b.sha(raw) != a.registry_sha256:
        raise ValueError('Registry SHA mismatch')
    registry = b.read_json(raw)
    audit_raw, families_raw = inc._regular_bytes(a.audit, a.stop_file), inc._regular_bytes(a.families, a.stop_file)
    result = build_groups(registry, b.read_json(audit_raw), b.read_json(families_raw))
    result['inputs'] = {'registry': inc.record(raw), 'audit': inc.record(audit_raw), 'families': inc.record(families_raw)}
    b._check_stop(a.stop_file); out.mkdir(parents=True)
    for name, data in [('AGRUPACION_SKILLS_OMEGA007.json', inc.json_bytes(result)),
                       ('AGRUPACION_SKILLS_OMEGA007.md', markdown(result, registry).encode())]:
        b._check_stop(a.stop_file)
        with (out / name).open('xb') as f:
            f.write(data)
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
