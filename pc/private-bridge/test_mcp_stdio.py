"""Integration smoke test for local MCP adapter, requires running PC Agent."""
import json,os,subprocess,sys,pathlib
here=pathlib.Path(__file__).resolve().parent
token=os.environ.get("KAI_PC_TOKEN_FILE")
if not token:raise SystemExit("KAI_PC_TOKEN_FILE not configured")
p=subprocess.Popen([sys.executable,str(here/"kai_pc_mcp_stdio.py"),"--token-file",token],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
def query(i,method,params=None):
    p.stdin.write(json.dumps({"jsonrpc":"2.0","id":i,"method":method,"params":params or {}})+"\n")
    p.stdin.flush()
    line=p.stdout.readline()
    if not line: raise AssertionError("MCP EOF")
    result=json.loads(line)
    assert result["id"]==i,result
    return result
try:
    init=query(1,"initialize",{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"kai-smoke","version":"0.1"}})
    assert init["result"]["serverInfo"]["name"]=="kai-private-pc"
    tools=query(2,"tools/list")["result"]["tools"]
    assert len(tools)==3 and all(t["name"].startswith("kai_pc_") for t in tools)
    health=query(3,"tools/call",{"name":"kai_pc_health","arguments":{}})
    assert not health["result"]["isError"]
    apps=query(4,"tools/call",{"name":"kai_pc_list_apps","arguments":{}})
    assert not apps["result"]["isError"]
    blocked=query(5,"tools/call",{"name":"kai_pc_launch_allowlisted_app","arguments":{"id":"cmd","extra":True}})
    assert blocked["error"]["code"]==-32602
    print("MCP_LOCAL_STDIO_TESTS_5_OF_5_PASS")
finally:
    p.terminate()
    p.wait(timeout=5)
