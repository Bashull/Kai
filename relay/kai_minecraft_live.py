#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import collections
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("KAI_LIVE_HOST", "127.0.0.1")
PORT = int(os.environ.get("KAI_LIVE_PORT", "7190"))
MAX_SIZE = int(os.environ.get("KAI_LIVE_MAX_SIZE", "960"))
MAX_FPS = int(os.environ.get("KAI_LIVE_MAX_FPS", "20"))
BIT_RATE = os.environ.get("KAI_LIVE_BIT_RATE", "3M")
JPEG_QUALITY = int(os.environ.get("KAI_LIVE_JPEG_QUALITY", "5"))
VIDEO_ENCODER = os.environ.get("KAI_LIVE_VIDEO_ENCODER", "").strip()
TOKEN_FILE = Path(os.environ.get("KAI_LIVE_TOKEN_FILE", str(Path.home() / ".kai_mobile" / "kai-live-token")))
ADB = shutil.which("adb") or "adb"
SCRCPY = shutil.which("scrcpy") or "scrcpy"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def resolve_token() -> str:
    configured = os.environ.get("KAI_LIVE_TOKEN", "").strip()
    if configured:
        return configured
    try:
        existing = TOKEN_FILE.read_text().strip()
        if existing:
            return existing
    except FileNotFoundError:
        pass
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        TOKEN_FILE.parent.chmod(0o700)
    except OSError:
        pass
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token + "\n")
    TOKEN_FILE.chmod(0o600)
    return token


AUTH_TOKEN = resolve_token()


def jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    n = len(data)
    while i + 8 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if i + 1 >= n:
            break
        seg_len = (data[i] << 8) | data[i + 1]
        if seg_len < 2 or i + seg_len > n:
            break
        if marker in SOF_MARKERS and seg_len >= 7:
            h = (data[i + 3] << 8) | data[i + 4]
            w = (data[i + 5] << 8) | data[i + 6]
            return w, h
        i += seg_len
    return None


def resolve_serial() -> str:
    explicit = os.environ.get("KAI_ANDROID_SERIAL") or os.environ.get("ANDROID_SERIAL")
    if explicit:
        return explicit.strip()
    proc = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=5)
    devices = []
    for line in proc.stdout.splitlines()[1:]:
        cols = line.split()
        if len(cols) >= 2 and cols[1] == "device":
            devices.append(cols[0])
    if len(devices) != 1:
        raise RuntimeError(f"Expected one authorized ADB device, found {devices}")
    return devices[0]


class LiveBridge:
    def __init__(self) -> None:
        self.serial = resolve_serial()
        self.lock = threading.RLock()
        self.cond = threading.Condition(self.lock)
        self.latest: bytes | None = None
        self.sequence = 0
        self.last_frame_at = 0.0
        self.frame_size: tuple[int, int] = (0, 0)
        self.frame_times = collections.deque(maxlen=240)
        self.logical_frame: tuple[int, int] = (0, 0)
        self.scrcpy: subprocess.Popen | None = None
        self.ffmpeg: subprocess.Popen | None = None
        self.stderr_tail = collections.deque(maxlen=80)
        self.stop_event = threading.Event()
        self.restart_count = 0
        self.pipeline_started_at = 0.0
        self.workdir = Path(tempfile.mkdtemp(prefix="kai-live-", dir=str(Path.home())))
        self.fifo = self.workdir / "video.mkv"
        os.mkfifo(self.fifo)

    def _log_reader(self, name: str, stream) -> None:
        if stream is None:
            return
        for raw in iter(stream.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            if line:
                with self.lock:
                    self.stderr_tail.append(f"{name}: {line}")

    def _spawn_pipeline(self) -> None:
        self.pipeline_started_at = time.monotonic()
        ff_args = [
            FFMPEG, "-hide_banner", "-loglevel", "error",
            "-flags", "low_delay",
            "-i", str(self.fifo), "-an",
            "-q:v", str(JPEG_QUALITY),
            "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
        ]
        self.ffmpeg = subprocess.Popen(
            ff_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        threading.Thread(target=self._log_reader, args=("ffmpeg", self.ffmpeg.stderr), daemon=True).start()

        sc_args = [
            SCRCPY, "--serial", self.serial,
            "--no-audio", "--no-control", "--no-playback", "--no-window",
            f"--record={self.fifo}", "--record-format=mkv",
            "--video-buffer=0",
            f"--max-size={MAX_SIZE}",
            f"--max-fps={MAX_FPS}",
            f"--video-bit-rate={BIT_RATE}",
            "--video-codec=h264",
            "--video-codec-options=i-frame-interval=1",
        ]
        if VIDEO_ENCODER:
            sc_args.append(f"--video-encoder={VIDEO_ENCODER}")
        self.scrcpy = subprocess.Popen(
            sc_args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        threading.Thread(target=self._log_reader, args=("scrcpy", self.scrcpy.stderr), daemon=True).start()
        threading.Thread(target=self._frame_reader, daemon=True).start()

    def _frame_reader(self) -> None:
        proc = self.ffmpeg
        if proc is None or proc.stdout is None:
            return
        buf = bytearray()
        while not self.stop_event.is_set():
            chunk = proc.stdout.read(65536)
            if not chunk:
                break
            buf.extend(chunk)
            while True:
                soi = buf.find(b"\xff\xd8")
                if soi < 0:
                    if len(buf) > 2_000_000:
                        del buf[:-2]
                    break
                eoi = buf.find(b"\xff\xd9", soi + 2)
                if eoi < 0:
                    if soi > 0:
                        del buf[:soi]
                    break
                frame = bytes(buf[soi:eoi + 2])
                del buf[:eoi + 2]
                dims = jpeg_dimensions(frame)
                now = time.monotonic()
                with self.cond:
                    self.latest = frame
                    self.sequence += 1
                    self.last_frame_at = now
                    if dims:
                        self.frame_size = dims
                    self.frame_times.append(now)
                    self.cond.notify_all()

    def start(self) -> None:
        self._spawn_pipeline()
        threading.Thread(target=self._supervise, daemon=True).start()

    def _supervise(self) -> None:
        orientation_mismatch = 0
        while not self.stop_event.wait(0.5):
            process_bad = (
                self.scrcpy is None or self.ffmpeg is None or
                self.scrcpy.poll() is not None or self.ffmpeg.poll() is not None
            )
            reason = "process-exit" if process_bad else None

            # scrcpy recording fixes the container geometry at session start.
            # If Android rotates, restart only the capture pipeline so the new
            # stream is born with the correct landscape/portrait dimensions.
            if not process_bad:
                try:
                    logical_w, logical_h = self._probe_logical_size()
                    with self.lock:
                        self.logical_frame = (logical_w, logical_h)
                        frame_w, frame_h = self.frame_size
                        frame_age = (time.monotonic() - self.last_frame_at) if self.last_frame_at else 999.0
                    comparable = frame_w > 0 and frame_h > 0 and frame_age < 2.0
                    mismatched = comparable and ((logical_w > logical_h) != (frame_w > frame_h))
                    orientation_mismatch = orientation_mismatch + 1 if mismatched else 0
                    if orientation_mismatch >= 2:
                        reason = f"orientation:{frame_w}x{frame_h}->{logical_w}x{logical_h}"
                except Exception as exc:
                    with self.lock:
                        self.stderr_tail.append(f"orientation-check: {type(exc).__name__}: {exc}")

            if reason is None:
                continue

            self.restart_count += 1
            with self.lock:
                self.stderr_tail.append(f"restart[{self.restart_count}]: {reason}")
            self._terminate_pipeline()
            orientation_mismatch = 0
            delay = min(5.0, 0.5 + self.restart_count * 0.5) if process_bad else 0.1
            if self.stop_event.wait(delay):
                return
            try:
                if self.fifo.exists():
                    self.fifo.unlink()
                os.mkfifo(self.fifo)
                self._spawn_pipeline()
            except Exception as exc:
                with self.lock:
                    self.stderr_tail.append(f"restart: {type(exc).__name__}: {exc}")

    def _terminate_pipeline(self) -> None:
        for proc in (self.scrcpy, self.ffmpeg):
            if proc is None:
                continue
            if proc.poll() is None:
                proc.terminate()
        deadline = time.monotonic() + 1.5
        for proc in (self.scrcpy, self.ffmpeg):
            if proc is None:
                continue
            while proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.03)
            if proc.poll() is None:
                proc.kill()
        self.scrcpy = None
        self.ffmpeg = None
        with self.cond:
            self.latest = None
            self.frame_size = (0, 0)
            self.last_frame_at = 0.0
            self.frame_times.clear()
            self.cond.notify_all()

    def stop(self) -> None:
        self.stop_event.set()
        self._terminate_pipeline()
        try:
            self.fifo.unlink(missing_ok=True)
            self.workdir.rmdir()
        except Exception:
            pass

    def fps(self) -> float:
        with self.lock:
            if len(self.frame_times) < 2:
                return 0.0
            dt = self.frame_times[-1] - self.frame_times[0]
            # FFmpeg may flush a burst of buffered frames immediately after a
            # rotation restart. Do not present that burst rate as steady FPS.
            return 0.0 if dt < 2.0 else (len(self.frame_times) - 1) / dt

    def status(self) -> dict:
        with self.lock:
            age_ms = None if not self.last_frame_at else round((time.monotonic() - self.last_frame_at) * 1000, 1)
            return {
                "ok": self.latest is not None,
                "serial": self.serial,
                "sequence": self.sequence,
                "delivery_fps": round(self.fps(), 2),
                "target_max_fps": MAX_FPS,
                "frame_age_ms": age_ms,
                "frame_size": {"width": self.frame_size[0], "height": self.frame_size[1]},
                "max_size": MAX_SIZE,
                "bit_rate": BIT_RATE,
                "scrcpy_alive": self.scrcpy is not None and self.scrcpy.poll() is None,
                "ffmpeg_alive": self.ffmpeg is not None and self.ffmpeg.poll() is None,
                "restart_count": self.restart_count,
                "diagnostic_tail": list(self.stderr_tail)[-12:],
            }

    def get_frame(self) -> tuple[int, bytes | None, float | None, tuple[int, int]]:
        with self.lock:
            age = None if not self.last_frame_at else (time.monotonic() - self.last_frame_at) * 1000
            return self.sequence, self.latest, age, self.frame_size

    def wait_frame(self, after: int, timeout_ms: int) -> tuple[int, bytes | None, float | None, tuple[int, int]]:
        deadline = time.monotonic() + max(0, timeout_ms) / 1000
        with self.cond:
            while self.sequence <= after and not self.stop_event.is_set():
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                self.cond.wait(left)
            age = None if not self.last_frame_at else (time.monotonic() - self.last_frame_at) * 1000
            return self.sequence, self.latest, age, self.frame_size

    def _probe_logical_size(self) -> tuple[int, int]:
        out = subprocess.check_output(
            [ADB, "-s", self.serial, "shell", "dumpsys", "input"],
            text=True, errors="replace", timeout=4,
        )
        m = re.search(r"Viewport INTERNAL: displayId=0[^\n]*logicalFrame=\[0, 0, (\d+), (\d+)\]", out)
        if not m:
            raise RuntimeError("Could not resolve active logical viewport")
        return int(m.group(1)), int(m.group(2))

    def logical_size(self) -> tuple[int, int]:
        with self.lock:
            cached = self.logical_frame
        if cached[0] > 0 and cached[1] > 0:
            return cached
        fresh = self._probe_logical_size()
        with self.lock:
            self.logical_frame = fresh
        return fresh

    def map_point(self, x: float, y: float, space: str) -> tuple[int, int]:
        logical_w, logical_h = self.logical_size()
        with self.lock:
            frame_w, frame_h = self.frame_size
        if space == "logical":
            return round(x), round(y)
        if space == "norm":
            return round(x * logical_w / 1000), round(y * logical_h / 1000)
        if space == "frame":
            if frame_w <= 0 or frame_h <= 0:
                raise RuntimeError("No frame geometry yet")
            return round(x * logical_w / frame_w), round(y * logical_h / frame_h)
        raise ValueError("space must be logical, norm, or frame")

    def run_actions(self, actions: list[dict]) -> dict:
        baseline = self.sequence
        t0 = time.monotonic()
        executed = []
        for action in actions:
            typ = str(action.get("type", "")).lower()
            if typ == "tap":
                space = str(action.get("space", "frame"))
                x, y = self.map_point(float(action["x"]), float(action["y"]), space)
                hold_ms = max(20, min(1500, int(action.get("hold_ms", 180))))
                subprocess.run(
                    [ADB, "-s", self.serial, "shell", "input", "touchscreen", "swipe",
                     str(x), str(y), str(x), str(y), str(hold_ms)],
                    check=True, timeout=5,
                )
                executed.append({"type": "tap", "logical": [x, y], "hold_ms": hold_ms})
            elif typ == "swipe":
                space = str(action.get("space", "frame"))
                x1, y1 = self.map_point(float(action["x1"]), float(action["y1"]), space)
                x2, y2 = self.map_point(float(action["x2"]), float(action["y2"]), space)
                duration = max(20, min(10000, int(action.get("duration_ms", 300))))
                subprocess.run(
                    [ADB, "-s", self.serial, "shell", "input", "touchscreen", "swipe",
                     str(x1), str(y1), str(x2), str(y2), str(duration)],
                    check=True, timeout=max(5, duration / 1000 + 3),
                )
                executed.append({"type": "swipe", "logical": [x1, y1, x2, y2], "duration_ms": duration})
            elif typ == "key":
                key = str(action["keycode"])
                subprocess.run(
                    [ADB, "-s", self.serial, "shell", "input", "keyevent", key],
                    check=True, timeout=5,
                )
                executed.append({"type": "key", "keycode": key})
            elif typ == "sleep":
                ms = max(0, min(5000, int(action.get("ms", 0))))
                time.sleep(ms / 1000)
                executed.append({"type": "sleep", "ms": ms})
            else:
                raise ValueError(f"Unsupported action type: {typ}")
        action_ms = round((time.monotonic() - t0) * 1000, 1)
        with self.lock:
            post_action_sequence = self.sequence
        wait_t0 = time.monotonic()
        seq, _, age, frame_size = self.wait_frame(post_action_sequence, 1200)
        next_frame_ms = round((time.monotonic() - wait_t0) * 1000, 1)
        logical_w, logical_h = self.logical_size()
        return {
            "ok": True,
            "baseline_sequence": baseline,
            "post_action_sequence": post_action_sequence,
            "sequence": seq,
            "action_ms": action_ms,
            "next_frame_ms": next_frame_ms,
            "frame_age_ms": None if age is None else round(age, 1),
            "frame_size": {"width": frame_size[0], "height": frame_size[1]},
            "logical_size": {"width": logical_w, "height": logical_h},
            "executed": executed,
        }

    def launch_minecraft(self) -> dict:
        baseline = self.sequence
        t0 = time.monotonic()
        proc = subprocess.run(
            [ADB, "-s", self.serial, "shell", "monkey", "-p", "com.mojang.minecraftpe",
             "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, text=True, timeout=8,
        )
        seq, _, age, frame_size = self.wait_frame(baseline, 1500)
        return {
            "ok": proc.returncode == 0,
            "sequence": seq,
            "elapsed_ms": round((time.monotonic() - t0) * 1000, 1),
            "frame_age_ms": None if age is None else round(age, 1),
            "frame_size": {"width": frame_size[0], "height": frame_size[1]},
        }


bridge = LiveBridge()


class Handler(BaseHTTPRequestHandler):
    server_version = "KaiLive/0.3"

    def _authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        if supplied.startswith("Bearer "):
            supplied = supplied[7:]
        else:
            supplied = parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return bool(supplied) and secrets.compare_digest(supplied, AUTH_TOKEN)

    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _image(self, seq: int, frame: bytes | None, age: float | None, size: tuple[int, int]) -> None:
        if frame is None:
            self._json(503, {"ok": False, "error": "no frame yet"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Length", str(len(frame)))
        self.send_header("X-Kai-Sequence", str(seq))
        self.send_header("X-Kai-Age-Ms", "" if age is None else f"{age:.1f}")
        self.send_header("X-Kai-Frame-Size", f"{size[0]}x{size[1]}")
        self.end_headers()
        self.wfile.write(frame)

    def do_GET(self) -> None:
        if not self._authorized():
            self._json(401, {"ok": False, "error": "unauthorized"})
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/health", "/status"):
            self._json(200, bridge.status())
            return
        if u.path == "/frame":
            self._image(*bridge.get_frame())
            return
        if u.path == "/next":
            try:
                after = int(q.get("after", [str(bridge.sequence)])[0])
                timeout_ms = max(0, min(5000, int(q.get("timeout_ms", ["1000"])[0])))
                self._image(*bridge.wait_frame(after, timeout_ms))
            except Exception as exc:
                self._json(400, {"ok": False, "error": str(exc)})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if not self._authorized():
            self._json(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(n)
            payload = json.loads(body or b"{}")
            if self.path == "/act":
                actions = payload.get("actions")
                if not isinstance(actions, list) or not actions:
                    raise ValueError("actions must be a non-empty list")
                self._json(200, bridge.run_actions(actions))
                return
            if self.path == "/minecraft":
                self._json(200, bridge.launch_minecraft())
                return
            self._json(404, {"ok": False, "error": "not found"})
        except Exception as exc:
            self._json(400, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def shutdown(*_args) -> None:
    bridge.stop()
    raise SystemExit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)
bridge.start()
server = ThreadingHTTPServer((HOST, PORT), Handler)
try:
    server.serve_forever(poll_interval=0.2)
finally:
    server.server_close()
    bridge.stop()
