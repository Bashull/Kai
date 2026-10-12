#!/usr/bin/env python3
"""KAI PC Agent: explicit loopback-only control plane, no arbitrary shell execution."""
import argparse
import hmac
import json
import pathlib
import secrets
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 4096

def read_config(path):
    config = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(config.get("apps"), dict):
        raise ValueError("apps must be a dictionary")
    return config

def is_allowed_app(config, app_id):
    app = config["apps"].get(app_id)
    if not isinstance(app, dict) or not app.get("enabled", False):
        return None
    path = pathlib.Path(app.get("path", ""))
    if not path.is_absolute() or not path.is_file() or path.suffix.lower() not in (".exe", ".com"):
        return None
    return path

def handler_factory(config, token, audit_path):
    audit_path = pathlib.Path(audit_path)
    class Handler(BaseHTTPRequestHandler):
        server_version = "KaiPC/0.1"
        def log_message(self, fmt, *args):
            pass
        def respond(self, status, value):
            body = json.dumps(value, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        def audit(self, action, ok):
            entry = {"at": time.time(), "action": action, "ok": bool(ok)}
            with audit_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        def authorized(self):
            supplied = self.headers.get("Authorization", "")
            return hmac.compare_digest(supplied, "Bearer " + token)
        def do_GET(self):
            if not self.authorized():
                return self.respond(401, {"error": "unauthorized"})
            if self.path == "/v1/health":
                return self.respond(200, {"ok": True, "version": "0.1", "transport": "loopback-only"})
            if self.path == "/v1/capabilities":
                return self.respond(200, {"capabilities": ["health", "app.enumerate.allowlisted", "app.launch.allowlisted"]})
            if self.path == "/v1/apps":
                items = [name for name, obj in config["apps"].items() if isinstance(obj, dict) and obj.get("enabled")]
                return self.respond(200, {"allowed_apps": sorted(items)})
            self.respond(404, {"error": "not_found"})
        def do_POST(self):
            if not self.authorized():
                return self.respond(401, {"error": "unauthorized"})
            if self.path != "/v1/apps/launch":
                return self.respond(404, {"error": "not_found"})
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if length <= 0:
                    return self.respond(413, {"error": "invalid_size"})
                if length > MAX_BODY:
                    # Windows resets TCP on close with an unread body; drain a bounded excess.
                    if length <= 2 * MAX_BODY:
                        self.connection.settimeout(2)
                        self.rfile.read(length)
                    return self.respond(413, {"error": "invalid_size"})
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict) or set(body) != {"id"} or not isinstance(body["id"], str):
                    raise ValueError("invalid schema")
                app_id = body["id"]
                exe = is_allowed_app(config, app_id)
                if exe is None:
                    self.audit("app.launch.denied", False)
                    return self.respond(403, {"error": "not_allowlisted"})
                subprocess.Popen([str(exe)], cwd=str(exe.parent), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                self.audit("app.launch:" + app_id, True)
                self.respond(202, {"accepted": True, "app": app_id})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self.respond(400, {"error": "invalid_request"})
            except OSError:
                self.audit("app.launch.error", False)
                self.respond(503, {"error": "launch_failed"})
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--port", type=int, default=18761)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("invalid port")
    config = read_config(args.config)
    token_file = pathlib.Path(args.token_file)
    if not token_file.exists():
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with token_file.open("x", encoding="utf-8") as f:
            f.write(secrets.token_urlsafe(48) + "\n")
    token = token_file.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise SystemExit("token too short")
    audit_path = pathlib.Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), handler_factory(config, token, audit_path)).serve_forever()

if __name__ == "__main__":
    main()
