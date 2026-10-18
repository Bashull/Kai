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
    sub.add_parser('capabilities')
    p = sub.add_parser('animation-library')
    p.add_argument('--category'); p.add_argument('--search')
    p.add_argument('--offset', type=int, default=0); p.add_argument('--limit', type=int, default=25)
    p = sub.add_parser('describe'); p.add_argument('capability_id')
    for name in ('validate', 'quote'):
        p = sub.add_parser(name); p.add_argument('capability_id'); p.add_argument('--parameters-json', required=True)
    p = sub.add_parser('tasks'); p.add_argument('capability_id'); p.add_argument('--cursor'); p.add_argument('--page-size', type=int, default=10)
    p = sub.add_parser('remote-task'); p.add_argument('capability_id'); p.add_argument('task_id')
    for name in ('operations', 'operation-cycle'):
        p = sub.add_parser(name); p.add_argument('job_id')
    for name in ('operation', 'operation-submit', 'operation-refresh', 'operation-poll', 'operation-download', 'operation-checkpoint', 'operation-reconcile'):
        p = sub.add_parser(name); p.add_argument('job_id'); p.add_argument('operation_id')
        if name == 'operation-download':
            from .capability_engine import OUTPUT_VARIANTS
            p.add_argument('format', choices=('glb', 'gltf', 'obj', 'mtl', 'fbx', 'stl', '3mf', 'usdz', 'blend', 'image', 'thumbnail', 'base_color', 'metallic', 'normal', 'roughness'))
            p.add_argument('--texture-index', type=int, default=0)
            p.add_argument('--variant', choices=sorted(OUTPUT_VARIANTS))
        if name == 'operation-checkpoint':
            p.add_argument('label'); p.add_argument('--asset-id', action='append', default=[])
        if name == 'operation-reconcile':
            p.add_argument('task_id'); p.add_argument('request_sha256'); p.add_argument('--receipt-asset-id', required=True)
    p = sub.add_parser('plan'); p.add_argument('job_id'); p.add_argument('capability_id')
    p.add_argument('--operation-id', default='main'); p.add_argument('--parameters-json', required=True)
    p.add_argument('--budget', type=int, default=500); p.add_argument('--dependency', action='append', default=[])
    p.add_argument('--parent-asset-id', action='append', default=[])
    args = parser.parse_args()
    try:
        f = make_forge()
        if args.command in ('stdio', 'http'):
            from .sdk_server import serve
            serve(f, transport=args.command)
            return
        writes = {'create', 'submit', 'cancel', 'download', 'cycle', 'refresh', 'approve', 'plan',
                  'operation-submit', 'operation-refresh', 'operation-poll', 'operation-download',
                  'operation-cycle', 'operation-checkpoint', 'operation-reconcile'}
        if args.command in writes and os.environ.get('KAI_MESHY_ALLOW_WRITES') != '1':
            raise ForgeError('WRITE_SCOPE_NOT_ENABLED')
        if args.command in ('approve', 'operation-reconcile') and os.environ.get('KAI_MESHY_ALLOW_APPROVALS') != '1':
            raise ForgeError('HUMAN_APPROVAL_SCOPE_NOT_ENABLED')
        extended = {'capabilities', 'describe', 'validate', 'quote', 'tasks', 'remote-task', 'plan',
                    'operations', 'operation', 'operation-submit', 'operation-refresh', 'operation-poll',
                    'operation-download', 'operation-cycle', 'operation-checkpoint', 'operation-reconcile'}
        if args.command in extended:
            from .capability_engine import CapabilityEngine
            engine = CapabilityEngine(f)
            if hasattr(args, 'parameters_json'):
                if len(args.parameters_json) > 1024 * 1024:
                    raise ForgeError('OPERATION_PARAMETERS_TOO_LARGE')
                parameters = json.loads(args.parameters_json)
                engine._safe_parameters(parameters)
        if args.command == 'doctor':
            value = {'auth': f.cli.auth(), 'workspace': str(f.root), 'cli': f.cli.executable,
                     'spending_enabled': f.spending_enabled, 'max_authorized_credits': f.max_credits,
                     'codex_transport': 'stdio', 'chatgpt': 'NOT_CONNECTED'}
        elif args.command == 'balance': value = f.cli.balance()
        elif args.command == 'animation-library':
            from .animation_library import AnimationLibrary
            value = AnimationLibrary.fetch(f.cli, timeout=30).query(
                category=args.category, search=args.search, offset=args.offset, limit=args.limit)
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
        elif args.command == 'capabilities': value = engine.list_capabilities()
        elif args.command == 'describe': value = engine.describe(args.capability_id)
        elif args.command == 'validate': value = engine.catalog.validation_report(args.capability_id, parameters)
        elif args.command == 'quote':
            value = engine.catalog.quote(args.capability_id, parameters)
            value['permission'] = value.pop('authorization', 'NOT_GRANTED_BY_CATALOGUE')
            value['request_sha256'] = value.pop('payload_fingerprint', None)
            value['pricing_gate_passed'] = value.pop('spend_allowed', False)
            value['current_spend_authorized'] = False
        elif args.command == 'tasks': value = engine.list_remote(args.capability_id, cursor=args.cursor, page_size=args.page_size)
        elif args.command == 'remote-task': value = engine.get_remote(args.capability_id, args.task_id, timeout=30)
        elif args.command == 'plan': value = engine.create_operation(args.job_id, args.capability_id, parameters,
            budget=args.budget, operation_id=args.operation_id, dependencies=args.dependency, parent_asset_ids=args.parent_asset_id)
        elif args.command == 'operations': value = engine.list_operations(args.job_id)
        elif args.command == 'operation': value = engine.get_operation(args.job_id, args.operation_id)
        elif args.command == 'operation-submit': value = engine.submit_operation(args.job_id, args.operation_id)
        elif args.command == 'operation-refresh': value = engine.refresh_operation(args.job_id, args.operation_id, timeout=30)
        elif args.command == 'operation-poll': value = engine.poll_operation(args.job_id, args.operation_id, timeout=30, max_attempts=6, max_stalled=3)
        elif args.command == 'operation-download': value = engine.download_operation(args.job_id, args.operation_id, args.format, texture_index=args.texture_index, variant=args.variant)
        elif args.command == 'operation-cycle':
            from .operation_loop import cycle_operations
            value = cycle_operations(engine, args.job_id, timeout=30)
        elif args.command == 'operation-checkpoint': value = engine.checkpoint(args.job_id, args.operation_id, args.label, asset_ids=args.asset_id)
        elif args.command == 'operation-reconcile':
            actor = os.environ.get('KAI_MESHY_APPROVAL_ACTOR')
            if not actor: raise ForgeError('HUMAN_APPROVAL_CONTEXT_REQUIRED')
            value = engine.reconcile_operation(args.job_id, args.operation_id, args.task_id, args.request_sha256,
                receipt_asset_id=args.receipt_asset_id, actor=actor)
        # Only immutable catalogue metadata bypasses runtime-data redaction;
        # otherwise real schema names such as image_url would disappear.
        trusted_catalogue = args.command in ('capabilities', 'describe')
        if trusted_catalogue and len(json.dumps(value, ensure_ascii=False).encode()) > 2 * 1024 * 1024:
            raise ForgeError('CATALOGUE_METADATA_SIZE_EXCEEDED')
        print(json.dumps(value if trusted_catalogue else public_json(value), ensure_ascii=False, indent=2))
    except (ForgeError, ValueError, OSError) as exc:
        print(json.dumps({'error': type(exc).__name__, 'message': public_json(str(exc))}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
