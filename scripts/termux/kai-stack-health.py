#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, subprocess, urllib.request
from pathlib import Path

HOME=Path.home()
ADB="adb"
SERIAL=os.environ.get("ANDROID_SERIAL","").strip()

def run(args, timeout=5):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        return {"ok":p.returncode==0,"rc":p.returncode,"out":p.stdout.strip(),"err":p.stderr.strip()}
    except Exception as e:
        return {"ok":False,"rc":None,"out":"","err":f"{type(e).__name__}: {e}"}

def pkg(name):
    r=run(["dpkg-query","-W","-f=${db:Status-Abbrev} ${Version}",name])
    if not r["ok"] or not r["out"].startswith("ii "):
        return None
    return r["out"][3:].strip() or None

def service(name):
    p=f"/data/data/com.termux/files/usr/var/service/{name}"
    r=run(["sv","status",p])
    return {"ok":r["ok"] and r["out"].startswith("run:"),"status":r["out"] or r["err"]}

def adb_serial():
    if SERIAL: return SERIAL
    r=run([ADB,"devices"])
    ds=[]
    for line in r["out"].splitlines()[1:]:
        cols=line.split()
        if len(cols)>=2 and cols[1]=="device": ds.append(cols[0])
    return ds[0] if len(ds)==1 else None

def live():
    token=HOME/".kai_mobile/kai-live-token"
    if not token.exists(): return {"ok":False,"reason":"token_missing"}
    try:
        req=urllib.request.Request("http://127.0.0.1:7190/status",headers={"Authorization":"Bearer "+token.read_text().strip()})
        with urllib.request.urlopen(req,timeout=2) as r:
            d=json.load(r)
        return {k:d.get(k) for k in ("ok","mode","sequence","frame_age_ms","frame_size","restart_count","scrcpy_alive","ffmpeg_alive","control_alive","preferred_input")}
    except Exception as e:
        return {"ok":False,"reason":f"{type(e).__name__}: {e}"}

def shizuku_present(serial):
    if not serial: return False
    r=run([ADB,"-s",serial,"shell","pm","list","packages","--user","0"])
    s=(r["out"]+"\n"+r["err"]).lower()
    return "shizuku" in s or "moe.shizuku" in s

def cpuset(pid_pattern):
    r=run(["pgrep","-f",pid_pattern])
    if not r["ok"] or not r["out"]: return None
    pid=r["out"].splitlines()[0]
    try:
        txt=Path(f"/proc/{pid}/status").read_text()
        for line in txt.splitlines():
            if line.startswith("Cpus_allowed_list:"): return line.split(":",1)[1].strip()
    except Exception: pass
    return None

serial=adb_serial()
codex_status=run(["sh","-lc",f"CODEX_HOME={HOME}/.kai_codex codex login status"])
data={
 "schema":"kai-s24-stack-health/v1",
 "android":{"serial":serial,"adb":bool(serial),"shizuku":shizuku_present(serial)},
 "core":{"proot_distro":pkg("proot-distro"),"ffmpeg":pkg("ffmpeg"),"imagemagick":pkg("imagemagick"),"tmux":pkg("tmux"),"ollama":pkg("ollama")},
 "services":{"kai_mobile":service("kai-mobile"),"minecraft_live":service("kai-minecraft-live")},
 "vision":live(),
 "agents":{"codex":pkg("codex"),"codex_logged_in":((codex_status["out"]+" "+codex_status["err"]).strip().lower().startswith("logged in")),"codex_android_sandbox_supported":False},
 "accel":{"llama_cpp":pkg("llama-cpp"),"ollama_vulkan":pkg("ollama-backend-vulkan"),"freedreno":pkg("mesa-vulkan-icd-freedreno")},
 "limits":{"minecraft_live_cpuset":cpuset("kai_minecraft_live.py")},
}
data["overall_ok"]=bool(data["android"]["adb"] and data["services"]["minecraft_live"]["ok"] and data["vision"].get("ok"))
print(json.dumps(data,ensure_ascii=False,indent=2))
