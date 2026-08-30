from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("KAI_ENV", "development")
    log_level: str = os.getenv("KAI_LOG_LEVEL", "INFO")
    audit_log_path: Path = Path(os.getenv("KAI_AUDIT_LOG", "logs/audit.jsonl"))
    operational_memory_path: Path = Path(os.getenv("KAI_MEMORY_PATH", "logs/operational_memory.jsonl"))
    drive_connector_url: str = os.getenv("KAI_DRIVE_CONNECTOR_URL", "")
    drive_connector_token: str = os.getenv("KAI_DRIVE_CONNECTOR_TOKEN", "")
    drive_connector_timeout: int = int(os.getenv("KAI_DRIVE_CONNECTOR_TIMEOUT", "30"))
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    vector_store_backend: str = os.getenv("KAI_VECTOR_STORE", "local")


SETTINGS = Settings()
