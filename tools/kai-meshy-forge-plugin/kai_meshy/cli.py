"""Scoped CLI for the same Forge used by MCP; no arbitrary shell or REST."""
import argparse
import inspect
import json
import os
import stat
from pathlib import Path
from .core import Forge, ForgeError, MeshyCLI, public_json


def make_forge():
    config_path = Path.home() / '.config/kai-meshy-forge/runtime.json'
    config = {}
    if config_path.exists() or config_path.is_symlink():
        if config_path.is_symlink() or stat.S_IMODE(config_path.stat().st_mode) & 0o077:
            raise ForgeError('RUNTIME_CONFIGURATION_MUST_BE_PRIVATE')
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if not isinstance(config, dict) or set(config) - {'schema', 'workspace', 'cli', 'reference_roots'}:
            raise ForgeError('INVALID_RUNTIME_CONFIGURATION_FIELDS')
        if config.get('schema') != 'kai.meshy.runtime/v1':
            raise ForgeError('INVALID_RUNTIME_CONFIGURATION_SCHEMA')
    root = Path(os.environ.get('KAI_MESHY_WORKSPACE', config.get('workspace', '~/KAI_VISUAL_STUDIO/KAI_MESHY_FORGE_OMEGA'))).expanduser()
    refs = json.loads(os.environ['KAI_MESHY_REFERENCE_ROOTS']) if 'KAI_MESHY_REFERENCE_ROOTS' in os.environ else config.get('reference_roots', [])
    if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
        raise ForgeError('INVALID_REFERENCE_ROOT_CONFIGURATION')
    kwargs = {'reference_roots': refs or None, 'spending_enabled': os.environ.get('KAI_MESHY_ALLOW_SPEND') == '1'}
    if 'spending_job_ids' in inspect.signature(Forge).parameters:
        kwargs['spending_job_ids'] = set(json.loads(os.environ.get('KAI_MESHY_SPEND_JOB_IDS', '[]')))
    runner = os.environ.get('KAI_MESHY_CLI') or config.get('cli')
    return Forge(root, cli=MeshyCLI(runner), max_credits=500, **kwargs)


def main():
    parser = argparse.ArgumentParser(prog='kai-meshy-job-engine')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('doctor', 'balance', 'jobs', 'stdio', 'http'):
        sub.add_parser(name)
    for name in ('job', 'cycle', 'cancel'):
        p = sub.add_parser(name)
        p.add_argument('job_id')
    p = sub.add_parser('create'); p.add_argument('job_id'); p.add_argument('source'); p.add_argument('--budget', type=int, default=36)
    p = sub.add_parser('submit'); p.add_argument('job_id'); p.add_argument('stage', choices=('prototype', 'build'))
    p = sub.add_parser('refresh'); p.add_argument('job_id'); p.add_argument('stage', choices=('prototype', 'build'))
    p = sub.add_parser('download'); p.add_argument('job_id'); p.add_argument('stage', choices=('prototype', 'build')); p.add_argument('format', choices=('preview', 'glb', 'obj', 'mtl', 'fbx'))
    p = sub.add_parser('approve'); p.add_argument('job_id'); p.add_argument('sha256'); p.add_argument('--actor', required=True)
    args = parser.parse_args()
    try:
        f = make_forge()
        if args.command in ('stdio', 'http'):
            from .sdk_server import serve
            serve(f, transport=args.command)
            return
        if args.command in ('create', 'submit', 'cancel', 'download', 'cycle', 'refresh', 'approve') and os.environ.get('KAI_MESHY_ALLOW_WRITES') != '1':
            raise ForgeError('WRITE_SCOPE_NOT_ENABLED')
        if args.command == 'approve' and os.environ.get('KAI_MESHY_ALLOW_APPROVALS') != '1':
            raise ForgeError('HUMAN_APPROVAL_SCOPE_NOT_ENABLED')
        if args.command == 'doctor':
            value = {'auth': f.cli.auth(), 'workspace': str(f.root), 'cli': f.cli.executable,
                     'spending_enabled': f.spending_enabled, 'max_authorized_credits': f.max_credits,
                     'codex_transport': 'stdio', 'chatgpt': 'NOT_CONNECTED'}
        elif args.command == 'balance': value = f.cli.balance()
        elif args.command == 'jobs':
            with f._db() as db: value = [dict(r) for r in db.execute('SELECT id,source_sha,budget FROM jobs ORDER BY created')]
        elif args.command == 'job': value = f.get_job(args.job_id)
        elif args.command == 'create': value = f.create_job(args.job_id, args.source, args.budget)
        elif args.command == 'submit': value = f.submit(args.job_id, args.stage)
        elif args.command == 'refresh': value = f.refresh(args.job_id, args.stage)
        elif args.command == 'download': value = f.download(args.job_id, args.stage, args.format)
        elif args.command == 'cancel': value = f.cancel(args.job_id, reason='OWNER_LOCAL_STOP')
        elif args.command == 'approve': value = f.approve(args.job_id, args.sha256, actor=args.actor)
        elif args.command == 'cycle':
            from .pipeline import cycle
            value = cycle(f, args.job_id, timeout=30)
        print(json.dumps(public_json(value), ensure_ascii=False, indent=2))
    except (ForgeError, ValueError, OSError) as exc:
        print(json.dumps({'error': type(exc).__name__, 'message': public_json(str(exc))}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
