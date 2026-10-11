from __future__ import annotations
import os,subprocess,time,secrets,select
from dataclasses import dataclass
from .models import ProvenanceEvidence,ProvenanceLevel
from .parsers import parse_line
@dataclass(frozen=True)
class MinecraftProcess:
    serial:str;pid:int;package:str='com.mojang.minecraftpe'
def adb_env():
    e=os.environ.copy();e.setdefault('TMPDIR','/data/data/com.termux/files/usr/tmp');return e
def resolve_minecraft(serial,package='com.mojang.minecraftpe'):
    out=subprocess.check_output(['adb','-s',serial,'shell','pidof',package],text=True,timeout=3,env=adb_env()).strip().split()
    if not out: raise RuntimeError('minecraft_not_running')
    return MinecraftProcess(serial,int(out[0]),package)
def logcat_command(p:MinecraftProcess):
    return ['adb','-s',p.serial,'logcat',f'--pid={p.pid}','-v','epoch','-T','1']
def evidence_for(p:MinecraftProcess,collector_instance:str,*,sensor_authenticated:bool=False,challenge:str|None=None,protocol:str|None=None):
    return ProvenanceEvidence(ProvenanceLevel.PROCESS_BOUND,'kai_nerve.logcat_pid','adb.logcat.pid',{'serial':p.serial,'minecraft_pid':p.pid,'package':p.package,'pid_filter':True,'collector_instance':collector_instance,'sensor_authenticated':sensor_authenticated,'challenge_matched':sensor_authenticated,'engine_boundary_verified':False,'protocol':protocol})
def _auth(obs,expected_challenge):
    payload=obs.payload or {}; proto=str(payload.get('_protocol_version') or '')
    actual=payload.get('challenge')
    # Only the canonical KAI NERVE protocol may satisfy the actuation-auth challenge.
    ok=bool(obs.source=='minecraft.kai_nerve' and proto=='4' and expected_challenge is not None and actual==expected_challenge)
    return ok,actual,proto
def iterate(serial:str,package='com.mojang.minecraftpe',expected_challenge:str|None=None,stop_event=None,max_wait_s=None):
    instance=secrets.token_urlsafe(10); p=resolve_minecraft(serial,package)
    proc=subprocess.Popen(logcat_command(p),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=adb_env())
    pending=b'';discard=False;last_check=time.monotonic();started=last_check
    try:
        while stop_event is None or not stop_event.is_set():
            if max_wait_s is not None and time.monotonic()-started>=max_wait_s:return
            if time.monotonic()-last_check>=2:
                if resolve_minecraft(serial,package).pid!=p.pid:raise RuntimeError('minecraft_pid_rotated')
                last_check=time.monotonic()
            ready,_,_=select.select([proc.stdout],[],[],.25)
            if not ready:
                if proc.poll() is not None:return
                continue
            data=os.read(proc.stdout.fileno(),8192)
            if not data:return
            pending+=data
            while b'\n' in pending:
                line,pending=pending.split(b'\n',1)
                if discard:discard=False;continue
                if len(line)>65536:continue
                if not any(m in line for m in (b'KAI_EYES:',b'KAIHB|',b'KAINERVE|')):continue
                obs=parse_line(line.decode('utf8',errors='replace'))
                authenticated,actual,proto=_auth(obs,expected_challenge) if obs else (False,None,None)
                yield line,evidence_for(p,instance,sensor_authenticated=authenticated,challenge=actual,protocol=proto),time.time()*1000
            if len(pending)>65536:pending=b'';discard=True
    finally:
        try:proc.terminate();proc.wait(timeout=1)
        except Exception:
            try:proc.kill();proc.wait(timeout=1)
            except Exception:pass
