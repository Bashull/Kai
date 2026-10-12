"""Small local-only JSON-RPC/MCP stdio envelope, not remotely network exposed."""
from __future__ import annotations
import json
import sys
from .gateway import Gateway

TOOLS=[
 {'name':'kai_master_status','description':'Show only the local master bridge status. No privileged actions.',
  'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},
 {'name':'kai_master_action','description':'Submit typed versioned action. Mutating and sensitive operations require separate local owner approval.',
  'inputSchema':{'type':'object','properties':{'action':{'type':'object'}},'required':['action'],'additionalProperties':False}}
]

class MCP:
    def __init__(self,gateway):self.gateway=gateway
    def handle(self,request):
        if not isinstance(request,dict) or request.get('jsonrpc')!='2.0':
            return None
        rid=request.get('id')
        if rid is None:return None
        method=request.get('method')
        p=request.get('params') or {}
        if method=='initialize':
            return {'jsonrpc':'2.0','id':rid,'result':{'protocolVersion':'2025-06-18',
                    'capabilities':{'tools':{'listChanged':False}},
                    'serverInfo':{'name':'kai-master-bridge-lab','version':'0.1.0'}}}
        if method=='ping':return {'jsonrpc':'2.0','id':rid,'result':{}}
        if method=='tools/list':return {'jsonrpc':'2.0','id':rid,'result':{'tools':TOOLS}}
        if method=='tools/call':
            name=p.get('name') if isinstance(p,dict) else None
            args=p.get('arguments',{}) if isinstance(p,dict) else None
            if not isinstance(args,dict):return self.err(rid,'INVALID_ARGUMENTS')
            if name=='kai_master_status' and not args:
                result=self.gateway.status()
            elif name=='kai_master_action' and set(args)=={'action'}:
                result=self.gateway.execute(args['action'])
            else:return self.err(rid,'UNKNOWN_TOOL_OR_ARGUMENTS')
            return {'jsonrpc':'2.0','id':rid,'result':{'content':[
                {'type':'text','text':json.dumps(result,ensure_ascii=False)}],
                'isError':result.get('status') in ('DENIED','FAILED')}}
        return self.err(rid,'UNKNOWN_METHOD')

    @staticmethod
    def err(rid,message):
        return {'jsonrpc':'2.0','id':rid,'error':{'code':-32602,'message':message}}

def serve(config_path,state_dir,stdin=sys.stdin,stdout=sys.stdout):
    mcp=MCP(Gateway(config_path,state_dir))
    for line in stdin:
        if len(line)>128*1024:continue
        try:msg=json.loads(line);answer=mcp.handle(msg)
        except (json.JSONDecodeError,TypeError,ValueError):answer=None
        if answer is not None:
            stdout.write(json.dumps(answer,ensure_ascii=False,separators=(',',':'))+'\n')
            stdout.flush()
