from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from kai_core.config import SETTINGS
from kai_core.connectors.google_drive import GoogleDriveConnector
from kai_core.extraction.document_extractor import extract_document
from kai_core.memory.operational_memory import OperationalMemory
from kai_core.tools.hashing import sha256_text


AUDIT_PATH = SETTINGS.audit_log_path


def _write_audit(record: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_document(file_id: str, target_master_id: str, connector: GoogleDriveConnector | None = None) -> dict[str, Any]:
    connector = connector or GoogleDriveConnector()
    memory = OperationalMemory()

    source = connector.readFileText(file_id)
    text = source.get("text") or source.get("content") or ""
    extraction = extract_document(text)

    doc_hash = sha256_text(text)
    now = datetime.now(timezone.utc).isoformat()

    audit = {
        "timestamp": now,
        "source": file_id,
        "destination": target_master_id,
        "action": "extract_document",
        "hash_previous": source.get("sha256") or doc_hash,
        "hash_new": doc_hash,
        "backup": False,
        "reason": "Extracción documental para unificación temática",
        "result": "ok",
    }
    _write_audit(audit)

    memory.append(
        event_type="document_extracted",
        source=file_id,
        result="ok",
        payload={"target_master_id": target_master_id, "themes": extraction.affected_themes},
    )

    return {
        "file_id": file_id,
        "target_master_id": target_master_id,
        "extraction": asdict(extraction),
        "ready_to_move_complete": False,
        "note": "No mover a 00_COMPLETA hasta actualizar maestro y registrar integración.",
    }
