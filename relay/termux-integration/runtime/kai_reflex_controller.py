#!/data/data/com.termux/files/usr/bin/python
"""Kai reflex controller: local, fail-closed and independent of chat latency.
Disabled for physical input by default; KAI_REFLEX_ARMED=1 enables evasive movement.
"""
import json, os, pathlib, time, urllib.request
from kai_nerve.perception_clock import health
HOME=pathlib.Path.home()
BASE=HOME/".kai_mobile"
PERCEPTION=BASE/"perception/status.json"
STATE=BASE/"reflex/status.json"
LOG=BASE/"reflex/events.jsonl"
TOKEN=(BASE/"kai-live-token").read_text().strip()
HOST="http://127.0.0.1:7190"
ARMED=os.environ.get("KAI_REFLEX_ARMED","0")=="1"
MIN_CONF=float(os.environ.get("KAI_REFLEX_MIN_CONF","0.75"))
MIN_AREA=float(os.environ.get("KAI_REFLEX_MIN_AREA","0.012"))
MAX_AGE=float(os.environ.get("KAI_REFLEX_MAX_STATUS_AGE","0.5"))
COOLDOWN=float(os.environ.get("KAI_REFLEX_COOLDOWN","2.5"))
BASE.joinpath("reflex").mkdir(exist_ok=True)
last_seq=-1; last_action=0; last_event=""
def write_status(payload):
    tmp=STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    os.replace(tmp,STATE)
def emit(payload):
    with LOG.open("a") as f:f.write(json.dumps(payload,ensure_ascii=False)+"\n")
def evade(side):
    # Movement control mapping must be calibrated before arming.
    # The controller deliberately never invents joystick coordinates.
    raise RuntimeError("movement_mapping_unverified")
while True:
    try:
        raw=PERCEPTION.read_bytes()
        age=time.time()-PERCEPTION.stat().st_mtime
        p=json.loads(raw)
        seq=p.get("seq",-1)
        hud=bool(p.get("hud_present"))
        hits=p.get("detections") or []
        creepers=[h for h in hits if h.get("class")=="Creeper" and h.get("confidence",0)>=MIN_CONF and h.get("area",0)>=MIN_AREA]
        timing=health(p,MAX_AGE*1000)
        fresh=timing["detection_fresh"]
        danger=bool(fresh and hud and creepers)
        action="none"
        reason="no_verified_creeper"
        if not fresh:reason="stale_or_failed_perception"
        elif not hud:reason="not_in_survival"
        elif danger:
            reason="verified_creeper_close"
            if seq!=last_seq and time.monotonic()-last_action>=COOLDOWN:
                if ARMED:
                    try:
                        evade("right" if creepers[0]["box_norm"][0]<.5 else "left")
                    except RuntimeError:
                        action="blocked_uncalibrated_movement"
                else:
                    action="alert_only_not_armed"
                last_action=time.monotonic()
                event={"ts":time.time(),"seq":seq,"reason":reason,"action":action,"creeper":creepers[0]}
                emit(event)
        last_seq=seq
        write_status({"build":"termux-integration-0.4.1","pid":os.getpid(),"timing":timing,"ok":True,"armed":ARMED,"age_s":round(age,3),"seq":seq,"hud":hud,"danger":danger,"action":action,"reason":reason,"cooldown_s":COOLDOWN,"requires":"calibrated joystick mapping before physical evasion"})
        time.sleep(.10)
    except KeyboardInterrupt:break
    except Exception as exc:
        write_status({"ok":False,"error":str(exc)[:180],"armed":ARMED})
        time.sleep(.5)
