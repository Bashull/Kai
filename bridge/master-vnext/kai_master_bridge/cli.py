"""Owner-local operator interface; approval and kill switch never MCP tools."""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import uuid
from .contracts import SCHEMA
from .gateway import Gateway

def main():
    p=argparse.ArgumentParser(prog='kai-master')
    p.add_argument('--config',required=True)
    p.add_argument('--state-dir',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    sub.add_parser('mcp')
    req=sub.add_parser('request');req.add_argument('capability');req.add_argument('--params',default='{}')
    approval=sub.add_parser('approve');approval.add_argument('request_id');approval.add_argument('digest')
    emergency=sub.add_parser('stop');emergency.add_argument('--reason',default='local owner emergency')
    sub.add_parser('unstop')
    args=p.parse_args()
    gw=Gateway(args.config,args.state_dir)
    if args.command=='mcp':
        from .mcp_stdio import serve
        serve(args.config,args.state_dir);return
    if args.command=='status':result=gw.status()
    elif args.command=='request':
        import time
        result=gw.execute({'schema':SCHEMA,'request_id':str(uuid.uuid4()),
                          'node_id':gw.policy.node_id,'capability':args.capability,
                          'params':json.loads(args.params),'deadline':int(time.time())+120})
    elif args.command=='approve':
        gw.ledger.add_approval(args.request_id,args.digest)
        result={'ok':True,'approval':'locally recorded; same request must be retried before deadline'}
    elif args.command=='stop':
        stop=gw.stop_flag
        stop.parent.mkdir(parents=True,exist_ok=True)
        if not stop.exists():
            with stop.open('x',encoding='utf-8') as fh:fh.write('Global bridge stop by local owner\n')
        result={'ok':True,'stopped':True}
    elif args.command=='unstop':
        # Restore only from owner's local CLI; never remotely from MCP.
        gw.stop_flag.unlink(missing_ok=True)
        result={'ok':True,'stopped':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
