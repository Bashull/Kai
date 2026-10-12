#!/usr/bin/env python3
"""KAI PC local MCP (stdio). A typed, allowlisted adapter; no shell and no remote listener."""
import argparse
import json
import sys
from kai_pc_client import request

VERSION="0.1.0"

TOOLS=[
 {"name":"kai_pc_health","description":"Read health of the user's locally authenticated KAI PC Agent.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
 {"name":"kai_pc_list_apps","description":"List applications explicitly allowlisted on the user's PC.","inputSchema":{"type":"object","properties":{},"additionalProperties":False}},
 {"name":"kai_pc_launch_allowlisted_app","description":"Request launch of one explicitly allowlisted PC app. This changes the PC and requires the user's approval.","inputSchema":{"type":"object","properties":{"id":{"type":"string","minLength":1,"maxLength":128}},"required":["id"],"additionalProperties":False}}
]

def reply(msg):
    sys.stdout.write(json.dumps(msg,ensure_ascii=False,separators=(",",":"))+"\n")
    sys.stdout.flush()

def tool_result(status,data):
    return {"content":[{"type":"text","text":json.dumps({"status":status,**data},ensure_ascii=False)}],"isError":status not in (200,202)}

def serve(token_file):
    for line in sys.stdin:
        if not line.strip():continue
        try:
            req=json.loads(line)
            if not isinstance(req,dict):continue
            method=req.get("method")
            request_id=req.get("id",None)
            params=req.get("params") or {}
            if method=="notifications/initialized" or request_id is None:continue
            if method=="initialize":
                requested=params.get("protocolVersion","2025-06-18")
                protocol=requested if requested in ("2025-03-26","2025-06-18","2025-11-25") else "2025-06-18"
                result={"protocolVersion":protocol,"capabilities":{"tools":{"listChanged":False}},"serverInfo":{"name":"kai-private-pc","version":VERSION}}
            elif method=="ping":
                result={}
            elif method=="tools/list":
                result={"tools":TOOLS}
            elif method=="tools/call":
                name=params.get("name");args=params.get("arguments") or {}
                if not isinstance(args,dict):raise ValueError("arguments must be a dict")
                if name=="kai_pc_health" and not args:
                    st,data=request("GET","/v1/health",token_file)
                elif name=="kai_pc_list_apps" and not args:
                    st,data=request("GET","/v1/apps",token_file)
                elif name=="kai_pc_launch_allowlisted_app" and set(args)=={"id"} and isinstance(args.get("id"),str) and 0<len(args["id"])<=128:
                    st,data=request("POST","/v1/apps/launch",token_file,{"id":args["id"]})
                else:
                    raise ValueError("not_allowlisted_or_invalid_schema")
                result=tool_result(st,data)
            else:
                reply({"jsonrpc":"2.0","id":request_id,"error":{"code":-32601,"message":"Method not found"}})
                continue
            reply({"jsonrpc":"2.0","id":request_id,"result":result})
        except (json.JSONDecodeError,ValueError,TypeError) as e:
            if isinstance(req,dict) and req.get("id") is not None:
                reply({"jsonrpc":"2.0","id":req["id"],"error":{"code":-32602,"message":"Invalid parameters"}})
        except Exception as e:
            if isinstance(req,dict) and req.get("id") is not None:
                reply({"jsonrpc":"2.0","id":req["id"],"error":{"code":-32603,"message":type(e).__name__}})

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--token-file",required=True)
    serve(p.parse_args().token_file)
