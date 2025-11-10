from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class KaiConfig:
    """Configuration for Kai's autonomous loop."""

    workspace_root: Path
    data_directory: Path
    stability_threshold: float = 0.95
    environment: str = "dev"

    @classmethod
    def from_environment(cls, *, workspace: Optional[str] = None) -> "KaiConfig":
        workspace_root = Path(workspace or os.getenv("KAI_WORKSPACE", Path.cwd()))
        data_dir = Path(os.getenv("KAI_DATA_DIR", workspace_root / "data"))
        threshold = float(os.getenv("KAI_STABILITY_THRESHOLD", "0.95"))
        env = os.getenv("KAI_ENV", "dev")
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(workspace_root=workspace_root, data_directory=data_dir, stability_threshold=threshold, environment=env)
