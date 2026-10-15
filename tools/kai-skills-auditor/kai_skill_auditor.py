#!/usr/bin/env python3
"""Offline, read-only source analyzer + candidate packager for a private skill catalog.

Never executes a skill, connects to providers, modifies active skill folders, or reads
secrets outside the input JSON archives explicitly supplied by the operator.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import zipfile

VERSION = '0.4.0'
NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
FILE_REF_RE = re.compile(r'(?<![a-zA-Z0-9_])(?:references|scripts|assets)/[\w./-]+')
URL_RE = re.compile(r'https?://[^\s<>\)\]"\']+')
FENCE_RE = re.compile(r'^\s*```', re.M)
SHELL_RISK_RE = re.compile(r'curl\s+[^\n|]+\|\s*(?:ba)?sh\b|rm\s+-rf\s+/\b|chmod\s+777\b', re.I)
SIDE_RE = re.compile(r'\b(send|delete|remove|publish|deploy|charge|purchase|refund|overwrite|book|push|commit|upload|post)\b', re.I)
PAY_RE = re.compile(r'\b(billing|cost|price|credits|paid|budget)\b', re.I)
AUTH_RE = re.compile(r'\b(mcp|connector|oauth|api|access token|api key|credential|service account)\b', re.I)
SECRET_HINT_RE = re.compile(r'\b(key|token|secret|password|credential)\b', re.I)
SECRET_GUARD_RE = re.compile(r'\b(redact|secrets manager|never log|do not log|secure storage|env var)\b', re.I)

STANDARDS = [
    'https://agentskills.io/specification',
    'https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md',
    'https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md',
]

CATEGORY_PATTERNS = [
    ('analytics', r'data|analytics|dashboard|metric|sql|kpi|spreadsheet|warehouse'),
    ('video', r'video|reel|render|animation|remotion|ugc'),
    ('visual', r'image|photo|design|graphic|canvas|poster|photoshop'),
    ('audio', r'music|audio|voice|sound|song|podcast'),
    ('engineering', r'code|git|developer|react|debug|test|build|sdk|app-builder|api-doc'),
    ('connectors', r'google|gmail|dropbox|sharepoint|calendar|drive|slack|notion|plugin'),
    ('research', r'research|search|paper|literature|academic|study'),
]
SPECIALIZED = {
    'analytics': 'comprobar linaje, granularidad, nulos, cálculos, reproducibilidad y confidencialidad',
    'video': 'comprobar duración, sincronización, licencias, formato, coste y continuidad entre planos',
    'visual': 'comprobar formato, dimensiones, consistencia visual, propiedad intelectual y exportación',
    'audio': 'comprobar formatos, derechos, idioma, voces, duración y límites del proveedor',
    'engineering': 'fijar entorno/dependencias, pruebas aisladas, regresiones, idempotencia y rollback',
    'connectors': 'verificar autorización, ámbitos OAuth, paginación, cuota, versión y confirmación de efectos',
    'research': 'comprobar fechas, fuentes primarias, citas, cobertura y separación entre hechos e hipótesis',
    'workflow': 'definir entradas, salidas, invariantes, límites, errores observables y recuperación',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean(value: str) -> str:
    return str(value or '')


def slug(value: str, maximum: int = 55) -> str:
    value = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return value[:maximum].rstrip('-') or 'unnamed'


def read_archives(source: Path) -> tuple[list[dict], list[str]]:
    rows = []
    errors = []
    for file in sorted(source.glob('skills_*.json')):
        try:
            raw = json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(raw, list):
                raise ValueError('not a list')
            for x in raw:
                if not isinstance(x, dict):
                    errors.append(f'{file.name}: invalid record')
                    continue
                row = dict(x)
                row['_archive_file'] = file.name
                rows.append(row)
        except (ValueError, OSError, UnicodeError) as exc:
            errors.append(f'{file.name}: {exc}')
    return rows, errors


def root_content(row: dict) -> str:
    entries = row.get('resources') or []
    uri = row.get('uri')
    root = next((x for x in entries if x.get('uri') == uri), None)
    if root is None:
        return ''
    return clean(root.get('content', ''))


def deduplicate(rows: list[dict], total: int) -> tuple[list[dict], list[dict], list[int]]:
    grouped = collections.defaultdict(list)
    for row in rows:
        index = row.get('index')
        if isinstance(index, int) and 1 <= index <= total:
            grouped[index].append(row)
    selected = []
    conflicts = []
    for index, candidates in sorted(grouped.items()):
        def rank(x: dict):
            content = root_content(x)
            return (bool(content), not bool(x.get('error')), len(content), x['_archive_file'])
        chosen = max(candidates, key=rank)
        selected.append(chosen)
        digests = {sha(root_content(x).encode('utf-8')) for x in candidates if root_content(x)}
        uris = {x.get('uri') for x in candidates}
        if len(uris) > 1 or len(digests) > 1:
            conflicts.append({'index': index, 'source_batches': [x['_archive_file'] for x in candidates],
                              'distinct_digests': sorted(digests), 'distinct_uris': sorted(map(str, uris))})
    return selected, conflicts, [i for i in range(1, total + 1) if i not in grouped]


def frontmatter(content: str) -> tuple[dict, list[str]]:
    if content.startswith('\ufeff'):
        content = content[1:]
    match = re.match(r'^---\r?\n([\s\S]*?)\r?\n---(?=\r?\n|$)', content)
    if not match:
        return {}, ['missing_yaml_frontmatter']
    text = match.group(1)
    parsed = {}
    problems = []
    try:
        import yaml  # Optional, commonly already available in Termux.
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            parsed = data
        else:
            problems.append('frontmatter_not_mapping')
    except ImportError:
        for key in ('name', 'description', 'license', 'compatibility'):
            found = re.search(r'^' + key + r':\s*(.*)$', text, re.M)
            if found:
                parsed[key] = found.group(1).strip().strip('"\'')
        problems.append('yaml_parser_unavailable_limited_validation')
    except Exception:
        problems.append('yaml_parse_error')
    return parsed, problems


def classify(label: str) -> str:
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, label, re.I):
            return category
    return 'workflow'


def audit(row: dict, conflicts: set[int]) -> dict:
    text = root_content(row)
    uri = clean(row.get('uri', ''))
    title = uri.rsplit('/', 1)[-1]
    fm, problems = frontmatter(text)
    name = clean(fm.get('name', ''))
    description = clean(fm.get('description', row.get('description', '')))
    lines = len(text.splitlines())
    label = title + ' ' + uri + ' ' + description
    category = classify(label)
    refs = sorted(set(FILE_REF_RE.findall(text)))[:150]
    urls = sorted(set(URL_RE.findall(text)))[:80]
    provider = bool(AUTH_RE.search(text))
    side_effects = bool(SIDE_RE.search(text))
    costly = bool(PAY_RE.search(text))
    tests = [
        f'Activación positiva explícita para {title}',
        f'No activación con una petición próxima pero fuera del alcance de {title}',
        'Simular dependencia ausente, fallo HTTP o acceso denegado sin repetir indefinidamente',
        f'Prueba de dominio: {SPECIALIZED[category]}',
    ]
    recommendations = [f'Revisar la especialidad {category}: {SPECIALIZED[category]}']
    if not text:
        problems.append('source_body_unavailable')
    if not name or len(name) > 64 or not NAME_RE.fullmatch(name):
        problems.append('invalid_or_missing_name')
        recommendations.append('Corregir metadatos NAME solo en candidato, preservando original')
    if name and name != title:
        problems.append('name_uri_discrepancy')
    if not description or len(description) > 1024:
        problems.append('invalid_description')
        recommendations.append('Redactar descripción de 1-1024 caracteres con alcance claro')
    if not re.search(r'\b(use when|when user|use this|cuando|si el usuario)\b', description, re.I):
        problems.append('trigger_needs_review')
        recommendations.append(f'Agregar 2 ejemplos positivos y 2 contraejemplos inequívocos para {title}')
    if lines > 500:
        problems.append('oversized_primary_skill')
        recommendations.append(f'Pasar secciones extensas de {title} a referencias de lectura progresiva')
    if refs:
        problems.append('auxiliary_files_unverified')
        recommendations.append(f'Comprobar las {len(refs)} rutas locales citadas y conservarlas con hashes')
    if urls:
        problems.append('external_references_freshness_unverified')
        recommendations.append('Revisar fechas, versiones oficiales y enlaces de documentación externos')
    if provider:
        problems.append('external_provider_or_auth_dependency')
        recommendations.append(f'Contrato de {title}: permisos mínimos, preflight, expiración de tokens y fallo seguro')
    if side_effects:
        tests.append('Ejecutar caso sintético de dry-run y verificación de STOP antes de efectos')
        recommendations.append('Añadir vista previa, autorización, idempotencia, STOP y reversión')
        if not re.search(r'\b(confirm|approv|consent|permission|autoriz)\w*', text, re.I):
            problems.append('approval_guard_not_evident')
        if not re.search(r'rollback|revert|restore|back.?up', text, re.I):
            problems.append('rollback_not_evident')
    if costly:
        tests.append('Prueba de límite de coste y cancelación sin consumir créditos reales')
        if not re.search(r'\b(limit|budget|cap|maximum|estimate|threshold)\b', text, re.I):
            problems.append('cost_guard_not_evident')
        recommendations.append('Solicitar presupuesto y límite de créditos antes de invocar un proveedor de pago')
    if SECRET_HINT_RE.search(text) and not SECRET_GUARD_RE.search(text):
        problems.append('secret_handling_needs_review')
        recommendations.append('No persistir secretos en logs, ejemplos, commits ni paquetes compartidos')
    if SHELL_RISK_RE.search(text):
        problems.append('potentially_risky_shell_example')
        recommendations.append('Reemplazar ejemplos destructivos por alternativas verificables con ruta explícita')
    if row.get('index') in conflicts:
        problems.append('multiple_source_revisions_detected')
        recommendations.append('Conciliar hashes distintos de copias antes de declarar versión actual')
    if not re.search(r'\b(test|verify|validat|check|assert|prueba|comprob)\w*', text, re.I):
        problems.append('verification_evidence_not_evident')
    data = {
        'index': row['index'], 'uri': uri, 'name': title,
        'declared_name': name, 'description': description,
        'category': category, 'source_archive': row['_archive_file'],
        'original_sha256': sha(text.encode('utf-8')), 'original_chars': len(text),
        'original_lines': lines, 'original_resources_returned': len(row.get('resources') or []),
        'references_mentioned': refs, 'external_urls_mentioned': urls,
        'provider_bound_heuristic': provider, 'possible_side_effects_heuristic': side_effects,
        'cost_related_heuristic': costly, 'yaml_frontmatter_fields': sorted(map(str, fm)),
        'issues': sorted(set(problems)), 'recommendations': list(dict.fromkeys(recommendations)),
        'test_cases_to_run': tests, 'state': 'root_instructions_automatically_reviewed',
        'functional_test': 'not_executed', 'upstream_upgrade': 'not_verified',
        'candidate_status': 'draft_only_not_installed',
    }
    return data


def pack_path(row: dict) -> str:
    uri = row.get('uri', '')
    parts = uri.split('/')
    provider = slug(parts[3] if len(parts) > 3 else 'unknown')
    skill = slug(parts[-1])
    return f'{provider}/{row["index"]:04d}-{skill}'


def draft(content: str, finding: dict) -> str:
    # Candidate copies are not described as verified functional upgrades.
    # Append only a fenced proposal as a Markdown comment; this preserves the
    # original operational instructions and makes this draft non-authoritative.
    appendix = '\n\n<!-- KAI vNEXT CANDIDATE: UNVERIFIED. This is a private review draft. -->\n'
    appendix += '\n## KAI · Lista de validación pendiente (no ejecutada)\n\n'
    appendix += '- Guardar original, comprobar permisos y mantener STOP y recuperación.\n'
    appendix += '- Confirmar versiones y documentación oficial antes de usar el proveedor.\n'
    for item in finding['recommendations'][:12]:
        appendix += '- PROPUESTA, NO VERIFICADA: ' + item.replace('\n', ' ') + '\n'
    return content.rstrip() + appendix


def report_markdown(findings: list[dict], missing: list[int], conflicts: list[dict], expected: int = 847) -> str:
    titles = collections.Counter(x['category'] for x in findings)
    issues = collections.Counter(y for x in findings for y in x['issues'])
    lines = ['# KAI Skills · Auditoría individual · v0.4', '',
             '**Alcance:** lectura automática de las instrucciones raíz disponibles. No se han ejecutado tests',
             'de terceros, no se han actualizado versiones oficiales ni desplegado skills activas.', '',
             f'- Cobertura: {len(findings)}/{expected}.', f'- Huecos: {missing}.',
             f'- Conflictos de revisiones: {len(conflicts)}.',
             '- Categorías: ' + ', '.join(f'{k}={v}' for k,v in sorted(titles.items())),
             '- Problemas indicativos frecuentes: ' + ', '.join(f'{k}={v}' for k,v in issues.most_common(12)),
             '', f'## Auditorías 1 a {expected}', '']
    for x in findings:
        lines += [f'### {x["index"]:04d}. {x["name"]}', '',
                  f'- Origen: `{x["uri"]}`. SHA-256 raíz: `{x["original_sha256"]}`.',
                  f'- Qué hace: {x["description"]}',
                  f'- Grupo: {x["category"]}. {x["original_lines"]} líneas; {x["original_resources_returned"]} recursos visibles.',
                  f'- Revisión: {", ".join(x["issues"]) or "sin alertas sintácticas heurísticas"}.',
                  '- Mejora propuesta: ' + '; '.join(x['recommendations']),
                  '- Prueba pendiente: ' + '; '.join(x['test_cases_to_run']),
                  '- Estado: copia propuesta, **NO instalada ni validada funcionalmente**.', '']
    return '\n'.join(lines)


def make_zip(out: Path, source: Path, originals: list[dict], findings: list[dict], conflicts: list[dict],
             missing: list[int], read_errors: list[str], include_originals: bool, expected: int = 847) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    report = report_markdown(findings, missing, conflicts, expected)
    (out/'AUDITORIA_847.md').write_text(report, encoding='utf-8')
    (out/'auditoria_847.json').write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'CONFLICTOS_DE_ORIGEN.json').write_text(json.dumps(conflicts, ensure_ascii=False, indent=2), encoding='utf-8')
    with (out/'auditoria_847.csv').open('w', newline='', encoding='utf-8-sig') as file:
        names = ['index','uri','name','category','original_sha256','original_lines','state','functional_test','upstream_upgrade','issues']
        writer=csv.DictWriter(file, fieldnames=names)
        writer.writeheader()
        for x in findings:
            writer.writerow({k: ';'.join(x[k]) if isinstance(x.get(k),list) else x.get(k,'') for k in names})
    manifest = {'version':VERSION,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                'total_expected':expected,'total_reviewed':len(findings),'missing':missing,
                'conflicts':len(conflicts),'input_archive_errors':read_errors,
                'executed_code_from_skills':False,'installed_to_active_paths':False,
                'files':[], 'reference_urls':STANDARDS,
                'release_state':'CANDIDATE_ONLY_NOT_TESTED_BEHAVIOR',
                'important':'Only root instructions are backed up. Referenced scripts/assets may be unavailable.'}
    target=out/'KAI_SKILLS_847_PRIVATE_CANDIDATE.zip'
    seen=set()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        def append(name: str, data: bytes):
            if name in seen: raise ValueError('duplicate zip path: '+name)
            seen.add(name)
            archive.writestr(name, data)
            manifest['files'].append({'path':name,'sha256':sha(data),'bytes':len(data)})
        for name in ['AUDITORIA_847.md', 'auditoria_847.json', 'auditoria_847.csv', 'CONFLICTOS_DE_ORIGEN.json']:
            append(name, (out/name).read_bytes())
        for row, finding in zip(originals, findings):
            content=root_content(row)
            prefix=pack_path(row)
            append(f'reviews/{prefix}/KAI_REVIEW.json',json.dumps(finding, ensure_ascii=False, indent=2).encode())
            if include_originals and content:
                append(f'originals/{prefix}/SKILL.md',content.encode())
                # A review draft is intentionally not an installed, validated new release.
                append(f'candidates/{prefix}/SKILL.md',draft(content, finding).encode())
        append('MANIFEST.json', json.dumps(manifest,ensure_ascii=False,indent=2).encode())
    with zipfile.ZipFile(target) as reader:
        if reader.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        if len(reader.namelist()) != len(set(reader.namelist())):
            raise ValueError('Duplicate ZIP paths')
        inside=json.loads(reader.read('MANIFEST.json'))
        for rec in inside['files']:
            if sha(reader.read(rec['path'])) != rec['sha256']:
                raise ValueError('Manifest mismatch: ' + rec['path'])
    (out/'ZIP_SHA256.txt').write_text(f'{sha(target.read_bytes())}  {target.name}\n',encoding='utf-8')
    (out/'RESULTADO.json').write_text(json.dumps({
        'zip':str(target), 'zip_sha256':sha(target.read_bytes()),'zip_bytes':target.stat().st_size,
        'count':len(findings),'missing':missing,'conflicts':len(conflicts),
        'zip_crc':'PASS','manifest_integrity':'PASS', 'candidate_only':True,
        'functional_tests':'NOT_RUN','auxiliary_resources':'NOT_FULLY_EXPORTED',
    },ensure_ascii=False,indent=2), encoding='utf-8')
    return {'zip':str(target),'sha256':sha(target.read_bytes()),'count':len(findings),
            'missing':missing,'conflicts':len(conflicts),'zip_crc':'PASS'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Consolidación segura de 847 skills ya extraídas')
    parser.add_argument('--source',type=Path,required=True,help='Directorio de JSON previamente capturados')
    parser.add_argument('--out',type=Path,required=True,help='Nuevo directorio de laboratorio (nunca un directorio de skills activo)')
    parser.add_argument('--expected',type=int,default=847)
    parser.add_argument('--reports-only', action='store_true',help='No incluir cuerpos originales/candidatos')
    args=parser.parse_args(argv)
    if args.expected < 1:
        parser.error('Expected count must be positive')
    source=args.source.expanduser().resolve()
    out=args.out.expanduser().resolve()
    if not source.is_dir():
        parser.error('Input source missing')
    if source == out or source in out.parents or out in source.parents:
        parser.error('Input and output must be disjoint folders')
    if any(part in {'.agents','.claude','.codex'} for part in out.parts):
        parser.error('Never write audit outputs into a live skill tree')
    if out.exists():
        parser.error('Output must be a new, non-existing directory')
    rows, read_errors=read_archives(source)
    for row in rows:
        index = row.get('index')
        uri = row.get('uri')
        resources = row.get('resources')
        if type(index) is not int or not 1 <= index <= args.expected:
            read_errors.append(f'Invalid or out-of-range index: {index!r}')
        if not isinstance(uri, str) or not re.fullmatch(r'skills?://plugins/[^/\s]+/[^/\s]+', uri):
            read_errors.append(f'Invalid source identity at index {index!r}')
        if not isinstance(resources, list) or any(not isinstance(x, dict) for x in resources):
            read_errors.append(f'Invalid resources at index {index!r}')
            row['resources'] = []
        roots = [x for x in row['resources'] if x.get('uri') == uri]
        if len(roots) != 1 or not isinstance(roots[0].get('content'), str) or not roots[0]['content'].strip():
            read_errors.append(f'Exact root content unavailable/ambiguous at index {index!r}')
        if any(isinstance(x.get('content'), str) and '\x00' in x['content'] for x in row['resources']):
            read_errors.append(f'NUL byte in source at index {index!r}; no silent rewrite')
    if read_errors:
        print(json.dumps({'version':VERSION,'status':'BLOCKED_INPUT','input_file_errors':read_errors},ensure_ascii=False,indent=2))
        return 2
    originals, conflicts, missing=deduplicate(rows,args.expected)
    identities = [x['uri'] for x in originals]
    if conflicts or missing or len(set(identities)) != len(identities):
        print(json.dumps({'version':VERSION,'status':'BLOCKED_RECONCILIATION','conflicts':conflicts,'missing':missing,
                          'duplicate_identities':len(identities)-len(set(identities))},ensure_ascii=False,indent=2))
        return 2
    findings=[audit(x,{c['index'] for c in conflicts}) for x in originals]
    result=make_zip(out,source,originals,findings,conflicts,missing,read_errors,not args.reports_only,args.expected)
    result['source_rows']=len(rows)
    result['input_file_errors']=read_errors
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if len(findings)==args.expected and not read_errors else 2

if __name__=='__main__':
    sys.exit(main())
