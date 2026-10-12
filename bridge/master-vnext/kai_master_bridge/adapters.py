"""Reuse *interfaces* from PC Agent, Mesh, Node/GUI and ADB. No new listeners."""
from __future__ import annotations
import hashlib
import http.client
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
from typing import Any

class AdapterError(RuntimeError):
    pass

SENSITIVE = re.compile(r'(?i)(^\.|pass(word|phrase)?|secret|token|credential|private.?key|\.pem$|\.key$|^auth\.json$)')
MAX_READ_BYTES = 64 * 1024 * 1024

class Adapters:
    def __init__(self, config):
        self.config = config

    def _expect(self, args: dict, keys: set[str]):
        if set(args) != keys or not all(isinstance(v, str) and v for v in args.values()):
            raise AdapterError('INVALID_ARGUMENTS')

    def _within_root(self, args, file_needed=False):
        self._expect(args, {'root', 'relative'})
        roots = self.config.get('roots', {})
        if args['root'] not in roots:
            raise AdapterError('UNKNOWN_ROOT')
        root = pathlib.Path(roots[args['root']])
        if not root.is_absolute():
            raise AdapterError('ROOT_NOT_ABSOLUTE')
        rel = pathlib.PurePath(args['relative'])
        if rel.is_absolute() or not rel.parts or any(p in ('.','..') or SENSITIVE.search(p) for p in rel.parts):
            raise AdapterError('UNSAFE_PATH')
        # Reject junctions / reparse points rather than following them. Concurrency
        # hardening remains a gate before offering filesystem writes.
        try:
            if root.is_symlink() or (hasattr(root,'is_junction') and root.is_junction()):
                raise AdapterError('UNSAFE_ROOT')
            base = root.resolve(strict=True)
            if not base.is_dir():
                raise AdapterError('INVALID_ROOT')
            p = root
            for part in rel.parts:
                p = p / part
                if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):
                    raise AdapterError('SYMLINK_OR_JUNCTION_BLOCKED')
            path = p.resolve(strict=True)
            if not path.is_relative_to(base):
                raise AdapterError('OUTSIDE_ROOT')
        except (OSError, ValueError):
            raise AdapterError('PATH_UNAVAILABLE') from None
        if file_needed and (not path.is_file() or path.stat().st_size > MAX_READ_BYTES):
            raise AdapterError('FILE_MISSING_OR_TOO_LARGE')
        return path

    def _pc_agent(self, route, method='GET', payload=None):
        settings = self.config.get('pc_agent', {})
        token_file = settings.get('token_file')
        if not token_file:
            raise AdapterError('PC_AGENT_NOT_PROVISIONED')
        path = pathlib.Path(token_file)
        if path.is_symlink() or not path.is_file():
            raise AdapterError('TOKEN_FILE_UNAVAILABLE')
        try:
            token = path.read_text(encoding='utf-8').strip()
            if len(token) < 32:
                raise AdapterError('INVALID_LOCAL_CREDENTIAL')
            port = int(settings.get('port', 18761))
            if port < 1024 or port > 65535:
                raise AdapterError('INVALID_LOCAL_PORT')
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=4)
            try:
                body = json.dumps(payload) if payload is not None else None
                conn.request(method, route, body=body, headers={
                    'Authorization':'Bearer '+token, 'Content-Type':'application/json'})
                response = conn.getresponse()
                raw = response.read(32*1024+1)
                if len(raw) > 32*1024:
                    raise AdapterError('REMOTE_OUTPUT_TOO_LARGE')
                if response.status not in (200, 202):
                    raise AdapterError('PC_AGENT_REJECTED')
                obj = json.loads(raw.decode('utf-8'))
                if not isinstance(obj, dict):
                    raise AdapterError('REMOTE_INVALID_RESPONSE')
                return {'status_code':response.status, 'response':obj}
            finally:
                conn.close()
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
            raise AdapterError('PC_AGENT_UNAVAILABLE') from None

    def _adb(self, argv):
        exe = self.config.get('android', {}).get('adb_executable')
        if not exe:
            raise AdapterError('ADB_NOT_CONFIGURED')
        binary = pathlib.Path(exe)
        if not binary.is_absolute() or not binary.is_file():
            raise AdapterError('ADB_NOT_VERIFIED')
        try:
            p = subprocess.run([str(binary), *argv], capture_output=True, stdin=subprocess.DEVNULL,
                               timeout=7, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise AdapterError('ADB_UNAVAILABLE') from None
        if p.returncode != 0:
            raise AdapterError('ADB_REJECTED')
        if len(p.stdout) > 16*1024:
            raise AdapterError('ADB_OUTPUT_TOO_LARGE')
        return p.stdout.decode('utf-8',errors='replace')

    def execute(self, capability: str, args: dict[str,Any]):
        if capability == 'host.status':
            self._expect(args, set())
            return {'status':'ready', 'platform':platform.system(), 'machine':platform.machine(),
                    'transport':'local-stdio', 'open_remote_listeners':0}
        if capability == 'fs.list':
            p = self._within_root(args)
            if not p.is_dir():
                raise AdapterError('NOT_DIRECTORY')
            names=[]
            for item in p.iterdir():
                if SENSITIVE.search(item.name):
                    continue
                names.append({'name':item.name[:128], 'type':('directory' if item.is_dir() else 'file')})
                if len(names) >= 100: break
            return {'entries':names, 'truncated':len(names)>=100}
        if capability == 'fs.sha256':
            p = self._within_root(args,file_needed=True)
            h=hashlib.sha256()
            with p.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):
                    h.update(block)
            return {'sha256':h.hexdigest(), 'size':p.stat().st_size}
        if capability == 'pc.agent.health':
            self._expect(args,set())
            return self._pc_agent('/v1/health')
        if capability == 'pc.agent.apps':
            self._expect(args,set())
            return self._pc_agent('/v1/apps')
        if capability == 'pc.agent.launch':
            self._expect(args,{'app_id'})
            permitted=self.config.get('pc_agent',{}).get('allowed_app_ids',[])
            if args['app_id'] not in permitted:
                raise AdapterError('APP_NOT_APPROVED_IN_LOCAL_POLICY')
            return self._pc_agent('/v1/apps/launch','POST',{'id':args['app_id']})
        if capability == 'android.adb.devices':
            self._expect(args,set())
            output=self._adb(['devices','-l'])
            devices=set()
            for line in output.splitlines()[1:]:
                columns=line.split()
                if len(columns)>=2 and columns[1]=='device':
                    devices.add(columns[0])
            return {'authorized_devices':len(devices),'device_identifiers_redacted':True}
        if capability in ('android.adb.model','android.adb.launch'):
            expected=self.config.get('android',{}).get('serial','')
            if not expected or '\x00' in expected or '\n' in expected:
                raise AdapterError('ADB_SERIAL_NOT_CONFIGURED')
            if capability == 'android.adb.model':
                self._expect(args,set())
                out=self._adb(['-s',expected,'shell','getprop','ro.product.model'])
                return {'model':out.strip()[:80]}
            self._expect(args,{'package'})
            package=args['package']
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+',package):
                raise AdapterError('INVALID_PACKAGE')
            allowed=self.config.get('android',{}).get('allowed_packages',[])
            if package not in allowed:
                raise AdapterError('PACKAGE_NOT_ALLOWED')
            self._adb(['-s',expected,'shell','monkey','-p',package,'1'])
            return {'submitted':True, 'effect_observed':False}
        if capability == 'pc.gui.windows':
            self._expect(args,set())
            script=self.config.get('gui',{}).get('script')
            if not script or not pathlib.Path(script).is_absolute() or not pathlib.Path(script).is_file():
                raise AdapterError('GUI_DONOR_NOT_VERIFIED')
            try:
                process=subprocess.run([sys.executable,script,'windows'],capture_output=True,
                                       stdin=subprocess.DEVNULL,timeout=6,check=False)
                if process.returncode or len(process.stdout)>16384:
                    raise AdapterError('GUI_DONOR_FAILURE')
                data=json.loads(process.stdout.decode('utf-8'))
                if not isinstance(data,dict) or not isinstance(data.get('windows'),list):
                    raise AdapterError('GUI_DONOR_BAD_RESPONSE')
                # No window titles/contents leave the process by default: privacy-preserving count.
                return {'count':int(data.get('count',0)), 'titles_redacted':True}
            except (OSError,ValueError,subprocess.TimeoutExpired,UnicodeError):
                raise AdapterError('GUI_DONOR_FAILURE') from None
        raise AdapterError('UNSUPPORTED_CAPABILITY')
