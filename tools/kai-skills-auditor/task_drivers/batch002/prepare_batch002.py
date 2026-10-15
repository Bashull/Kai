"""Task-specific evidence overlay; reuse verified Batch001, never recreate originals."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'toolkit_vnext'))
from audit_records import FIELDS, generate_records, write_records
import bundle_io as b

BASE = ROOT / 'lote001_recovered/complete/payload/KAI_SKILLS_FORGE_BATCH001_CANDIDATE_20261015.zip'
BASE_SHA = '670a8a697d4fc6badc1db22dbcbea6868c1cdbd3cffd050a351319eaf4b9f010'
PIN = 'd4b42bf96f550e427a16a5ac7b5f40117cb26963'
MANUAL_IDS = [711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721]
EVOLVED_IDS = [713, 714, 715, 718, 719, 721]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    target = ROOT / 'batch002_records'
    if target.exists():
        raise ValueError('Overlay output must be new')
    if b.sha(BASE.read_bytes()) != BASE_SHA:
        raise ValueError('Batch001 SHA pin mismatch')
    b.verify_bundle(BASE)
    with zipfile.ZipFile(BASE) as z:
        catalog = json.loads(z.read(b.CATALOG_PATH))
        matrix = json.loads(z.read('batch_001/evidence/AUDIT_MATRIX_847_BATCH001.json'))
        inherited = {}
        for number in (711, 712, 713, 716, 717, 720, 721):
            path = f'batch_001/evidence/aictrl_batch/{number}.md'
            text = z.read(path).decode('utf-8')
            sections = re.split(r'^## (\d+)\. [^\n]*\n', text, flags=re.M)
            parsed = {}
            for i in range(1, len(sections), 2):
                n = int(sections[i])
                content = sections[i+1].split('\n## ', 1)[0].strip()
                if 1 <= n <= 21:
                    parsed[FIELDS[n-1]] = {'evidencia_heredada_lote': '001',
                        'documento': path, 'texto': content,
                        'reinspeccion_individual_lote002': False}
            if set(parsed) != set(FIELDS):
                raise ValueError(f'Incomplete inherited dossier {number}')
            inherited[number] = parsed
    by_id = {r['id']: r for r in catalog}
    rows = {r['id']: r for r in matrix['rows']}
    for number in (714, 715, 718, 719):
        row = by_id[number]
        tree = ROOT / 'batch002_candidates' / row['staged_root']
        files = sorted(p for p in tree.rglob('*') if p.is_file())
        row['portable_sha256'] = row['candidate_sha256'] = b.sha((tree/'SKILL.md').read_bytes())
        row['aux_expected'] = row['aux_recovered'] = len(files)-1
        row['aux_missing'] = []
        row['candidate_resource_files'] = [{'path': p.relative_to(tree).as_posix(),
            'bytes': p.stat().st_size, 'sha256': b.sha(p.read_bytes())}
            for p in files if p.name != 'SKILL.md' or p.parent != tree]
        rows[number].update(state='IMPROVED', manual_instruction_review=True,
            manual_scope='instruction_contract_and_explicitly_documented_resources',
            manual_review_evidence=f'batch_002/evidence/fichas/{number:04d}.json',
            upstream_public_head_compared=True, provider_runtime_tested=False,
            whole_capability_verified=False, offline_component_tested=number in (714,719),
            new_improvement_categories=['DOCUMENTARY'] if number in (715,718) else ['DOCUMENTARY','STRUCTURAL','FUNCTIONAL_LOCAL_COMPONENT'],
            next_action='Consultar campo21 y límites de la ficha individual')
    source = by_id[714]
    vals = [
        {'id_original':714, 'nombre':'create-workflow', 'namespace':source['namespace'],
         'id_estable':source['namespace']+':create-workflow', 'uri_original':source['uri'],
         'upstream':'https://github.com/aictrl-dev/skills', 'commit':PIN,
         'base_lote001_sha256':BASE_SHA},
        {'estado':'IMPROVED', 'version_paquete_upstream':'1.1.0-beta.2',
         'version_individual':'No declarada como versión independiente',
         'licencia':'MIT aictrl 2026; js-yaml MIT preservada en vendor; Ajv/ajv-formats externos fijados'},
        'Autoría de workflows AICtrl v2 y preflight offline de esquema, grafos y referencias locales antes de revisar aplicación en la organización.',
        ['create a workflow','write workflow YAML','automate this engineering process','archivo .aictrl/workflows/'],
        {'entrada':'Ruta regular JSON/YAML UTF-8 de hasta1MiB; esquema workflow/v2.',
         'salida':'Código0 sólo para los checks offline definidos;1 validación rechazada;2 lectura/parser/dependencia fallida. No aplica workflows ni contacta servicios.',
         'limites':'Profundidad64,100000 valores, presupuesto merge1000;3 niveles de loop y producto1000. JSON_SCHEMA no construye tags especiales ni expande merge keys.'},
        {'archivos_candidatos':43, 'recursos':source['candidate_resource_files'],
         'esquemas':'Sin modificaciones respecto al donor fijado.',
         'cierre':'Unidad create-workflow completa + runtime YAML inspeccionado; no certifica cierre transitivo de servicios/organización.'},
        {'runtime':'Node probado24.19.0 Work y26.4.0 Termux; Ajv8.20.0 y ajv-formats3.0.1 del toolchain aislado recuperado.',
         'yaml':'js-yaml4.3.2 vendorizado,31 archivos exactos inspeccionados del commit79ca68d90f333fbe6d9e42827527e62636200191.',
         'permisos':'Lectura local para preflight. Autoría de archivos y git-sync se evalúan aparte; sin npm install ni proveedor activado.'},
        {'flujo':['Lectura acotada de fichero regular','Parser fijo JSON_SCHEMA','Recorrido iterativo y límites de complejidad','Ajv con formats requerido','Checks locales de IDs/referencias, loops, ciclos y retry','Resultado con alcance explícito'],
         'arquitectura':'CLI Node sin red; algoritmo Kahn iterativo para ciclos; código proveedor leído antes de ejecutarse sobre datos sintéticos.'},
        {'ChatGPT':'Instrucciones inspeccionadas; activación/servicio NO_COMPROBADO.',
         'Work':'28/28 fixtures finales +25/25 regresiones offline.',
         'Termux':'28/28+25/25 sobre el mismo SHA de validate.mjs; Node26.4.0.',
         'PC':'NO_COMPROBADO para714; las pruebas de719 en Windows no se transfieren a esta skill.'},
        {'mejoras':'Parser4.3.2 fijado evita depender de versiones3.15.0/3.15.1 observadas en caches; límites de lectura y recorridos, errores de parser sin volcar datos.',
         'datos':'Fixtures sintéticos, sin claves ni apply.',
         'limites':'No demuestra seguridad de un workflow ejecutado. Secretos, efectos, presupuestos y permisos de organización siguen pendientes.'},
        {'corregido_en002':['ParserYAML host no fijado y expuesto a avisos oficiales','Alias cíclicos/no finitos y complejidad no acotada','Recursión para ciclos de grafos grandes','Referencias a nodos inexistentes','retry>0 permitido por esquema pero rechazado por contrato apply','Ejemplo de output con clave no admitida'],
         'heredado001':['Ajv-formats obligatorio','No recorrer instancias inválidas por esquema','Tercer nivel de loop permitido; cuarto rechazado'],
         'pendiente':['CEL','input parameter existence','required task inputs','static input types','gate existence/type/wave','output ordering','JSON duplicate keys last-value behavior','organization apply/runtime']},
        'Componer con713 governance y721 seguridad en el ecosistema existente; el preflight no sustituye controles de organización ni requiere otro cerebro.',
        {'existente':'SKILL.md, SPEC.md, authoring-guide, schemas, cinco ejemplos y validator.',
         'nuevo':'reference/kai-offline-contract.md delimita exactamente garantías y pendientes; instalación selectiva y recuperación heredadas.'},
        {'fuente':'https://github.com/aictrl-dev/skills/tree/'+PIN+'/skills/create-workflow',
         'fecha':'2026-10-15 UTC', 'js_yaml':'https://github.com/nodeca/js-yaml/tree/79ca68d90f333fbe6d9e42827527e62636200191',
         'actualizaciones':'HEAD público observado y fijado; no equivale a actualización de la instalación activa.'},
        {'decision':'REUSE unidad oficial y toolchain previo → ADAPT validator y ejemplo → COMPOSE parser MIT inspeccionado.',
         'alternativas':'Ajv oficial conserva JSON Schema; parser host no fijado descartado para este candidato; no se construye motor de workflows paralelo.'},
        'Mantener candidato aislado. Próxima evolución: contratos locales de inputs/gates/orden y fixtures negativos; después gate de organización cuando exista sesión válida y un caso concreto autorizado.',
        {'DOCUMENTARY':['Alcance offline/dependencias/versiones/limitaciones','Ejemplo output pullRequestUrl'],
         'STRUCTURAL':['Vendor YAML4.3.2 con manifiesto y MIT'],
         'FUNCTIONAL':['Lectura/parseo/recorridos acotados','Algoritmo iterativo de ciclo','Referencia local de nodo','No-retry conforme guía apply'],
         'heredado':'No se atribuyen como nuevas las correcciones ya realizadas en001.'},
        {'Work_final':'skill_714/local_final/RESULTS_candidate_final.json:28/28; INHERITED_25_FINAL_RECEIPTS.json:25/25.',
         'Termux_final':'skill_714/TERMUX_FINAL_COMBINED_RESULTS.json:28/28+25/25; códigos runner0.',
         'forward_previo':'validator_forward_check/26 checks y6 límites observados sobre revisión previa; no se presenta como prueba del hash final.',
         'proveedor':'0 llamadas de ejecución/E2E; list_organizations rechazado por oauth_token_invalid_grant.',
         'evidencia_negativa':'RESULTS_upstream conserva reproducción de defectos y caso skeleton incompleto corregido en expectativa del harness.'},
        {'original_sha256':source['original_sha256'], 'candidate_SKILL_sha256':source['portable_sha256'],
         'validate_mjs_sha256':'e90519b2eee324b57a2e2464d639edcbeace1bd5fa9a8f4a8d9e3341804cc706',
         'manifiesto':'skill_714/CANDIDATE_FINAL_HASHES.json', 'captura_original':'originals/... conservada sin normalización'},
        {'instalacion':'NO_INSTALADO; copia selectiva a nuevo laboratorio tras verify_bundle y comprobación de licencia/dependencias.',
         'rollback':'bundle_io --rollback-target requiere recibo y bytes exactos; árbol anterior en HISTORICAL/before_batch_002. Originales inmutables.',
         'STOP':'Marcador cooperativo heredado, comprobado antes y entre ficheros; no servicio adicional.'},
        {'estado':'IMPROVED', 'grado_inspeccion':'UNDERSTOOD del contrato y componente offline inspeccionado; no de toda ejecución del proveedor.',
         'component_tests':'TESTED; checks concretos anteriores superados sobre hash final.',
         'whole_capability_verified':False, 'siguiente':'Completar contratos locales pendientes con fixtures; recuperar autenticación AICtrl sólo cuando proceda; no aplicar ni publicar para simular una prueba offline.'},
    ]
    manual = dict(inherited)
    manual[714] = dict(zip(FIELDS, vals))
    for number, folder in ((715,'skills_715_718'),(718,'skills_715_718'),(719,'skill_719')):
        manual[number] = json.loads((ROOT/folder/f'FICHA_{number}.json').read_text())
    # Normalize the state label without changing any test or outcome claim.
    final719 = dict(manual[719][FIELDS[-1]])
    final719['descripcion_revision'] = final719['estado']
    final719['estado'] = 'IMPROVED'
    final719['whole_capability_verified'] = False
    manual[719][FIELDS[-1]] = final719
    records = generate_records(catalog, list(rows.values()), manual)
    write_records(target/'fichas', records)
    dump(target/'MANUAL_DOSSIERS_11.json', manual)
    dump(target/'CATALOG_PROJECTED_BATCH002.json', catalog)
    dump(target/'AUDIT_MATRIX_847_BATCH002.json', {'scope':'847_COVERAGE_11_MANUAL_NOT_847_DEEP_AUDITS', 'rows':list(rows.values())})
    dump(target/'COVERAGE.json', {'original_entries':847,'individual_records_21_fields':847,
        'automated_static_inspected':847, 'manual_reviewed_cumulative':11,
        'manual_reviewed_ids':MANUAL_IDS, 'manual_new_in002':[715,718,719],
        'manual_revised_in002':[714], 'pending_manual':836,
        'understood_scope':'11 instruction contracts with individually documented resource scope, not11 provider runtimes',
        'improved_cumulative_ids':EVOLVED_IDS, 'improved_current_ids':[714,715,718,719],
        'functional_offline_component_tested_ids':[714,719],
        'provider_runtime_tested':0, 'whole_capability_verified':0,
        'state':'PARTIAL', 'base_sha256':BASE_SHA})
    graph = {'scope':'DECLARED_RESOURCE_EDGES_NOT_TRANSITIVE_CLOSURE', 'edges':[
        {'from':r['namespace']+':'+r['name'], 'to':uri, 'kind':'captured_declared_resource'}
        for r in catalog for uri in r.get('support_files',[])]}
    dump(target/'DEPENDENCY_GRAPH_DECLARED.json', graph)
    dump(target/'CAPABILITY_DNA.json', {'scope':'IDENTITY_AND_EVIDENCE_NOT_AUTOMATIC_SEMANTIC_UNDERSTANDING',
        'entries':[{'id':r['id'],'identity':r['namespace']+':'+r['name'],
            'description_captured':r.get('description',''), 'domain_captured':r.get('domain'),
            'original_sha256':r['original_sha256'], 'manual':r['id'] in MANUAL_IDS,
            'functional_provider_verified':False} for r in catalog]})
    print(json.dumps({'fichas':len(records),'manual':len(manual),'graph_edges':len(graph['edges'])}))


if __name__ == '__main__':
    main()
