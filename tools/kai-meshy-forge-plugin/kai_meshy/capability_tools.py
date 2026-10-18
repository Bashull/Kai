"""Typed capability facade, using the same Forge, contracts and permission gates.

There is intentionally no tool accepting an HTTP method, endpoint or credential.
Read tools cannot create local plans or submit vendor tasks.
"""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal

from mcp import types
from pydantic import Field

from .capability_engine import CapabilityEngine

CapabilityID = Annotated[str, Field(pattern=r'^[a-z0-9_.-]{1,100}$')]
OperationID = Annotated[str, Field(pattern=r'^[a-zA-Z0-9_-]{1,70}$')]
TaskID = Annotated[str, Field(pattern=r'^[a-zA-Z0-9-]{8,100}$')]
SHA256 = Annotated[str, Field(pattern=r'^[a-fA-F0-9]{64}$')]
AssetID = Annotated[str, Field(pattern=r'^sha256-[a-f0-9]{64}$')]
OutputVariant = Literal['rigged_character_glb', 'rigged_character_fbx', 'animation_glb', 'animation_fbx',
                        'processed_usdz', 'processed_armature_fbx', 'processed_animation_fps_fbx',
                        'walking_glb', 'walking_fbx', 'walking_armature_glb', 'running_glb', 'running_fbx', 'running_armature_glb']


def register_capability_tools(server, forge, policy, *, call, catalogue_call, read, write, paid):
    # Additive migration of the existing ledger; never opens a second authority.
    engine = CapabilityEngine(forge)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_capabilities() -> types.CallToolResult:
        """List installed versioned request contracts and price rules. Documentary coverage does not imply a paid E2E test or spending authorization."""
        return catalogue_call(engine.list_capabilities)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_describe_capability(capability_id: CapabilityID) -> types.CallToolResult:
        """Read one allowlisted capability's real routes, input schema, sources, constraints and pricing. No vendor request."""
        return catalogue_call(engine.describe, capability_id)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_validate_request(capability_id: CapabilityID, parameters: dict[str, Any]) -> types.CallToolResult:
        """Validate a REST payload in memory against the pinned contract, returning only field names and its hash. No files, vendor calls or echoed media."""
        def run():
            engine._safe_parameters(parameters)
            value = engine.catalog.validate(capability_id, parameters)
            digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            return {'valid': True, 'capability_id': capability_id,
                    'request_sha256': digest, 'fields': sorted(value), 'submitted': False}
        return call(run)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_quote(capability_id: CapabilityID, parameters: dict[str, Any]) -> types.CallToolResult:
        """Calculate a documentary credit quote without a POST. Unknown/stale pricing blocks submission; the catalogue never grants owner authorization."""
        def run():
            engine._safe_parameters(parameters)
            quote = engine.catalog.quote(capability_id, parameters)
            quote['permission'] = quote.pop('authorization', 'NOT_GRANTED_BY_CATALOGUE')
            quote['request_sha256'] = quote.pop('payload_fingerprint', None)
            quote['pricing_gate_passed'] = quote.pop('spend_allowed', False)
            quote['current_spend_authorized'] = False
            return quote
        return call(run)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_list_remote_tasks(
        capability_id: CapabilityID,
        cursor: Annotated[str | None, Field(max_length=2000)] = None,
        page_size: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> types.CallToolResult:
        """GET one real task page for an allowlisted capability. Preserve returned pagination; no create, cancel or download."""
        return call(engine.list_remote, capability_id, cursor=cursor, page_size=page_size)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_get_remote_task(capability_id: CapabilityID, task_id: TaskID) -> types.CallToolResult:
        """GET an exact existing remote task identity. Asset URLs and credentials are redacted; this does not import or approve it."""
        return call(engine.get_remote, capability_id, task_id, timeout=30)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_list_operations(job_id: OperationID) -> types.CallToolResult:
        """Read capability operations, quotes, costs and dependencies from the same local Forge ledger."""
        return call(engine.list_operations, job_id)

    @server.tool(annotations=read, structured_output=False)
    def kai_meshy_get_operation(job_id: OperationID, operation_id: OperationID = 'main') -> types.CallToolResult:
        """Read a local operation's immutable request/contract hashes, task identity and checkpoint. No vendor request."""
        return call(engine.get_operation, job_id, operation_id)

    if policy.allow_writes:
        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_plan_operation(
            job_id: OperationID, capability_id: CapabilityID, parameters: dict[str, Any],
            operation_id: OperationID = 'main',
            budget: Annotated[int, Field(ge=1, le=500)] = 500,
            dependencies: Annotated[list[OperationID], Field(max_length=100)] = [],
            parent_asset_ids: Annotated[list[AssetID], Field(max_length=100)] = [],
            confirm: bool = False,
        ) -> types.CallToolResult:
            """Create an immutable local plan, not a Meshy task. Use {local_path: ...} media references from allowed roots or {task_from_operation: ...} dependencies. A budget is only a ceiling."""
            def run():
                policy.gate(confirm=confirm)
                return engine.create_operation(job_id, capability_id, parameters, budget=budget,
                                               operation_id=operation_id, dependencies=dependencies,
                                               parent_asset_ids=parent_asset_ids)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_refresh_operation(job_id: OperationID, operation_id: OperationID = 'main', confirm: bool = False) -> types.CallToolResult:
            """Observe an existing operation task once with GET and persist its audit receipt. No submission."""
            def run():
                policy.gate(confirm=confirm)
                return engine.refresh_operation(job_id, operation_id, timeout=30)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_poll_operation(
            job_id: OperationID, operation_id: OperationID = 'main',
            timeout_seconds: Annotated[int, Field(ge=1, le=30)] = 20,
            confirm: bool = False,
        ) -> types.CallToolResult:
            """Bounded observation of the same task, at most six GETs and three stalled observations; never POST or regenerate."""
            def run():
                policy.gate(confirm=confirm)
                return engine.poll_operation(job_id, operation_id, timeout=timeout_seconds,
                                             interval=5, max_attempts=6, max_stalled=3)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_operation_cycle(
            job_id: OperationID, timeout_seconds: Annotated[int, Field(ge=1, le=30)] = 20,
            max_operations: Annotated[int, Field(ge=1, le=50)] = 20, confirm: bool = False,
        ) -> types.CallToolResult:
            """Resume one bounded operation observation pass; report explicit submit/reconcile/output gates. Never creates a paid task."""
            def run():
                from .operation_loop import cycle_operations
                policy.gate(confirm=confirm)
                return cycle_operations(engine, job_id, timeout=timeout_seconds, max_operations=max_operations)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_download_operation(
            job_id: OperationID, operation_id: OperationID = 'main',
            format: Literal['glb', 'gltf', 'obj', 'mtl', 'fbx', 'stl', '3mf', 'usdz', 'blend', 'image', 'thumbnail', 'base_color', 'metallic', 'normal', 'roughness'] = 'glb',
            texture_index: Annotated[int, Field(ge=0, le=99)] = 0,
            variant: OutputVariant | None = None, confirm: bool = False,
        ) -> types.CallToolResult:
            """Recover one output of the original succeeded task with hash/receipt and cache validation. Failed downloads never regenerate the model."""
            def run():
                policy.gate(confirm=confirm)
                return engine.download_operation(job_id, operation_id, format=format, texture_index=texture_index, variant=variant)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_extract_operation_archive(
            job_id: OperationID, operation_id: OperationID, asset_id: AssetID, confirm: bool = False,
        ) -> types.CallToolResult:
            """CRC-audit and extract a previously downloaded operation ZIP into its confined derivative folder. No execution; reject traversal, links, unsafe names and excessive expansion."""
            def run():
                policy.gate(confirm=confirm)
                return engine.extract_operation_archive(job_id, operation_id, asset_id)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_checkpoint_operation(
            job_id: OperationID, operation_id: OperationID, label: Annotated[str, Field(min_length=1, max_length=100)],
            asset_ids: Annotated[list[AssetID], Field(max_length=100)] = [], confirm: bool = False,
        ) -> types.CallToolResult:
            """Append an audit checkpoint for existing immutable assets without changing the operation or remote task identity."""
            def run():
                policy.gate(confirm=confirm)
                return engine.checkpoint(job_id, operation_id, label, asset_ids=asset_ids)
            return call(run)

    if policy.allow_writes and policy.allow_spend and forge.spending_enabled and forge.spending_job_ids:
        @server.tool(annotations=paid, structured_output=False)
        def kai_meshy_submit_operation(job_id: OperationID, operation_id: OperationID = 'main', confirm: bool = False) -> types.CallToolResult:
            """Exactly one billable submission of an approved planned operation. Requires current exact quote, per-job owner allowlist, balance and shared budget. Unknown outcome must be reconciled, never repeated."""
            def run():
                policy.gate(confirm=confirm, paid=True)
                return engine.submit_operation(job_id, operation_id)
            return call(run)

    if policy.allow_writes and policy.allow_approvals and policy.approval_actor:
        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_approve_operation_preview(
            job_id: OperationID, operation_id: OperationID, asset_id: AssetID, confirm: bool = False,
        ) -> types.CallToolResult:
            """Record an operator's human visual approval of this operation's exact downloaded preview asset. Server supplies the actor. Never approve a rejected job or a candidate input image."""
            def run():
                policy.gate(confirm=confirm, approval=True)
                return engine.approve_operation(job_id, operation_id, asset_id, actor=policy.approval_actor)
            return call(run)

        @server.tool(annotations=write, structured_output=False)
        def kai_meshy_reconcile_operation(
            job_id: OperationID, operation_id: OperationID, task_id: TaskID, request_sha256: SHA256,
            receipt_asset_id: AssetID, confirm: bool = False,
        ) -> types.CallToolResult:
            """Bind an uncertain request to an operator-verified task using exact request hash and registered receipt evidence. GET only; no replacement POST."""
            def run():
                policy.gate(confirm=confirm, approval=True)
                return engine.reconcile_operation(job_id, operation_id, task_id, request_sha256,
                                                  receipt_asset_id=receipt_asset_id, actor=policy.approval_actor)
            return call(run)

    return engine
