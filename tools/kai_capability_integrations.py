from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IntegrationSpec:
    slug: str
    module: str
    script_name: str
    allowed_operations: tuple[str, ...]
    probe_args: tuple[str, ...] = ("--help",)
    mutation_policy: str = "READ_ONLY"
    requires_live_transport: bool = False


INTEGRATIONS: dict[str, IntegrationSpec] = {
    "storage-commander": IntegrationSpec(
        slug="storage-commander",
        module="kai_storage_commander.cli",
        script_name="kai-storage-commander",
        allowed_operations=("plan",),
        mutation_policy="PLAN_ONLY",
        requires_live_transport=True,
    ),
    "termux-bridge-planner": IntegrationSpec(
        slug="termux-bridge-planner",
        module="kai_termux_bridge_planner.cli",
        script_name="kai-termux-bridge-planner",
        allowed_operations=("plan",),
        mutation_policy="OBSERVATION_AND_PLANNING_ONLY",
    ),
    "backup-manifest": IntegrationSpec(
        slug="backup-manifest",
        module="kai_backup_manifest.cli",
        script_name="kai-backup-manifest",
        allowed_operations=("verify",),
        mutation_policy="READ_ONLY_EXCEPT_MANIFEST_OUTPUT",
    ),
    "file-indexer": IntegrationSpec(
        slug="file-indexer",
        module="kai_file_indexer.cli",
        script_name="kai-file-indexer",
        allowed_operations=("stats", "query"),
        mutation_policy="WRITES_INDEX_DATABASE_ONLY",
    ),
    "local-knowledge-vault": IntegrationSpec(
        slug="local-knowledge-vault",
        module="kai_local_knowledge_vault.cli",
        script_name="kai-local-knowledge-vault",
        allowed_operations=("doctor", "stats", "search"),
        mutation_policy="LOCAL_VAULT_OUTPUTS_ONLY",
    ),
}


class CapabilityIntegrationManager:
    def __init__(self, capability_home: Path, timeout_seconds: float = 10.0):
        self.capability_home = Path(capability_home).resolve()
        self.timeout_seconds = float(timeout_seconds)

    @property
    def registry_path(self) -> Path:
        return self.capability_home / "capabilities_current.json"

    def _load_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.is_file():
            return []
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("capabilities_current.json must contain a JSON list")
        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def _path_parts(value: Any) -> tuple[str, ...]:
        if not value:
            return ()
        normalized = str(value).replace("\\", "/")
        return tuple(part for part in normalized.split("/") if part)

    def _record_for_slug(self, slug: str) -> dict[str, Any] | None:
        records = self._load_registry()
        exact = [item for item in records if str(item.get("name", "")) == slug]
        if exact:
            return exact[0]
        for item in records:
            provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
            for key in ("runtime_path", "source"):
                if slug in self._path_parts(provenance.get(key)):
                    return item
        return None

    def _runtime_path(self, slug: str, record: dict[str, Any] | None) -> Path:
        if record:
            provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
            runtime = provenance.get("runtime_path")
            if runtime:
                return Path(runtime).resolve()
        base = self.capability_home / "candidates" / slug
        versions = sorted((item for item in base.iterdir() if item.is_dir()), reverse=True) if base.is_dir() else []
        return versions[0].resolve() if versions else (base / "0.1.0").resolve()

    @staticmethod
    def _load_json_object(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _load_scripts(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return {}
        project = data.get("project") if isinstance(data.get("project"), dict) else {}
        scripts = project.get("scripts") if isinstance(project.get("scripts"), dict) else {}
        return {str(key): str(value) for key, value in scripts.items()}

    @staticmethod
    def _manifest_lifecycle_claim(manifest: dict[str, Any] | None) -> str | None:
        if not manifest:
            return None
        for key in ("promotion_state", "state", "status_claim", "promotion"):
            value = manifest.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _describe(self, spec: IntegrationSpec) -> dict[str, Any]:
        record = self._record_for_slug(spec.slug)
        runtime = self._runtime_path(spec.slug, record)
        manifest_path = runtime / "manifest.json"
        pyproject_path = runtime / "pyproject.toml"
        manifest = self._load_json_object(manifest_path)
        scripts = self._load_scripts(pyproject_path)
        registry_state = str(record.get("state", "MISSING")) if record else "MISSING"
        lifecycle_claim = self._manifest_lifecycle_claim(manifest)
        warnings: list[str] = []
        if lifecycle_claim and registry_state == "PROMOTED" and lifecycle_claim.upper() not in {"PROMOTED", "CANONICAL"}:
            warnings.append("manifest lifecycle claim differs from registry")
        if spec.script_name not in scripts:
            warnings.append("expected CLI script is not declared in pyproject.toml")
        available = runtime.is_dir() and (runtime / "src").is_dir()
        return {
            "slug": spec.slug,
            "version": str(manifest.get("version", runtime.name)) if manifest else runtime.name,
            "capability_id": record.get("capability_id") if record else None,
            "registry_state": registry_state,
            "promoted": registry_state == "PROMOTED",
            "runtime_path": str(runtime),
            "manifest_path": str(manifest_path),
            "manifest_valid": manifest is not None,
            "manifest_lifecycle_claim": lifecycle_claim,
            "module": spec.module,
            "script_name": spec.script_name,
            "script_configured": spec.script_name in scripts,
            "available": available,
            "allowed_operations": list(spec.allowed_operations),
            "mutation_policy": spec.mutation_policy,
            "requires_live_transport": spec.requires_live_transport,
            "warnings": warnings,
        }

    def list_integrations(self) -> list[dict[str, Any]]:
        return [self._describe(INTEGRATIONS[slug]) for slug in sorted(INTEGRATIONS)]

    def _spec(self, slug: str) -> IntegrationSpec:
        try:
            return INTEGRATIONS[str(slug)]
        except KeyError as exc:
            raise KeyError(f"unknown integration: {slug}") from exc

    def _command(self, spec: IntegrationSpec, operation: str | None, args: list[str]) -> tuple[list[str], Path]:
        record = self._record_for_slug(spec.slug)
        runtime = self._runtime_path(spec.slug, record)
        command = [sys.executable, "-m", spec.module]
        if operation:
            command.append(operation)
        command.extend(str(value) for value in args)
        return command, runtime

    def _run(self, spec: IntegrationSpec, operation: str | None, args: list[str]) -> dict[str, Any]:
        command, runtime = self._command(spec, operation, args)
        if not runtime.is_dir():
            return {
                "slug": spec.slug,
                "operation": operation,
                "status": "DEGRADED",
                "returncode": None,
                "stdout": "",
                "stderr": "runtime path is missing",
                "timed_out": False,
                "shell": False,
                "command": command,
            }
        env = os.environ.copy()
        src = runtime / "src"
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(src) if not existing else os.pathsep.join((str(src), existing))
        try:
            result = subprocess.run(
                command,
                cwd=runtime,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "slug": spec.slug,
                "operation": operation,
                "status": "BLOCKED_EXTERNAL" if spec.requires_live_transport else "DEGRADED",
                "returncode": None,
                "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "") if isinstance(exc.stderr, str) else "timeout",
                "timed_out": True,
                "shell": False,
                "command": command,
            }
        status = "HEALTHY" if result.returncode == 0 else (
            "BLOCKED_EXTERNAL" if spec.requires_live_transport else "DEGRADED"
        )
        return {
            "slug": spec.slug,
            "operation": operation,
            "status": status,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
            "shell": False,
            "command": command,
        }

    def probe(self, slug: str) -> dict[str, Any]:
        spec = self._spec(slug)
        return self._run(spec, None, list(spec.probe_args))

    def invoke(self, slug: str, operation: str, args: list[str] | None = None) -> dict[str, Any]:
        spec = self._spec(slug)
        if operation not in spec.allowed_operations:
            raise ValueError(
                f"operation is not allowlisted for {slug}: {operation}; "
                f"allowed={','.join(spec.allowed_operations)}"
            )
        return self._run(spec, operation, list(args or []))

    def doctor(self) -> dict[str, Any]:
        records = self.list_integrations()
        degraded: list[str] = []
        blocked_external: list[str] = []
        probes: dict[str, dict[str, Any]] = {}
        for item in records:
            slug = item["slug"]
            if not item["available"] or not item["manifest_valid"] or not item["promoted"]:
                degraded.append(slug)
                continue
            probe = self.probe(slug)
            probes[slug] = probe
            if probe["status"] == "BLOCKED_EXTERNAL":
                blocked_external.append(slug)
            elif probe["status"] != "HEALTHY":
                degraded.append(slug)
        if degraded:
            status = "DEGRADED"
        elif blocked_external:
            status = "BLOCKED_EXTERNAL"
        else:
            status = "HEALTHY"
        return {
            "status": status,
            "required_count": len(INTEGRATIONS),
            "integrations": records,
            "probes": probes,
            "degraded": sorted(degraded),
            "blocked_external": sorted(blocked_external),
        }
