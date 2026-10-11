#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, json, os, statistics, subprocess, time, urllib.request
from pathlib import Path

HOME = Path.home()
TOKEN_FILE = HOME / ".kai_mobile" / "kai-live-token"
OUT = HOME / ".kai_mobile" / "benchmarks" / "balanced.jsonl"

def get_status(port: int) -> dict:
    token = TOKEN_FILE.read_text().strip()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.load(r)

def shell(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=5)

def proc_snapshot():
    p = shell(["ps","-A","-o","pid,%cpu,rss,args"])
    rows = []
    for line in p.stdout.splitlines():
        if ("kai_minecraft_live.py" in line or
            "ffmpeg" in line and "image2pipe" in line or
            "com.genymobile.scrcpy.Server" in line):
            rows.append(" ".join(line.split()))
    return rows

def adb_serial():
    p = shell(["adb","devices"])
    ds=[]
    for line in p.stdout.splitlines()[1:]:
        c=line.split()
        if len(c)>=2 and c[1]=="device": ds.append(c[0])
    return ds[0] if len(ds)==1 else None

def battery_temp_c():
    serial=adb_serial()
    if not serial:return None
    p = shell(["adb","-s",serial,"shell","dumpsys","battery"])
    for line in p.stdout.splitlines():
        if "temperature:" in line:
            try: return int(line.split(":",1)[1].strip()) / 10.0
            except Exception: return None
    return None

def foreground_package():
    serial=adb_serial()
    if not serial:return None
    p = shell(["adb","-s",serial,"shell","dumpsys","activity","activities"])
    for line in p.stdout.splitlines():
        if "topResumedActivity=" in line:
            return line.strip()[-220:]
    return None

def thermal_snapshot():
    serial=adb_serial()
    if not serial:return None
    p=shell(["adb","-s",serial,"shell","dumpsys","thermalservice"])
    status=None; skin=[]
    for line in p.stdout.splitlines():
        line=line.strip()
        if line.startswith("Thermal Status:"):
            try: status=int(line.split(":",1)[1].strip())
            except Exception: pass
        if "mName=SKIN" in line and "mValue=" in line:
            try: skin.append(float(line.split("mValue=",1)[1].split(",",1)[0]))
            except Exception: pass
    return {"status":status,"skin_c_max":max(skin) if skin else None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--port", type=int, default=7190)
    ap.add_argument("--stale-ms", type=float, default=1500)
    args = ap.parse_args()
    t0 = time.monotonic()
    samples = []
    failures = []
    start_restarts = None
    while time.monotonic() - t0 < args.duration:
        ts = time.time()
        try:
            s = get_status(args.port)
            if start_restarts is None:
                start_restarts = int(s.get("restart_count", 0))
            age = s.get("frame_age_ms")
            ok = (
                s.get("ok") is True and
                s.get("scrcpy_alive") is True and
                s.get("ffmpeg_alive") is True and
                s.get("control_alive") is True and
                isinstance(age, (int,float)) and age <= args.stale_ms and
                s.get("frame_size",{}).get("width",0) > 0 and
                s.get("frame_size",{}).get("height",0) > 0
            )
            if not ok:
                failures.append({"ts":ts,"status":s})
            samples.append({
                "ts": ts,
                "ok": ok,
                "seq": s.get("sequence"),
                "frame_age_ms": age,
                "delivery_fps": s.get("delivery_fps"),
                "restart_count": s.get("restart_count"),
                "frame_size": s.get("frame_size"),
            })
        except Exception as e:
            failures.append({"ts":ts,"error":f"{type(e).__name__}: {e}"})
        time.sleep(args.interval)
    ages = [x["frame_age_ms"] for x in samples if isinstance(x.get("frame_age_ms"),(int,float))]
    fps = [x["delivery_fps"] for x in samples if isinstance(x.get("delivery_fps"),(int,float))]
    final = get_status(args.port)
    restart_delta=int(final.get("restart_count",0)) - int(start_restarts or 0)
    reasons=[x for x in final.get("diagnostic_tail",[]) if str(x).startswith("restart[")]
    orientation_reasons=[x for x in reasons if "orientation:" in str(x)]
    unexplained=max(0,restart_delta-len(orientation_reasons))
    result = {
        "profile":"balanced",
        "duration_s":args.duration,
        "interval_s":args.interval,
        "samples":len(samples),
        "failures":len(failures),
        "frame_age_ms":{
            "median":round(statistics.median(ages),1) if ages else None,
            "p95":round(sorted(ages)[max(0, min(len(ages)-1, int(len(ages)*0.95)-1))],1) if ages else None,
            "max":round(max(ages),1) if ages else None,
        },
        "delivery_fps_median":round(statistics.median(fps),2) if fps else None,
        "restart_delta":restart_delta,
        "restart_reasons":reasons,
        "unexplained_restart_delta":unexplained,
        "final_status":{k:final.get(k) for k in (
            "ok","sequence","frame_age_ms","frame_size","scrcpy_alive",
            "ffmpeg_alive","control_alive","preferred_input","restart_count"
        )},
        "battery_temp_c":battery_temp_c(),
        "thermal":thermal_snapshot(),
        "foreground":foreground_package(),
        "processes":proc_snapshot(),
        "pass":len(failures)==0 and unexplained==0,
        "failure_examples":failures[:5],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a") as f:
        f.write(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["pass"] else 2)

if __name__ == "__main__":
    main()