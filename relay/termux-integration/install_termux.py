#!/usr/bin/env python3
"""Versioned Termux deployment. Preflight by default; --apply publishes and verifies.
Rollback restores only run scripts and wrappers; it never discards DB events.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shutil,sqlite3,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
HOME_PATH=Path.home()
PREFIX=Path('/data/data/com.termux/files/usr')
BASE=HOME_PATH/'.kai_mobile'
SERVICES=PREFIX/'var/service'
BUILD='termux-integration-0.4.1'
PAIRS={'kai-minecraft-perception':'kai_perception_live.py','kai-minecraft-worldbus':'kai_worldbus.py','kai-minecraft-reflex':'kai_reflex_controller.py'}
PREIMAGES={'kai_worldbus.py':'6e96cc636e61e6f82b6e528af4f7ce1a47b46d4ef69337c78548675174ae79fb','kai_perception_live.py':'5615619c4f7567e537eb2e6031c50dff052712ed20c840d475411d29757e2b6e','kai_reflex_controller.py':'d4dc2dbb4ff916d12dbf2ea6bf6dbd9ef266802f8568494ce88187fa4140cc9a'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kwargs):return subprocess.run(args,check=True,timeout=60,**kwargs)
def atomic(path,data,mode=0o700):
    tmp=path.with_name(path.name+'.integration.tmp');tmp.write_bytes(data);tmp.chmod(mode);os.replace(tmp,path)
def sv(action,service):return run(['sv','-w','10',action,str(SERVICES/service)],capture_output=True,text=True)
def preflight():
    if not (PREFIX/'bin/python').exists():raise RuntimeError('Termux_required')
    for name,digest in PREIMAGES.items():
        if sha(BASE/name)!=digest:raise RuntimeError('preimage_changed:'+name)
    for sub in ['nerve','harvester']:
        run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=ROOT/sub)
    for f in (ROOT/'runtime').glob('*.py'):compile(f.read_text(),str(f),'exec')
    with sqlite3.connect((BASE/'worldbus/kai_worldbus.db').as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    print('PREFLIGHT_PASS',flush=True)
def restore(backup):
    saved=json.loads((backup/'deployment.json').read_text())
    for name in PAIRS:sv('down',name)
    for name in PAIRS:atomic(SERVICES/name/'run',(backup/(name+'.run')).read_bytes())
    for name,meta in saved['wrappers'].items():
        target=PREFIX/'bin'/name
        if meta['exists']:atomic(target,(backup/(name+'.wrapper')).read_bytes())
        else:target.unlink(missing_ok=True)
    for name in PAIRS:sv('up',name)
    print('ROLLBACK_RUN_SCRIPTS_RESTORED',flush=True)
def deploy():
    preflight();os.umask(0o077)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=HOME_PATH/'KAI_RUNTIME_LAB/TERMUX_INTEGRATION_20261011'/('deployment-'+stamp);backup.mkdir(parents=True,exist_ok=False)
    dest=BASE/'releases'/('nerve-0.4.1-'+sha(ROOT/'runtime/kai_worldbus.py')[:12])
    harv=HOME_PATH/'KAI_TOOLS/kai-harvester-fusion-v0.2.2'
    if dest.exists() or harv.exists():raise RuntimeError('versioned_destination_exists_review_before_retry')
    before_capture=json.loads((BASE/'perception/status.json').read_text()).get('ok') is True
    saved={'build':BUILD,'utc':stamp,'dest':str(dest),'harvester':str(harv),'wrappers':{},'services_before':{}}
    for name,file in PAIRS.items():
        shutil.copy2(SERVICES/name/'run',backup/(name+'.run'));shutil.copy2(BASE/file,backup/file)
        saved['services_before'][name]=sv('status',name).stdout.strip()
    for name in ['kai-nerve','kai-harvest-v022','kai-harvest-next']:
        f=PREFIX/'bin'/name;saved['wrappers'][name]={'exists':f.exists()}
        if f.exists():shutil.copy2(f,backup/(name+'.wrapper'))
    with sqlite3.connect((BASE/'worldbus/kai_worldbus.db').as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(backup/'worldbus-consistent.sqlite3') as target:db.backup(target)
    (backup/'deployment.json').write_text(json.dumps(saved,indent=2))
    dest.parent.mkdir(parents=True,exist_ok=True)
    stage=dest.with_name(dest.name+'.staging');stage.mkdir()
    for name in ['nerve','runtime']:shutil.copytree(ROOT/name,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    os.replace(stage,dest)
    hs=harv.with_name(harv.name+'.staging');shutil.copytree(ROOT/'harvester',hs,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));os.replace(hs,harv)
    # Preserve the known parent-owned logcat child so it can be retired after stopping the old parent.
    wbpid=int(re.search(r'\(pid (\d+)\)',saved['services_before']['kai-minecraft-worldbus']).group(1));children=[]
    try:
        for pid in set(pid for task in (Path('/proc')/str(wbpid)/'task').glob('*/children') for pid in task.read_text().split()):
            args=(Path('/proc')/pid/'cmdline').read_bytes().split(b'\0')
            if args and Path(os.fsdecode(args[0])).name=='adb' and b'logcat' in args:children.append((int(pid),args))
    except OSError:pass
    try:
        deployment_started=time.time()
        for name in PAIRS:sv('down',name)
        for pid,original_args in children:
            try:
                if (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')==original_args:os.kill(pid,15)
            except (OSError,ProcessLookupError):pass
        for name,file in PAIRS.items():
            body=f'#!{PREFIX}/bin/sh\numask 077\nexport HOME={HOME_PATH}\nexport TMPDIR={PREFIX}/tmp\nexport PYTHONPATH={dest}/nerve\n'
            if name=='kai-minecraft-reflex':body+='export KAI_REFLEX_ARMED=0\n'
            body+=f'exec {PREFIX}/bin/python -P {dest}/runtime/{file}\n';atomic(SERVICES/name/'run',body.encode())
        wrappers={'kai-nerve':(dest/'nerve','kai_nerve.cli'),'kai-harvest-v022':(harv,'kai_harvester'),'kai-harvest-next':(harv,'kai_harvester')}
        for name,(source,module) in wrappers.items():
            atomic(PREFIX/'bin'/name,f'#!{PREFIX}/bin/sh\numask 077\nexport PYTHONPATH={source}\nexec {PREFIX}/bin/python -P -m {module} "$@"\n'.encode())
        for name in PAIRS:sv('up',name)
        expected={'perception','worldbus','reflex'};states={}
        for attempt in range(30):
            for short in expected:
                try:states[short]=json.loads((BASE/short/'status.json').read_text())
                except (OSError,ValueError):pass
            if all(states.get(x,{}).get('build')==BUILD and (states[x].get('ok') is True or (x=='perception' and not before_capture)) and (BASE/x/'status.json').stat().st_mtime>=deployment_started for x in expected):break
            time.sleep(.5)
        else:raise RuntimeError('new_runtime_not_healthy')
        if states['reflex'].get('armed') is not False:raise RuntimeError('reflex_not_disarmed')
        saved['services_after']={n:sv('status',n).stdout.strip() for n in PAIRS}
        for name,file in PAIRS.items():
            pid=int(re.search(r'\(pid (\d+)\)',saved['services_after'][name]).group(1))
            old_pid=int(re.search(r'\(pid (\d+)\)',saved['services_before'][name]).group(1))
            args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
            if pid==old_pid or os.fsencode(dest/'runtime'/file) not in args:raise RuntimeError('process_identity_not_verified:'+name)
            short=name.removeprefix('kai-minecraft-')
            if states[short].get('pid')!=pid:raise RuntimeError('status_pid_mismatch:'+name)
        saved['verified_states']=states;saved['runtime_files']={n:sha(dest/'runtime'/n) for n in PREIMAGES}
        saved['status']='DEPLOYED_OBSERVATION_ONLY' if states['perception'].get('ok') else 'DEPLOYED_CAPTURE_UNAVAILABLE'
        saved['capture_operational']=states['perception'].get('ok') is True
        (backup/'deployment.json').write_text(json.dumps(saved,indent=2))
        print(json.dumps({'status':saved['status'],'backup':str(backup),'release':str(dest),'harvester':str(harv),'services':saved['services_after']},indent=2),flush=True)
    except BaseException:
        restore(backup);raise
    return backup
if __name__=='__main__':
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group();g.add_argument('--apply',action='store_true');g.add_argument('--rollback',type=Path);a=parser.parse_args()
    if a.rollback:restore(a.rollback)
    elif a.apply:deploy()
    else:preflight()
