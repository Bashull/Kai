"""Package a recovered OMEGA007 layout using the existing batch002 ZIP verifier.

All private inputs must already be local. No downloads, installation or services.
Use a new output directory. This driver preserves original archive bytes.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys


EVOLVED = [1, 2, 3, 4, 5, 713, 714, 715, 718, 719, 721]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workdir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--previous-release-driver',type=Path,required=True)
    p.add_argument('--stop-file',type=Path)
    p.add_argument('--reuse-components-from',type=Path,
                   help='Reuse only byte-identical components from a preserved partial run')
    a=p.parse_args(); w=a.workdir.resolve(); out=a.output.resolve()
    sys.path.insert(0,str(w/'toolkit_omega007'))
    import bundle_io as b
    import build_incremental as inc
    from run_tool_checks import validate_receipt
    b._check_stop(a.stop_file)
    if out.exists() or out.is_symlink(): raise ValueError('Release output must be new')
    spec=importlib.util.spec_from_file_location('prior_release',a.previous_release_driver)
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    prior.OUT=out
    validate_receipt(w/'evidence_omega007/INHERITED_OMEGA004/TOOL_TEST_RECEIPT_RELEASE_004.json',w/'toolkit_omega007')
    out.mkdir(parents=True)

    def dump(path,value):
        with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

    def files(root):
        return {n:d for n,d in prior.files(root).items() if '__pycache__' not in Path(n).parts}

    def package(name,payload,catalog=None):
        b._check_stop(a.stop_file)
        for n,d in payload.items():
            if not n.lower().endswith('.zip'):inc._secret_preflight(n,d)
        old=a.reuse_components_from/name if a.reuse_components_from else None
        if old and old.is_file():
            # Reuse is conditional on the complete intended file set and bytes;
            # changed evidence is rebuilt rather than silently accepted.
            import zipfile
            manifest=(inc._manifest(payload,catalog) if catalog is not None else
                {'format':'kai.skills.release-component/1','release_state':'CANDIDATE_PARTIAL',
                 'provider_E2E':False,'files':{n:inc.record(d) for n,d in sorted(payload.items())}})
            marker='MANIFEST_SHA256.json' if catalog is not None else 'COMPONENT_MANIFEST_SHA256.json'
            expected={**payload,marker:inc.json_bytes(manifest)}
            with zipfile.ZipFile(old) as z:
                identical=set(z.namelist())==set(expected) and all(z.read(n)==d for n,d in expected.items())
            if identical:
                with (out/name).open('xb') as f:f.write(old.read_bytes())
        return prior.write_zip(out/name,payload,catalog)

    build_path=w/'builds/KAI_SKILLS_FORGE_OMEGA007_CANDIDATE_20261016.zip'
    build_receipt=b.read_json(build_path.with_name(build_path.name+'.build.json').read_bytes())
    if inc.record(build_path.read_bytes())!={k:build_receipt[k] for k in ('bytes','sha256')}:
        raise ValueError('Built payload/receipt hash mismatch')
    b.verify_bundle(build_path,a.stop_file)
    tree=w/'builds/KAI_SKILLS_FORGE_OMEGA007_CANDIDATE_20261016'
    catalog=b.read_json((tree/b.CATALOG_PATH).read_bytes()); by_id={r['id']:r for r in catalog}
    if len(catalog)!=847:raise ValueError('Original catalog scope changed')
    records=[]
    original=w/'recovered_batch002/components/01_ORIGINALS_PRESERVED_847_20261015.zip'
    raw_sources={'ori847_original_component.zip':original.read_bytes(),
                 'pc_capture.zip':(w/'sources/pc_capture.zip').read_bytes(),
                 'termux_capture.zip':(w/'sources/termux_capture.zip').read_bytes()}
    source_index={'state':'PRIVATE_PRESERVATION_NOT_A_LICENSE_TO_REDISTRIBUTE',
        'scope':'847 originals plus fixed723 PC and3659 Termux occurrence captures',
        'sources':{n:inc.record(d) for n,d in raw_sources.items()},
        'canonical_paths':'Read individual SOURCE_CENSUS and CAPTURE_MANIFEST inside each capture',
        'full_device_inventory':False}
    records.append(package('01_KAI_SKILLS_ORIGINALS_PRESERVED_5229_OMEGA007_PRIVATE.zip',
                           {**{'sources/'+n:d for n,d in raw_sources.items()},'SOURCE_INDEX.json':inc.json_bytes(source_index)}))
    audit=files(w/'evidence_omega007')
    audit['PAYLOAD_BUILD_RECEIPT.json']=build_path.with_name(build_path.name+'.build.json').read_bytes()
    records.append(package('02_KAI_SKILLS_AUDIT_EVIDENCE_OMEGA007.zip',audit))
    dna={n:audit[n] for n in ('CAPABILITY_DNA.json','SPIRAL_IMPACT.json','EXTERNAL_RESEARCH.json',
        'PROVIDER_RESOURCE_CAPTURE.json','SIBLING_RUNTIME_AUXILIARIES.json',
        'ORI-0005/COMPARISON_MATRIX.json','ORI-0005/CHANGE_CONTRACT.json','ORI-0005/SKILL.md.patch')}
    records.append(package('03_KAI_SKILLS_EVOLUTION_DNA_OMEGA007_PRIVATE.zip',dna))
    selected=[by_id[i] for i in EVOLVED]; improved={}
    for row in selected:
        for n,d in files(tree/row['staged_root']).items():improved[row['staged_root']+'/'+n]=d
        improved[row['original_path']]=(tree/row['original_path']).read_bytes()
        for entry in row.get('provider_resource_files', []):
            improved[entry['path']]=(tree/entry['path']).read_bytes()
    improved[b.CATALOG_PATH]=inc.json_bytes(selected)
    improved['DISTRIBUTION_LIMITS.txt']=(
        'PRIVATE CANDIDATES. Provider proprietary material retains its original terms.\n'
        'Eleven candidate trees; shared resources do not certify sibling skills or whole capabilities.\n'
        'Local toolkit/runtime evidence and a separate forward scenario retain their exact scopes.\n'
        'No mass installation, active deployment, external provider E2E or relicensing.\n').encode()
    records.append(package('04_KAI_SKILLS_IMPROVED_OMEGA007_PRIVATE_CANDIDATES.zip',improved,selected))
    toolkit={n if '/' in n or n.endswith('.py') or n=='README.md'
             else 'HISTORICAL/recovered_batch002_component/'+n:d
             for n,d in files(w/'toolkit_omega007').items()}
    toolkit['evidence/INHERITED_OMEGA004_TOOL_TEST_RECEIPT.json']=(w/'evidence_omega007/INHERITED_OMEGA004/TOOL_TEST_RECEIPT_RELEASE_004.json').read_bytes()
    records.append(package('05_KAI_SKILLS_FORGE_TOOLKIT_OMEGA007.zip',toolkit))
    archive=out/'04_KAI_SKILLS_IMPROVED_OMEGA007_PRIVATE_CANDIDATES.zip'
    target=out/'synthetic_selected_lab'; witness=out/'external_witness.txt'
    witness.write_text('external-owned-witness\n')
    dry=b.stage_selected(archive,EVOLVED,target,False,a.stop_file)
    if target.exists():raise ValueError('Dry-run created a target')
    applied=b.stage_selected(archive,EVOLVED,target,True,a.stop_file)
    rollback_dry=b.rollback_stage(target,False,a.stop_file)
    rollback=b.rollback_stage(target,True,a.stop_file)
    if target.exists() or witness.read_text()!='external-owned-witness\n':raise ValueError('Rollback postcondition failed')
    stop=out/'synthetic_STOP';stop.touch();blocked=False
    try:b.stage_selected(archive,[1],out/'must_not_be_created',True,stop)
    except RuntimeError:blocked=True
    stop.unlink()
    if not blocked or (out/'must_not_be_created').exists():raise ValueError('STOP preflight failed')
    stage={'scope':'NEW_SYNTHETIC_LAB_ONLY_NOT_ACTIVE_INSTALLATION','dry_run':dry,'copy':applied,
           'rollback_dry_run':rollback_dry,'rollback':rollback,'lab_absent_after_rollback':True,
           'external_witness_intact':True,'STOP_preflight_blocked_before_write':True,
           'limits':'Cooperative STOP and rollback are not atomic; no active target was touched'}
    dump(out/'SELECTIVE_STAGE_ROLLBACK_OMEGA007.json',stage)
    records.append(package('09_KAI_SKILLS_INSTALL_ROLLBACK_OMEGA007_LAB_ONLY.zip',{
        'tools/bundle_io.py':(w/'toolkit_omega007/bundle_io.py').read_bytes(),
        'tools/README.md':(w/'toolkit_omega007/README.md').read_bytes(),
        'SELECTIVE_STAGE_ROLLBACK_OMEGA007.json':inc.json_bytes(stage)}))
    capsule=(w/'RECOVERY_CAPSULE_OMEGA007_INNER.md').read_bytes()
    index={'state':'PARTIAL_MISSION_CANDIDATE_NOT_INSTALLED_NOT_CANONICAL',
           'components':records,'withheld_target_distributions':{
               '06_PC_ASIER':'No per-skill whole target verification; no whole document conversion target run',
               '07_TERMUX_ANDROID':'No per-skill whole target verification; no whole document conversion target run',
               '08_CHATGPT_WORK':'No native installation/provider certification; isolated runtime and instruction scenarios only'}}
    complete={'RECOVERY_CAPSULE_OMEGA007.md':capsule,
              'COMPONENT_INDEX_OMEGA007.json':inc.json_bytes(index),
              'SELECTIVE_STAGE_ROLLBACK_OMEGA007.json':inc.json_bytes(stage),
              'payload/'+build_path.name:build_path.read_bytes(),
              'payload/'+build_path.name+'.build.json':inc.json_bytes(build_receipt)}
    for record in records:
        name=Path(record['path']).name if 'path' in record else record['name']
        complete['components/'+name]=(out/name).read_bytes()
    full=package('10_KAI_SKILLS_COMPLETE_PORTABLE_RELEASE_OMEGA007_PARTIAL.zip',complete)
    index['complete_release']=full
    dump(out/'PACKAGE_INDEX_OMEGA007.json',index)
    all_records=records+[full]
    checks=''.join(r['sha256']+'  '+Path(r.get('path',r.get('name',''))).name+'\n' for r in all_records)
    (out/'SHA256SUMS_OMEGA007.txt').write_text(checks)
    print(json.dumps({'components':len(records),'complete':full,'selective_copy_files':applied['files'],
                      'rollback':'PASS','STOP':'PASS','target_distributions':'WITHHELD_NOT_VERIFIED'},ensure_ascii=False))


if __name__=='__main__':main()
