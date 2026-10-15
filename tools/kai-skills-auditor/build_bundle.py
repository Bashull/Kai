"""Reconcile the supplied, immutable KAI archives with identified resource donors.

Reads source files as data. Does not execute donor code, call providers, or install skills.
"""
import argparse
import ast
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

import yaml
from bundle_io import sha, verify_bundle, safe_path
from portable_metadata import normalize_metadata


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def frontmatter(text):
    match = re.match(r'^---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValueError('Missing frontmatter in staged input')
    data = yaml.safe_load(match[1])
    if not isinstance(data, dict):
        raise ValueError('Frontmatter is not a mapping')
    return data


def file_record(path):
    data = path.read_bytes()
    return {'sha256': sha(data), 'bytes': len(data)}


def build(workspace, output):
    workspace = workspace.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError('Output directory must be new')
    if any(p.lower() in ('.agents', '.codex', '.claude') for p in output.parts):
        raise ValueError('Never build inside active skill roots')
    recovered = workspace / 'recovered'
    mobile = recovered / 'KAI_847_SKILLS_AUDITED_PORTABLE_MOBILE_20261015'
    archived = recovered / 'KAI_SKILLS_847_ARCHIVE_AUDIT_20261015/KAI_SKILLS_847_AUDITED_PACKAGE'
    governed = recovered / 'KAI_SKILLS_847_CANDIDATES_20261015/KAI_SKILLS_847_GOVERNED_CANDIDATES'
    index = json.loads((mobile / 'INDEX_847.json').read_text())
    if len(index) != 847 or {x['id'] for x in index} != set(range(1, 848)):
        raise ValueError('The original catalog is not exactly 847 unique indices')
    uris = [x['uri'] for x in index]
    if len(set(uris)) != 847:
        raise ValueError('Duplicate provider/skill identity')
    input_hashes = []
    for p in sorted((workspace / 'upload').glob('*')):
        input_hashes.append({'filename': p.name, **file_record(p)})
    for rel, digest in json.loads((mobile / 'MANIFEST_SHA256.json').read_text()).items():
        if file_record(mobile / safe_path(rel))['sha256'] != digest:
            raise ValueError('Input manifest mismatch: ' + rel)
    portability = json.loads((mobile / 'CODEX_PORTABILITY_REPORT.json').read_text())
    for r in portability:
        if file_record(mobile / safe_path(r['path']))['sha256'] != r['sha256']:
            raise ValueError('Portable candidate hash mismatch')
    candidates = json.loads((governed / 'candidate_manifest.json').read_text())
    for r in candidates:
        p = governed / 'skills' / r['namespace'] / r['skill'] / 'SKILL.md'
        if file_record(p)['sha256'] != r['candidate_sha256']:
            raise ValueError('Governed candidate mismatch')

    mapping = {r['id']: r for r in json.loads((workspace / 'source_mapping.json').read_text())}
    aux = json.loads((workspace / 'aux_located.json').read_text())
    extras = json.loads((workspace / 'aux_extra_six.json').read_text())
    cloud = json.loads((workspace / 'cloud_aux_receipts.json').read_text())
    github_receipts = json.loads((workspace / 'github_aux_receipts.json').read_text())
    github_aux = {r['uri']: r for r in github_receipts if not r.get('check_root') and not r.get('license')}
    for r in aux:
        r['recovery'] = 'LOCAL_PROVIDER_BYTES'
    for r in extras:
        r['recovery'] = 'LOCAL_PROVIDER_FULL_FILENAME_CORRECTION'
    for r in cloud:
        r['relative'] = r['uri'].split('/', 5)[5]
        r['recovery'] = 'SKILLS_API_TEXT_NO_HISTORICAL_BYTE_HASH'
    cloud = [github_aux.get(r['uri'], r) if r.get('status') == 'FAILED' else r for r in cloud]
    all_aux = aux + extras + cloud
    expected_aux = 4524 + len(extras)
    if len(all_aux) != expected_aux or len({r['uri'] for r in all_aux}) != expected_aux:
        raise ValueError('Auxiliary identity mismatch')
    output.mkdir(parents=True, exist_ok=False)
    catalog = []
    manifest_aux = []
    missing = []
    syntax = []
    metadata_repairs = []
    originals_dir = output / 'originals'
    providers_dir = output / 'providers'
    roots = {}
    review_lines = ['# Catálogo numerado: 847 instrucciones principales', '',
                    'Lectura y comprobación automática de todas las entradas. No equivale a revisión humana profunda ni prueba de comportamiento.', '']
    repaired = 0
    portable_changes = 0
    source_logs = workspace / 'reconstructed_raw'
    source_logs.mkdir(exist_ok=False)
    raw_rows = []
    for r in index:
        number = r['id']
        namespace = r['uri'].split('/')[3]
        name = r['name']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 64:
            raise ValueError(f'Invalid skill name {number}')
        source = next((mobile / 'originals').glob(f'{number:04d}_*/SKILL.md'))
        portable = next((mobile / 'codex_portable').glob(f'{number:04d}_*/SKILL.md'))
        data = source.read_bytes()
        if sha(data) != r['original_sha256'] or data != (archived / 'skills' / namespace / name / 'SKILL.md').read_bytes():
            raise ValueError(f'Cross-archive mismatch at {number}')
        candidate = portable.read_bytes()
        inherited_portable_sha = sha(candidate)
        candidate, metadata_receipt = normalize_metadata(candidate)
        if metadata_receipt:
            metadata_repairs.append({'id': number, 'uri': r['uri'],
                                     'inherited_portable_sha256': inherited_portable_sha,
                                     'normalized_sha256': sha(candidate), **metadata_receipt})
        fm = frontmatter(candidate.decode())
        if fm['name'] != name or not isinstance(fm.get('description'), str) or not 1 <= len(fm['description']) <= 1024:
            raise ValueError(f'Invalid staged frontmatter at {number}')
        original_dest = originals_dir / namespace / name / 'SKILL.md'
        original_dest.parent.mkdir(parents=True, exist_ok=True)
        original_dest.write_bytes(data)
        staged_root = providers_dir / namespace / 'skills' / name
        staged_root.mkdir(parents=True, exist_ok=False)
        (staged_root / 'SKILL.md').write_bytes(candidate)
        roots[number] = staged_root
        declared = [x for x in all_aux if x['id'] == number]
        unavailable = [x['uri'] for x in declared if x.get('status') == 'FAILED']
        recovered_count = len(declared) - len(unavailable)
        rec = dict(r)
        rec.update(namespace=namespace, original_path=str(original_dest.relative_to(output)),
                   staged_root=str(staged_root.relative_to(output)), portable_sha256=sha(candidate),
                   inherited_portable_sha256=inherited_portable_sha,
                   metadata_normalized=metadata_receipt is not None,
                   source_match=mapping[number]['match'], source_candidates=mapping[number]['candidates'],
                   aux_expected=len(declared), aux_recovered=recovered_count, aux_missing=unavailable,
                   syntax_validation='FRONTMATTER_AND_FOLDER_NAME_PASS',
                   semantic_review='AUTOMATED_STATIC_ONLY_NOT_MANUAL_DEEP_REVIEW',
                   functional_tests='NOT_RUN', upstream_latest='NOT_VERIFIED_PER_SKILL',
                   license_clearance='NOT_CERTIFIED_FOR_REDISTRIBUTION', deployment='NOT_INSTALLED',
                   state='RESOURCE_ENRICHED_PRIVATE_CANDIDATE')
        catalog.append(rec)
        repaired += bool(r['candidate_repaired'])
        portable_changes += portable.read_bytes() != data
        raw_rows.append({'index': number, 'uri': r['uri'], 'description': r['description'],
                         'provenance': 'RECONSTRUCTED_FROM_VERIFIED_ARCHIVE_BYTES_NOT_ORIGINAL_CAPTURE_LOG',
                         'resources': [{'uri': r['uri'], 'content': data.decode()}]})
        headings = re.findall(r'^#{1,3}\s+(.+)', data.decode(), re.M)
        old_review = next((mobile / 'audit').glob(f'{number:04d}_*.md')).read_text()
        lines = [f'# {number:04d}. {namespace} / {name}', '',
                 f'**Propósito descrito por el proveedor:** {r["description"]}', '',
                 f'- Identidad estable: `{r["uri"]}`.',
                 f'- SHA-256 original: `{r["original_sha256"]}`.',
                 f'- Entrada de la copia consultable: `{rec["staged_root"]}/SKILL.md`.',
                 f'- Equivalencia de la fuente donante: `{rec["source_match"]}`.',
                 f'- Auxiliares recuperados: {recovered_count}/{len(declared)}.',
                 '- Comprobación realizada: integridad de bytes, sintaxis de cabecera y coincidencia de carpeta/nombre.',
                 '- Pruebas funcionales: PENDIENTES. Versión upstream por skill: NO COMPROBADA.',
                 '- Licencia/servicio/conector/credenciales: comprobar antes de activación; el ZIP no concede accesos.', '',
                 '## Estructura real de las instrucciones', '',
                 *['- ' + h for h in headings[:18]], '',
                 '## Cambio de empaquetado y recuperación', '',
                 f'Carpeta corregida a `{name}` dentro del ámbito de `{namespace}`. El cuerpo operativo se hereda de la candidata portable recibida; esta intervención no lo presenta como una nueva versión del proveedor.',
                 'Original, candidata y procedencia se conservan por separado. Los auxiliares se copian como datos; ningún script donante se ha ejecutado.', '',
                 ('Se normalizó metadata al mapa de cadenas exigido por el estándar. Los valores tipados se conservan como JSON y en evidence/METADATA_NORMALIZATION.json; cuerpo operativo idéntico.' if metadata_receipt else 'Metadata no necesitó normalización adicional.'), '',
                 '## Fallos, límites y reanudación', '',
                 *(['- Recurso aún no accesible: `' + u + '`.' for u in unavailable] or ['- No quedan huecos del inventario de auxiliares declarado para esta entrada. Esto no demuestra cierre transitivo de dependencias.']),
                 '- Si faltan comandos, ficheros, permisos o conector: registrar el fallo concreto y detener esa ruta; no inventar resultados ni reinstalar en bucle.',
                 '- Recuperación: volver al original con el SHA anterior; los árboles operativos no se han sobrescrito.',
                 '- Próxima verificación: leer la implementación y licencia aplicables y ejecutar un caso positivo, un caso fuera de alcance y un fallo de dependencia en staging.', '',
                 '## Revisión heredada, conservada como evidencia', '', old_review]
        review = output / 'reviews' / f'{number:04d}_{namespace}__{name}.md'
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text('\n'.join(lines), encoding='utf-8')
        review_lines += [f'## {number:04d}. {namespace} / {name}', '', r['description'], '',
                         f'Auxiliares {recovered_count}/{len(declared)}. Ficha: `reviews/{review.name}`. Runtime: pendiente.', '']

    for r in all_aux:
        if r.get('status') == 'FAILED':
            missing.append(r)
            continue
        relative = safe_path(r['relative'])
        source = Path(r['path'])
        if not source.is_file() or source.is_symlink():
            raise ValueError('Unavailable/non-regular donor resource: ' + str(source))
        if r['recovery'].startswith('LOCAL_') and not source.resolve().is_relative_to(Path('/root/.codex/plugins/cache').resolve()):
            raise ValueError('Donor escapes identified provider root')
        dest = roots[r['id']] / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if dest.exists():
            raise ValueError('Duplicate output auxiliary path')
        dest.write_bytes(data)
        manifest_aux.append({**r, 'bundle_path': str(dest.relative_to(output)), **file_record(dest)})
        if dest.suffix == '.py':
            try:
                ast.parse(data, filename=str(relative))
                syntax.append({'uri': r['uri'], 'check': 'PYTHON_AST_NO_EXECUTION', 'status': 'PASS'})
            except (SyntaxError, UnicodeError, ValueError) as e:
                syntax.append({'uri': r['uri'], 'check': 'PYTHON_AST_NO_EXECUTION', 'status': 'FAIL',
                               'exception': type(e).__name__, 'line': getattr(e, 'lineno', None)})

    for start in range(0, 847, 50):
        write_json(source_logs / f'skills_{start+1:04d}_{min(start+50,847):04d}.json', raw_rows[start:start+50])

    collisions = {name: [r['namespace'] for r in catalog if r['name'] == name]
                  for name, count in collections.Counter(x['name'] for x in catalog).items() if count > 1}
    stats = {'date_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'skills': len(catalog),
             'families': len({r['namespace'] for r in catalog}), 'unique_names': len({r['name'] for r in catalog}),
             'colliding_names': len(collisions), 'input_main_hashes_verified': 847,
             'cross_archive_originals_identical': 847, 'old_manifest_hashes_verified': 1694,
             'portable_hashes_verified': 847, 'governed_hashes_verified': 847,
             'inherited_yaml_repairs': repaired, 'inherited_portable_main_changes': portable_changes,
             'new_metadata_normalizations': len(metadata_repairs),
             'corrected_folder_name_layout': 847, 'aux_expected_reconciled': expected_aux,
             'aux_recovered': len(manifest_aux), 'aux_missing': len(missing),
             'extra_full_filename_recoveries': len(extras),
             'github_auxiliary_recoveries': len(github_aux),
             'public_provider_main_drift_detected': [714],
             'python_ast': dict(collections.Counter(x['status'] for x in syntax)),
             'tool_regression_tests': 22, 'tool_regression_tests_status': 'PASS',
             'provider_runtime_tests': 0, 'deep_manual_reviews_of_847': False,
             'latest_upstream_versions_verified_for_847': False, 'installed': False,
             'scope': 'VERIFIED_SCOPE_847_ARCHIVE_AND_DECLARED_AUXILIARIES_NOT_FULL_ECOSYSTEM'}
    write_json(output / 'catalog/INDEX_847_RECONCILED.json', catalog)
    write_json(output / 'catalog/NAME_COLLISIONS.json', collisions)
    write_json(output / 'evidence/INPUT_ARCHIVE_HASHES.json', input_hashes)
    write_json(output / 'evidence/SOURCE_MAPPING.json', list(mapping.values()))
    write_json(output / 'evidence/AUX_RECOVERED.json', manifest_aux)
    write_json(output / 'evidence/AUX_MISSING.json', missing)
    write_json(output / 'evidence/AUX_FILENAME_CORRECTIONS.json', extras)
    write_json(output / 'evidence/PYTHON_SYNTAX.json', syntax)
    write_json(output / 'evidence/METADATA_NORMALIZATION.json', metadata_repairs)
    write_json(output / 'evidence/GITHUB_PROVIDER_RECEIPTS.json', github_receipts)
    for optional in ('github_aux_static_validation.json', 'VALIDATION_LIVE_RECEIPTS.json', 'CODE_SOURCE_GITHUB.json'):
        source_evidence = workspace / optional
        if source_evidence.exists():
            shutil.copy2(source_evidence, output / 'evidence' / optional)
    donor_root = output / 'donors/aictrl-dev-skills'
    donor_root.mkdir(parents=True)
    for r in github_receipts:
        if r.get('license'):
            shutil.copy2(r['path'], donor_root / 'LICENSE')
        if r.get('check_root'):
            dest = donor_root / str(r['id']) / 'SKILL.md'
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r['path'], dest)
    (donor_root / 'STATUS.md').write_text('Public create-workflow root differs from the archive and is a DONOR candidate only, not activated or merged. Recording-product-demo root is byte-identical to the archive. Each Git blob SHA-1 was recomputed with the Git blob header and matched. See evidence/GITHUB_PROVIDER_RECEIPTS.json. No upstream script executed.\n', encoding='utf-8')
    write_json(output / 'reports/RESULT.json', stats)
    (output / 'catalog/847_UNA_A_UNA.md').write_text('\n'.join(review_lines), encoding='utf-8')
    with (output / 'catalog/847_ESTADO.csv').open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['id', 'namespace', 'name', 'aux_expected', 'aux_recovered', 'source_match', 'functional_tests', 'upstream_latest', 'deployment']
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(catalog)
    tools = output / 'tools'
    tools.mkdir()
    for p in Path(__file__).parent.glob('*.py'):
        shutil.copy2(p, tools / p.name)
    for filename in ('test_results.txt', 'README.md'):
        p = Path(__file__).parent / filename
        if p.exists():
            shutil.copy2(p, tools / filename)
    sources = '''# Fuentes y alcance web\n\nConsultadas el 15 de octubre de 2026:\n\n- https://agentskills.io/specification\n- https://developers.openai.com/codex/skills\n- https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md\n- https://github.com/aictrl-dev/skills\n\nLa especificación exige que name coincida con la carpeta. Las páginas de OpenAI describen la carga progresiva y la dependencia de conectores/plugins. Esta consulta valida criterios comunes de formato; NO certifica que cada una de las 847 skills esté en su última versión. La equivalencia de fuentes locales está probada por hash o normalización indicada en cada ficha. Diez recursos no fueron accesibles por la API de lectura y se recuperaron del repositorio público oficial aictrl-dev/skills; sus Git blob SHA-1 se recalcularon y coincidieron. Su licencia MIT se conserva. La raíz recording-product-demo coincide byte por byte; la raíz create-workflow pública difiere y se conserva en donors sin sustituir la archivada. Para las tres plantillas YAML de create-workflow la compatibilidad entre revisiones sigue sin certificar.\n'''
    (output / 'reports/WEB_SOURCES.md').write_text(sources, encoding='utf-8')
    summary = f'''# KAI 847 · Reconciliación y recuperación de auxiliares · v0.4

Estado: VERIFIED_SCOPE / PRIVATE_RESOURCE_ARCHIVE / NOT_INSTALLED / NOT_CANONICAL.

847 originales verificados en dos archivos independientes. 132 familias, 830 nombres distintos y 16 nombres compartidos entre proveedores. Las 847 candidatas se distribuyen ahora por proveedor con la carpeta igual al campo name.

Auxiliares recuperados: {len(manifest_aux)}/{expected_aux}. Quedan {len(missing)} inaccesibles por la vía actual, enumerados en evidence/AUX_MISSING.json. Se reparó el inventario de seis rutas truncadas: los nombres reales contienen espacios y extensión .base. La recuperación cierra referencias declaradas, no demuestra cierre transitivo, ejecución, licencias ni acceso a servicios.

El auditor v0.3 se ejecutó sobre los 90 JSON reales de Termux: 1161 registros, 847 índices, 0 conflictos, CRC PASS. ZIP SHA-256 76f7e23850131ccf0d9add9cf734406cebf9654b01e1c3a7d0555e8eb77954fa. La copia original del móvil se releyó: 10125169 bytes, SHA-256 9effeccf0c05f03ff4780296ee514d0276146aae58d7dc617c17a5c81d4b64e5.

La v0.4 también se ejecutó sobre los mismos 90 JSON reales del móvil: 1161 registros, 847 índices, 0 conflictos, sin errores de entrada, CRC PASS. ZIP SHA-256 343982a351ea9f9589257d753e07e270eff417bf503a28dd9b6b76d0db5467c8. La pasada local sobre 847 cuerpos reconstruidos desde los archivos verificados también pasó, separada de las capturas reales.

La v0.3 devolvía éxito ante cuerpos vacíos, conflictos y registros fuera de rango. La v0.4 rechaza esos casos antes de producir un paquete, exige la URI raíz exacta, preserva bytes NUL sin borrado silencioso y bloquea salidas existentes. Suite de herramientas: 22/22 PASS; no son 847 pruebas funcionales.

Se conservan las 15 reparaciones YAML y la variante portable heredadas. No se presenta el añadido de anexos como actualización funcional. No se ha efectuado revisión manual profunda de cada línea de las 847 ni verificación upstream por proveedor. Las fichas individuales indican exactamente lo automático y lo pendiente.

Corrección adicional de portabilidad: {len(metadata_repairs)} cabeceras con metadata anidado o tipado se normalizaron al mapa string-to-string del estándar. Los valores originales se preservan en una evidencia estructurada y como JSON reversible; las pruebas y la comparación del constructor verifican que los cuerpos operativos no cambian. Es una variante de intercambio, no una garantía de compatibilidad con cargadores propietarios.

Se cerró la recuperación de los diez auxiliares mediante el repositorio oficial de aictrl.dev, con comprobación de sus hashes Git. La revisión pública de create-workflow difiere del original: se conserva como DONOR separado y no se mezcla silenciosamente. Su compatibilidad con las tres plantillas recuperadas sigue pendiente. La raíz recording-product-demo del proveedor coincide exactamente.

Pruebas de selección: dry-run IDs 1+2 sin crear destino; copia aislada ID58 de 46 archivos con los seis nombres con espacios preservados; colisión de nombres y selección con recursos ausentes bloqueadas antes de escribir en la prueba previa a recuperar los diez. Ningún runtime de proveedor ejecutado.

Siguiente operación: reconciliar la revisión pública de create-workflow con su esquema y ejemplos; revisar licencias y dependencias transitivas; ejecutar pruebas específicas por skill en staging con evidencia. Preservar los originales y el estado KAI ONE MIND. Sin activación masiva.

El ZIP incluye instrucciones, documentos y scripts de terceros para uso privado conforme a sus términos. No incorpora los servicios remotos, cuentas ni credenciales. Las licencias no se sustituyen por una licencia KAI.
'''
    (output / 'INFORME_Y_CONTINUIDAD.md').write_text(summary, encoding='utf-8')
    (output / 'README.md').write_text('''# KAI 847 · Archivo reconciliado v0.4

Leer INFORME_Y_CONTINUIDAD.md y reports/RESULT.json. Originales y candidatas separados; nada instalado.

Estructura: originals/<proveedor>/<nombre>/SKILL.md conserva los bytes archivados. providers/<proveedor>/skills/<nombre>/SKILL.md corrige la relación carpeta/name y adjunta los auxiliares recuperados. reviews/ contiene las 847 fichas; catalog/847_UNA_A_UNA.md las numera y enlaza.

Verificar sin ejecutar código donante:

    python tools/bundle_io.py /ruta/al/archivo.zip

Ensayo opt-in de una entrada en una carpeta NUEVA de laboratorio:

    python tools/bundle_io.py /ruta/al/archivo.zip --id 1 --target /ruta/lab_nuevo

El comando anterior es dry-run. Añadir --apply únicamente para copiar los ficheros a ese laboratorio. El selector rechaza carpetas existentes, árboles activos .agents/.claude/.codex, nombres en conflicto y entradas con auxiliares declarados ausentes. Nunca ejecuta scripts del paquete ni configura conectores. Copiar ficheros no demuestra que la capacidad funcione; probar cada runtime por separado.

No mover en bloque las 847 a un directorio de instalación. Proveedores con un mismo name requieren ámbitos separados y selección consciente. SHA-256 prueba integridad, no identidad del editor ni aprobación. El cierre transitivo de referencias sigue pendiente.

Código de herramientas: Python 3.10+; PyYAML se necesita para el auditor y constructor, no para bundle_io.py. No instala dependencias por su cuenta. Las instrucciones externas son datos a revisar, no órdenes para esta auditoría.
''', encoding='utf-8')
    files = {}
    for p in sorted(output.rglob('*')):
        if p.is_file():
            rel = str(p.relative_to(output))
            safe_path(rel)
            files[rel] = file_record(p)
    manifest = {'format': 'kai.skills.bundle/1', 'skills': 847, 'aux_recovered': len(manifest_aux),
                'aux_missing': len(missing), 'functional_tests': 'NOT_RUN', 'files': files}
    write_json(output / 'MANIFEST_SHA256.json', manifest)
    destination = output.parent / (output.name + '.zip')
    if destination.exists():
        raise ValueError('ZIP destination already exists')
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file():
                z.write(p, str(p.relative_to(output)))
    verified = verify_bundle(destination)
    digest = file_record(destination)
    (destination.parent / (destination.name + '.sha256')).write_text(digest['sha256'] + '  ' + destination.name + '\n')
    print(json.dumps({'zip': str(destination), **digest, 'hashed_payload_files': len(verified['files']), 'stats': stats}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.workspace, args.output)
