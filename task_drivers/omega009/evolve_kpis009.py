"""Adapt pinned private KPI instructions in a new isolated candidate overlay."""
import argparse
import io
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bundle_io as b
import build_incremental as inc

PIN='6f3f3841371e4269d8bc6be406537145de3e86d7ca8d34d65af21548dfff2d46'


def evolve(base, pin, output, stop_file=None):
    b._check_stop(stop_file)
    output=Path(output).absolute()
    if output.exists() or any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in [output,*output.parents]):
        raise ValueError('Output must be a new isolated directory without links')
    if any(p.lower() in {'.codex','.claude','.agents'} for p in output.parts):
        raise ValueError('Active installation paths are not allowed')
    raw=inc._regular_bytes(base,stop_file)
    if not isinstance(pin,str) or not b.DIGEST_RE.fullmatch(pin) or b.sha(raw)!=pin:
        raise ValueError('Base SHA mismatch')
    payload={}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        manifest=b._verify_open_zip(z,stop_file);rows=b._catalog_by_id(z,manifest)
        row=rows[7];root=row['staged_root']
        if row['namespace']!='data-analytics' or b.sha(z.read(root+'/SKILL.md'))!=PIN:
            raise ValueError('Exact private skill baseline differs')
        existing=[n for n in manifest['files'] if n.startswith(root+'/')]
        if existing!=[root+'/SKILL.md']:
            raise ValueError('Expected the single baseline main')
        main='candidates/'+root+'/SKILL.md';text=z.read(root+'/SKILL.md').decode()
        anchor='### 5. Set Targets When Needed\n'
        if text.count(anchor)!=1:raise ValueError('Metric contract anchor differs')
        text=text.replace(anchor,'Before finalizing selected metrics, apply [operational KPI contracts](references/metric-contracts.md): preserve governed definitions, make population/grain/window and aggregation explicit, and distinguish measured, missing and provisional values. Keep this detail proportional to the decision.\n\n'+anchor)
        anchor='### 6. Deliver The Recommendation\n'
        if text.count(anchor)!=1:raise ValueError('Target contract anchor differs')
        text=text.replace(anchor,'Tie proposed targets and guardrails to the baseline definition, horizon, unit, evidence and review action using the same [contract guide](references/metric-contracts.md). Distinguish aspirations from approved thresholds and percentage points from relative changes. Describe missing collection and validation as proposed work; do not imply instrumentation or queries were executed.\n\n'+anchor)
        payload[main]=text.encode()
        reference=inc._regular_bytes(Path(__file__).with_name('metric-contracts.md'),stop_file)
        payload['candidates/'+root+'/references/metric-contracts.md']=reference
        # Existing common files are copied byte-exact only to make the explicit
        # binding input acceptable to the retained builder. No provider changes.
        common=['providers/data-analytics/.codex-plugin/plugin.json','providers/data-analytics/shared/shared-skill-instructions.md']
        sibling='providers/data-analytics/skills/visualize-data/references/inline-sources-receipt.md'
        for n in common:payload['provider_resources/'+n]=z.read(n)
        if sibling not in manifest['files']:raise ValueError('Conditional Desktop reference is absent')
        bindings={'format':'kai.skills.provider-bindings/1','bindings':[{'id':7,'files':common+[sibling]}]}
        payload['RESOURCE_BINDINGS_009.json']=inc.json_bytes(bindings)
        inc._candidate_header(payload[main],row['name'])
    b._validate_paths(list(payload))
    for n,d in payload.items():inc._secret_preflight(n,d)
    output.mkdir(parents=True);created_files,created_dirs=[],[output]
    try:
        for n,d in sorted(payload.items()):
            b._check_stop(stop_file);b._write_new_file(output/n,d,output,created_files,created_dirs)
    except BaseException as error:
        if b._rollback_new_stage(created_files,created_dirs):
            raise RuntimeError('Incomplete cleanup; foreign data retained') from error
        raise
    return {'format':'kai.skills.own-evolution/1','base_sha256':pin,'candidate_ids':[7],
            'files':{n:inc.record(d) for n,d in sorted(payload.items())},
            'provider_runtime_modified':False,'active_installation':False,
            'existing_tooling_reused':['bundle_io','build_incremental','existing grouping engine'],
            'new_runtime_helper':False,'new_common_provider_files':0,
            'new_binding':'Existing conditional Desktop sources guide; no renderer or Desktop execution certified'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-bundle',type=Path,required=True)
    p.add_argument('--base-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stop-file',type=Path);a=p.parse_args()
    print(json.dumps(evolve(a.base_bundle,a.base_sha256,a.output,a.stop_file),indent=2))
