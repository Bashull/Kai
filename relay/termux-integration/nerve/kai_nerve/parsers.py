from __future__ import annotations
import json, math, re
from .models import ParsedObservation

SESSION_RE=re.compile(r'^[A-Za-z0-9._~:-]{1,160}$')

def _strict_int(v):
    return v if type(v) is int and 0 <= v <= 9007199254740991 else None

def _float(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)): return None
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None

def _session(v):
    if not isinstance(v,str):return None
    v=v.strip()
    return v if SESSION_RE.fullmatch(v) else None

def _obs(source,kind,payload):
    return ParsedObservation(source,kind,payload,
        _session(payload.get('session_id') or payload.get('session')),
        _strict_int(payload.get('seq')),
        _float(payload.get('observed_wall_ms',payload.get('wall_ms'))),
        _strict_int(payload.get('tick')),
        payload.get('provenance') if isinstance(payload.get('provenance'),dict) else None)

def _parse_line(line:str)->ParsedObservation|None:
    line=line.strip()
    if 'KAI_EYES:' in line:
        p=json.loads(line.split('KAI_EYES:',1)[1].strip()); return _obs('minecraft.kai_eyes',str(p.get('kind') or p.get('type') or 'telemetry'),p)
    if 'KAIHB|' in line:
        line=line[line.find('KAIHB|'):]; parts=line.split('|',2)
        if len(parts)!=3:return None
        p=json.loads(parts[2]); return _obs('minecraft.hyperbridge',parts[1],p)
    if 'KAINERVE|' in line:
        line=line[line.find('KAINERVE|'):]; parts=line.split('|',3)
        if len(parts)!=4 or parts[1] not in {'1','2','3','4'}: return None
        p=json.loads(parts[3]); o=_obs('minecraft.kai_nerve',parts[2],p); o.payload['_protocol_version']=parts[1]; return o
    return None

def parse_mcwss_frame(frame:dict)->ParsedObservation|None:
    body=frame.get('body') or {}; props=body.get('properties') or {}
    for item in [body.get('message'),props.get('Message'),props.get('message'),body.get('statusMessage'),props.get('StatusMessage')]:
        if isinstance(item,str):
            o=parse_line(item)
            if o:return o
    return None

MAX_LINE_BYTES=65536
def parse_line(line:str)->ParsedObservation|None:
    if not isinstance(line,str) or len(line.encode('utf-8')) > MAX_LINE_BYTES: return None
    try:
        o=_parse_line(line)
        if o is None or not isinstance(o.payload,dict): return None
        if len(o.kind)>64: return None
        return o
    except (ValueError,TypeError,AttributeError,RecursionError):
        return None
