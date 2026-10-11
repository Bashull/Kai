#!/data/data/com.termux/files/usr/bin/python
"""Read-only Balanced profile preflight; never launches Minecraft or modifies Android."""
from __future__ import annotations
import json, pathlib, subprocess, time, urllib.error, urllib.request

H=pathlib.Path.home(); S=H/".kai_mobile"; P=S/"profiles"/"active.env"
def cmd(*a,timeout=5):
    try:
        p=subprocess.run(a,text=True,capture_output=True,timeout=timeout)
        return {"ok":p.returncode==0,"output":(p.stdout or p.stderr).strip()[:320]}
    except Exception as e:return {"ok":False,"error":type(e).__name__}

report={"timestamp":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"profile":{},"checks":{}}
for line in P.read_text().splitlines():
    if line.startswith("export KAI_") and "=" in line:
        k,v=line.removeprefix("export ").split("=",1)
        if not any(x in k for x in ("TOKEN","SECRET","PASSWORD")):report["profile"][k]=v.strip("\"'")

report["checks"]["codex"]=cmd("codex","--version")
report["checks"]["ffmpeg"]=cmd("ffmpeg","-version")
report["checks"]["scrcpy"]=cmd("scrcpy","--version")
report["checks"]["adb"]=cmd("adb","devices","-l")
report["checks"]["service"]=cmd("sv","status","/data/data/com.termux/files/usr/var/service/kai-minecraft-live")
report["checks"]["python_compile"]=cmd("python","-m","py_compile",str(S/"kai_minecraft_live.py"))
try:
    urllib.request.urlopen("http://127.0.0.1:7190/status",timeout=2)
    report["checks"]["anonymous_auth"]={"ok":False,"reason":"unexpected anonymous success"}
except urllib.error.HTTPError as e:
    report["checks"]["anonymous_auth"]={"ok":e.code==401,"http":e.code}
except Exception as e:
    report["checks"]["anonymous_auth"]={"ok":False,"reason":type(e).__name__}
try:
    token=(S/"kai-live-token").read_text().strip()
    req=urllib.request.Request("http://127.0.0.1:7190/status",headers={"Authorization":"Bearer "+token})
    with urllib.request.urlopen(req,timeout=2) as f:
        d=json.load(f)
    keys=("ok","serial","sequence","delivery_fps","frame_age_ms","frame_size","logical_size","scrcpy_alive","ffmpeg_alive","control_alive","preferred_input","restart_count")
    report["checks"]["stream"]={k:d.get(k) for k in keys}
except Exception as e:report["checks"]["stream"]={"ok":False,"reason":type(e).__name__}
print(json.dumps(report,indent=2,ensure_ascii=False))
