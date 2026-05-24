from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DocumentState(str, Enum):
    PENDING = "pendiente"
    READ = "leído"
    EXTRACTED = "extraído"
    INTEGRATED = "integrado"
    COMPLETED = "completado"


@dataclass
class DocumentRecord:
    file_id: str
    title: str
    source: str
    content_hash: str | None = None
    labels: list[str] = field(default_factory=list)
    sensitive: bool = False
    state: DocumentState = DocumentState.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def mark_state(self, state: DocumentState) -> None:
        self.state = state
        self.updated_at = datetime.now(timezone.utc).isoformat()
