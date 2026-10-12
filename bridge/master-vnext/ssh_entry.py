"""On-demand, key-restricted Windows SSH entrypoint for the KAI Master MCP stdio gateway.

Deploy only behind an OpenSSH authorized_keys forced command with restrictions.
Never use it as a generic remote shell or unattended administrator daemon.
"""
from __future__ import annotations

import os
from pathlib import Path

from kai_master_bridge.mcp_stdio import serve


def main() -> int:
    # OpenSSH exposes any caller-supplied remote command in this variable.
    # The owner key is for a fixed MCP channel only, never arbitrary commands.
    if os.environ.get("SSH_ORIGINAL_COMMAND"):
        return 126

    root = Path(__file__).resolve().parent
    policy = root / "config" / "windows-vnext-lab.json"
    state = root / "state" / "windows-vnext-lab"
    if not policy.is_file():
        return 78

    serve(policy, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
