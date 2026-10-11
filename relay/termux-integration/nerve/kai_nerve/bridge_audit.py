from __future__ import annotations
import re

HOST_PORT = re.compile(r'(?:127\.0\.0\.1|localhost|0\.0\.0\.0|\[::1\])\s*:\s*(\d{2,5})', re.I)
LISTEN = re.compile(r'\blisten\s*\(\s*(\d{2,5})', re.I)
PORT_ASSIGN = re.compile(r'\b[A-Z0-9_]*PORT[A-Z0-9_]*\b[^0-9\n]{0,64}(\d{2,5})', re.I)
SS_LOCAL = re.compile(r'\s(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]|\[::1\]|\*):(\d{2,5})\s')


def _valid(n: str) -> int | None:
    x = int(n)
    return x if 1024 <= x <= 65535 else None


def ports(text: str) -> set[int]:
    """Extract likely TCP/WS/HTTP port configuration without treating every 4-digit number as a port."""
    out: set[int] = set()
    text = text or ''
    for regex in (HOST_PORT, LISTEN):
        for s in regex.findall(text):
            x = _valid(s)
            if x is not None:
                out.add(x)
    for s in PORT_ASSIGN.findall(text):
        x = _valid(s)
        if x is not None:
            out.add(x)
    return out


def listener_ports(rows: list[str]) -> set[int]:
    out: set[int] = set()
    for row in rows or []:
        for s in SS_LOCAL.findall(row):
            x = _valid(s)
            if x is not None:
                out.add(x)
    return out


def audit(runtime: dict) -> dict:
    rows = []
    configured_owners: dict[int, list[str]] = {}
    listening_owners: dict[int, list[str]] = {}
    blockers = []
    for name, x in runtime.items():
        desired_target = x.get('desired_target') or {}
        running_target = x.get('running_target') or {}
        desired_text = '\n'.join([x.get('run_script', ''), desired_target.get('text') or '', repr(x.get('env') or {})])
        running_text = '\n'.join([x.get('cmdline', ''), running_target.get('text') or '', repr(x.get('env') or {})])
        desired = ports(desired_text)
        running_cfg = ports(running_text)
        listeners = listener_ports(x.get('listeners') or [])
        target_match = x.get('target_identity_match')
        port_match = desired == running_cfg if desired and running_cfg else None
        row = {
            'service': name,
            'desired_ports': sorted(desired),
            'running_config_ports': sorted(running_cfg),
            'listener_ports': sorted(listeners),
            'desired_target': desired_target.get('path'),
            'running_target': running_target.get('path'),
            'target_identity_match': target_match,
            'config_process_port_match': port_match,
            'runtime_identity': x.get('runtime_identity_sha256'),
        }
        rows.append(row)
        for p in desired | running_cfg:
            configured_owners.setdefault(p, []).append(name)
        for p in listeners:
            listening_owners.setdefault(p, []).append(name)
        if target_match is not True:
            blockers.append(f'{name}:target_identity_{"mismatch" if target_match is False else "unknown"}')
        if port_match is not True:
            blockers.append(f'{name}:port_config_{"mismatch" if port_match is False else "unknown"}')
        if not listeners:
            blockers.append(f'{name}:listener_identity_unknown')
    configured_collisions = {p: sorted(set(v)) for p, v in configured_owners.items() if len(set(v)) > 1}
    listener_collisions = {p: sorted(set(v)) for p, v in listening_owners.items() if len(set(v)) > 1}
    if configured_collisions:
        blockers.append('configured_port_collision')
    if listener_collisions:
        blockers.append('listener_port_collision')
    return {
        'services': rows,
        'configured_port_collisions': configured_collisions,
        'listener_port_collisions': listener_collisions,
        'blockers': sorted(set(blockers)),
        'safe_to_restart': not blockers,
    }
