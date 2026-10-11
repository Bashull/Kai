#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import io, json, math, os, pathlib, time, urllib.request, warnings
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

seq=0
prev=None
last_detect=0.0
last_save=0.0
last_hits=[]
detect_ms=None
start=time.monotonic()
processed=0
while True:
    try:
        with req(f"/next?after={seq}&timeout_ms=1200",2.0) as f:
            raw=f.read()
            seq=int(f.headers.get("X-Kai-Sequence",seq+1))
            age=float(f.headers.get("X-Kai-Age-Ms","0") or 0)
        im=Image.open(io.BytesIO(raw)).convert("RGB")
        th=motion_thumb(im)
        motion={"global":0.0,"left":0.0,"center":0.0,"right":0.0,"top":0.0,"middle":0.0,"bottom":0.0} if prev is None else region_motion(prev,th)
        prev=th
        now=time.monotonic(); hot=motion["global"]>=MOTION_HOT
        base_interval=HOT_DETECT if hot else BASE_DETECT
        duty_cap=0.45 if hot else 0.25
        compute_guard=((detect_ms or 0.0)/1000.0)/duty_cap if detect_ms else 0.0
        interval=max(base_interval,compute_guard)
        do_detect=(now-last_detect)>=interval
        if do_detect:
            last_hits,detect_ms=detect(im); last_detect=now
        top=last_hits[0] if last_hits else None
        urgent=bool(top and ((top["class"]=="Creeper" and top["danger"]>=0.45) or top["danger"]>=0.70))
        scene_cut=motion["global"]>=SCENE_CUT
        event=urgent or scene_cut or (last_hits and now-last_save>=SAVE_GAP)
        frame_path=None
        if event and now-last_save>=SAVE_GAP:
            frame_path=FRAMES/f"{int(time.time()*1000)}_s{seq}.jpg"
            frame_path.write_bytes(raw); last_save=now; prune()
            with EVENTS.open("a") as log:
                log.write(json.dumps({"ts":time.time(),"seq":seq,"motion":motion,"detections":last_hits,"urgent":urgent,"scene_cut":scene_cut,"frame":str(frame_path)},ensure_ascii=False)+"\n")
        processed+=1
        status={
            "ok":True,"seq":seq,"frame_age_ms":round(age,2),"processed":processed,
            "uptime_s":round(time.monotonic()-start,1),"motion":{k:round(v,4) for k,v in motion.items()},
            "hot":hot,"scene_cut":scene_cut,"detections":last_hits,"top_threat":top,"urgent":urgent,
            "detector":{"model":"mob-radar best.onnx","classes":CLASSES,"confidence":CONF,"last_infer_ms":detect_ms,"base_interval_s":BASE_DETECT,"hot_interval_s":HOT_DETECT,"effective_interval_s":round(interval,3),"duty_cap":duty_cap},
            "last_event_frame":str(frame_path) if frame_path else None
        }
        atomic_json(STATUS,status)
    except KeyboardInterrupt:
        break
    except Exception as e:
        atomic_json(STATUS,{"ok":False,"seq":seq,"error":type(e).__name__,"message":str(e)[:240],"ts":time.time()})
        time.sleep(0.5)
