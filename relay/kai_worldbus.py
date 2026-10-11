#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, pathlib, sqlite3, subprocess, threading, time, urllib.parse
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
            fresh=age<0.75 and p.get("ok") is True
            seq=p.get("seq",-1)
            snapshot={
                "fresh":fresh,"age_s":round(age,3),"seq":seq,
                "hud":bool(p.get("hud_present")),"motion":p.get("motion",{}),
                "tiles":p.get("tiles",{}),"detections":p.get("detections",[]),
                "top_threat":p.get("top_threat"),"thermal":p.get("thermal",{}),
                "frame_age_ms":p.get("frame_age_ms")
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
                top=p.get("top_threat")
                sig=None if not top else (top.get("class"),round(float(top.get("confidence",0)),2),tuple(top.get("box_norm") or []))
                if sig!=last_threat:
                    if top: emit("perception","threat.detected",top,2 if top.get("danger",0)>=0.45 else 1)
                    elif last_threat is not None: emit("perception","threat.cleared",{"seq":seq},0)
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
    """Listen for KAI_EYES console.warn payloads if Minecraft content logging reaches logcat."""
    env=os.environ.copy(); env.setdefault("TMPDIR","/data/data/com.termux/files/usr/tmp")
    while not _stop.is_set():
        serial=adb_serial()
        if not serial:
            time.sleep(2); continue
        proc=None
        try:
            proc=subprocess.Popen(["adb","-s",serial,"logcat","-v","raw"],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8",errors="replace",bufsize=1,env=env)
            for line in proc.stdout:
                if _stop.is_set(): break
                mark="KAI_EYES:"
                if mark not in line: continue
                raw=line.split(mark,1)[1].strip()
                try: payload=json.loads(raw)
                except Exception:
                    emit("minecraft","telemetry.parse_error",{"raw":raw[:1000]},1)
                    continue
                with _lock: _latest["minecraft"]=payload
                put_state("minecraft",payload)
                emit("minecraft","telemetry",payload,0)
        except Exception as exc:
            emit("worldbus","logcat.error",{"error":str(exc)[:220]},1,"logcat.error")
        finally:
            if proc:
                try: proc.terminate()
                except Exception: pass
        time.sleep(1)

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
            return self.send_json({"ok":True,"service":"kai-worldbus","latest":_latest,"db":str(DB)})
        if u.path=="/state":
            return self.send_json({"ok":True,"latest":_latest})
        if u.path=="/events":
            after=int(q.get("after",["0"])[0]); limit=int(q.get("limit",["100"])[0])
            return self.send_json({"ok":True,"events":recent_events(after,limit)})
        if u.path=="/stream":
            after=int(q.get("after",["0"])[0])
            self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.send_header("Cache-Control","no-cache"); self.send_header("Connection","keep-alive"); self.end_headers()
            deadline=time.monotonic()+25
            try:
                while time.monotonic()<deadline:
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
            atomic_json(STATUS,{"ok":True,"port":PORT,"events":count,"last_event_id":maxid,"latest_keys":sorted(_latest.keys()),"updated":time.time()})
        except Exception: pass
        time.sleep(1)

if __name__=="__main__":
    emit("worldbus","service.start",{"pid":os.getpid(),"port":PORT},0)
    threading.Thread(target=perception_loop,daemon=True).start()
    threading.Thread(target=logcat_loop,daemon=True).start()
    threading.Thread(target=status_loop,daemon=True).start()
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
