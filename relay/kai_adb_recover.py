#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, pathlib, re, subprocess, time

HOME=pathlib.Path.home()
BASE=HOME/".kai_mobile"
OUT=BASE/"adb-recover"
OUT.mkdir(parents=True,exist_ok=True)
STATUS=OUT/"status.json"
ADB="/data/data/com.termux/files/usr/bin/adb"
NMAP="/data/data/com.termux/files/usr/bin/nmap"
os.environ.setdefault("TMPDIR","/data/data/com.termux/files/usr/tmp")
SCAN_MIN=int(os.environ.get("KAI_ADB_SCAN_MIN","30000"))
SCAN_MAX=int(os.environ.get("KAI_ADB_SCAN_MAX","60000"))
IDLE=float(os.environ.get("KAI_ADB_RECOVER_IDLE_S","5"))
RETRY=float(os.environ.get("KAI_ADB_RECOVER_RETRY_S","20"))

def run(args,timeout=6):
    try:
        p=subprocess.run(args,text=True,capture_output=True,timeout=timeout)
        return p.returncode,(p.stdout+p.stderr).strip()
    except Exception as e:
        return 124,str(e)

def devices():
    _,out=run([ADB,"devices","-l"],3)
    good=[]; bad=[]
    for line in out.splitlines()[1:]:
        if not line.strip(): continue
        serial=line.split()[0]
        if "\tdevice" in line or re.search(r"\sdevice\s",line): good.append(serial)
        else: bad.append(serial)
    return good,bad,out

def atomic(obj):
    tmp=STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False))
    os.replace(tmp,STATUS)

last_scan=0.0
scans=0
while True:
    good,bad,raw=devices()
    if good:
        for s in bad:
            if s.startswith(("127.0.0.1:","localhost:")): run([ADB,"disconnect",s],2)
        atomic({"ok":True,"connected":True,"serials":good,"last_scan_at":last_scan or None,"scans":scans,"ts":time.time()})
        time.sleep(IDLE)
        continue
    now=time.time()
    if now-last_scan < RETRY:
        atomic({"ok":True,"connected":False,"state":"waiting","last_scan_at":last_scan or None,"scans":scans,"ts":now})
        time.sleep(2)
        continue
    last_scan=now; scans+=1
    rc,out=run([NMAP,"-n","-Pn","-T5","--min-rate","2500","-p",f"{SCAN_MIN}-{SCAN_MAX}","--open","127.0.0.1"],25)
    ports=[]
    for m in re.finditer(r"^(\d+)/tcp\s+open\b",out,re.M):
        ports.append(int(m.group(1)))
    winner=None
    attempts=[]
    for p in ports:
        serial=f"127.0.0.1:{p}"
        rc2,o2=run([ADB,"connect",serial],2.2)
        g,b,_=devices()
        ok=serial in g
        attempts.append({"port":p,"ok":ok,"reply":o2[:120]})
        if ok:
            winner=serial
            break
        run([ADB,"disconnect",serial],1.5)
    good,bad,_=devices()
    for s in bad:
        if s.startswith(("127.0.0.1:","localhost:")): run([ADB,"disconnect",s],1.5)
    atomic({"ok":True,"connected":bool(good),"serials":good,"winner":winner,"ports":ports,"attempts":attempts[-12:],"last_scan_at":last_scan,"scans":scans,"ts":time.time()})
    time.sleep(IDLE if good else 2)
