#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

VERSION = "2.0.0"
LOCATOR_URL = "https://raw.githubusercontent.com/Bashull/Kai/main/relay/locator-v2.json"
DEFAULT_BASE_URL = "https://kai-termux-bridge-v2.floot.app"

ROOT = Path.home() / ".kai_termux_bridge_v2"
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"
OUTBOX = ROOT / "outbox"
LOG_PATH = ROOT / "agent.log"
PID_PATH = ROOT / "agent.pid"
STOP = False


def log(message: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def save_json(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, mode)
    os.replace(tmp, path)
    os.chmod(path, mode)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def unwrap_superjson(raw: str) -> Any:
    data = json.loads(raw)
    return data.get("json", data) if isinstance(data, dict) else data


def api_request(base_url: str, route: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    url = base_url.rstrip("/") + "/_api/" + route.lstrip("/")
    headers = {
        "Cache-Control": "no-store",
        "User-Agent": f"KaiTermuxBridge/{VERSION}",
    }
    if payload is None:
        request = urllib.request.Request(url, method="GET", headers=headers)
    else:
        body = json.dumps({"json": payload}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", "replace")
            value = unwrap_superjson(text)
            if isinstance(value, dict) and value.get("error"):
                raise RuntimeError(str(value["error"]))
            return value
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        try:
            parsed = unwrap_superjson(detail)
            if isinstance(parsed, dict) and parsed.get("error"):
                detail = str(parsed["error"])
        except Exception:
            pass
        raise RuntimeError(f"HTTP {exc.code} {route}: {detail}") from exc


def fetch_locator() -> dict[str, Any]:
    request = urllib.request.Request(
        LOCATOR_URL,
        headers={"Cache-Control": "no-cache", "User-Agent": f"KaiTermuxBridge/{VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    base = str(data.get("base_url", "")).strip().rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("Locator returned a non-HTTPS base_url")
    if int(data.get("protocol", 0)) != 2:
        raise ValueError("Locator protocol mismatch")
    return data


def current_base_url(config: dict[str, Any] | None = None) -> str:
    if config and str(config.get("base_url", "")).startswith("https://"):
        return str(config["base_url"]).rstrip("/")
    try:
        return str(fetch_locator()["base_url"]).rstrip("/")
    except Exception:
        return DEFAULT_BASE_URL


def refresh_locator(config: dict[str, Any]) -> bool:
    data = fetch_locator()
    base = str(data["base_url"]).rstrip("/")
    changed = base != str(config.get("base_url", "")).rstrip("/")
    config["base_url"] = base
    config["locator_url"] = LOCATOR_URL
    config["protocol"] = 2
    save_json(CONFIG_PATH, config)
    if changed:
        log(f"Relay endpoint updated: {base}")
    return changed


def load_config() -> dict[str, Any]:
    config = load_json(CONFIG_PATH, None)
    if not isinstance(config, dict):
        raise RuntimeError(f"Bridge is not paired. Missing {CONFIG_PATH}")
    for key in ("device_id", "device_token"):
        if not config.get(key):
            raise RuntimeError(f"Bridge config missing {key}")
    return config


def load_state() -> dict[str, Any]:
    state = load_json(STATE_PATH, {"processed": [], "result_cache": {}})
    if not isinstance(state, dict):
        state = {"processed": [], "result_cache": {}}
    if not isinstance(state.get("processed"), list):
        state["processed"] = []
    if not isinstance(state.get("result_cache"), dict):
        state["result_cache"] = {}
    state["processed"] = [str(x) for x in state["processed"]][-1000:]
    return state


def remember_result(command_id: str, result: dict[str, Any]) -> None:
    state = load_state()
    processed = [x for x in state["processed"] if x != command_id]
    processed.append(command_id)
    state["processed"] = processed[-1000:]
    cache = state["result_cache"]
    cache[command_id] = result
    keep = set(state["processed"][-100:])
    state["result_cache"] = {k: v for k, v in cache.items() if k in keep}
    save_json(STATE_PATH, state)


def cached_result(command_id: str) -> dict[str, Any] | None:
    state = load_state()
    value = state.get("result_cache", {}).get(command_id)
    return value if isinstance(value, dict) else None


def queue_result(result: dict[str, Any]) -> Path:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{result['commandId']}.json"
    save_json(path, result)
    return path


def post_result(config: dict[str, Any], result: dict[str, Any]) -> None:
    payload = {
        "deviceId": config["device_id"],
        "deviceToken": config["device_token"],
        **result,
    }
    api_request(current_base_url(config), "result", payload, timeout=40)


def flush_outbox(config: dict[str, Any]) -> None:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    for path in sorted(OUTBOX.glob("*.json")):
        item = load_json(path, None)
        if not isinstance(item, dict):
            path.unlink(missing_ok=True)
            continue
        post_result(config, item)
        path.unlink(missing_ok=True)
        log(f"Result delivered: {item.get('commandId')}")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def execute_command(command: str, timeout: int) -> dict[str, Any]:
    command = str(command).strip()
    if not command:
        raise ValueError("Empty command")
    if len(command) > 16000:
        raise ValueError("Command too long")
    timeout = max(1, min(int(timeout), 900))
    try:
        completed = subprocess.run(
            ["sh", "-lc", command],
            cwd=str(Path.home()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exitCode": int(completed.returncode),
            "stdout": completed.stdout[-262144:],
            "stderr": completed.stderr[-262144:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exitCode": 124,
            "stdout": _text(exc.stdout)[-262144:],
            "stderr": ("Timeout after %ss\n" % timeout + _text(exc.stderr))[-262144:],
        }
    except Exception as exc:
        return {
            "ok": False,
            "exitCode": 125,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}"[-262144:],
        }


def heartbeat(config: dict[str, Any]) -> Any:
    return api_request(current_base_url(config), "heartbeat", {
        "deviceId": config["device_id"],
        "deviceToken": config["device_token"],
        "appVersion": VERSION,
        "capabilities": ["PING", "TERMUX_COMMAND", "FILESYSTEM", "HASH_SHA256", "OUTBOX"],
    })


def pull(config: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    response = api_request(current_base_url(config), "pull", {
        "deviceId": config["device_id"],
        "deviceToken": config["device_token"],
        "limit": max(1, min(int(limit), 50)),
    }, timeout=40)
    commands = response.get("commands", []) if isinstance(response, dict) else []
    return commands if isinstance(commands, list) else []


def process_command(config: dict[str, Any], item: dict[str, Any]) -> None:
    command_id = str(item.get("id", ""))
    if not command_id:
        log("Ignored malformed command without id")
        return

    cached = cached_result(command_id)
    if cached is not None:
        queue_result(cached)
        log(f"Redelivery detected; cached result re-queued: {command_id}")
        return

    command = str(item.get("command", ""))
    timeout = max(1, min(int(item.get("timeout", 300)), 900))
    log(f"Executing {command_id} attempt={item.get('attempt', '?')} timeout={timeout}s")
    outcome = execute_command(command, timeout)
    result = {"commandId": command_id, **outcome}
    queue_result(result)
    remember_result(command_id, result)
    log(f"Executed {command_id} exit={outcome['exitCode']} ok={outcome['ok']}")


def run_once(config: dict[str, Any]) -> None:
    flush_outbox(config)
    heartbeat(config)
    for item in pull(config, 10):
        if isinstance(item, dict):
            process_command(config, item)
            flush_outbox(config)


def pair(pair_code: str, device_name: str | None = None) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
    os.chmod(OUTBOX, 0o700)
    base_url = current_base_url()
    response = api_request(base_url, "pair-device", {
        "pairCode": pair_code.strip(),
        "deviceName": (device_name or platform.node() or "termux-android")[:80],
    }, timeout=40)
    config = {
        "base_url": base_url,
        "locator_url": LOCATOR_URL,
        "protocol": 2,
        "device_id": response["deviceId"],
        "device_token": response["deviceToken"],
        "paired_at": int(time.time()),
    }
    save_json(CONFIG_PATH, config)
    save_json(STATE_PATH, {"processed": [], "result_cache": {}})
    log(f"Paired device {config['device_id']} with {base_url}")
    heartbeat(config)


def is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def write_pid() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    if PID_PATH.exists():
        try:
            old = int(PID_PATH.read_text().strip())
            if old != os.getpid() and is_process_alive(old):
                raise RuntimeError(f"Bridge already running with pid {old}")
        except ValueError:
            pass
    PID_PATH.write_text(str(os.getpid()), encoding="ascii")
    os.chmod(PID_PATH, 0o600)


def on_signal(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def run_forever() -> None:
    global STOP
    config = load_config()
    write_pid()
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    last_heartbeat = 0.0
    last_locator = 0.0
    backoff = 5
    log(f"Kai Termux Bridge v{VERSION} started")
    try:
        while not STOP:
            try:
                now_mono = time.monotonic()
                if now_mono - last_locator >= 300:
                    last_locator = now_mono
                    try:
                        refresh_locator(config)
                    except Exception as exc:
                        log(f"Locator warning: {type(exc).__name__}: {exc}")

                flush_outbox(config)
                if now_mono - last_heartbeat >= 60:
                    heartbeat(config)
                    last_heartbeat = now_mono
                    log("Heartbeat OK")

                for item in pull(config, 10):
                    if isinstance(item, dict):
                        process_command(config, item)
                flush_outbox(config)
                backoff = 5
                time.sleep(5)
            except Exception as exc:
                log(f"Cycle failed: {type(exc).__name__}: {exc}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
    finally:
        PID_PATH.unlink(missing_ok=True)
        log("Kai Termux Bridge stopped")


def status() -> int:
    config = load_config()
    pid = None
    alive = False
    if PID_PATH.exists():
        try:
            pid = int(PID_PATH.read_text().strip())
            alive = is_process_alive(pid)
        except Exception:
            pass
    health = api_request(current_base_url(config), "health", None, timeout=20)
    print(json.dumps({
        "version": VERSION,
        "device_id": config.get("device_id"),
        "base_url": current_base_url(config),
        "paired": True,
        "token_stored": True,
        "pid": pid,
        "running": alive,
        "health": health,
    }, ensure_ascii=False, indent=2))
    return 0


def stop() -> int:
    if not PID_PATH.exists():
        print("Bridge is not running")
        return 0
    try:
        pid = int(PID_PATH.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Stop signal sent to pid {pid}")
    except ProcessLookupError:
        PID_PATH.unlink(missing_ok=True)
        print("Stale pid removed")
    return 0


def usage() -> None:
    print("Usage:")
    print("  kai-termux-bridge-v2 pair <PAIR_CODE> [DEVICE_NAME]")
    print("  kai-termux-bridge-v2 run")
    print("  kai-termux-bridge-v2 once")
    print("  kai-termux-bridge-v2 status")
    print("  kai-termux-bridge-v2 stop")


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "pair" and len(sys.argv) >= 3:
        pair(sys.argv[2], sys.argv[3] if len(sys.argv) >= 4 else None)
        return 0
    if command == "run":
        run_forever()
        return 0
    if command == "once":
        run_once(load_config())
        return 0
    if command == "status":
        return status()
    if command == "stop":
        return stop()
    usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
