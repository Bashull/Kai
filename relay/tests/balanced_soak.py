#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, json, pathlib, statistics, time, urllib.error, urllib.request

HOME=pathlib.Path.home()
TOKEN=(HOME/".kai_mobile/kai-live-token").read_text().strip()
URL="http://127.0.0.1:7190/status"

def pct(xs,p):
    if not xs:return None
    ys=sorted(xs); i=min(len(ys)-1,max(0,round((len(ys)-1)*p)))
    return round(ys[i],2)

def status():
    req=urllib.request.Request(URL,headers={"Authorization":"Bearer "+TOKEN})
    with urllib.request.urlopen(req,timeout=2) as f:return json.load(f)

ap=argparse.ArgumentParser()
ap.add_argument("--duration",type=float,default=600.0)
ap.add_argument("--interval",type=float,default=2.0)
ap.add_argument("--output",default="")
a=ap.parse_args()
start=time.monotonic(); end=start+a.duration
ages=[]; fps=[]; samples=0; failures=[]; bad=[]; serials=[]; restart_first=None; restart_last=None
while time.monotonic()<end:
    t=time.monotonic(); samples+=1
    try:
        d=status()
        serials.append(d.get("serial"))
        rc=int(d.get("restart_count") or 0)
        if restart_first is None:restart_first=rc
        restart_last=rc
        age=d.get("frame_age_ms")
        if isinstance(age,(int,float)):ages.append(float(age))
        f=d.get("delivery_fps")
        if isinstance(f,(int,float)):fps.append(float(f))
        if not (d.get("ok") and d.get("scrcpy_alive") and d.get("ffmpeg_alive") and d.get("control_alive")):
            bad.append({"t":round(t-start,2),"ok":d.get("ok"),"scrcpy":d.get("scrcpy_alive"),"ffmpeg":d.get("ffmpeg_alive"),"control":d.get("control_alive")})
    except Exception as e:
        failures.append({"t":round(t-start,2),"error":type(e).__name__})
    left=a.interval-(time.monotonic()-t)
    if left>0:time.sleep(left)
summary={
 "duration_s":round(time.monotonic()-start,2),"interval_s":a.interval,"samples":samples,
 "transport_failures":len(failures),"unhealthy_samples":len(bad),
 "frame_age_ms":{"count":len(ages),"p50":pct(ages,.50),"p95":pct(ages,.95),"p99":pct(ages,.99),"max":round(max(ages),2) if ages else None},
 "delivery_fps":{"count":len(fps),"p50":pct(fps,.50),"p05":pct(fps,.05),"min":round(min(fps),2) if fps else None},
 "restart_count":{"first":restart_first,"last":restart_last,"delta":None if restart_first is None or restart_last is None else restart_last-restart_first},
 "serials":list(dict.fromkeys(x for x in serials if x)),
 "failures_tail":failures[-5:],"unhealthy_tail":bad[-5:]
}
out=json.dumps(summary,indent=2)
print(out)
if a.output:pathlib.Path(a.output).write_text(out+"\n")
