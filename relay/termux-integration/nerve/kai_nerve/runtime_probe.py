from __future__ import annotations

import hashlib
import os
import pathlib
import re
import shlex
import subprocess
from typing import Any

SERVICE_ROOT = pathlib.Path('/data/data/com.termux/files/usr/var/service')
SCRIPT_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.sh')
MAX_TEXT = 512_000
SAFE_ENV_KEYS={'HOME','TMPDIR','KAI_PROFILE','KAI_LIVE_HOST','KAI_LIVE_PORT','KAI_LIVE_FORWARD','KAI_LIVE_MAX_SIZE','KAI_LIVE_MAX_FPS','KAI_LIVE_BIT_RATE','KAI_LIVE_START_TIMEOUT','KAI_LIVE_START_ATTEMPTS','KAI_BEDROCK_WS_PORT','KAI_BEDROCK_HTTP_PORT','KAI_MCWSS_WS_PORT','KAI_MCWSS_HTTP_PORT','KAI_WORLDBUS_PORT'}

def _safe_env_value(key: str, value: bytes):
    text=value.decode(errors='replace')
    if key in SAFE_ENV_KEYS:return text
    # Never copy arbitrary KAI_* values; token/key/secret material is represented only by a hash.
    return {'redacted':True}


def _sha256(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def _read_text(path: pathlib.Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT:
            return None
        return path.read_text(errors='replace')
    except Exception:
        return None


def _resolve_candidate(token: str, cwd: pathlib.Path) -> pathlib.Path | None:
    token = token.strip().strip('"\'')
    if not token or not token.lower().endswith(SCRIPT_SUFFIXES):
        return None
    p = pathlib.Path(os.path.expandvars(os.path.expanduser(token)))
    if not p.is_absolute():
        p = cwd / p
    try:
        return p.resolve()
    except Exception:
        return p


def target_from_run_script(run_script: str, service_root: pathlib.Path) -> pathlib.Path | None:
    """Resolve the file a runit run script intends to execute.

    This intentionally supports the simple run scripts used by the KAI stack;
    it does not pretend to be a full shell parser.
    """
    cwd = service_root
    for raw in (run_script or '').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('cd '):
            try:
                parts = shlex.split(line)
                if len(parts) >= 2:
                    p = pathlib.Path(os.path.expandvars(os.path.expanduser(parts[1])))
                    cwd = p if p.is_absolute() else (cwd / p)
            except Exception:
                pass
            continue
        if line.startswith('exec '):
            try:
                parts = shlex.split(line[5:])
            except Exception:
                parts = line[5:].split()
            for tok in parts:
                p = _resolve_candidate(tok, cwd)
                if p is not None:
                    return p
    return None


def target_from_cmdline(cmdline: str, cwd: pathlib.Path) -> pathlib.Path | None:
    try:
        parts = shlex.split(cmdline or '')
    except Exception:
        parts = (cmdline or '').split()
    for tok in parts[1:]:
        p = _resolve_candidate(tok, cwd)
        if p is not None:
            return p
    return None


def _target_record(path: pathlib.Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return {
        'path': str(path),
        'exists': path.exists(),
        'sha256': _sha256(path),
        'text': None,
    }


def _listeners_for_pid(pid: int) -> list[str]:
    """Best-effort listener snapshot. Missing permission is recorded as no rows, not inferred healthy."""
    try:
        text = subprocess.check_output(
            ['ss', '-ltnp'], text=True, stderr=subprocess.STDOUT, timeout=2
        )
    except Exception:
        return []
    rows = []
    needle = f'pid={pid},'
    for line in text.splitlines():
        if needle in line:
            rows.append(line.strip())
    return rows


def inspect_service(name: str) -> dict[str, Any]:
    root = SERVICE_ROOT / name
    out: dict[str, Any] = {
        'service': name,
        'exists': root.exists(),
        'run_path': str(root / 'run'),
    }
    if not root.exists():
        return out

    run_script = ''
    try:
        run_script = (root / 'run').read_text()
        out['run_script'] = None
        out['run_sha256'] = hashlib.sha256(run_script.encode()).hexdigest()
    except Exception as exc:
        out['run_script_error'] = str(exc)

    run_target = target_from_run_script(run_script, root)
    out['desired_target'] = _target_record(run_target)

    try:
        status = subprocess.check_output(
            ['sv', 'status', str(root)],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=2,
        ).strip()
        out['sv_status'] = status
        match = re.search(r'\(pid (\d+)\)', status)
        if match:
            pid = int(match.group(1))
            out['pid'] = pid
            proc = pathlib.Path('/proc') / str(pid)
            cmdline = ''
            cwd = root
            try:
                cmdline = (
                    (proc / 'cmdline').read_bytes().replace(b'\x00', b' ').decode().strip()
                )
                out['cmdline'] = None
                out['argv_count'] = len(cmdline.split())
            except Exception:
                pass
            try:
                cwd = pathlib.Path(os.readlink(proc / 'cwd'))
                out['cwd'] = str(cwd)
            except Exception:
                pass
            try:
                env_parts = (proc / 'environ').read_bytes().split(b'\x00')
                keep = {}
                for item in env_parts:
                    if b'=' not in item:
                        continue
                    key, value = item.split(b'=', 1)
                    key_s = key.decode(errors='ignore')
                    if key_s in SAFE_ENV_KEYS or key_s.startswith(('KAI_', 'PORT', 'WS_', 'HTTP_')):
                        keep[key_s] = _safe_env_value(key_s,value)
                out['env'] = keep
            except Exception:
                pass
            process_target = target_from_cmdline(cmdline, cwd)
            out['running_target'] = _target_record(process_target)
            out['listeners'] = _listeners_for_pid(pid)
    except Exception as exc:
        out['sv_error'] = str(exc)

    desired = out.get('desired_target') or {}
    running = out.get('running_target') or {}
    out['target_identity_match'] = (
        desired.get('sha256') == running.get('sha256')
        if desired.get('sha256') and running.get('sha256')
        else None
    )
    identity_material = '\n'.join(
        [
            out.get('run_script') or '',
            out.get('cmdline') or '',
            out.get('cwd', ''),
            repr(sorted((out.get('env') or {}).items())),
            repr(desired.get('sha256')),
            repr(running.get('sha256')),
            repr(out.get('listeners') or []),
        ]
    ).encode()
    out['loaded_code_verified'] = False
    out['runtime_identity_sha256'] = hashlib.sha256(identity_material).hexdigest()
    return out


def inspect_many(names: list[str]) -> dict[str, Any]:
    return {name: inspect_service(name) for name in names}
