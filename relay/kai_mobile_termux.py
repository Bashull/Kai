from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import secrets
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path.home() / ".kai_mobile"
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"
OUTBOX = ROOT / "outbox"
IDEAS_PATH = ROOT / "ideas_received.jsonl"
LOG_PATH = ROOT / "agent.log"
LOCATOR_URL = "https://raw.githubusercontent.com/Bashull/Kai/main/relay/locator.json"
STOP = False


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}"
    print(line, flush=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def b64d(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def decrypt_payload(key: bytes, envelope: dict[str, Any], aad: bytes) -> Any:
    if envelope.get("alg") != "AES-256-GCM":
        raise ValueError("Algoritmo de cifrado no soportado")
    nonce = b64d(envelope["nonce_b64"])
    ciphertext = b64d(envelope["ciphertext_b64"])
    try:
        plain = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise ValueError("Fallo de autenticacion AES-GCM") from exc
    return json.loads(plain.decode("utf-8"))


def encrypt_payload(key: bytes, value: Any, aad: bytes) -> dict[str, str]:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, canonical_json(value), aad)
    return {
        "alg": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


class RelayClient:
    def __init__(self, config: dict[str, Any]):
        self.base_url = str(config["relay_base_url"]).rstrip("/")
        self.device_id = str(config["device_id"])
        self.hmac_key = b64d(config["auth"]["secret_b64"])
        self.aes_key = b64d(config["payload_encryption"]["key_b64"])

    def _signed_headers(self, method: str, path: str, body: bytes) -> dict[str, str]:
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(24)
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}".encode("utf-8")
        signature = hmac.new(self.hmac_key, canonical, hashlib.sha256).hexdigest()
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
            "X-Relay-Device": self.device_id,
            "X-Relay-Timestamp": timestamp,
            "X-Relay-Nonce": nonce,
            "X-Relay-Signature": signature,
        }

    def post(self, path: str, payload: dict[str, Any], timeout: int = 40) -> dict[str, Any]:
        body = canonical_json(payload)
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers=self._signed_headers("POST", path, body),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:1000]
            raise RuntimeError(f"Relay HTTP {exc.code}: {detail}") from exc

    def heartbeat(self) -> dict[str, Any]:
        return self.post("/v1/mobile/heartbeat", {
            "status": "ready",
            "app_version": "termux-0.2.0",
            "capabilities": ["PING", "STORE_IDEA", "TERMUX_COMMAND"],
        })

    def pull(self, limit: int = 10) -> list[dict[str, Any]]:
        response = self.post("/v1/mobile/pull", {"limit": max(1, min(limit, 100))})
        messages = response.get("messages", [])
        return messages if isinstance(messages, list) else []

    def decrypt_message(self, message: dict[str, Any]) -> dict[str, Any]:
        message_id = str(message["message_id"])
        message_type = str(message["type"])
        aad = f"kai-relay/v1|outbound|{self.device_id}|{message_id}|{message_type}".encode("utf-8")
        payload = decrypt_payload(self.aes_key, message["payload"], aad)
        if not isinstance(payload, dict):
            raise ValueError("El payload remoto no es un objeto JSON")
        return payload

    def post_result(self, item: dict[str, Any]) -> dict[str, Any]:
        message_id = str(item["message_id"])
        message_type = str(item["type"])
        result = item["result"]
        aad = f"kai-relay/v1|result|{self.device_id}|{message_id}|{message_type}".encode("utf-8")
        encrypted = encrypt_payload(self.aes_key, result, aad)
        return self.post("/v1/mobile/result", {
            "message_id": message_id,
            "status": "SUCCEEDED" if item.get("succeeded", False) else "FAILED",
            "result": encrypted,
        })


def refresh_relay_from_locator(client: RelayClient, config: dict[str, Any]) -> bool:
    locator_url = str(config.get("locator_url") or LOCATOR_URL)
    request = urllib.request.Request(
        locator_url,
        headers={"Cache-Control": "no-cache", "User-Agent": "KaiMobileTermux/0.2"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    relay_url = str(data.get("relay_url", "")).strip().rstrip("/")
    if not relay_url.startswith("https://"):
        raise ValueError("Locator devolvio una URL no HTTPS")
    changed = relay_url != client.base_url
    client.base_url = relay_url
    if changed:
        config["relay_base_url"] = relay_url
        config["locator_url"] = locator_url
        save_json(CONFIG_PATH, config)
        os.chmod(CONFIG_PATH, 0o600)
        log(f"Relay actualizado desde locator: {relay_url}")
    return changed


def load_state() -> dict[str, Any]:
    state = load_json(STATE_PATH, {"processed": []})
    if not isinstance(state, dict):
        state = {"processed": []}
    processed = state.get("processed", [])
    if not isinstance(processed, list):
        processed = []
    state["processed"] = processed[-500:]
    return state


def mark_processed(message_id: str) -> None:
    state = load_state()
    processed = [str(item) for item in state.get("processed", []) if item]
    if message_id not in processed:
        processed.append(message_id)
    state["processed"] = processed[-500:]
    save_json(STATE_PATH, state)


def was_processed(message_id: str) -> bool:
    return message_id in set(str(item) for item in load_state().get("processed", []))


def queue_result(item: dict[str, Any]) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{item['message_id']}.json"
    save_json(path, item)
    return path


def flush_outbox(client: RelayClient) -> None:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    for path in sorted(OUTBOX.glob("*.json")):
        item = load_json(path, None)
        if not isinstance(item, dict):
            path.unlink(missing_ok=True)
            continue
        client.post_result(item)
        path.unlink(missing_ok=True)
        log(f"Resultado entregado: {item.get('message_id')}")


def execute_message(message: dict[str, Any], client: RelayClient) -> dict[str, Any]:
    message_id = str(message["message_id"])
    message_type = str(message["type"])
    payload = client.decrypt_message(message)

    if message_type == "PING":
        return {
            "ok": True,
            "pong": True,
            "time": int(time.time()),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
        }

    if message_type == "STORE_IDEA":
        text = str(payload.get("text", "")).strip()
        if not text:
            raise ValueError("STORE_IDEA sin texto")
        record = {
            "id": message_id,
            "received_at": int(time.time()),
            "text": text,
        }
        ROOT.mkdir(parents=True, exist_ok=True)
        with IDEAS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"ok": True, "saved": True, "idea_id": message_id}

    if message_type == "TERMUX_COMMAND":
        command = str(payload.get("command", "")).strip()
        if not command:
            raise ValueError("TERMUX_COMMAND vacio")
        if len(command) > 16000:
            raise ValueError("TERMUX_COMMAND demasiado largo")
        timeout = int(payload.get("timeout", 300))
        timeout = max(1, min(timeout, 900))
        completed = subprocess.run(
            ["sh", "-lc", command],
            cwd=str(Path.home()),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-262144:],
            "stderr": completed.stderr[-262144:],
        }

    raise ValueError(f"Tipo remoto no permitido: {message_type}")


def handle_message(message: dict[str, Any], client: RelayClient) -> None:
    message_id = str(message.get("message_id", ""))
    message_type = str(message.get("type", ""))
    if not message_id or not message_type:
        raise ValueError("Mensaje remoto incompleto")
    if was_processed(message_id):
        return

    succeeded = True
    try:
        result = execute_message(message, client)
    except Exception as exc:
        succeeded = False
        result = {
            "ok": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }

    item = {
        "message_id": message_id,
        "type": message_type,
        "succeeded": succeeded,
        "result": result,
    }
    queue_result(item)
    mark_processed(message_id)
    log(f"Procesado {message_type}: {message_id} success={succeeded}")


def on_signal(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
    config = load_json(CONFIG_PATH, None)
    if not isinstance(config, dict):
        raise RuntimeError(f"Falta configuración privada: {CONFIG_PATH}")

    client = RelayClient(config)
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    last_heartbeat = 0.0
    last_locator_check = 0.0
    backoff = 5
    log("Kai Mobile Termux Agent iniciado")
    while not STOP:
        try:
            flush_outbox(client)
            now = time.monotonic()
            if now - last_heartbeat >= 60:
                client.heartbeat()
                last_heartbeat = now
                log("Heartbeat OK")

            messages = client.pull(10)
            for message in messages:
                handle_message(message, client)
            flush_outbox(client)
            backoff = 5
            time.sleep(5)
        except Exception as exc:
            log(f"Ciclo fallido: {type(exc).__name__}: {exc}")
            now = time.monotonic()
            if now - last_locator_check >= 30:
                last_locator_check = now
                try:
                    if refresh_relay_from_locator(client, config):
                        backoff = 5
                except Exception as locator_exc:
                    log(f"Locator fallido: {type(locator_exc).__name__}: {locator_exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

    log("Kai Mobile Termux Agent detenido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
