from __future__ import annotations

from pathlib import Path
from typing import Any

from .audit import AuditWriter
from .manifest import build_manifest, fingerprint_manifest, verify_manifest_fingerprint
from .policy import MUTATING_ACTIONS, build_plan
from .transport import StorageTransport, build_http_payload


class ExecutionBlocked(RuntimeError):
    pass


class StorageCommander:
    def __init__(self, transport: StorageTransport, audit_path: Path | str) -> None:
        self.transport = transport
        self.audit = AuditWriter(audit_path)

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        plan = build_plan(request)
        manifest = build_manifest(plan.payload)
        fingerprint = fingerprint_manifest(manifest)
        result = {
            "status": "VALIDATED_LOCAL_CANDIDATE",
            "plan": plan.to_dict(),
            "manifest": manifest,
            "manifest_fingerprint": fingerprint,
        }
        self.audit.append({"event": "plan", "request": request, "result": result})
        return result

    def execute(self, request: dict[str, Any], manifest_fingerprint: str | None = None) -> dict[str, Any]:
        plan = build_plan(request)
        payload = dict(plan.payload)

        if plan.action in MUTATING_ACTIONS:
            if request.get("confirm") is not True:
                raise ExecutionBlocked("Mutating execution requires confirm=true")
            manifest = build_manifest(payload)
            if not manifest_fingerprint or not verify_manifest_fingerprint(manifest, manifest_fingerprint):
                raise ExecutionBlocked("Manifest fingerprint mismatch")
            payload["dry_run"] = False
            payload["confirm"] = True

        response = self.transport.send(build_http_payload(payload))
        result = {
            "status": "EXECUTED_CANDIDATE",
            "action": plan.action,
            "response": response,
        }
        self.audit.append({"event": "execute", "request": request, "response": response})
        return result
