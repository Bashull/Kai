#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import io, json, math, os, pathlib, time, urllib.request, warnings, uuid
from kai_nerve.perception_clock import BOOT_ID,parse_frame_sequence
from collections import deque

import numpy as np
from PIL import Image
warnings.filterwarnings("ignore", message="Unsupported platform")
import onnxruntime as ort

HOME=pathlib.Path.home()
BASE=HOME/".kai_mobile"
TOKEN=(BASE/"kai-live-token").read_text().strip()
BRIDGE="http://127.0.0.1:7190"
MODEL=BASE/"models/mob-radar/best.onnx"
OUT=BASE/"perception"
FRAMES=OUT/"events"
STATUS=OUT/"status.json"
EVENTS=OUT/"events.jsonl"
CLASSES=["Creeper","Skeleton","Spider","Zombie","Enderman"]
WEIGHTS={"Creeper":1.0,"Skeleton":0.65,"Spider":0.55,"Zombie":0.55,"Enderman":0.45}
CONF=float(os.environ.get("KAI_MOB_CONF","0.50"))
BASE_DETECT=float(os.environ.get("KAI_MOB_INTERVAL","0.75"))
HOT_DETECT=float(os.environ.get("KAI_MOB_HOT_INTERVAL","0.33"))
MOTION_HOT=float(os.environ.get("KAI_MOTION_HOT","0.028"))
SCENE_CUT=float(os.environ.get("KAI_SCENE_CUT","0.10"))
SAVE_GAP=float(os.environ.get("KAI_EVENT_SAVE_GAP","0.5"))
MAX_EVENT_FILES=int(os.environ.get("KAI_EVENT_FILES","40"))
THERMAL_GUARD_ON=float(os.environ.get("KAI_BATTERY_GUARD_ON_C","40.0"))
THERMAL_GUARD_OFF=float(os.environ.get("KAI_BATTERY_GUARD_OFF_C","38.5"))
THERMAL_CHECK=float(os.environ.get("KAI_THERMAL_CHECK_S","2.0"))

OUT.mkdir(parents=True,exist_ok=True)
FRAMES.mkdir(parents=True,exist_ok=True)
session=ort.InferenceSession(str(MODEL),providers=["CPUExecutionProvider"])
input_name=session.get_inputs()[0].name

def atomic_json(path: pathlib.Path, obj):
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    os.replace(tmp,path)

def req(path, timeout=2.0):
    r=urllib.request.Request(BRIDGE+path,headers={"Authorization":"Bearer "+TOKEN})
    return urllib.request.urlopen(r,timeout=timeout)

def crop169(im: Image.Image):
    w,h=im.size; target=16/9; cur=w/h
    if cur>target:
        nw=int(h*target); x=(w-nw)//2
        return im.crop((x,0,x+nw,h))
    if cur<target:
        nh=int(w/target); y=(h-nh)//2
        return im.crop((0,y,w,y+nh))
    return im

def motion_thumb(im: Image.Image):
    g=im.convert("L").resize((160,90),Image.Resampling.BILINEAR)
    return np.asarray(g,dtype=np.int16)

def survival_hud_score(im: Image.Image):
    w,h=im.size
    crop=np.asarray(im.crop((0,0,min(w,150),min(h,22))).convert("RGB"),dtype=np.int16)
    r,g,b=crop[:,:,0],crop[:,:,1],crop[:,:,2]
    red=(r>15)&(r>g*1.22)&(r>b*1.22)
    return int(red.sum())

def region_motion(a,b):
    d=np.abs(a-b).astype(np.float32)/255.0
    h,w=d.shape
    return {
        "global":float(d.mean()),
        "left":float(d[:, :w//3].mean()),
        "center":float(d[:, w//3:2*w//3].mean()),
        "right":float(d[:, 2*w//3:].mean()),
        "top":float(d[:h//3].mean()),
        "middle":float(d[h//3:2*h//3].mean()),
        "bottom":float(d[2*h//3:].mean()),
    }

def tile_motion(a,b,cols=10,rows=6):
    """x11vnc-inspired dirty-tile map over the cheap motion thumbnail."""
    d=np.abs(a-b).astype(np.float32)/255.0
    h,w=d.shape
    hits=[]
    for ry in range(rows):
        y1=(ry*h)//rows; y2=((ry+1)*h)//rows
        for cx in range(cols):
            x1=(cx*w)//cols; x2=((cx+1)*w)//cols
            score=float(d[y1:y2,x1:x2].mean())
            hits.append((score,cx,ry))
    hits.sort(reverse=True)
    peak,cx,ry=hits[0]
    dirty=[{"x":x,"y":y,"score":round(s,4)} for s,x,y in hits[:8] if s>=0.018]
    return {
        "cols":cols,"rows":rows,"peak":round(float(peak),4),
        "peak_norm":[round((cx+0.5)/cols,3),round((ry+0.5)/rows,3)],
        "dirty_count":sum(1 for s,_,__ in hits if s>=0.018),
        "top":dirty,
    }

def detect(im: Image.Image):
    c=crop169(im.convert("RGB")).resize((1024,576),Image.Resampling.BILINEAR)
    x=np.asarray(c,dtype=np.float32).transpose(2,0,1)[None]/255.0
    t=time.perf_counter()
    out=session.run(None,{input_name:x})[0][0]
    infer_ms=(time.perf_counter()-t)*1000
    hits=[]
    for p in out:
        score=float(p[4])
        if score<CONF: continue
        cid=int(p[5])
        if cid<0 or cid>=len(CLASSES): continue
        x1,y1,x2,y2=map(float,p[:4])
        cx=((x1+x2)/2)/1024; cy=((y1+y2)/2)/576
        bw=max(0.0,(x2-x1)/1024); bh=max(0.0,(y2-y1)/576)
        area=bw*bh
        dist=math.hypot(cx-.5,cy-.5)/math.hypot(.5,.5)
        name=CLASSES[cid]
        danger=WEIGHTS[name]*score*(0.35+min(1.0,area*8.0))*(1.25-0.55*min(1.0,dist))
        hits.append({"class":name,"confidence":round(score,4),"box_norm":[round(cx,4),round(cy,4),round(bw,4),round(bh,4)],"area":round(area,5),"center_distance":round(dist,4),"danger":round(danger,4)})
    hits.sort(key=lambda z:z["danger"],reverse=True)
    return hits,round(infer_ms,2)

def prune():
    files=sorted(FRAMES.glob("*.jpg"),key=lambda p:p.stat().st_mtime,reverse=True)
    for p in files[MAX_EVENT_FILES:]:
        try:p.unlink()
        except:pass

def find_battery_temp_path():
    root=pathlib.Path("/sys/class/thermal")
    for p in root.glob("thermal_zone*/type"):
        try:
            if p.read_text().strip()=="battery":
                return p.parent/"temp"
        except Exception:
            pass
    return None

BATTERY_TEMP_PATH=find_battery_temp_path()
def read_battery_temp_c():
    if not BATTERY_TEMP_PATH:
        return None
    try:
        return float(BATTERY_TEMP_PATH.read_text().strip())/1000.0
    except Exception:
        return None

seq=0
session_id=uuid.uuid4().hex
captured_mono=None
previous_frame_seq=None
detection_observed_mono=None
detection_seq=None
prev=None
last_detect=0.0
last_save=0.0
last_event_path=None
last_hits=[]
prev_hud=None
detect_ms=None
battery_temp_c=read_battery_temp_c()
thermal_guard=bool(battery_temp_c is not None and battery_temp_c>=THERMAL_GUARD_ON)
last_thermal_check=0.0
start=time.monotonic()
processed=0
while True:
    try:
        request_started=time.monotonic()
        with req(f"/next?after={seq}&timeout_ms=1200",2.0) as f:
            raw=f.read()
            seq=parse_frame_sequence(f.headers.get("X-Kai-Sequence"))
            header_age=f.headers.get("X-Kai-Age-Ms")
            try: age=float(header_age)
            except (ValueError,TypeError):age=None
            if age is not None and (not math.isfinite(age) or age<0):age=None
        if seq != previous_frame_seq:
            captured_mono=request_started-age/1000 if age is not None else None
            previous_frame_seq=seq
        elif age is None:
            captured_mono=None
        im=Image.open(io.BytesIO(raw)).convert("RGB")
        hud_score=survival_hud_score(im)
        if prev_hud is None:
            hud=hud_score>=300
        elif prev_hud:
            hud=hud_score>=120
        else:
            hud=hud_score>=300
        hud_changed=(prev_hud is not None and hud!=prev_hud)
        prev_hud=hud
        th=motion_thumb(im)
        motion={"global":0.0,"left":0.0,"center":0.0,"right":0.0,"top":0.0,"middle":0.0,"bottom":0.0} if prev is None else region_motion(prev,th)
        tiles={"cols":10,"rows":6,"peak":0.0,"peak_norm":[0.5,0.5],"dirty_count":0,"top":[]} if prev is None else tile_motion(prev,th)
        prev=th
        now=time.monotonic(); hot=motion["global"]>=MOTION_HOT
        if now-last_thermal_check>=THERMAL_CHECK:
            t=read_battery_temp_c()
            if t is not None:
                battery_temp_c=t
                if not thermal_guard and t>=THERMAL_GUARD_ON: thermal_guard=True
                elif thermal_guard and t<=THERMAL_GUARD_OFF: thermal_guard=False
            last_thermal_check=now
        base_interval=HOT_DETECT if hot else BASE_DETECT
        duty_cap=0.45 if hot else 0.25
        if thermal_guard:
            base_interval=max(base_interval,1.0 if hot else 3.0)
            duty_cap=0.22 if hot else 0.10
        compute_guard=((detect_ms or 0.0)/1000.0)/duty_cap if detect_ms else 0.0
        interval=max(base_interval,compute_guard)
        do_detect=hud and (now-last_detect)>=interval
        if do_detect:
            last_hits,detect_ms=detect(im); last_detect=now
            detection_observed_mono=captured_mono; detection_seq=seq
        elif not hud:
            last_hits=[]
            detection_observed_mono=None; detection_seq=None
        top=last_hits[0] if last_hits else None
        urgent=bool(top and ((top["class"]=="Creeper" and top["danger"]>=0.45) or top["danger"]>=0.70))
        scene_cut=motion["global"]>=SCENE_CUT
        event=urgent or scene_cut or hot or hud_changed or (last_hits and now-last_save>=SAVE_GAP)
        frame_path=None
        if event and now-last_save>=SAVE_GAP:
            frame_path=FRAMES/f"{int(time.time()*1000)}_s{seq}.jpg"
            frame_path.write_bytes(raw); last_save=now; last_event_path=frame_path; prune()
            with EVENTS.open("a") as log:
                log.write(json.dumps({"ts":time.time(),"seq":seq,"motion":motion,"detections":last_hits,"urgent":urgent,"scene_cut":scene_cut,"frame":str(frame_path)},ensure_ascii=False)+"\n")
        processed+=1
        published_mono=time.monotonic()
        status={
            "build":"termux-integration-0.4.1","pid":os.getpid(),"boot_id":BOOT_ID,"session_id":session_id,
            "captured_mono_s":captured_mono,"published_mono_s":published_mono,
            "detection_observed_mono_s":detection_observed_mono,"detection_seq":detection_seq,
            "ok":True,"seq":seq,"frame_age_ms":round((time.monotonic()-captured_mono)*1000,2) if captured_mono is not None else None,"processed":processed,
            "uptime_s":round(time.monotonic()-start,1),"hud_present":hud,"hud_score":hud_score,"hud_changed":hud_changed,"motion":{k:round(v,4) for k,v in motion.items()},
            "tiles":tiles,"hot":hot,"scene_cut":scene_cut,"detections":last_hits,"top_threat":top,"urgent":urgent,
            "detector":{"model":"mob-radar best.onnx","classes":CLASSES,"confidence":CONF,"last_infer_ms":detect_ms,"base_interval_s":BASE_DETECT,"hot_interval_s":HOT_DETECT,"effective_interval_s":round(interval,3),"duty_cap":duty_cap},
            "thermal":{"battery_c":round(battery_temp_c,2) if battery_temp_c is not None else None,"guard":thermal_guard,"guard_on_c":THERMAL_GUARD_ON,"guard_off_c":THERMAL_GUARD_OFF},
            "last_event_frame":str(last_event_path) if last_event_path else None
        }
        atomic_json(STATUS,status)
    except KeyboardInterrupt:
        break
    except Exception as e:
        atomic_json(STATUS,{"build":"termux-integration-0.4.1","pid":os.getpid(),"boot_id":BOOT_ID,"session_id":session_id,"ok":False,"seq":seq,"error":type(e).__name__,"message":str(e)[:240],"ts":time.time()})
        time.sleep(0.5)
