from __future__ import annotations

from pathlib import Path
from typing import Any
import json

try:
    from tools.kai_federation_cycle import FederationCycleConfig, FederationCycleRunner
    from tools.kai_source_adapters import (
        AdbTreeAdapter,
        BackupManifestAdapter,
        ConnectorSnapshotAdapter,
        FileIndexDatabaseAdapter,
        KaiMasterInventoryAdapter,
        LocalGitAdapter,
        PathListAdapter,
        PowerShellCsvInventoryAdapter,
        SourceRegistry,
    )
    from tools.kai_source_federation import FederationLedger
except ModuleNotFoundError:
    import sys
    local_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(local_dir))
    from kai_federation_cycle import FederationCycleConfig, FederationCycleRunner
    from kai_source_adapters import (
        AdbTreeAdapter,
        BackupManifestAdapter,
        ConnectorSnapshotAdapter,
        FileIndexDatabaseAdapter,
        KaiMasterInventoryAdapter,
        LocalGitAdapter,
        PathListAdapter,
        PowerShellCsvInventoryAdapter,
        SourceRegistry,
    )
    from kai_source_federation import FederationLedger


def _load_roots(source: dict[str, Any]) -> list[Path]:
    if isinstance(source.get("roots"), list):
        return [Path(item) for item in source["roots"]]
    roots_path = source.get("roots_path")
    if roots_path:
        payload = json.loads(Path(roots_path).read_text(encoding="utf-8-sig"))
        roots = payload.get("roots") if isinstance(payload, dict) else None
        if not isinstance(roots, list):
            raise ValueError("roots_path JSON requires a roots list")
        return [Path(item) for item in roots]
    raise ValueError("local_git adapter requires roots or roots_path")


def build_adapter(source: dict[str, Any]):
    adapter = source.get("adapter")
    source_id = str(source.get("source_id") or "")
    if not source_id:
        raise ValueError("source requires source_id")
    if adapter == "kai_master_inventory":
        return KaiMasterInventoryAdapter(source_id, Path(source["path"]))
    if adapter == "powershell_csv":
        return PowerShellCsvInventoryAdapter(source_id, Path(source["path"]))
    if adapter == "path_list":
        return PathListAdapter(
            source_id,
            str(source["kind"]),
            Path(source["path"]),
            str(source["logical_root"]),
        )
    if adapter == "backup_manifest":
        return BackupManifestAdapter(source_id, Path(source["path"]))
    if adapter == "file_index":
        return FileIndexDatabaseAdapter(source_id, Path(source["path"]))
    if adapter == "connector_snapshot":
        return ConnectorSnapshotAdapter(
            source_id,
            str(source["kind"]),
            Path(source["path"]),
        )
    if adapter == "local_git":
        return LocalGitAdapter(source_id, _load_roots(source))
    if adapter == "adb_tree":
        return AdbTreeAdapter(
            source_id,
            Path(source["adb_executable"]),
            str(source["serial"]),
            str(source["remote_root"]),
        )
    raise ValueError(f"unsupported adapter: {adapter!r}")


def run_federation_cycle(
    *,
    federation_home: Path,
    source_registry_path: Path,
    cycle_id: str,
    max_items_per_source: int,
) -> dict[str, Any]:
    registry = SourceRegistry.from_json(source_registry_path)
    sources = registry.enabled()
    ledger = FederationLedger(Path(federation_home) / "ledger")
    runner = FederationCycleRunner(
        Path(federation_home) / "cycles",
        ledger,
        sources,
        build_adapter,
    )
    return runner.run(FederationCycleConfig(cycle_id, max_items_per_source))
