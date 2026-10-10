#!/usr/bin/env python3
"""Bounded local Minecraft Java adapter. Stdlib except optional desktop helpers."""
import argparse
import json
import os
import re
import socket
import struct
import sys
from pathlib import Path

SAFE_KEYS = {'w', 'a', 's', 'd', 'space', 'shift', 'esc', 'e', 'f5', 't'}
LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1'}
WINDOW_WORDS = ('minecraft', 'lunar client', 'badlion client')


def rcon_packet(request_id, kind, message):
    payload = struct.pack('<ii', request_id, kind) + message.encode('utf-8') + b'\x00\x00'
    return struct.pack('<i', len(payload)) + payload


def recv_exact(sock, length):
    result = b''
    while len(result) < length:
        part = sock.recv(length - len(result))
        if not part:
            raise ConnectionError('RCON connection closed prematurely')
        result += part
    return result


def recv_packet(sock):
    size = struct.unpack('<i', recv_exact(sock, 4))[0]
    if not 10 <= size <= 1024 * 1024:
        raise ValueError('Invalid RCON packet size')
    body = recv_exact(sock, size)
    request_id, kind = struct.unpack('<ii', body[:8])
    if not body.endswith(b'\x00\x00'):
        raise ValueError('Invalid RCON packet termination')
    return request_id, kind, body[8:-2].decode('utf-8', 'replace')


def run_rcon(host, port, password, command, timeout=3):
    if host not in LOCAL_HOSTS:
        raise ValueError('Remote RCON rejected. Create an SSH/VPN tunnel bound to localhost.')
    if not password:
        raise ValueError('KAI_MC_RCON_PASSWORD is absent; resolve secret locally, do not print it.')
    if not 1 <= port <= 65535:
        raise ValueError('Invalid RCON port')
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(rcon_packet(41, 3, password))
        # Servers may send auth empty response before auth confirmation.
        for _ in range(3):
            rid, kind, _ = recv_packet(sock)
            if rid == -1:
                raise PermissionError('RCON authentication failed')
            if rid == 41 and kind == 2:
                break
        else:
            raise ConnectionError('No RCON authentication confirmation')
        sock.sendall(rcon_packet(42, 2, command))
        rid, _, response = recv_packet(sock)
        if rid != 42:
            raise ConnectionError('Unexpected RCON request identifier')
        return response


def validate_message(message):
    if not message or len(message) > 180 or any(ord(c) < 32 or ord(c) == 127 for c in message):
        raise ValueError('Message must contain 1-180 printable characters on one line')
    if message.lstrip().startswith('/'):
        raise ValueError('Do not inject Minecraft commands through chat')
    return '[Kai] ' + message


def active_mc_window():
    try:
        import pygetwindow as gw
    except (ImportError, NotImplementedError) as exc:
        raise RuntimeError('Desktop driver unavailable: install pygetwindow and pyautogui locally') from exc
    title = gw.getActiveWindowTitle() or ''
    if not any(word in title.lower() for word in WINDOW_WORDS):
        raise PermissionError('Minecraft is not the foreground window; no inputs sent')
    return title


def gui_action(mode, value, apply=False):
    title = active_mc_window()
    if mode == 'key' and value not in SAFE_KEYS:
        raise ValueError('Key is not allowlisted')
    if mode == 'chat':
        validate_message(value)
        if not value.isascii():
            raise ValueError('GUI typing limited to ASCII; use RCON for Unicode text')
    if mode == 'screenshot':
        path = Path(value).expanduser().resolve()
        if path.suffix.lower() != '.png':
            raise ValueError('Screenshot must use .png extension')
    if not apply:
        return {'status': 'dry_run', 'window': title, 'action': mode, 'value': value}
    try:
        import pyautogui as pg
    except ImportError as exc:
        raise RuntimeError('Install pyautogui locally to use GUI control') from exc
    pg.FAILSAFE = True
    pg.PAUSE = .10
    if mode == 'key':
        pg.press(value)
    elif mode == 'chat':
        # Press T, type the literal text, then Enter; never accept slash commands.
        pg.press('t'); pg.write(value, interval=.025); pg.press('enter')
    elif mode == 'screenshot':
        pg.screenshot().save(str(path))
    return {'status': 'executed', 'window': title, 'action': mode, 'value': value}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Kai Minecraft local operator; dry-run by default')
    ap.add_argument('action', choices=['doctor', 'players', 'say', 'key', 'chat', 'screenshot'])
    ap.add_argument('value', nargs='?', default='')
    ap.add_argument('--apply', action='store_true', help='Explicitly execute permitted action')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=25575)
    args = ap.parse_args(argv)
    if args.action == 'doctor':
        result = {'status': 'checked', 'platform': sys.platform, 'rcon_env_present': bool(os.getenv('KAI_MC_RCON_PASSWORD')), 'gui_driver': False, 'rcon_scope': 'localhost_only'}
        try:
            import pygetwindow  # noqa: F401
            import pyautogui  # noqa: F401
            result['gui_driver'] = True
        except (ImportError, NotImplementedError, OSError):
            pass
    elif args.action in {'players', 'say'}:
        # Validate the configured target BEFORE preview, so a dry-run never approves
        # arguments that execution would reject.
        if args.host not in LOCAL_HOSTS:
            raise ValueError('Remote RCON rejected: localhost tunnel only')
        if not (1 <= args.port <= 65535):
            raise ValueError('Invalid RCON port')
        if args.action == 'say':
            command = 'say ' + validate_message(args.value)
            if not args.apply:
                result = {'status': 'dry_run', 'command': command, 'host': args.host, 'port': args.port}
            else:
                result = {'status': 'executed', 'reply': run_rcon(args.host, args.port, os.getenv('KAI_MC_RCON_PASSWORD'), command)}
        else:
            # Explicit observation action. No world mutation.
            result = {'status': 'observed', 'reply': run_rcon(args.host, args.port, os.getenv('KAI_MC_RCON_PASSWORD'), 'list')} if args.apply else {'status': 'dry_run', 'command': 'list'}
    else:
        if not args.value:
            raise ValueError('GUI action requires a value')
        result = gui_action(args.action, args.value, args.apply)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, PermissionError, ConnectionError, OSError, RuntimeError) as exc:
        print(json.dumps({'status': 'blocked', 'reason': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
