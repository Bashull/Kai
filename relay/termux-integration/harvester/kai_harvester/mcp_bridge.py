"""Local stdio MCP proof of concept, read-only tools, no socket, no authentication data.
Not installed into ChatGPT; compatible MCP hosts must explicitly launch it.
"""
import argparse
import json
import os
import sys
from .advanced import doctor,search_messages,asset_gaps
from .store import Store

TOOL_SCHEMAS={
'kai_harvest_doctor':{'type':'object','properties':{},'additionalProperties':False},
'kai_harvest_stats':{'type':'object','properties':{},'additionalProperties':False},
'kai_harvest_audit':{'type':'object','properties':{},'additionalProperties':False},
'kai_harvest_asset_gaps':{'type':'object','properties':{},'additionalProperties':False},
'kai_harvest_search':{'type':'object','properties':{'query':{'type':'string'},'limit':{'type':'integer'}},'required':['query'],'additionalProperties':False}}

def serve(root):
    os.umask(0o077)
    # MCP stdio uses one JSON-RPC message per line. Do not print debug to stdout.
    for line in sys.stdin:
        req=None
        try:
            req=json.loads(line)
            if not isinstance(req,dict): continue
            method=req.get('method')
            if method=='notifications/initialized' or 'id' not in req: continue
            rid=req['id'];params=req.get('params') or {}
            if method=='initialize':
                result={'protocolVersion':'2025-06-18','capabilities':{'tools':{'listChanged':False}},
                        'serverInfo':{'name':'kai-harvester-local','version':'0.2.2'}}
            elif method=='ping': result={}
            elif method=='tools/list':
                result={'tools':[{'name':name,'description':'Local-only, read-only KAI Harvester operation','inputSchema':schema}
                                for name,schema in TOOL_SCHEMAS.items()]}
            elif method=='tools/call':
                name=params.get('name');args=params.get('arguments') or {}
                if name not in TOOL_SCHEMAS or not isinstance(args,dict): raise ValueError('UNKNOWN_TOOL')
                if any(k not in TOOL_SCHEMAS[name]['properties'] for k in args): raise ValueError('INVALID_ARGS')
                if name=='kai_harvest_doctor': payload=doctor()
                else:
                    with_root=Store(root)
                    try:
                        if name=='kai_harvest_stats':payload=with_root.stats()
                        elif name=='kai_harvest_audit':payload=with_root.audit()
                        elif name=='kai_harvest_asset_gaps':payload=asset_gaps(with_root)
                        elif name=='kai_harvest_search':payload=search_messages(with_root,args.get('query'),args.get('limit',20))
                        else:raise ValueError('UNKNOWN_TOOL')
                    finally: with_root.close()
                result={'content':[{'type':'text','text':json.dumps(payload,ensure_ascii=False)}]}
            else:
                raise ValueError('METHOD_NOT_FOUND')
            sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':rid,'result':result},ensure_ascii=False)+'\n')
        except Exception as exc:
            if not isinstance(locals().get('req'),dict) or 'id' not in req: continue
            # avoid reflecting exception details / private provider payload in protocol output
            sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':req['id'],
                                          'error':{'code':-32602,'message':type(exc).__name__}},ensure_ascii=False)+'\n')
        sys.stdout.flush()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='~/KAI_RUNTIME_LAB/chatgpt-harvester')
    args=p.parse_args();serve(args.root)
if __name__=='__main__': main()
