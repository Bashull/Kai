"""Termux-compatible read-only-to-input, offline-first command line."""
import argparse
import os
import json
import sys
from .store import Store
from .importer import ingest_file
from .advanced import doctor,index_messages,search_messages,asset_gaps,compare_manifests,scan_zip
from .rate_policy import decide_retry

def main(argv=None):
    os.umask(0o077)
    p=argparse.ArgumentParser(prog='kai-harvest',description='KAI Harvester Fusion offline evidence inspector')
    p.add_argument('--root',default='~/KAI_RUNTIME_LAB/chatgpt-harvester',help='Private archive directory')
    sub=p.add_subparsers(dest='command',required=True)
    i=sub.add_parser('ingest',help='Ingest JSON, JSONL, official ZIP or selected folder (offline)')
    i.add_argument('paths',nargs='+')
    sub.add_parser('audit',help='Rehash all immutable evidence')
    sub.add_parser('stats',help='Counts; never infer full inventory')
    sub.add_parser('render',help='Generate active-path Markdown from RAW')
    sub.add_parser('manifest',help='Write verification manifest')
    sub.add_parser('reader',help='Generate safe local HTML index (no internet)')
    sub.add_parser('doctor',help='Inspect local Termux features without secrets')
    zscan=sub.add_parser('scan-zip',help='Metadata-only ZIP triage; supports large archives')
    zscan.add_argument('archive')
    sub.add_parser('index',help='Create private FTS5 index across all available branches')
    find=sub.add_parser('search',help='Search all imported messages including regenerated branches')
    find.add_argument('query'); find.add_argument('--limit',type=int,default=20)
    sub.add_parser('assets',help='Report physical assets versus references; no false completeness')
    compare=sub.add_parser('compare-manifest',help='Compare local snapshot against another offline manifest')
    compare.add_argument('other')
    rate=sub.add_parser('rate-policy',help='Simulate safe retry, without connecting to service')
    rate.add_argument('status',type=int);rate.add_argument('--attempt',type=int,default=0);rate.add_argument('--retry-after')
    args=p.parse_args(argv)
    if args.command=='doctor': print(json.dumps(doctor(),indent=2));return 0
    if args.command=='scan-zip':print(json.dumps(scan_zip(args.archive),ensure_ascii=False,indent=2));return 0
    if args.command=='rate-policy': print(json.dumps(decide_retry(args.status,args.attempt,args.retry_after),indent=2));return 0
    s=Store(args.root)
    try:
        if args.command=='ingest':
            imported=0
            for path in args.paths:imported+=ingest_file(s,path)
            print(json.dumps({'imported_records_attempted':imported,'state':s.stats()},indent=2))
            s.manifest()
        elif args.command=='stats':print(json.dumps(s.stats(),indent=2))
        elif args.command=='audit':
            result=s.audit();print(json.dumps(result,indent=2))
            if not result['integrity_pass']:return 2
        elif args.command=='render':print(json.dumps({'rendered':s.export_views()},indent=2))
        elif args.command=='manifest':print(s.manifest())
        elif args.command=='reader':print(s.export_reader())
        elif args.command=='index':print(json.dumps(index_messages(s),indent=2))
        elif args.command=='search':print(json.dumps(search_messages(s,args.query,args.limit),ensure_ascii=False,indent=2))
        elif args.command=='assets':print(json.dumps(asset_gaps(s),indent=2))
        elif args.command=='compare-manifest':
            with open(os.path.expanduser(args.other),encoding='utf-8') as f:other=json.load(f)
            print(json.dumps(compare_manifests(s,other),indent=2))
    except (OSError,ValueError,RuntimeError) as e:
        print('ERROR:',str(e),file=sys.stderr);return 1
    finally:s.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
