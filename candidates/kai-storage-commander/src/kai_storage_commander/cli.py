from __future__ import annotations

import argparse
import json
from pathlib import Path

from .commander import StorageCommander
from .transport import HttpStorageTransport


def main() -> int:
    parser = argparse.ArgumentParser(prog="kai-storage-commander")
    parser.add_argument("mode", choices=("plan", "execute"))
    parser.add_argument("request_json", help="JSON object describing the storage action")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", default="")
    parser.add_argument("--audit", default=str(Path.home() / ".kai_storage_commander" / "audit.jsonl"))
    parser.add_argument("--fingerprint")
    args = parser.parse_args()

    request = json.loads(args.request_json)
    transport = HttpStorageTransport(args.base_url, args.token)
    commander = StorageCommander(transport=transport, audit_path=args.audit)
    if args.mode == "plan":
        result = commander.plan(request)
    else:
        result = commander.execute(request, manifest_fingerprint=args.fingerprint)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
