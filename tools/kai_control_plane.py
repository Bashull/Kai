from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tools.kai_location_policy import PlacementPolicy
except ModuleNotFoundError:
    import sys
    local_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(local_dir))
    from kai_location_policy import PlacementPolicy

try:
    from tools.kai_capability_integrations import CapabilityIntegrationManager
except ModuleNotFoundError:
    import sys
    local_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(local_dir))
    from kai_capability_integrations import CapabilityIntegrationManager


COMMAND_ALIASES = {
    "/despierta": "wake",
    "/recuerda": "remember",
    "/absorbe": "absorb-chat",
    "/cierra": "close-session",
    "/crea-skill": "create-skill",
    "/crea-herramienta": "create-tool",
    "/actualiza-skill": "update-skill",
    "/actualiza-herramienta": "update-tool",
    "/donde-va": "where",
    "/promueve": "promote",
    "/organiza": "organize",
    "/checkpoint": "checkpoint",
    "/evidencia": "evidence",
    "/doctor-global": "doctor",
    "/integraciones": "integrations",
    "/doctor-integraciones": "integration-doctor",
    "/usa-capacidad": "integration-call",
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_class(module_path: Path, class_name: str):
    if not module_path.is_file():
        raise FileNotFoundError(module_path)
    module_name = f"kai_dynamic_{module_path.stem}_{abs(hash(str(module_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


class KaiControlPlane:
    def __init__(
        self,
        repo_root: Path,
        bridge_root: Path,
        state_root: Path,
        memory_home: Path,
        capability_home: Path,
        policy: PlacementPolicy,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.bridge_root = Path(bridge_root).resolve()
        self.state_root = Path(state_root).resolve()
        self.memory_home = Path(memory_home).resolve()
        self.capability_home = Path(capability_home).resolve()
        self.policy = policy

        self.skills_source = self.repo_root / "skills"
        self.tools_source = self.repo_root / "tools"
        self.snapshots_root = self.state_root / "snapshots"
        self.evidence_root = self.state_root / "evidence"
        self.candidates_root = self.state_root / "candidates"
        for path in (
            self.skills_source,
            self.tools_source,
            self.snapshots_root,
            self.evidence_root,
            self.candidates_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def memory_ledger(self):
        candidates = (
            self.repo_root / "tools" / "kai_memory_ledger.py",
            Path(__file__).resolve().parent / "kai_memory_ledger.py",
            self.bridge_root / "agent_tools" / "kai_memory" / "kai_memory_ledger.py",
        )
        source = next((path for path in candidates if path.is_file()), candidates[-1])
        cls = load_class(source, "MemoryLedger")
        return cls(self.memory_home)

    @property
    def capability_registry(self):
        candidates = (
            self.repo_root / "tools" / "kai_capability_registry.py",
            Path(__file__).resolve().parent / "kai_capability_registry.py",
            self.bridge_root / "agent_tools" / "kai_capability_registry" / "kai_capability_registry.py",
        )
        source = next((path for path in candidates if path.is_file()), candidates[-1])
        cls = load_class(source, "CapabilityRegistry")
        return cls(self.capability_home)

    @property
    def integration_manager(self):
        return CapabilityIntegrationManager(self.capability_home)

    @staticmethod
    def _validate_skill_name(name: str) -> str:
        value = str(name).strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("skill name must use lowercase letters, numbers and hyphens")
        return value

    @staticmethod
    def _validate_tool_name(name: str) -> str:
        value = str(name).strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
            raise ValueError("tool name must be a lowercase Python identifier")
        return value

    def where(self, artifact_kind: str) -> dict[str, Any]:
        return self.policy.route(artifact_kind)

    @staticmethod
    def _skill_scaffold(name: str, description: str) -> str:
        desc = str(description).strip()
        if not desc.startswith("Use when"):
            raise ValueError("skill description must start with 'Use when'")
        return (
            "---\n"
            f"name: {name}\n"
            f"description: {desc}\n"
            "---\n\n"
            f"# {name}\n\n"
            "## Overview\n\n"
            "Describe the reusable technique or pattern.\n\n"
            "## When to use\n\n"
            "- Add concrete triggers and symptoms.\n\n"
            "## Evidence contract\n\n"
            "Require source, provenance and verifiable evidence.\n\n"
            "## Safety contract\n\n"
            "Do not overwrite originals, expose secrets or bypass validation.\n\n"
            "## Workflow\n\n"
            "1. Inspect.\n2. Compare.\n3. Test.\n4. Record.\n\n"
            "## Decision labels\n\n"
            "DISCOVERED · CANDIDATE · TESTING · VALIDATED · PROMOTED · CANONICAL\n"
        )

    @staticmethod
    def _tool_scaffold(name: str) -> str:
        return (
            "from __future__ import annotations\n\n"
            "import argparse\n"
            "import json\n"
            "from typing import Any\n\n\n"
            f"def run() -> dict[str, Any]:\n    return {{\"tool\": \"{name}\", \"status\": \"CANDIDATE\"}}\n\n\n"
            "def main() -> int:\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.parse_args()\n"
            "    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))\n"
            "    return 0\n\n\n"
            "if __name__ == \"__main__\":\n    raise SystemExit(main())\n"
        )

    def create_skill(self, name: str, description: str) -> dict[str, Any]:
        safe_name = self._validate_skill_name(name)
        target = self.skills_source / safe_name / "SKILL.md"
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self._skill_scaffold(safe_name, description), encoding="utf-8")
        route = self.policy.route("skill")
        runtime = Path(route["local_runtime_root"]) / safe_name / "SKILL.md"
        return {
            "action": "CREATE_SKILL",
            "name": safe_name,
            "source_path": str(target),
            "runtime_target": str(runtime),
            "drive_evidence_zone": route["drive_evidence_zone"],
            "drive_canonical_zone": route["drive_canonical_zone"],
            "state": "CANDIDATE",
            "requires_tests": True,
            "requires_promotion": True,
        }

    def create_tool(self, name: str) -> dict[str, Any]:
        safe_name = self._validate_tool_name(name)
        target = self.tools_source / f"{safe_name}.py"
        if target.exists():
            raise FileExistsError(target)
        target.write_text(self._tool_scaffold(safe_name), encoding="utf-8")
        route = self.policy.route("tool")
        runtime = Path(route["local_runtime_root"]) / safe_name / f"{safe_name}.py"
        return {
            "action": "CREATE_TOOL",
            "name": safe_name,
            "source_path": str(target),
            "runtime_target": str(runtime),
            "drive_evidence_zone": route["drive_evidence_zone"],
            "drive_canonical_zone": route["drive_canonical_zone"],
            "state": "CANDIDATE",
            "requires_tests": True,
            "requires_promotion": True,
        }

    def _snapshot(self, source: Path, category: str, name: str) -> Path:
        snapshot_dir = self.snapshots_root / category / name
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        suffix = source.suffix or ".txt"
        target = snapshot_dir / f"{utc_stamp()}_{source.stem}{suffix}"
        shutil.copy2(source, target)
        return target

    @staticmethod
    def _replace_atomic(target: Path, replacement: Path) -> None:
        if not replacement.is_file():
            raise FileNotFoundError(replacement)
        tmp = target.with_suffix(target.suffix + ".tmp")
        shutil.copy2(replacement, tmp)
        tmp.replace(target)

    def update_skill(self, name: str, replacement: Path) -> dict[str, Any]:
        safe_name = self._validate_skill_name(name)
        target = self.skills_source / safe_name / "SKILL.md"
        if not target.is_file():
            raise FileNotFoundError(target)
        snapshot = self._snapshot(target, "skills", safe_name)
        self._replace_atomic(target, Path(replacement))
        route = self.policy.route("skill")
        return {
            "action": "UPDATE_SKILL",
            "name": safe_name,
            "source_path": str(target),
            "snapshot_path": str(snapshot),
            "runtime_target": str(Path(route["local_runtime_root"]) / safe_name / "SKILL.md"),
            "state": "CANDIDATE",
            "requires_tests": True,
            "requires_promotion": True,
        }

    def update_tool(self, name: str, replacement: Path) -> dict[str, Any]:
        safe_name = self._validate_tool_name(name)
        target = self.tools_source / f"{safe_name}.py"
        if not target.is_file():
            raise FileNotFoundError(target)
        snapshot = self._snapshot(target, "tools", safe_name)
        self._replace_atomic(target, Path(replacement))
        route = self.policy.route("tool")
        return {
            "action": "UPDATE_TOOL",
            "name": safe_name,
            "source_path": str(target),
            "snapshot_path": str(snapshot),
            "runtime_target": str(Path(route["local_runtime_root"]) / safe_name / f"{safe_name}.py"),
            "state": "CANDIDATE",
            "requires_tests": True,
            "requires_promotion": True,
        }

    def wake(self, project: str = "kai", max_chars: int = 12000) -> dict[str, Any]:
        ledger = self.memory_ledger
        markdown_path, json_path = ledger.write_boot_packet(max_chars=max_chars, project=project)
        packet = json.loads(Path(json_path).read_text(encoding="utf-8"))
        packet["markdown_path"] = str(markdown_path)
        packet["json_path"] = str(json_path)
        return packet

    def remember(self, query: str, limit: int = 20, scope: str | None = None) -> list[dict[str, Any]]:
        return self.memory_ledger.search(query=query, limit=limit, scope=scope)

    def close_session(self, summary: dict[str, Any], project: str = "kai") -> dict[str, Any]:
        ledger = self.memory_ledger
        closed = ledger.close_session(summary)
        packet = ledger.build_boot_packet(project=project)
        return {
            "session_id": closed["session_id"],
            "snapshot_path": closed["session_file"],
            "memory_id": closed["memory_id"],
            "decision": closed["decision"],
            "boot_health": packet["health"],
        }

    def register_candidate(self, candidate_path: Path) -> dict[str, Any]:
        data = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("candidate file must contain a JSON object")
        return self.capability_registry.register(data)

    def promote(self, capability_id: str, state: str, evidence: dict[str, Any]) -> dict[str, Any]:
        return self.capability_registry.transition(capability_id, state, evidence)

    def capabilities(self) -> list[dict[str, Any]]:
        return self.capability_registry.current_manifest()

    def integrations(self) -> list[dict[str, Any]]:
        return self.integration_manager.list_integrations()

    def integration_doctor(self) -> dict[str, Any]:
        return self.integration_manager.doctor()

    def integration_call(self, slug: str, operation: str, args: list[str] | None = None) -> dict[str, Any]:
        return self.integration_manager.invoke(slug, operation, list(args or []))

    def organize(self, artifact_kind: str) -> dict[str, Any]:
        result = dict(self.where(artifact_kind))
        result["action"] = "RECOMMEND_PLACEMENT"
        result["movement_performed"] = False
        result["rule"] = "inspect-before-move; preserve provenance and references"
        return result

    def evidence(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name)).strip("-._")
        if not safe_name:
            raise ValueError("evidence name has no safe characters")
        target = self.evidence_root / f"{utc_stamp()}_{safe_name}.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "action": "WRITE_EVIDENCE",
            "path": str(target),
            "drive_zone": "10_KAI_LAB_INGESTION_FORENSICS",
        }

    def checkpoint(self, summary: dict[str, Any], project: str = "kai") -> dict[str, Any]:
        result = self.close_session(summary, project=project)
        result["action"] = "CHECKPOINT"
        return result

    def absorb_chat(self, summary_path: Path, project: str = "kai") -> dict[str, Any]:
        data = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("chat absorption summary must be a JSON object")
        result = self.close_session(data, project=project)
        result["action"] = "ABSORB_CHAT"
        return result

    def doctor(self) -> dict[str, Any]:
        ledger = self.memory_ledger
        if not (self.memory_home / "boot_packet.json").is_file():
            ledger.write_boot_packet(project="kai")
        memory = ledger.doctor()
        capabilities = self.capability_registry.doctor()
        location_valid = all(
            zone in self.policy.drive
            for zone in (
                "00_KAI_CORE",
                "10_KAI_LAB_INGESTION_FORENSICS",
                "80_INBOX_UNCLASSIFIED",
                "90_ARCHIVE_HISTORICAL",
                "99_PRIVATE_SENSITIVE",
            )
        )
        core_status = "HEALTHY" if (
            memory["status"] == "HEALTHY"
            and capabilities["status"] == "HEALTHY"
            and location_valid
        ) else "DEGRADED"
        integrations = self.integration_doctor()
        status = "HEALTHY" if (
            core_status == "HEALTHY"
            and integrations["status"] in {"HEALTHY", "BLOCKED_EXTERNAL"}
        ) else "DEGRADED"
        return {
            "status": status,
            "core_status": core_status,
            "memory": memory,
            "capabilities": capabilities,
            "integrations": integrations,
            "location_policy": {"valid": location_valid},
            "commands": sorted(COMMAND_ALIASES),
        }


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def default_policy_path() -> Path:
    here = Path(__file__).resolve()
    candidates = (
        here.parents[1] / "config" / "kai_location_policy.json",
        here.parents[2] / "config" / "kai_location_policy.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kai unified control plane")
    parser.add_argument("--policy", type=Path, default=default_policy_path())
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--bridge-root", type=Path)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--memory-home", type=Path)
    parser.add_argument("--capability-home", type=Path)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("commands")
    where = sub.add_parser("where")
    where.add_argument("--kind", required=True)
    organize = sub.add_parser("organize")
    organize.add_argument("--kind", required=True)

    create_skill = sub.add_parser("create-skill")
    create_skill.add_argument("--name", required=True)
    create_skill.add_argument("--description", required=True)

    update_skill = sub.add_parser("update-skill")
    update_skill.add_argument("--name", required=True)
    update_skill.add_argument("--source-file", type=Path, required=True)

    create_tool = sub.add_parser("create-tool")
    create_tool.add_argument("--name", required=True)

    update_tool = sub.add_parser("update-tool")
    update_tool.add_argument("--name", required=True)
    update_tool.add_argument("--source-file", type=Path, required=True)

    wake = sub.add_parser("wake")
    wake.add_argument("--project", default="kai")
    wake.add_argument("--max-chars", type=int, default=12000)

    remember = sub.add_parser("remember")
    remember.add_argument("--query", required=True)
    remember.add_argument("--limit", type=int, default=20)
    remember.add_argument("--scope")

    close_session = sub.add_parser("close-session")
    close_session.add_argument("--summary-file", type=Path, required=True)
    close_session.add_argument("--project", default="kai")

    absorb = sub.add_parser("absorb-chat")
    absorb.add_argument("--summary-file", type=Path, required=True)
    absorb.add_argument("--project", default="kai")

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--summary-file", type=Path, required=True)
    checkpoint.add_argument("--project", default="kai")

    evidence = sub.add_parser("evidence")
    evidence.add_argument("--name", required=True)
    evidence.add_argument("--payload-file", type=Path, required=True)

    sub.add_parser("capabilities")
    sub.add_parser("integrations")
    sub.add_parser("integration-doctor")
    integration_call = sub.add_parser("integration-call")
    integration_call.add_argument("--name", required=True)
    integration_call.add_argument("--operation", required=True)
    integration_call.add_argument("args", nargs=argparse.REMAINDER)

    promote = sub.add_parser("promote")
    promote.add_argument("--capability-id", required=True)
    promote.add_argument("--state", required=True)
    promote.add_argument("--evidence-file", type=Path, required=True)

    sub.add_parser("doctor")
    return parser


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def build_plane_from_args(args: argparse.Namespace) -> KaiControlPlane:
    policy = PlacementPolicy.from_json(args.policy)
    local = policy.local
    repo_root = args.repo_root or Path(local["repo_root"])
    bridge_root = args.bridge_root or Path(local["bridge_root"])
    state_root = args.state_root or Path(local["state_root"])
    memory_home = args.memory_home or (Path.home() / ".kai_memory")
    capability_home = args.capability_home or state_root
    return KaiControlPlane(
        repo_root=repo_root,
        bridge_root=bridge_root,
        state_root=state_root,
        memory_home=memory_home,
        capability_home=capability_home,
        policy=policy,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    plane = build_plane_from_args(args)

    if args.command == "commands":
        print_json(COMMAND_ALIASES)
        return 0
    if args.command == "where":
        print_json(plane.where(args.kind))
        return 0
    if args.command == "organize":
        print_json(plane.organize(args.kind))
        return 0
    if args.command == "create-skill":
        print_json(plane.create_skill(args.name, args.description))
        return 0
    if args.command == "update-skill":
        print_json(plane.update_skill(args.name, args.source_file))
        return 0
    if args.command == "create-tool":
        print_json(plane.create_tool(args.name))
        return 0
    if args.command == "update-tool":
        print_json(plane.update_tool(args.name, args.source_file))
        return 0
    if args.command == "wake":
        print_json(plane.wake(project=args.project, max_chars=args.max_chars))
        return 0
    if args.command == "remember":
        print_json(plane.remember(args.query, limit=args.limit, scope=args.scope))
        return 0
    if args.command == "close-session":
        print_json(plane.close_session(load_json_object(args.summary_file), project=args.project))
        return 0
    if args.command == "absorb-chat":
        print_json(plane.absorb_chat(args.summary_file, project=args.project))
        return 0
    if args.command == "checkpoint":
        print_json(plane.checkpoint(load_json_object(args.summary_file), project=args.project))
        return 0
    if args.command == "evidence":
        print_json(plane.evidence(args.name, load_json_object(args.payload_file)))
        return 0
    if args.command == "capabilities":
        print_json(plane.capabilities())
        return 0
    if args.command == "integrations":
        print_json(plane.integrations())
        return 0
    if args.command == "integration-doctor":
        diagnosis = plane.integration_doctor()
        print_json(diagnosis)
        return 0 if diagnosis["status"] in {"HEALTHY", "BLOCKED_EXTERNAL"} else 2
    if args.command == "integration-call":
        call_args = list(args.args)
        if call_args[:1] == ["--"]:
            call_args = call_args[1:]
        try:
            result = plane.integration_call(args.name, args.operation, call_args)
        except (KeyError, ValueError) as exc:
            parser.error(str(exc))
        print_json(result)
        return 0 if result["status"] in {"HEALTHY", "BLOCKED_EXTERNAL"} else 2
    if args.command == "promote":
        print_json(plane.promote(
            args.capability_id,
            args.state,
            load_json_object(args.evidence_file),
        ))
        return 0
    if args.command == "doctor":
        diagnosis = plane.doctor()
        print_json(diagnosis)
        return 0 if diagnosis["status"] == "HEALTHY" else 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
