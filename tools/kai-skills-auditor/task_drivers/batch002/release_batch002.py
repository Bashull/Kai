"""Reproducible task driver: recover -> overlay -> inspect -> selective lab copy.

Private inputs are deliberately not downloaded or published by this driver.
Run beside the recovered forge_vnext_lab layout; every output must be new.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'toolkit_vnext'))
import bundle_io as b
import build_incremental as inc
from run_tool_checks import validate_receipt

OUT = ROOT/'release_batch002'
BASE = ROOT/'lote001_recovered/complete/payload/KAI_SKILLS_FORGE_BATCH001_CANDIDATE_20261015.zip'
BASE_SHA = '670a8a697d4fc6badc1db22dbcbea6868c1cdbd3cffd050a351319eaf4b9f010'
EVOLVED = [713,714,715,718,719,721]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def copy(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Only explicit regular evidence files are accepted')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as f:
        f.write(source.read_bytes())


def tree(source, destination, reject=()):
    for p in sorted(Path(source).rglob('*')):
        rel = p.relative_to(source)
        if p.is_file() and not any(part in reject for part in rel.parts):
            copy(p, Path(destination)/rel)


def evidence():
    if OUT.exists():
        raise ValueError('Release directory must be new')
    OUT.mkdir()
    ev = OUT/'evidence'
    ev.mkdir()
    root_names = [
        'CAPSULE_RECOVERY_BYTE_RECEIPT.json','CAPTURE_VS_ORIGINAL_RECONCILIATION.json',
        'ADVERTISED_TOOL_INVENTORY.json','SKILL_API_DISCOVERY_executor.json',
        'SKILL_API_DISCOVERY_cloud.json','LOCAL_SKILL_DISCOVERY.json',
        'TERMUX_DISCOVERY.json','PC_DISCOVERY.json','ADDITIONAL_SKILLS_RECONCILIATION.json',
        'AIICTRL_CONNECTION_READONLY.json','AIICTRL_OPEN_ISSUES_20261015.json',
        'CONNECTION_PERMISSION_EVIDENCE.json','LOTE001_CODE_READBACK_VERIFICATION.json',
        'PINNED_UPSTREAM.json','UPSTREAM_FETCH_RECEIPTS.json','UPSTREAM_TEXT_PLAN.json',
        'YAML_REUSED_NPM_VS_GIT.json','INCREMENTAL_SECOND_BATCH_RED.json',
        'TOOLKIT_BATCH002_TEST_RECEIPT_RELEASE.json',
        'TOOLKIT_BATCH002_TEST_STDOUT_RELEASE.txt','TOOLKIT_BATCH002_TEST_STDERR_RELEASE.txt',
        'GITHUB_BATCH002_READBACK.json','PATCH_REPLAY_BATCH002.json',
        'prepare_batch002.py','release_batch002.py',
    ]
    for name in root_names:
        copy(ROOT/name, ev/name)
    copy(ROOT/'capsule_byte_source/KAI_SKILLS_RELEVO_WORK_20261015.md', ev/'recovery/ORIGINAL_CAPSULE_BYTE_EXACT.md')
    copy(ROOT/'KAI_847_ORIGINALES_PRIVADO_20261015.zip', ev/'recovery/RAW_847_CAPTURE_PRIVATE.zip')
    lab = json.loads((ROOT/'TERMUX_LAB_READONLY.json').read_text())
    # Keep the whole hash census; avoid a redundant export of recovered raw text.
    dump(ev/'recovery/TERMUX_LAB_HASH_CENSUS.json', {k:v for k,v in lab.items() if k!='texts'})
    tree(ROOT/'batch002_records', ev)
    tree(ROOT/'upstream', ev/'donor_pinned_text_subset')
    for p in (ROOT/'skill_714').iterdir():
        if p.is_file() and p.suffix=='.json':
            copy(p, ev/'skill_714'/p.name)
    for name in ('run_validation.py','CASES.json'):
        if not (ev/'skill_714'/name).exists():
            copy(ROOT/'skill_714'/name, ev/'skill_714'/name)
    tree(ROOT/'skill_714/fixtures', ev/'skill_714/fixtures')
    for name in ('RESULTS_candidate_final.json','run_validation.py'):
        copy(ROOT/'skill_714/local_final'/name, ev/'skill_714/local_final'/name)
    tree(ROOT/'skills_715_718', ev/'skills_715_718', reject=('candidate','original','upstream','__pycache__'))
    for name in ('FICHA_719.json','FICHA_719.md','INFORME_719.md','candidate.patch','FINDINGS.json'):
        copy(ROOT/'skill_719'/name, ev/'skill_719'/name)
    for name in ('evidence','tests','revisions'):
        tree(ROOT/'skill_719'/name, ev/'skill_719'/name, reject=('__pycache__',))
    tree(ROOT/'skill_719/remote_pc_asier/returned_final', ev/'skill_719/remote_pc_asier/returned_final')
    tree(ROOT/'skill_719/remote_pc_asier/returned_initial', ev/'skill_719/remote_pc_asier/returned_initial')
    for folder in ('yaml_donor_4.3.2','validator_forward_check','incremental_forward_check'):
        src = ROOT/folder
        for p in src.iterdir():
            if p.is_file() and p.suffix in ('.json','.md','.py','.cjs','.diff','.txt'):
                copy(p, ev/folder/p.name)
    tree(ROOT/'validator_forward_check/fixtures', ev/'validator_forward_check/fixtures')
    tree(ROOT/'incremental_forward_check/candidate_source_r4', ev/'incremental_forward_check/candidate_source_r4')
    for name in ('RESULTS.json','COMMANDS.json','SOURCE_HASHES_AFTER.json','UPSTREAM_TEST_COMMAND.json'):
        copy(ROOT/'incremental_forward_check/run04'/name, ev/'incremental_forward_check/run04'/name)
    validate_receipt(ROOT/'TOOLKIT_BATCH002_TEST_RECEIPT_RELEASE.json', ROOT/'toolkit_vnext')
    # Use the recovered immutable original component; no reconstruction.
    old = ROOT/'lote001_recovered/complete/components/01_ORIGINALS_PRESERVED_847_20261015.zip'
    copy(old, OUT/old.name)
    print(json.dumps({'evidence_files':len(list(ev.rglob('*'))),'state':'READY_FOR_INCREMENTAL_BUILD'}))


def candidate():
    receipt = inc.build_incremental(BASE, ROOT/'batch002_candidates', OUT/'evidence',
        OUT/'KAI_SKILLS_FORGE_BATCH002_CANDIDATE_20261015',
        base_sha256=BASE_SHA, tools_dir=ROOT/'toolkit_vnext', expected_skills=847, batch_id='002')
    print(json.dumps({k:receipt[k] for k in ('zip','sha256','catalog_entries','candidate_ids','archive_integrity')}))


def write_zip(path, payload, bundle_catalog=None):
    b._validate_paths(list(payload)+['COMPONENT_MANIFEST_SHA256.json' if bundle_catalog is None else 'MANIFEST_SHA256.json'])
    manifest = {'format':'kai.skills.release-component/1','release_state':'CANDIDATE_PARTIAL',
        'provider_E2E':False,'files':{n:inc.record(d) for n,d in sorted(payload.items())}}
    name = 'COMPONENT_MANIFEST_SHA256.json'
    if bundle_catalog is not None:
        manifest = inc._manifest(payload, bundle_catalog)
        name = 'MANIFEST_SHA256.json'
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        for n,d in sorted({**payload,name:inc.json_bytes(manifest)}.items()):
            info = zipfile.ZipInfo(n, date_time=(2026,10,15,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(stat.S_IFREG|0o644)<<16
            z.writestr(info,d)
    return inspect(path)


def files(path):
    return {p.relative_to(path).as_posix():p.read_bytes() for p in sorted(Path(path).rglob('*')) if p.is_file()}


def inspect(path):
    extract = OUT/'clean_extract'/path.stem
    if extract.exists():
        raise ValueError('Clean extraction must be new')
    with zipfile.ZipFile(path) as z:
        b._validate_paths(z.namelist())
        if z.testzip() is not None:
            raise ValueError('CRC failed')
        name = 'MANIFEST_SHA256.json' if 'MANIFEST_SHA256.json' in z.namelist() else 'COMPONENT_MANIFEST_SHA256.json'
        manifest = b.read_json(z.read(name))
        if set(z.namelist()) != set(manifest['files'])|{name}:
            raise ValueError('Manifest coverage failed')
        for n,record in manifest['files'].items():
            info = z.getinfo(n)
            if (info.external_attr>>16)&0o170000 not in (0,stat.S_IFREG):
                raise ValueError('Unexpected file type')
            data = z.read(n)
            if inc.record(data)!=record:
                raise ValueError('SHA/size mismatch')
        extract.mkdir(parents=True)
        for n in z.namelist():
            p = extract/b.safe_path(n)
            p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:
                f.write(z.read(n))
        for n,record in manifest['files'].items():
            if inc.record((extract/n).read_bytes()) != record:
                raise ValueError('Extracted bytes mismatch')
    if name=='MANIFEST_SHA256.json':
        b.verify_bundle(path)
    return {'name':path.name,**inc.record(path.read_bytes()),'payload_files':len(manifest['files']),
        'manifest':name,'CRC':'PASS','paths':'PASS','manifest_SHA256':'PASS','clean_extraction':'PASS',
        'provider_functionality':'NOT_VERIFIED'}


def components():
    candidate = OUT/'KAI_SKILLS_FORGE_BATCH002_CANDIDATE_20261015.zip'
    b.verify_bundle(candidate)
    with zipfile.ZipFile(candidate) as z:
        catalog = json.loads(z.read(b.CATALOG_PATH))
        by_id={r['id']:r for r in catalog}
        # Prove all original bytes, preceding batch and untouched trees survived.
        with zipfile.ZipFile(BASE) as old:
            preserved=[n for n in old.namelist() if n.startswith(('originals/','batch_001/'))]
            changed_roots=tuple(by_id[i]['staged_root']+'/' for i in (714,715,718,719))
            untouched=[n for n in old.namelist() if n.startswith('providers/') and not n.startswith(changed_roots)]
            for n in preserved+untouched:
                if old.read(n)!=z.read(n):
                    raise ValueError('Historical data changed: '+n)
        dump(OUT/'PRESERVATION_RECEIPT.json',{'original_files_and_prior_batch_payloads':len(preserved),
            'unselected_provider_files_unchanged':len(untouched),'result':'PASS','base_sha256':BASE_SHA})
        # 02 includes previous evidence as immutable historical evidence.
        audit = {'current_batch/'+n:d for n,d in files(OUT/'evidence').items()}
        old02=ROOT/'lote001_recovered/complete/components/02_AUDIT_AND_EVIDENCE_BATCH001_20261015.zip'
        with zipfile.ZipFile(old02) as prior:
            audit.update({'inherited_batch001/'+n:prior.read(n) for n in prior.namelist()})
        audit['PRESERVATION_RECEIPT.json']=(OUT/'PRESERVATION_RECEIPT.json').read_bytes()
        records=[inspect(OUT/'01_ORIGINALS_PRESERVED_847_20261015.zip')]
        records.append(write_zip(OUT/'02_AUDIT_AND_EVIDENCE_BATCH002_20261015.zip',audit))
        selected=[by_id[i] for i in EVOLVED]
        improved={b.CATALOG_PATH:inc.json_bytes(selected),
            'SCOPE.json':inc.json_bytes({'candidate_ids':EVOLVED,'state':'CANDIDATE_PARTIAL','installed':False,
                'categories':{'documentary_only':[713,715,718,721], 'functional_local_component':[714,719]},
                'whole_capability_verified':0,'licenses':'MIT for selected AICtrl units, retained in each unit; original847 private corpus not cleared for redistribution.'})}
        for row in selected:
            root=row['staged_root']+'/'
            improved.update({n:z.read(n) for n in z.namelist() if n.startswith(root) or n==row['original_path']})
        for n in ('batch_001/CHANGES.json','batch_002/CHANGES.json','batch_002/PROVENANCE.json'):
            improved[n]=z.read(n)
        improved.update({'patches/'+n:d for n,d in files(ROOT/'toolkit_vnext/patches/batch002').items()})
        records.append(write_zip(OUT/'03_IMPROVED_SKILLS_BATCH002_20261015.zip',improved,selected))
    tools=files(ROOT/'toolkit_vnext')
    tools={n:d for n,d in tools.items() if '__pycache__' not in Path(n).parts}
    tools.update({'task_drivers/'+n:(ROOT/n).read_bytes() for n in ('prepare_batch002.py','release_batch002.py')})
    tools['evidence/TOOLKIT_TEST_RECEIPT.json']=(ROOT/'TOOLKIT_BATCH002_TEST_RECEIPT_RELEASE.json').read_bytes()
    tools['evidence/GITHUB_READBACK.json']=(ROOT/'GITHUB_BATCH002_READBACK.json').read_bytes()
    tools['evidence/FORWARD_CHECK.json']=(ROOT/'incremental_forward_check/FINAL_RECEIPT.json').read_bytes()
    records.append(write_zip(OUT/'04_KAI_SKILLS_FORGE_BATCH002_20261015.zip',tools))
    package03=OUT/'03_IMPROVED_SKILLS_BATCH002_20261015.zip'
    target=OUT/'selective_staging_test'
    sentinel=OUT/'outside_staging_sentinel.txt'
    sentinel.write_text('Preserve this unrelated lab file.\n')
    preview=b.stage_selected(package03,EVOLVED,target,apply=False)
    if target.exists():
        raise ValueError('Dry run wrote target')
    staged=b.stage_selected(package03,EVOLVED,target,apply=True)
    receipt=b.read_json((target/b.RECEIPT_NAME).read_bytes())
    before_rollback={n:inc.record(d) for n,d in files(target).items()}
    rollback_preview=b.rollback_stage(target)
    if {n:inc.record(d) for n,d in files(target).items()}!=before_rollback:
        raise ValueError('Rollback dry run changed data')
    rolled=b.rollback_stage(target,apply=True)
    if target.exists() or sentinel.read_text()!='Preserve this unrelated lab file.\n':
        raise ValueError('Rollback postcondition failed')
    stage_receipt={'scope':'REAL_SELECTIVE_COPY_OF_SIX_CANDIDATES_IN_NEW_LAB_ONLY',
        'preview':preview,'staged':staged,'stage_receipt':receipt,
        'post_copy_hashes':before_rollback,'rollback_preview':rollback_preview,
        'rollback':rolled,'target_absent_after_rollback':True,'outside_sentinel_intact':True,
        'active_installation':False,'provider_execution':False}
    dump(OUT/'SELECTIVE_STAGING_AND_ROLLBACK.json',stage_receipt)
    install=files(ROOT/'reused_workflow_toolchain')
    install={n:d for n,d in install.items() if '__pycache__' not in Path(n).parts}
    install.update({'tools/bundle_io.py':(ROOT/'toolkit_vnext/bundle_io.py').read_bytes(),
        'tools/README.md':(ROOT/'toolkit_vnext/README.md').read_bytes(),
        'SELECTIVE_STAGING_AND_ROLLBACK.json':inc.json_bytes(stage_receipt),
        'INSTALLATION_AND_ROLLBACK.md':(ROOT/'INSTALLATION_BATCH002.md').read_bytes()})
    records.append(write_zip(OUT/'05_INSTALLATION_AND_ROLLBACK_BATCH002_20261015.zip',install))
    payload_record=inspect(candidate)
    dump(OUT/'PACKAGE_INDEX_BATCH002.json',{'state':'PARTIAL_RELEASE_NOT_847_AUDITS_COMPLETED',
        'coverage':json.loads((ROOT/'batch002_records/COVERAGE.json').read_text()),
        'components':records,'cumulative_payload':payload_record,
        'build_receipt':candidate.name+'.build.json'})
    portable={'components/'+r['name']:(OUT/r['name']).read_bytes() for r in records}
    portable['payload/'+candidate.name]=candidate.read_bytes()
    for n in ('PACKAGE_INDEX_BATCH002.json','PRESERVATION_RECEIPT.json','SELECTIVE_STAGING_AND_ROLLBACK.json'):
        portable[n]=(OUT/n).read_bytes()
    portable['RECOVERY_CAPSULE_BATCH002.md']=(ROOT/'RECOVERY_CAPSULE_BATCH002.md').read_bytes()
    portable['payload/'+candidate.name+'.build.json']=candidate.with_name(candidate.name+'.build.json').read_bytes()
    final=write_zip(OUT/'06_COMPLETE_PORTABLE_RELEASE_BATCH002_PARTIAL_20261015.zip',portable)
    dump(OUT/'RELEASE_VERIFICATION_BATCH002.json',{'components':records,'cumulative_payload':payload_record,
        'complete':final,'selective_stage_and_rollback':'PASS','provider_E2E':0,'state':'PARTIAL'})
    sums=''.join(r['sha256']+'  '+r['name']+'\n' for r in records+[final,payload_record])
    with (OUT/'SHA256SUMS_BATCH002.txt').open('x') as f:
        f.write(sums)
    print(json.dumps({'components':len(records)+1,'complete':final,'staging_files':staged['files']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('evidence','candidate','components'))
    globals()[p.parse_args().phase]()
