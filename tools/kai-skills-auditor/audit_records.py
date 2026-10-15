"""Generate coverage records without upgrading static evidence into understanding.

Input catalog must come from a separately verified bundle. Manual dossiers are
explicit overlays; absent evidence remains pending. No provider code is run.
"""
import argparse
import json
from pathlib import Path


FIELDS = (
    '01_identidad_procedencia', '02_version_licencia_estado', '03_proposito',
    '04_triggers', '05_entradas_salidas', '06_recursos', '07_dependencias_permisos',
    '08_codigo_arquitectura', '09_compatibilidad_4_plataformas',
    '10_seguridad_privacidad', '11_deuda_errores', '12_redundancias_composicion',
    '13_documentacion', '14_upstream_updates', '15_alternativas', '16_propuesta',
    '17_modificaciones', '18_pruebas_evidencias', '19_SHA_traza',
    '20_instalacion_recuperacion', '21_estado_siguiente',
)
STATES = {'DISCOVERED', 'INVENTORIED', 'INSPECTED', 'UNDERSTOOD', 'IMPROVED',
          'TESTED', 'VERIFIED', 'BLOCKED', 'UNCHANGED', 'REJECTED'}
PENDING = 'NO_COMPROBADO: requiere inspección individual de instrucciones, recursos y fuentes.'


def generate_records(catalog, matrix_rows, manual, expected_count=847):
    if type(expected_count) is not int or expected_count < 1:
        raise ValueError('Expected count must be a positive integer')
    if not isinstance(catalog, list) or len(catalog) != expected_count:
        raise ValueError('Catalog must cover the explicit original count')
    ids = [r.get('id') for r in catalog]
    if any(type(i) is not int for i in ids) or set(ids) != set(range(1, expected_count + 1)):
        raise ValueError('Original IDs must be unique and contiguous')
    identities = [(r.get('namespace'), r.get('name')) for r in catalog]
    if any(not all(isinstance(s, str) and s for s in pair) for pair in identities):
        raise ValueError('Provider namespace and name are required')
    if len(set(identities)) != expected_count:
        raise ValueError('Namespaced identities must be unique')
    evidence_ids = [r.get('id') for r in matrix_rows]
    if len(evidence_ids) != expected_count or set(evidence_ids) != set(ids):
        raise ValueError('Matrix must cover the same original IDs exactly once')
    matrix = {r['id']: r for r in matrix_rows}
    if not isinstance(manual, dict) or set(manual) - set(ids):
        raise ValueError('Unknown manual dossier ID')
    records = []
    for row in sorted(catalog, key=lambda r: r['id']):
        number = row['id']
        evidence = matrix[number]
        state = evidence.get('state', 'INSPECTED')
        if state not in STATES:
            raise ValueError('Unsupported evidence state')
        # A whole-capability VERIFIED claim needs its own externally reviewed
        # evidence. This generator deliberately cannot certify such a claim.
        if state == 'VERIFIED' or evidence.get('whole_capability_verified'):
            raise ValueError('Whole capability verification cannot be inferred here')
        if evidence.get('manual_instruction_review') is True:
            if number not in manual or set(manual[number]) != set(FIELDS):
                raise ValueError('Manual coverage requires a complete 21-field dossier')
            dossier = dict(manual[number])
        else:
            if number in manual:
                raise ValueError('Manual dossier must have matching matrix evidence')
            dossier = {key: PENDING for key in FIELDS}
            dossier.update({
                FIELDS[0]: {'id_original': number, 'nombre': row['name'],
                    'namespace': row['namespace'],
                    'id_estable': row['namespace'] + ':' + row['name'],
                    'uri_original': row['uri']},
                FIELDS[1]: {'estado': state, 'version': 'NO_COMPROBADO',
                    'licencia': row.get('license_clearance', 'NO_COMPROBADO')},
                FIELDS[2]: {'descripcion_capturada': row.get('description', ''),
                    'comprension_funcional': PENDING},
                FIELDS[5]: {'recursos_declarados': row.get('support_files', []),
                    'archivos_auxiliares_empaquetados': row.get('aux_recovered'),
                    'faltantes_capturados': row.get('aux_missing', []),
                    'cierre_transitivo': 'NO_COMPROBADO'},
                FIELDS[10]: {'hallazgos_automaticos_heredados': row.get('issues', []),
                    'revision_manual': PENDING},
                FIELDS[16]: {'estado': 'Sin evolución individual justificada en este lote.',
                    'cambios_heredados': 'Consultar catálogo e historial; una diferencia de hash no prueba mejora funcional.'},
                FIELDS[17]: {'integridad_captura': evidence.get('capture_integrity_verified', False),
                    'inspeccion_estatica_automatica': evidence.get('automated_static_inspected', False),
                    'prueba_funcional': 'NO_COMPROBADO'},
                FIELDS[18]: {'original_path': row['original_path'],
                    'original_sha256': row['original_sha256'],
                    'candidate_sha256': row['portable_sha256'],
                    'staged_root': row['staged_root']},
                FIELDS[19]: {'instalacion': 'NO_INSTALADO',
                    'procedimiento': 'Staging selectivo en directorio nuevo mediante bundle_io; rollback verifica recibo y bytes antes de eliminar sólo esa copia.'},
                FIELDS[20]: {'estado': state, 'grado_inspeccion': 'AUTOMATED_STATIC_ONLY',
                    'whole_capability_verified': False,
                    'siguiente': evidence.get('next_action', PENDING)},
            })
        records.append({'id': number, 'stable_id': row['namespace'] + ':' + row['name'],
                        'evidence_dimensions': evidence, 'fields': dossier})
    return records


def write_records(output, records):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Dossier output must be new')
    output.mkdir(parents=True, exist_ok=False)
    for record in records:
        stem = f"{record['id']:04d}"
        (output / (stem + '.json')).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        text = f"# {stem} — {record['stable_id']}\n\n"
        text += ('Ficha de cobertura; consulte evidence_dimensions para distinguir '
                 'inspección automática, revisión manual y pruebas.\n\n')
        for key in FIELDS:
            text += f'## {key}\n\n' + json.dumps(record['fields'][key], ensure_ascii=False, indent=2) + '\n\n'
        (output / (stem + '.md')).write_text(text, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--manual', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-count', type=int, default=847)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    matrix = json.loads(args.matrix.read_text(encoding='utf-8'))['rows']
    manual = {int(k): v for k, v in json.loads(args.manual.read_text(encoding='utf-8')).items()}
    records = generate_records(catalog, matrix, manual, args.expected_count)
    write_records(args.output, records)
    print(json.dumps({'dossiers': len(records), 'manual': len(manual),
                      'scope': 'COVERAGE_RECORDS_NOT_847_DEEP_AUDITS'}))


if __name__ == '__main__':
    main()
