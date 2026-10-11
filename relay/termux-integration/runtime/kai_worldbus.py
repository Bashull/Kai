#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, pathlib, sqlite3, subprocess, threading, time, urllib.parse, signal
from kai_nerve.perception_clock import health,TIMING_KEYS
from kai_nerve.pipeline import IngestPipeline
from kai_nerve.collector_logcat import iterate
from kai_nerve.consumption import at_consumption
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME=pathlib.Path.home()
BASE=HOME/".kai_mobile"
ROOT=BASE/"worldbus"
ROOT.mkdir(parents=True,exist_ok=True)
DB=ROOT/"kai_worldbus.db"
STATUS=ROOT/"status.json"
PERCEPTION=BASE/"perception/status.json"
TOKEN=(BASE/"kai-live-token").read_text().strip()
HOST="127.0.0.1"
PORT=int(os.environ.get("KAI_WORLDBUS_PORT","7191"))
RETENTION=int(os.environ.get("KAI_WORLDBUS_RETENTION","5000"))
POLL=float(os.environ.get("KAI_WORLDBUS_POLL","0.10"))

_lock=threading.Lock()
_latest={}
_stop=threading.Event()

def db_connect():
    cx=sqlite3.connect(DB,timeout=5,isolation_level=None,check_same_thread=False)
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA synchronous=NORMAL")
    cx.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        source TEXT NOT NULL,
        type TEXT NOT NULL,
        severity INTEGER NOT NULL DEFAULT 0,
        dedupe_key TEXT,
        payload TEXT NOT NULL
    )""")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
    cx.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
    cx.execute("""CREATE TABLE IF NOT EXISTS state(
        key TEXT PRIMARY KEY,
        updated_ts REAL NOT NULL,
        value TEXT NOT NULL
    )""")
    return cx

def atomic_json(path,obj):
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
    os.replace(tmp,path)

def emit(source,etype,payload,severity=0,dedupe_key=None):
    now=time.time()
    body=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
    with _lock:
        cx=db_connect()
        try:
            cx.execute("BEGIN IMMEDIATE")
            if dedupe_key:
                row=cx.execute("SELECT id,payload FROM events WHERE dedupe_key=? ORDER BY id DESC LIMIT 1",(dedupe_key,)).fetchone()
                if row and row[1]==body:
                    cx.execute("ROLLBACK")
                    return row[0]
            cur=cx.execute("INSERT INTO events(ts,source,type,severity,dedupe_key,payload) VALUES(?,?,?,?,?,?)",
                (now,source,etype,int(severity),dedupe_key,body))
            eid=cur.lastrowid
            cx.execute("DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id),0)-? FROM events)",(RETENTION,))
            cx.execute("COMMIT")
            return eid
        finally: cx.close()

def put_state(key,value):
    now=time.time(); body=json.dumps(value,ensure_ascii=False,separators=(",",":"))
    with _lock:
        cx=db_connect()
        try:
            cx.execute("INSERT INTO state(key,updated_ts,value) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET updated_ts=excluded.updated_ts,value=excluded.value",(key,now,body))
        finally: cx.close()

def perception_loop():
    prev={}
    stale_state=False
    last_seq=-1
    last_hot=False
    last_scene=False
    last_threat=None
    last_guard=None
    while not _stop.is_set():
        try:
            st=PERCEPTION.stat()
            age=time.time()-st.st_mtime
            p=json.loads(PERCEPTION.read_text())
            timing=health(p)
            fresh=timing["frame_fresh"]
            seq=p.get("seq",-1)
            snapshot={
                **{k:p.get(k) for k in TIMING_KEYS},"ok":p.get("ok"),
                "fresh":fresh,"age_s":round(age,3),"seq":seq,
                "hud":bool(p.get("hud_present")),"motion":p.get("motion",{}),
                "tiles":p.get("tiles",{}),"detections":p.get("detections",[]),
                "top_threat":p.get("top_threat") if timing["detection_fresh"] else None,"thermal":p.get("thermal",{}),
                **timing
            }
            with _lock:
                _latest["perception"]=snapshot
            put_state("perception",snapshot)
            if not fresh and not stale_state:
                emit("perception","stream.stale",snapshot,2,"stream.stale")
                stale_state=True
            elif fresh and stale_state:
                emit("perception","stream.recovered",snapshot,0,"stream.recovered")
                stale_state=False
            if seq!=last_seq:
                hud=bool(p.get("hud_present"))
                if prev.get("hud") is not None and hud!=prev.get("hud"):
                    emit("perception","hud.enter" if hud else "hud.exit",{"seq":seq,"score":p.get("hud_score")},0)
                guard=bool((p.get("thermal") or {}).get("guard"))
                if last_guard is not None and guard!=last_guard:
                    emit("thermal","thermal.guard_on" if guard else "thermal.guard_off",p.get("thermal") or {},1 if guard else 0)
                last_guard=guard
                top=p.get("top_threat") if timing["detection_fresh"] else None
                sig=None if not top else (top.get("class"),round(float(top.get("confidence",0)),2),tuple(top.get("box_norm") or []))
                if sig!=last_threat:
                    if top: emit("perception","threat.detected",top,2 if top.get("danger",0)>=0.45 else 1)
                    elif last_threat is not None: emit("perception","threat.cleared" if timing["detection_fresh"] else "threat.unobserved",{"seq":seq},0)
                    last_threat=sig
                hot=bool(p.get("hot"))
                if hot and not last_hot:
                    emit("perception","motion.hot",{"seq":seq,"motion":p.get("motion"),"tiles":p.get("tiles")},1)
                last_hot=hot
                scene=bool(p.get("scene_cut"))
                if scene and not last_scene:
                    emit("perception","scene.cut",{"seq":seq,"motion":p.get("motion"),"tiles":p.get("tiles")},1)
                last_scene=scene
                prev["hud"]=hud
                last_seq=seq
            time.sleep(POLL)
        except FileNotFoundError:
            time.sleep(.5)
        except Exception as exc:
            emit("worldbus","ingest.error",{"error":type(exc).__name__,"message":str(exc)[:220]},2,"ingest.error")
            time.sleep(.5)

def adb_serial():
    try:
        env=os.environ.copy(); env.setdefault("TMPDIR","/data/data/com.termux/files/usr/tmp")
        out=subprocess.check_output(["adb","devices"],text=True,timeout=3,env=env)
        for line in out.splitlines()[1:]:
            parts=line.split()
            if len(parts)>=2 and parts[1]=="device": return parts[0]
    except Exception: pass
    return None

def logcat_loop():
    """The existing WorldBus owns ingress; no third bridge or physical driver."""
    global _nerve_status
    pipe=IngestPipeline(nerve_db=ROOT/'nerve.db',replay_db=ROOT/'nerve-replay.db',worldbus_db=DB)
    try:
        while not _stop.is_set():
            try:pipe.drain_pending()
            except Exception as exc:
                _nerve_status={'state':'pending_delivery_retry','error':type(exc).__name__,'actuation_allowed':False}
                _stop.wait(2);continue
            serial=adb_serial()
            if not serial:
                _nerve_status={"state":"adb_unavailable","actuation_allowed":False}
                _stop.wait(2);continue
            try:
                _nerve_status={"state":"waiting_for_sensor","serial":serial,"engine_verified":False,"actuation_allowed":False}
                for raw,evidence,received in iterate(serial,stop_event=_stop):
                    result=pipe.process_line(raw,evidence,received)
                    if result.get('parse_error'):
                        emit('minecraft_unverified','telemetry.parse_error',{'raw':result['raw']},1)
                        continue
                    e=result['event']
                    value={"event_id":e.event_id,"session_id":e.session_id,"seq":e.source_seq,"freshness":e.freshness.value,"freshness_at_ingest":e.freshness.value,"receipt_monotonic_ms":e.receipt_monotonic_ms,"clock_instance":e.clock_instance,"max_age_ms":e.max_age_ms,"effective_age_ms":e.effective_age_ms,"provenance":e.provenance,"raw":result['raw'],"tracks":result['tracks'],"scan_state":result['scan_state'],"engine_verified":False,"actuation_allowed":False}
                    with _lock:_latest['nerve']=value
                    put_state('nerve',value)
                    _nerve_status={"state":"observing_process_bound","event_id":e.event_id,"engine_verified":False,"actuation_allowed":False}
                if not _stop.is_set():
                    _nerve_status={"state":"collector_eof_retry","engine_verified":False,"actuation_allowed":False}
                    _stop.wait(2)
            except Exception as exc:
                _nerve_status={"state":"waiting_for_minecraft" if str(exc)=='minecraft_not_running' else "collector_retry","error":type(exc).__name__,"engine_verified":False,"actuation_allowed":False}
                _stop.wait(2)
    finally:pipe.close()

_nerve_status={"state":"starting","engine_verified":False,"actuation_allowed":False}
def latest_view():
    with _lock: result=dict(_latest)
    if 'perception' in result:
        result['perception']={**result['perception'],**health(result['perception'])}
        if not result['perception']['detection_fresh']:result['perception']['top_threat']=None
    if 'nerve' in result:
        result['nerve']=at_consumption(result['nerve'])
        if result['nerve']['freshness']!='fresh':result['nerve'].update(tracks=[],scan_state='STALE_OR_UNKNOWN')
    result['nerve_collector']=dict(_nerve_status)
    return result

def recent_events(after=0,limit=100):
    cx=db_connect()
    try:
        rows=cx.execute("SELECT id,ts,source,type,severity,payload FROM events WHERE id>? ORDER BY id ASC LIMIT ?",(after,min(max(limit,1),500))).fetchall()
        return [{"id":r[0],"ts":r[1],"source":r[2],"type":r[3],"severity":r[4],"payload":json.loads(r[5])} for r in rows]
    finally: cx.close()

class Handler(BaseHTTPRequestHandler):
    server_version="KaiWorldBus/1.0"
    def log_message(self,*args): pass
    def auth(self):
        return self.headers.get("Authorization","")==f"Bearer {TOKEN}"
    def send_json(self,obj,status=200):
        b=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if not self.auth(): return self.send_json({"error":"unauthorized"},401)
        u=urllib.parse.urlparse(self.path); q=urllib.parse.parse_qs(u.query)
        if u.path=="/health":
            return self.send_json({"ok":True,"service":"kai-worldbus","latest":latest_view(),"db":str(DB)})
        if u.path=="/state":
            return self.send_json({"ok":True,"latest":latest_view()})
        if u.path=="/events":
            after=int(q.get("after",["0"])[0]); limit=int(q.get("limit",["100"])[0])
            return self.send_json({"ok":True,"events":recent_events(after,limit)})
        if u.path=="/stream":
            after=int(q.get("after",["0"])[0])
            self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.send_header("Cache-Control","no-cache"); self.send_header("Connection","keep-alive"); self.end_headers()
            deadline=time.monotonic()+25
            try:
                while time.monotonic()<deadline and not _stop.is_set():
                    ev=recent_events(after,100)
                    if ev:
                        for e in ev:
                            after=e["id"]
                            self.wfile.write(("id: %s\nevent: %s\ndata: %s\n\n"%(e["id"],e["type"],json.dumps(e,ensure_ascii=False,separators=(",",":")))).encode())
                        self.wfile.flush()
                    else:
                        self.wfile.write(b": heartbeat\n\n"); self.wfile.flush()
                    time.sleep(.5)
            except Exception: pass
            return
        return self.send_json({"error":"not_found"},404)

def status_loop():
    while not _stop.is_set():
        try:
            cx=db_connect()
            try:
                count=cx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                maxid=cx.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]
            finally: cx.close()
            atomic_json(STATUS,{"build":"termux-integration-0.4.1","pid":os.getpid(),"nerve":latest_view().get("nerve_collector"),"nerve_observation":latest_view().get("nerve"),"ok":True,"port":PORT,"events":count,"last_event_id":maxid,"latest_keys":sorted(_latest.keys()),"updated":time.time()})
        except Exception: pass
        time.sleep(1)

if __name__=="__main__":
    os.umask(0o077)
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    server.daemon_threads=True
    workers=[threading.Thread(target=fn,daemon=True) for fn in (perception_loop,logcat_loop,status_loop)]
    def shutdown(*args):
        _stop.set()
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    emit("worldbus","service.start",{"pid":os.getpid(),"port":PORT,"build":"termux-integration-0.4.1"},0)
    for worker in workers:worker.start()
    try:server.serve_forever()
    finally:
        _stop.set();server.server_close()
        deadline=time.monotonic()+6
        for worker in workers:worker.join(max(0,deadline-time.monotonic()))
