"""Official MCP SDK 2 facade over the existing Forge and its single ledger.

Lineage: KAI_MASTER_MCP_DUAL_ERA_20261017/kai_dual_era_mcp.py transport
pattern, adapted to the Meshy Forge capability. No shell or arbitrary REST tool.
The SDK negotiates legacy initialize and modern server/discover itself.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
from typing import Annotated, Any, Literal

from mcp import types
from mcp.server import MCPServer
from pydantic import Field

from .core import Forge, ForgeError, public_json
from .registry import AssetRegistry

Stage = Literal["prototype", "build"]
AssetFormat = Literal["preview", "glb", "obj", "mtl", "fbx", "texture", "thumbnail"]
JobID = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,70}$")]
SHA256 = Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")]


@dataclass(frozen=True)
class Policy:
    allow_writes: bool = False
    allow_spend: bool = False
    allow_approvals: bool = False
    approval_actor: str | None = None

    @classmethod
    def from_env(cls):
        return cls(
            allow_writes=os.environ.get("KAI_MESHY_ALLOW_WRITES") == "1",
            allow_spend=os.environ.get("KAI_MESHY_ALLOW_SPEND") == "1",
            allow_approvals=os.environ.get("KAI_MESHY_ALLOW_APPROVALS") == "1",
            approval_actor=os.environ.get("KAI_MESHY_APPROVAL_ACTOR") or None,
        )

    def gate(self, *, confirm: bool, paid=False, approval=False):
        if not self.allow_writes or confirm is not True:
            raise ForgeError("MCP_WRITE_REQUIRES_OPERATOR_ENABLE_AND_CONFIRM")
        if paid and not self.allow_spend:
            raise ForgeError("MCP_SPENDING_DISABLED")
        if approval and (not self.allow_approvals or not self.approval_actor):
            raise ForgeError("MCP_HUMAN_APPROVAL_CONTEXT_REQUIRED")


def _result(value: Any = None, *, error: str | None = None, trusted_catalogue: bool = False):
    body = {"schema": "kai.meshy.mcp/v1", "ok": error is None}
    if error:
        body["error"] = error
    else:
        body["result"] = value if trusted_catalogue else public_json(value)
    return types.CallToolResult(
        content=[types.TextContent(text=json.dumps(body, ensure_ascii=False, sort_keys=True))],
        structuredContent=body,
        isError=error is not None,
    )


def _call(fn, *args, _trusted_catalogue=False, **kwargs):
    try:
        value = fn(*args, **kwargs)
        if _trusted_catalogue and len(json.dumps(value, ensure_ascii=False).encode()) > 2 * 1024 * 1024:
            raise ForgeError('CATALOGUE_METADATA_SIZE_EXCEEDED')
        return _result(value, trusted_catalogue=_trusted_catalogue)
    except ForgeError as exc:
        # Core errors are machine codes; never expose arbitrary exception text.
        message = str(exc)
        code = message if re.fullmatch(r"[A-Z0-9_:.-]{1,180}", message) else "FORGE_OPERATION_FAILED"
        return _result(error=code)
    except (OSError, ValueError, TypeError):
        return _result(error="LOCAL_OPERATION_FAILED")


def create_server(forge: Forge, policy: Policy | None = None) -> MCPServer:
    policy = policy or Policy.from_env()
    registry = AssetRegistry(forge)
    server = MCPServer(
        name="kai-meshy-mcp", version="0.3.0-staging",
        instructions=(
            "KAI Meshy Forge: same local Forge/ledger for stdio and HTTP. "
            "Only advertised operations are installed. Meshy Brick Figure prototype/build "
            "are separate; preserve the visual approval gate. Paid submits are disabled by "
            "default. Never retry a submission_unknown; reconcile its receipt. "
            "Local cancellation does not cancel a remote task or release its reservation. "
            "Do not claim ChatGPT is connected without a real conversation tool receipt."
        ),
    )
    read = types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
    write = types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    paid = types.ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_connection_status() -> types.CallToolResult:
        """Read installed adapter scope, permission gates and local budget; no vendor request."""
        return _result({
            "adapter": "kai-meshy-mcp", "sdk": "mcp-python-2",
            "implemented_generation": ["creative-lab.brick-figure.prototype", "creative-lab.brick-figure.build"],
            "capability_operation_engine": "INSTALLED_STAGING",
            "catalogue_contract_count": len(capability_engine.list_capabilities()),
            "catalogue_is_spend_authorization": False,
            "writes_enabled": policy.allow_writes,
            "spend_enabled": policy.allow_writes and policy.allow_spend and forge.spending_enabled and bool(forge.spending_job_ids),
            "human_approval_enabled": policy.allow_writes and policy.allow_approvals and bool(policy.approval_actor),
            "chatgpt_connection": "READY_FOR_CHATGPT_CONNECTION_NOT_E2E_VERIFIED",
            "budget": forge.budget_status(),
        })

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_auth_status() -> types.CallToolResult:
        """Read effective Meshy CLI authentication booleans; never return credential files."""
        return _call(forge.cli.auth)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_balance() -> types.CallToolResult:
        """Read Meshy API balance through the authenticated existing CLI; no generation."""
        return _call(forge.cli.balance)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_budget() -> types.CallToolResult:
        """Read reservations, actual costs and uncertain submissions from the shared ledger."""
        return _call(forge.budget_status)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_list_jobs() -> types.CallToolResult:
        """List local jobs and visual approval/cancellation flags without a vendor call."""
        return _call(forge.list_jobs)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_get_job(job_id: JobID) -> types.CallToolResult:
        """Read a known local job, its stages, task identities and persistent costs."""
        return _call(forge.get_job, job_id)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_list_assets(limit: Annotated[int, Field(ge=1, le=500)] = 100) -> types.CallToolResult:
        """Read assets from the shared Forge database and verify their current content hashes."""
        return _call(registry.list, limit=limit)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_get_asset(asset_id: Annotated[str, Field(pattern=r"^sha256-[a-f0-9]{64}$")]) -> types.CallToolResult:
        """Read one registered workspace asset and verify immutable content; never return file contents."""
        return _call(registry.get, asset_id)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_inspect_reference(path: str) -> types.CallToolResult:
        """Inspect image format, dimensions and hash within the Forge workspace. Visual identity still requires human review."""
        return _call(registry.inspect_reference, path)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_inspect_model(path: str) -> types.CallToolResult:
        """Inspect a workspace OBJ/STL/GLB deterministically. This is the installed structural inspector; Blender is not implied."""
        def run():
            from .assets import inspect_model
            target = forge._workspace_path(path)
            return inspect_model(target)
        return _call(run)

    # Metadata only advertises implemented operations for the active policy.
    if policy.allow_writes:
        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_create_job(
            job_id: JobID, source: str,
            budget: Annotated[int, Field(ge=1, le=500)] = 36,
            confirm: bool = False,
        ) -> types.CallToolResult:
            """Copy an approved local image into an immutable job; creates no Meshy task. Requires confirm and an allowed reference root."""
            def run():
                policy.gate(confirm=confirm)
                return forge.create_job(job_id, source, budget=budget)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_refresh_job(job_id: JobID, stage: Stage, confirm: bool = False) -> types.CallToolResult:
            """Read the existing remote task once and audit its status locally. Never submits a task."""
            def run():
                policy.gate(confirm=confirm)
                return forge.refresh(job_id, stage)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_download(
            job_id: JobID, stage: Stage, format: AssetFormat, confirm: bool = False,
        ) -> types.CallToolResult:
            """Download/cache a succeeded job asset into its fixed workspace location and hash it; never regenerates."""
            def run():
                policy.gate(confirm=confirm)
                return forge.download(job_id, stage, format=format)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_cancel_job(
            job_id: JobID, reason: Annotated[str, Field(min_length=1, max_length=500)], confirm: bool = False,
        ) -> types.CallToolResult:
            """Stop local orchestration; remote task continues and reservations remain. No remote DELETE."""
            def run():
                policy.gate(confirm=confirm)
                return forge.cancel(job_id, reason=reason)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_cycle(
            job_id: JobID, timeout_seconds: Annotated[int, Field(ge=1, le=30)] = 10,
            confirm: bool = False,
        ) -> types.CallToolResult:
            """Run one bounded recovery tick: resume the same task, recover files or report the next human gate. Never submits a paid stage."""
            def run():
                from .pipeline import cycle
                policy.gate(confirm=confirm)
                return cycle(forge, job_id, timeout=timeout_seconds)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_register_asset(
            path: str, role: Literal["reference", "preview", "model", "texture", "thumbnail", "derivative", "evidence"],
            parent_id: Annotated[str | None, Field(pattern=r"^sha256-[a-f0-9]{64}$")] = None,
            source_id: Annotated[str, Field(max_length=500)] = "operator-registered",
            author: Annotated[str, Field(max_length=500)] = "unknown",
            license: Annotated[str, Field(max_length=500)] = "UNDETERMINED",
            document_state: Literal["CURRENT", "CANONICAL", "DRAFT", "STAGING", "HISTORICAL", "ANCESTOR", "SUPERSEDED", "QUARANTINED", "REJECTED"] = "STAGING",
            confirm: bool = False,
        ) -> types.CallToolResult:
            """Register an existing workspace file by content hash and immutable parent, with narrow provenance. No uploads, copying or file-content exposure."""
            def run():
                policy.gate(confirm=confirm)
                return registry.register(path, role, parent_id=parent_id, provenance={
                    "source_id": source_id, "author": author, "license": license, "document_state": document_state,
                })
            return _call(run)

    if policy.allow_writes and policy.allow_spend and forge.spending_enabled and forge.spending_job_ids:
        @server.tool(annotations=paid, structured_output=False)
        def kai_meshy_submit_stage(job_id: JobID, stage: Stage, confirm: bool = False) -> types.CallToolResult:
            """Billable single Brick Figure POST: prototype6 or build30 credits. Same ledger budget and human visual gate apply. Unknown outcome must be reconciled, never retried."""
            def run():
                policy.gate(confirm=confirm, paid=True)
                return forge.submit(job_id, stage)
            return _call(run)

    if policy.allow_writes and policy.allow_approvals and policy.approval_actor:
        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_approve_preview(job_id: JobID, sha256: SHA256, confirm: bool = False) -> types.CallToolResult:
            """Record a human visual decision for the exact preview hash. Only present in an explicitly enabled human approval context; actor is server configured."""
            def run():
                policy.gate(confirm=confirm, approval=True)
                return forge.approve(job_id, sha256, actor=policy.approval_actor)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_import_historical_task(
            job_id: JobID, stage: Stage,
            task_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9-]{8,100}$")],
            actual_credits: Annotated[float, Field(ge=0, le=500)],
            status: Literal["PENDING", "IN_PROGRESS", "SUCCEEDED", "FAILED", "CANCELED"] = "SUCCEEDED",
            rejected: bool = True, confirm: bool = False,
        ) -> types.CallToolResult:
            """Import an operator-verified historical task/cost into an existing job; defaults rejected. Does not create or approve a remote build."""
            def run():
                policy.gate(confirm=confirm, approval=True)
                return forge.import_task(job_id, stage, task_id, actual_credits, status=status, rejected=rejected)
            return _call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_reconcile_unknown(
            job_id: JobID, stage: Stage,
            task_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9-]{8,100}$")],
            request_sha256: SHA256, confirm: bool = False,
        ) -> types.CallToolResult:
            """Bind an operator-identified remote task to its uncertain original request hash. Performs GET, never a replacement POST."""
            def run():
                policy.gate(confirm=confirm, approval=True)
                return forge.reconcile(job_id, stage, task_id, request_sha256)
            return _call(run)

    from .capability_tools import register_capability_tools
    # Only metadata from the bundled, code-reviewed catalogue uses this path.
    # Remote task data and all caller-provided payloads keep strict redaction.
    def catalogue_call(fn, *args):
        return _call(fn, *args, _trusted_catalogue=True)
    capability_engine = register_capability_tools(server, forge, policy, call=_call,
        catalogue_call=catalogue_call, read=read, write=write, paid=paid)
    return server


def _loopback(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def _read_http_token(path):
    if not path:
        raise ForgeError("HTTP_TOKEN_FILE_REQUIRED")
    target = Path(os.path.abspath(Path(path).expanduser()))
    if any(p.is_symlink() for p in [target, *target.parents]):
        raise ForgeError("HTTP_TOKEN_SYMLINK_DENIED")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
        raise ForgeError("HTTP_TOKEN_FILE_MUST_BE_PRIVATE")
    token = target.read_text().strip()
    if not 32 <= len(token) <= 4096 or any(c.isspace() for c in token) or not token.isascii():
        raise ForgeError("HTTP_TOKEN_INVALID")
    return token.encode("ascii")


class LoopbackBearerMiddleware:
    def __init__(self, app, token):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        peer = (scope.get("client") or ("", 0))[0]
        auth = [value for name, value in scope.get("headers", []) if name.lower() == b"authorization"]
        permitted = _loopback(peer) and len(auth) == 1 and hmac.compare_digest(auth[0], b"Bearer " + self.token)
        if not permitted:
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")]})
            await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
            return
        await self.app(scope, receive, send)


def create_http_app(server: MCPServer, *, token_file, host="127.0.0.1"):
    if not _loopback(host):
        raise ForgeError("HTTP_BIND_MUST_BE_LOOPBACK")
    token = _read_http_token(token_file)
    app = server.streamable_http_app(host=host, json_response=True)
    app.add_middleware(LoopbackBearerMiddleware, token=token)
    return app


async def serve_async(forge: Forge, transport="stdio", *, host="127.0.0.1", port=18772, token_file=None):
    server = create_server(forge)
    if transport == "stdio":
        await server.run_stdio_async()
    elif transport in ("http", "streamable-http"):
        import uvicorn
        app = create_http_app(server, host=host, token_file=token_file or os.environ.get("KAI_MESHY_HTTP_TOKEN_FILE"))
        await uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False)).serve()
    else:
        raise ForgeError("UNSUPPORTED_MCP_TRANSPORT")


def serve(forge: Forge, transport="stdio", **kwargs):
    asyncio.run(serve_async(forge, transport=transport, **kwargs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", "--state-root", type=Path)
    parser.add_argument("--transport", choices=["stdio", "http", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18772)
    parser.add_argument("--token-file", type=Path)
    args = parser.parse_args()
    if args.root:
        os.environ["KAI_MESHY_WORKSPACE"] = str(args.root)
    from .cli import make_forge
    forge = make_forge()
    serve(forge, args.transport, host=args.host, port=args.port, token_file=args.token_file)


if __name__ == "__main__":
    main()
