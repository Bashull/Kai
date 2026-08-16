#!/data/data/com.termux/files/usr/bin/python3
from __future__ import annotations

import functools
import http.client
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 7860
PROXY_PREFIX = "/hf"
UPSTREAM_HOST = "bashull-qwen-image-edit-2511-loras-fast.hf.space"
APP_DIR = Path(__file__).resolve().parent
LOCAL_ROOT = f"http://{HOST}:{PORT}{PROXY_PREFIX}"
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
}


def upstream_path(path: str) -> str:
    if path != PROXY_PREFIX and not path.startswith(PROXY_PREFIX + "/"):
        raise ValueError("not a Kai HF proxy path")
    value = path[len(PROXY_PREFIX):] or "/"
    return value if value.startswith("/") else "/" + value


def rewrite_config(body: bytes, local_root: str = LOCAL_ROOT) -> bytes:
    data = json.loads(body.decode("utf-8"))
    if isinstance(data, dict):
        data["root"] = local_root
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def load_vault_token() -> str | None:
    secrets_dir = Path.home() / ".kai_secrets"
    sys.path.insert(0, str(secrets_dir))
    try:
        from vault import has_hf_token, load_hf_token
        return load_hf_token() if has_hf_token() else None
    except Exception:
        return None


def upstream_headers(source, token: str, body_len: int) -> dict[str, str]:
    headers = {}
    for key, value in source.items():
        lower = key.lower()
        if lower in HOP_HEADERS or lower in {"host", "authorization", "content-length", "accept-encoding"}:
            continue
        headers[key] = value
    headers["Authorization"] = "Bearer " + token
    headers["Accept-Encoding"] = "identity"
    if body_len:
        headers["Content-Length"] = str(body_len)
    return headers


class KaiHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    vault_token: str | None = None

    def _proxy_request(self) -> None:
        if not self.vault_token:
            self._json_response(503, {"ok": False, "error": "HF_VAULT_NOT_CONFIGURED"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        path = upstream_path(self.path)
        headers = upstream_headers(self.headers, self.vault_token, length)
        conn = http.client.HTTPSConnection(UPSTREAM_HOST, timeout=420)
        try:
            conn.request(self.command, path, body=body, headers=headers)
            response = conn.getresponse()
            if path.split("?", 1)[0] == "/config":
                payload = rewrite_config(response.read())
                self._send_upstream_headers(response, len(payload))
                if self.command != "HEAD":
                    self.wfile.write(payload)
                return
            self._send_upstream_headers(response, None)
            if self.command != "HEAD":
                self._stream(response)
        except Exception as exc:
            self._json_response(502, {"ok": False, "error": type(exc).__name__})
        finally:
            conn.close()

    def _send_upstream_headers(self, response, content_length: int | None) -> None:
        self.send_response(response.status, response.reason)
        for key, value in response.getheaders():
            lower = key.lower()
            if lower in HOP_HEADERS or lower in {"content-length", "content-encoding"}:
                continue
            if lower == "location":
                remote = "https://" + UPSTREAM_HOST
                value = value.replace(remote, LOCAL_ROOT)
            self.send_header(key, value)
        if content_length is not None:
            self.send_header("Content-Length", str(content_length))
        elif response.getheader("Content-Length"):
            self.send_header("Content-Length", response.getheader("Content-Length"))
        else:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.send_header("X-Kai-HF-Proxy", "vault")
        self.end_headers()

    def _stream(self, response) -> None:
        while True:
            chunk = response.read1(65536)
            if not chunk:
                break
            self.wfile.write(chunk)
            self.wfile.flush()

    def _json_response(self, status: int, data: dict) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _is_proxy(self) -> bool:
        return self.path == PROXY_PREFIX or self.path.startswith(PROXY_PREFIX + "/")

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json_response(200, {
                "ok": True,
                "vault": bool(self.vault_token),
                "space": "Bashull/Qwen-Image-Edit-2511-LoRAs-Fast",
            })
        elif self._is_proxy():
            self._proxy_request()
        else:
            super().do_GET()

    def do_HEAD(self) -> None:
        if self._is_proxy():
            self._proxy_request()
        else:
            super().do_HEAD()

    def do_POST(self) -> None:
        if self._is_proxy():
            self._proxy_request()
        else:
            self._json_response(404, {"ok": False, "error": "NOT_FOUND"})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


def main() -> None:
    token = load_vault_token()
    KaiHandler.vault_token = token
    handler = functools.partial(KaiHandler, directory=str(APP_DIR))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    print(f"Kai Edit Mobile · http://{HOST}:{PORT} · vault={'OK' if token else 'NO'}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
