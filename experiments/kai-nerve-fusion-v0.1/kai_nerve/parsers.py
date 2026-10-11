from __future__ import annotations
import json
from .models import ParsedObservation

def _int(v):
    try:return int(v)
    except (TypeError,ValueError):return None
def _float(v):
    try:return float(v)
    except (TypeError,ValueError):return None

def parse_line(line:str,*,transport="unknown"):
    line=line.strip()
    if "KAI_EYES:" in line:
        p=json.loads(line.split("KAI_EYES:",1)[1].strip())
        return ParsedObservation("minecraft.kai_eyes",str(p.get("kind") or p.get("type") or "telemetry"),
            p,p.get("session_id") or p.get("session"),_int(p.get("seq")),
            _float(p.get("observed_wall_ms") or p.get("wall_ms")),_int(p.get("tick")),
            {"transport":transport,"format":"KAI_EYES"})
    if line.startswith("KAIHB|"):
        q=line.split("|",2)
        if len(q)!=3:return None
        p=json.loads(q[2])
        return ParsedObservation("minecraft.hyperbridge",q[1],p,p.get("session_id") or p.get("session"),
            _int(p.get("seq")),_float(p.get("observed_wall_ms") or p.get("wall_ms")),_int(p.get("tick")),
            {"transport":transport,"format":"KAIHB"})
    if line.startswith("KAINERVE|"):
        q=line.split("|",3)
        if len(q)!=4 or q[1]!="1":return None
        p=json.loads(q[3])
        return ParsedObservation("minecraft.kai_nerve",q[2],p,p.get("session_id"),_int(p.get("seq")),
            _float(p.get("observed_wall_ms")),_int(p.get("tick")),
            {"transport":transport,"format":"KAINERVE/1"})
    return None

def parse_mcwss_frame(frame:dict,*,bridge_id="mcwss"):
    b=frame.get("body") or {}; props=b.get("properties") or {}
    candidates=[b.get("message"),props.get("Message"),props.get("message"),
                b.get("statusMessage"),props.get("StatusMessage")]
    for item in candidates:
        if not isinstance(item,str):continue
        for marker in ("KAINERVE|","KAI_EYES:","KAIHB|"):
            i=item.find(marker)
            if i>=0:
                x=parse_line(item[i:],transport="mcwss")
                if x:
                    x.provenance.update({"bridge_id":bridge_id});return x
    return None
