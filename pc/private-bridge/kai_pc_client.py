#!/usr/bin/env python3
"""KAI PC local client: typed actions only; no arbitrary URL or command."""
import argparse
import http.client
import json
import pathlib
import sys

DEFAULT_PORT=18761

def request(method, route, token_file, payload=None, port=DEFAULT_PORT):
    token=pathlib.Path(token_file).read_text(encoding="utf-8").strip()
    if len(token)<32: raise RuntimeError("Invalid local token")
    conn=http.client.HTTPConnection("127.0.0.1",port,timeout=5)
    body=None if payload is None else json.dumps(payload,separators=(",",":"))
    try:
        conn.request(method,route,body,headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        r=conn.getresponse()
        data=json.loads(r.read(1024*64).decode("utf-8"))
        return r.status,data
    finally:
        conn.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--token-file",required=True)
    sub=p.add_subparsers(dest="cmd",required=True)
    sub.add_parser("status");sub.add_parser("apps")
    launch=sub.add_parser("launch");launch.add_argument("app_id")
    args=p.parse_args()
    try:
        if args.cmd=="status":s,data=request("GET","/v1/health",args.token_file)
        elif args.cmd=="apps":s,data=request("GET","/v1/apps",args.token_file)
        else:s,data=request("POST","/v1/apps/launch",args.token_file,{"id":args.app_id})
        print(json.dumps({"status":s,**data},ensure_ascii=False))
        return 0 if s in (200,202) else 1
    except Exception as exc:
        print(json.dumps({"ok":False,"error":type(exc).__name__}),file=sys.stderr)
        return 2
if __name__=="__main__":raise SystemExit(main())
