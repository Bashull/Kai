#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, pathlib, statistics, subprocess, time, urllib.request
H=pathlib.Path.home(); T=(H/".kai_mobile/kai-live-token").read_text().strip(); BASE="http://127.0.0.1:7190"
HDR={"Authorization":"Bearer "+T}
def pct(xs,p):
    ys=sorted(xs); return round(ys[min(len(ys)-1,max(0,round((len(ys)-1)*p)))],2)
def get_status():
    r=urllib.request.Request(BASE+"/status",headers=HDR)
    with urllib.request.urlopen(r,timeout=2) as f:return json.load(f)
def wait_next(after):
    r=urllib.request.Request(BASE+f"/next?after={after}&timeout_ms=1200",headers=HDR)
    t=time.perf_counter()
    with urllib.request.urlopen(r,timeout=2) as f:
        f.read(1); seq=int(f.headers.get("X-Kai-Sequence","0")); age=float(f.headers.get("X-Kai-Age-Ms","nan"))
    return (time.perf_counter()-t)*1000,seq,age
def post_key():
    b=json.dumps({"actions":[{"type":"key","keycode":0}]}).encode()
    r=urllib.request.Request(BASE+"/act",data=b,headers={**HDR,"Content-Type":"application/json"},method="POST")
    t=time.perf_counter()
    with urllib.request.urlopen(r,timeout=3) as f:d=json.load(f)
    wall=(time.perf_counter()-t)*1000
    return d,wall
n=30; scr_action=[];scr_next=[];scr_wall=[];adb_dispatch=[];adb_next=[];transports=[]
serial=get_status()["serial"]
for _ in range(n):
    d,w=post_key();scr_action.append(float(d["action_ms"]));scr_next.append(float(d["next_frame_ms"]));scr_wall.append(w);transports.append(d["executed"][0].get("transport"))
    time.sleep(.03)
for _ in range(n):
    s=get_status(); seq=int(s["sequence"])
    t=time.perf_counter();p=subprocess.run(["adb","-s",serial,"shell","input","keyevent","0"],capture_output=True,text=True,timeout=3)
    adb_dispatch.append((time.perf_counter()-t)*1000)
    wn,_,_=wait_next(seq);adb_next.append(wn)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    time.sleep(.03)
def stats(x):return {"n":len(x),"p50":pct(x,.5),"p95":pct(x,.95),"p99":pct(x,.99),"min":round(min(x),2),"max":round(max(x),2)}
out={"safe_event":"KEYCODE_UNKNOWN(0)","scrcpy_transport":sorted(set(transports)),"scrcpy_action_ms":stats(scr_action),"scrcpy_next_frame_ms":stats(scr_next),"scrcpy_api_wall_ms":stats(scr_wall),"adb_shell_dispatch_ms":stats(adb_dispatch),"adb_end_to_next_frame_ms":stats(adb_next)}
print(json.dumps(out,indent=2))
(H/".kai_mobile/tests/results/balanced_input_latency.json").write_text(json.dumps(out,indent=2)+"\n")
