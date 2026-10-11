#!/data/data/com.termux/files/usr/bin/python
import json, sys, urllib.request
from pathlib import Path
BASE="http://127.0.0.1:7190"
TOKEN=Path.home().joinpath(".kai_mobile/kai-live-token").read_text().strip()
def call(path,payload=None):
    url=BASE+path+"?token="+TOKEN
    if payload is None:
        req=urllib.request.Request(url,method="GET")
    else:
        body=json.dumps(payload).encode()
        req=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=4) as r:
        print(r.read().decode())
cmd=sys.argv[1]
if cmd=="status": call("/status")
elif cmd=="tap":
    x=float(sys.argv[2]); y=float(sys.argv[3]); hold=int(sys.argv[4]) if len(sys.argv)>4 else 180
    call("/act",{"actions":[{"type":"tap","space":"frame","x":x,"y":y,"hold_ms":hold}]})
elif cmd=="swipe":
    x1,y1,x2,y2=map(float,sys.argv[2:6]); dur=int(sys.argv[6]) if len(sys.argv)>6 else 300
    call("/act",{"actions":[{"type":"swipe","space":"frame","x1":x1,"y1":y1,"x2":x2,"y2":y2,"duration_ms":dur}]})
elif cmd=="key": call("/act",{"actions":[{"type":"key","keycode":int(sys.argv[2])}]})
else: raise SystemExit("usage: kai-live-client status|tap x y [hold]|swipe x1 y1 x2 y2 [ms]|key code")
