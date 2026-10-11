#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import collections, json, os, random, re, secrets, signal, socket, struct, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOME=Path.home()
HOST=os.environ.get("KAI_LIVE_HOST","127.0.0.1")
PORT=int(os.environ.get("KAI_LIVE_PORT","7190"))
FORWARD_PORT=int(os.environ.get("KAI_LIVE_FORWARD","27185"))
MAX_SIZE=int(os.environ.get("KAI_LIVE_MAX_SIZE","960"))
MAX_FPS=int(os.environ.get("KAI_LIVE_MAX_FPS","20"))
BIT_RATE=int(os.environ.get("KAI_LIVE_BIT_RATE","3000000"))
START_TIMEOUT=float(os.environ.get("KAI_LIVE_START_TIMEOUT","12"))
START_ATTEMPTS=max(1,min(5,int(os.environ.get("KAI_LIVE_START_ATTEMPTS","3"))))
VIDEO_ENCODER=os.environ.get("KAI_LIVE_VIDEO_ENCODER","c2.qti.avc.encoder").strip()
ADB="adb"; FFMPEG="ffmpeg"; SCRCPY="scrcpy"
SERVER_HOST="/data/data/com.termux/files/usr/share/scrcpy/scrcpy-server"
SERVER_LOCAL="/data/local/tmp/scrcpy-server-kai-live.jar"
TOKEN_FILE=HOME/".kai_mobile/kai-live-token"
SOF={0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}

def run(args,timeout=10,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and p.returncode!=0: raise RuntimeError((p.stderr or p.stdout or "command failed").strip())
    return p

def resolve_serial():
    e=os.environ.get("ANDROID_SERIAL","").strip()
    if e:return e
    out=run([ADB,"devices"]).stdout
    ds=[]
    for l in out.splitlines()[1:]:
        c=l.split()
        if len(c)>=2 and c[1]=="device": ds.append(c[0])
    if len(ds)!=1: raise RuntimeError(f"expected one authorized adb device, got {ds}")
    return ds[0]

def scrcpy_version():
    m=re.search(r"scrcpy\s+([0-9]+(?:\.[0-9]+){1,2})",run([SCRCPY,"--version"]).stdout)
    if not m: raise RuntimeError("cannot detect scrcpy version")
    return m.group(1)

def recv_exact(s,n):
    b=bytearray()
    while len(b)<n:
        c=s.recv(n-len(b))
        if not c: raise RuntimeError("socket closed")
        b.extend(c)
    return bytes(b)

def jpeg_dims(data):
    if len(data)<4 or data[:2]!=b"\xff\xd8": return None
    i=2
    while i+8<len(data):
        if data[i]!=0xff:i+=1;continue
        while i<len(data) and data[i]==0xff:i+=1
        if i>=len(data):break
        m=data[i];i+=1
        if m in (0xd8,0xd9) or 0xd0<=m<=0xd7:continue
        if i+1>=len(data):break
        n=(data[i]<<8)|data[i+1]
        if n<2 or i+n>len(data):break
        if m in SOF and n>=7:
            h=(data[i+3]<<8)|data[i+4];w=(data[i+5]<<8)|data[i+6]
            return w,h
        i+=n
    return None

def u16fp(v):
    return min(0xffff,round(max(0.0,min(1.0,v))*65536))

AUTH=TOKEN_FILE.read_text().strip()

class Bridge:
    def __init__(self):
        self.serial=resolve_serial(); self.version=scrcpy_version()
        self.lock=threading.RLock(); self.cond=threading.Condition(self.lock)
        self.restart_lock=threading.Lock(); self.stop_evt=threading.Event()
        self.latest=None; self.sequence=0; self.last_frame_at=0.0
        self.frame_size=(0,0); self.logical=(0,0); self.frame_times=collections.deque(maxlen=240)
        self.video=None; self.control=None; self.server=None; self.ffmpeg=None
        self.generation=0; self.restart_count=0; self.h264_bytes=0; self.stderr=collections.deque(maxlen=60)
        self.ready_evt=threading.Event()

    def log(self,s):
        with self.lock:self.stderr.append(str(s))

    def probe_logical(self):
        out=run([ADB,"-s",self.serial,"shell","dumpsys","input"],timeout=5).stdout
        m=re.search(r"Viewport INTERNAL: displayId=0[^\n]*logicalFrame=\[0, 0, (\d+), (\d+)\]",out)
        if not m: raise RuntimeError("logical viewport unavailable")
        return int(m.group(1)),int(m.group(2))

    def _stderr_reader(self,p,gen):
        if not p.stderr:return
        for line in p.stderr:
            if gen!=self.generation:break
            line=line.strip()
            if line:self.log("server: "+line)

    def _connect_video(self):
        deadline=time.monotonic()+8; last=None
        while time.monotonic()<deadline and not self.stop_evt.is_set():
            try:
                s=socket.create_connection((HOST,FORWARD_PORT),timeout=1);s.settimeout(2)
                recv_exact(s,1);return s
            except Exception as e:
                last=e;time.sleep(.08)
        raise RuntimeError(f"video socket unavailable: {last}")

    def start_session(self):
        gen=self.generation+1; self.generation=gen; self.ready_evt.clear()
        run([ADB,"-s",self.serial,"push",SERVER_HOST,SERVER_LOCAL],timeout=30)
        run([ADB,"-s",self.serial,"forward","--remove",f"tcp:{FORWARD_PORT}"],check=False)
        scid=random.randint(1,0x7fffffff); sockname=f"scrcpy_{scid:08x}"
        run([ADB,"-s",self.serial,"forward",f"tcp:{FORWARD_PORT}",f"localabstract:{sockname}"])
        args=[ADB,"-s",self.serial,"shell",f"CLASSPATH={SERVER_LOCAL}","app_process","/","com.genymobile.scrcpy.Server",self.version,
              f"scid={scid:08x}","log_level=warn",f"max_size={MAX_SIZE}",f"max_fps={MAX_FPS}",f"video_bit_rate={BIT_RATE}",
              "tunnel_forward=true","control=true","audio=false","video=true","cleanup=true","power_off_on_close=false",
              "clipboard_autosync=false","downsize_on_error=false","send_device_meta=true","send_frame_meta=false",
              "send_dummy_byte=true","send_stream_meta=true","video_codec=h264","video_codec_options=i-frame-interval=1"]
        if VIDEO_ENCODER:args.append(f"video_encoder={VIDEO_ENCODER}")
        self.server=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,bufsize=1)
        threading.Thread(target=self._stderr_reader,args=(self.server,gen),daemon=True).start()
        self.video=self._connect_video()
        self.control=socket.create_connection((HOST,FORWARD_PORT),timeout=3);self.control.settimeout(None)
        meta=recv_exact(self.video,80)
        self.video.settimeout(None)
        fw=struct.unpack(">I",meta[72:76])[0];fh=struct.unpack(">I",meta[76:80])[0]
        self.logical=self.probe_logical(); self.frame_size=(fw,fh)
        ff=[FFMPEG,"-hide_banner","-loglevel","error","-flags","low_delay","-f","h264","-i","pipe:0",
            "-an","-vf",f"fps={MAX_FPS}","-q:v","5","-fps_mode","passthrough","-f","image2pipe","-vcodec","mjpeg","pipe:1"]
        self.ffmpeg=subprocess.Popen(ff,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        threading.Thread(target=self._fferr,args=(self.ffmpeg,gen),daemon=True).start()
        threading.Thread(target=self._pump,args=(gen,),daemon=True).start()
        threading.Thread(target=self._frames,args=(gen,),daemon=True).start()
        if not self.ready_evt.wait(START_TIMEOUT): raise RuntimeError(f"first frame timeout after {START_TIMEOUT:.1f}s h264_bytes={self.h264_bytes} diagnostics={list(self.stderr)[-6:]}")
        self.log(f"ready gen={gen} frame={self.frame_size} logical={self.logical}")

    def _fferr(self,p,gen):
        if not p.stderr:return
        for raw in iter(p.stderr.readline,b""):
            if gen!=self.generation:break
            s=raw.decode("utf-8","replace").strip()
            if s:self.log("ffmpeg: "+s)

    def _pump(self,gen):
        try:
            while gen==self.generation and not self.stop_evt.is_set():
                b=self.video.recv(65536)
                if not b:break
                self.h264_bytes+=len(b)
                self.ffmpeg.stdin.write(b);self.ffmpeg.stdin.flush()
        except Exception as e:
            if gen==self.generation and not self.stop_evt.is_set():
                self.log(f"pump: {type(e).__name__}: {e}")

    def _frames(self,gen):
        buf=bytearray()
        try:
            while gen==self.generation and not self.stop_evt.is_set():
                b=self.ffmpeg.stdout.read(65536)
                if not b:break
                buf.extend(b)
                while True:
                    a=buf.find(b"\xff\xd8")
                    if a<0:break
                    z=buf.find(b"\xff\xd9",a+2)
                    if z<0:
                        if a>0:del buf[:a]
                        break
                    frame=bytes(buf[a:z+2]);del buf[:z+2]; dims=jpeg_dims(frame); now=time.monotonic()
                    with self.cond:
                        self.latest=frame;self.sequence+=1;self.last_frame_at=now
                        if dims:self.frame_size=dims
                        self.frame_times.append(now);self.ready_evt.set();self.cond.notify_all()
        except Exception as e:self.log(f"frames: {type(e).__name__}: {e}")

    def stop_session(self):
        self.generation+=1
        for s in (self.control,self.video):
            try:
                if s:
                    try:s.shutdown(socket.SHUT_RDWR)
                    except:pass
                    s.close()
            except:pass
        self.control=None;self.video=None
        if self.ffmpeg and self.ffmpeg.stdin:
            try:self.ffmpeg.stdin.close()
            except:pass
        procs=[self.ffmpeg,self.server]
        for p in procs:
            try:
                if p and p.poll() is None:p.terminate()
            except:pass
        deadline=time.monotonic()+1.2
        for p in procs:
            if not p:continue
            while p.poll() is None and time.monotonic()<deadline:
                time.sleep(.03)
            if p.poll() is None:
                try:p.kill()
                except:pass
            try:p.wait(timeout=.5)
            except:pass
        self.ffmpeg=None;self.server=None
        run([ADB,"-s",self.serial,"forward","--remove",f"tcp:{FORWARD_PORT}"],check=False)
        with self.cond:
            self.latest=None;self.frame_size=(0,0);self.last_frame_at=0;self.frame_times.clear();self.cond.notify_all()

    def restart(self,reason):
        if not self.restart_lock.acquire(blocking=False):return
        try:
            self.restart_count+=1;self.log(f"restart[{self.restart_count}]: {reason}")
            self.stop_session();time.sleep(.12);self.start_session()
        finally:self.restart_lock.release()

    def supervise(self):
        mismatch=0
        while not self.stop_evt.wait(.5):
            bad=(not self.server or self.server.poll() is not None or not self.ffmpeg or self.ffmpeg.poll() is not None or not self.control_ready())
            if bad:self.restart("process-or-socket");continue
            try:
                logical=self.probe_logical()
                with self.lock:fw,fh=self.frame_size;age=time.monotonic()-self.last_frame_at if self.last_frame_at else 999
                mm=fw>0 and fh>0 and age<2 and ((logical[0]>logical[1])!=(fw>fh))
                mismatch=mismatch+1 if mm else 0
                self.logical=logical
                if mismatch>=2:self.restart(f"orientation:{fw}x{fh}->{logical[0]}x{logical[1]}");mismatch=0
            except Exception as e:self.log(f"supervise: {type(e).__name__}: {e}")

    def start(self):
        last=None
        for attempt in range(1,START_ATTEMPTS+1):
            try:
                self.start_session();last=None;break
            except Exception as e:
                last=e;self.log(f"startup[{attempt}/{START_ATTEMPTS}]: {type(e).__name__}: {e}")
                try:self.stop_session()
                except Exception as cleanup:self.log(f"startup-cleanup: {type(cleanup).__name__}: {cleanup}")
                if attempt<START_ATTEMPTS:time.sleep(min(2.0,0.35*attempt))
        if last is not None:raise last
        threading.Thread(target=self.supervise,daemon=True).start()

    def stop(self):
        self.stop_evt.set();self.stop_session()

    def fps(self):
        with self.lock:
            if len(self.frame_times)<2:return 0.0
            dt=self.frame_times[-1]-self.frame_times[0]
            return 0.0 if dt<2 else (len(self.frame_times)-1)/dt

    def status(self):
        with self.lock:
            age=None if not self.last_frame_at else round((time.monotonic()-self.last_frame_at)*1000,1)
            return {"ok":self.latest is not None,"mode":"scrcpy-direct-v2","serial":self.serial,"scrcpy":self.version,
                    "sequence":self.sequence,"delivery_fps":round(self.fps(),2),"target_max_fps":MAX_FPS,"frame_age_ms":age,
                    "frame_size":{"width":self.frame_size[0],"height":self.frame_size[1]},"logical_size":{"width":self.logical[0],"height":self.logical[1]},
                    "max_size":MAX_SIZE,"bit_rate":BIT_RATE,"scrcpy_alive":self.server is not None and self.server.poll() is None,
                    "ffmpeg_alive":self.ffmpeg is not None and self.ffmpeg.poll() is None,
                    "control_alive":self.control_ready(),"preferred_input":"scrcpy" if self.control_ready() else "adb-fallback","h264_bytes":self.h264_bytes,"restart_count":self.restart_count,
                    "diagnostic_tail":list(self.stderr)[-12:]}

    def get_frame(self):
        with self.lock:
            age=None if not self.last_frame_at else (time.monotonic()-self.last_frame_at)*1000
            return self.sequence,self.latest,age,self.frame_size

    def wait_frame(self,after,timeout_ms):
        end=time.monotonic()+timeout_ms/1000
        with self.cond:
            while self.sequence<=after and not self.stop_evt.is_set():
                left=end-time.monotonic()
                if left<=0:break
                self.cond.wait(left)
            age=None if not self.last_frame_at else (time.monotonic()-self.last_frame_at)*1000
            return self.sequence,self.latest,age,self.frame_size

    def map_point(self,x,y,space):
        lw,lh=self.logical;fw,fh=self.frame_size
        if space=="logical":return round(x),round(y)
        if space=="frame":return round(x*lw/fw),round(y*lh/fh)
        if space=="norm":return round(x*lw/1000),round(y*lh/1000)
        raise ValueError("space must be logical, frame, or norm")

    def touch_msg(self,action,x,y,pressure):
        lw,lh=self.logical;fw,fh=self.frame_size
        fx=round(x*fw/lw);fy=round(y*fh/lh)
        b=bytearray(32);b[0]=2;b[1]=action;struct.pack_into(">Q",b,2,(1<<64)-2)
        struct.pack_into(">i",b,10,fx);struct.pack_into(">i",b,14,fy);struct.pack_into(">H",b,18,fw);struct.pack_into(">H",b,20,fh)
        struct.pack_into(">H",b,22,min(0xffff,round(max(0,min(1,pressure))*65536)));struct.pack_into(">I",b,24,0);struct.pack_into(">I",b,28,0)
        self.control.sendall(b)

    def key_msg(self,action,keycode):
        b=bytearray(14);b[0]=0;b[1]=action;struct.pack_into(">i",b,2,keycode);struct.pack_into(">i",b,6,0);struct.pack_into(">i",b,10,0)
        self.control.sendall(b)

    def control_ready(self):
        c=self.control
        return c is not None and c.fileno() >= 0

    def adb_tap(self,x,y,hold_ms):
        run([ADB,"-s",self.serial,"shell","input","touchscreen","swipe",str(x),str(y),str(x),str(y),str(hold_ms)],timeout=max(5,hold_ms/1000+3))

    def adb_swipe(self,x1,y1,x2,y2,duration_ms):
        run([ADB,"-s",self.serial,"shell","input","touchscreen","swipe",str(x1),str(y1),str(x2),str(y2),str(duration_ms)],timeout=max(5,duration_ms/1000+3))

    def adb_key(self,keycode):
        run([ADB,"-s",self.serial,"shell","input","keyevent",str(keycode)],timeout=5)

    def actions(self,acts):
        baseline=self.sequence;t0=time.perf_counter();done=[]
        try:
            for a in acts:
                typ=a.get("type","").lower()
                if typ=="tap":
                    x,y=self.map_point(float(a["x"]),float(a["y"]),a.get("space","frame"));hold=max(5,min(1500,int(a.get("hold_ms",10))))
                    if self.control_ready():
                        transport="scrcpy"
                        self.touch_msg(0,x,y,1);time.sleep(hold/1000);self.touch_msg(1,x,y,0)
                    else:
                        transport="adb-fallback"
                        self.adb_tap(x,y,hold)
                    done.append({"type":"tap","transport":transport,"logical":[x,y],"hold_ms":hold})
                elif typ=="swipe":
                    x1,y1=self.map_point(float(a["x1"]),float(a["y1"]),a.get("space","frame"));x2,y2=self.map_point(float(a["x2"]),float(a["y2"]),a.get("space","frame"))
                    dur=max(20,min(5000,int(a.get("duration_ms",200))))
                    if self.control_ready():
                        transport="scrcpy"
                        steps=max(2,int(dur/16));delay=dur/1000/steps
                        self.touch_msg(0,x1,y1,1)
                        for i in range(1,steps):
                            time.sleep(delay);self.touch_msg(2,round(x1+(x2-x1)*i/steps),round(y1+(y2-y1)*i/steps),1)
                        time.sleep(delay);self.touch_msg(1,x2,y2,0)
                    else:
                        transport="adb-fallback"
                        self.adb_swipe(x1,y1,x2,y2,dur)
                    done.append({"type":"swipe","transport":transport,"logical":[x1,y1,x2,y2],"duration_ms":dur})
                elif typ=="key":
                    k=int(a["keycode"])
                    if self.control_ready():
                        transport="scrcpy"
                        self.key_msg(0,k);time.sleep(.01);self.key_msg(1,k)
                    else:
                        transport="adb-fallback"
                        self.adb_key(k)
                    done.append({"type":"key","transport":transport,"keycode":k})
                elif typ=="sleep":
                    ms=max(0,min(5000,int(a.get("ms",0))));time.sleep(ms/1000);done.append({"type":"sleep","ms":ms})
                else:raise ValueError(f"unsupported action {typ}")
        except Exception as e:
            # ADB is the explicit safety fallback, never the silent primary path.
            self.log(f"control-fallback: {type(e).__name__}: {e}")
            raise
        action_ms=(time.perf_counter()-t0)*1000
        with self.lock:post=self.sequence
        w0=time.perf_counter();seq,_,age,size=self.wait_frame(post,1200);next_ms=(time.perf_counter()-w0)*1000
        return {"ok":True,"baseline_sequence":baseline,"post_action_sequence":post,"sequence":seq,"action_ms":round(action_ms,2),
                "next_frame_ms":round(next_ms,2),"frame_age_ms":None if age is None else round(age,1),
                "frame_size":{"width":size[0],"height":size[1]},"executed":done}

    def launch_minecraft(self):
        base=self.sequence;t=time.perf_counter()
        p=run([ADB,"-s",self.serial,"shell","monkey","-p","com.mojang.minecraftpe","-c","android.intent.category.LAUNCHER","1"],timeout=8,check=False)
        seq,_,age,size=self.wait_frame(base,1500)
        return {"ok":p.returncode==0,"sequence":seq,"elapsed_ms":round((time.perf_counter()-t)*1000,1),"frame_age_ms":None if age is None else round(age,1),"frame_size":{"width":size[0],"height":size[1]}}

bridge=Bridge();bridge.start()

class H(BaseHTTPRequestHandler):
    def log_message(self,*a):pass
    def auth(self):
        v=self.headers.get("Authorization","")
        if v.startswith("Bearer "):v=v[7:]
        else:v=parse_qs(urlparse(self.path).query).get("token",[""])[0]
        return bool(v) and secrets.compare_digest(v,AUTH)
    def js(self,c,d):
        b=json.dumps(d,separators=(",",":")).encode();self.send_response(c);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def img(self,t):
        seq,frame,age,size=t
        if not frame:return self.js(503,{"ok":False})
        self.send_response(200);self.send_header("Content-Type","image/jpeg");self.send_header("Content-Length",str(len(frame)));self.send_header("Cache-Control","no-store")
        self.send_header("X-Kai-Sequence",str(seq));self.send_header("X-Kai-Age-Ms","" if age is None else f"{age:.1f}");self.end_headers();self.wfile.write(frame)
    def do_GET(self):
        if not self.auth():return self.js(401,{"ok":False})
        u=urlparse(self.path);q=parse_qs(u.query)
        if u.path in ("/","/status"):return self.js(200,bridge.status())
        if u.path=="/frame":return self.img(bridge.get_frame())
        if u.path=="/next":
            return self.img(bridge.wait_frame(int(q.get("after",[str(bridge.sequence)])[0]),max(0,min(5000,int(q.get("timeout_ms",["1000"])[0])))))
        return self.js(404,{"ok":False})
    def do_POST(self):
        if not self.auth():return self.js(401,{"ok":False})
        try:
            n=int(self.headers.get("Content-Length","0") or 0);d=json.loads(self.rfile.read(n) or b"{}")
            path=urlparse(self.path).path
            if path=="/act":return self.js(200,bridge.actions(d["actions"]))
            if path=="/minecraft":return self.js(200,bridge.launch_minecraft())
            return self.js(404,{"ok":False})
        except Exception as e:return self.js(400,{"ok":False,"error":f"{type(e).__name__}: {e}"})

def shutdown(*_):
    bridge.stop();raise SystemExit
signal.signal(signal.SIGINT,shutdown);signal.signal(signal.SIGTERM,shutdown)
srv=ThreadingHTTPServer((HOST,PORT),H)
try:srv.serve_forever(.2)
finally:srv.server_close();bridge.stop()
