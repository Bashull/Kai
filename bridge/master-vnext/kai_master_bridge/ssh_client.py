"""Phone-side KAI Master SSH client: typed MCP, pinned host, no remote shell.

LAN-only bootstrap. Not a ChatGPT cloud connector or a WAN exposure mechanism.
"""
from __future__ import annotations
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from .contracts import Action, SCHEMA

class ClientError(RuntimeError):
    pass

def load_config(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ClientError("INVALID_CONFIG")
    host = data.get("ssh_host")
    try:
        addr = ipaddress.ip_address(host)
        if addr.version != 4 or not (addr.is_private or addr.is_loopback):
            raise ValueError()
    except (ValueError, TypeError):
        raise ClientError("LAN_IP_REQUIRED") from None
    user = data.get("ssh_user")
    if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", user):
        raise ClientError("INVALID_SSH_USER")
    port = data.get("ssh_port")
    if type(port) is not int or not (1 <= port <= 65535):
        raise ClientError("INVALID_SSH_PORT")
    node = data.get("node_id")
    if not isinstance(node, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", node):
        raise ClientError("INVALID_NODE")
    for key in ("identity_file", "known_hosts"):
        path = Path(data.get(key, ""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink():
            raise ClientError("MISSING_PIN_OR_IDENTITY")
    if os.name != "nt" and Path(data["identity_file"]).stat().st_mode & 0o077:
        raise ClientError("PRIVATE_KEY_PERMISSIONS")
    allowed = data.get("allowed_apps", [])
    if not isinstance(allowed, list) or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", x) for x in allowed):
        raise ClientError("INVALID_APP_ALLOWLIST")
    return data

def send(config, action, *, runner=subprocess.run):
    checked = Action.parse(action)
    if checked.node_id != config["node_id"]:
        raise ClientError("REMOTE_NODE_NOT_PINNED")
    cmd = [
        "ssh", "-F", "/dev/null", "-T", "-p", str(config["ssh_port"]),
        "-i", config["identity_file"],
        "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
        "-o", "PasswordAuthentication=no", "-o", "KbdInteractiveAuthentication=no",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=" + config["known_hosts"],
        "-o", "ClearAllForwardings=yes",
        "-o", "ConnectTimeout=7", "-o", "NumberOfPasswordPrompts=0",
        config["ssh_user"] + "@" + config["ssh_host"],
    ]
    frame = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "kai_master_action", "arguments": {"action": action}}}
    try:
        p = runner(cmd, input=json.dumps(frame, separators=(",", ":")) + "\n",
                   capture_output=True, text=True, timeout=25, shell=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ClientError("SSH_CONNECTION_FAILED") from None
    if p.returncode != 0:
        raise ClientError("SSH_AUTH_OR_POLICY_DENIED")
    if len(p.stdout.encode("utf-8")) > 65536:
        raise ClientError("MCP_RESPONSE_TOO_LARGE")
    lines = [x for x in p.stdout.splitlines() if x.strip()]
    if len(lines) != 1:
        raise ClientError("MCP_FRAMING_ERROR")
    try:
        rpc = json.loads(lines[0])
        if rpc.get("jsonrpc") != "2.0" or rpc.get("id") != 1:
            raise ValueError()
        txt = rpc["result"]["content"][0]["text"]
        rec = json.loads(txt)
        if rec.get("schema") != "kai.master.receipt/1" or rec.get("request_id") != action["request_id"]:
            raise ValueError()
        return rec
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ClientError("MCP_RESPONSE_INVALID") from None

def make_action(config, capability, params):
    result = {"schema": SCHEMA, "request_id": str(uuid.uuid4()),
              "node_id": config["node_id"], "capability": capability,
              "params": params, "deadline": int(time.time()) + 240}
    Action.parse(result)
    return result

def main(argv=None):
    p = argparse.ArgumentParser(prog="kai-master-pc")
    p.add_argument("--config", required=True)
    p.add_argument("--state-dir", required=True)
    subs = p.add_subparsers(dest="cmd", required=True)
    subs.add_parser("status")
    subs.add_parser("health")
    subs.add_parser("apps")
    ls = subs.add_parser("list")
    ls.add_argument("--root", default="kai")
    ls.add_argument("--relative", required=True)
    launch = subs.add_parser("launch")
    launch.add_argument("app_id")
    retry = subs.add_parser("retry")
    retry.add_argument("request_id")
    args = p.parse_args(argv)
    try:
        cfg = load_config(args.config)
        home = Path(args.state_dir)
        if args.cmd == "retry":
            rid = str(uuid.UUID(args.request_id))
            if rid != args.request_id:
                raise ClientError("INVALID_REQUEST_ID")
            path = home / "pending" / (rid + ".json")
            action = json.loads(path.read_text(encoding="utf-8"))
            Action.parse(action)
        else:
            if args.cmd == "status":
                cap,params = "host.status", {}
            elif args.cmd == "health":
                cap,params = "pc.agent.health", {}
            elif args.cmd == "apps":
                cap,params = "pc.agent.apps", {}
            elif args.cmd == "list":
                cap,params = "fs.list", {"root":args.root,"relative":args.relative}
            else:
                if args.app_id not in cfg["allowed_apps"]:
                    raise ClientError("APP_NOT_IN_PHONE_ALLOWLIST")
                cap,params = "pc.agent.launch", {"app_id":args.app_id}
            action = make_action(cfg, cap, params)
        rec = send(cfg, action)
        if rec["status"] == "PENDING_LOCAL_APPROVAL":
            folder = home / "pending"
            folder.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                os.chmod(folder, 0o700)
            path = folder / (action["request_id"] + ".json")
            if not path.exists():
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(action, stream, separators=(",", ":"))
        print(json.dumps(rec, ensure_ascii=False))
        return 0 if rec["status"] in ("COMPLETED", "PENDING_LOCAL_APPROVAL") else 1
    except (ClientError, OSError, ValueError, KeyError) as exc:
        code = str(exc) if isinstance(exc, ClientError) else "INVALID_REQUEST_OR_CONFIG"
        print(json.dumps({"ok": False, "error": code}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
