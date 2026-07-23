from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ExtractionResult:
    summary_short: str
    useful_ideas: list[str] = field(default_factory=list)
    canonical_candidates: list[str] = field(default_factory=list)
    symbolic_concepts: list[str] = field(default_factory=list)
    technical_concepts: list[str] = field(default_factory=list)
    operational_directives: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    related_duplicates: list[str] = field(default_factory=list)
    affected_themes: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    state: str = "extraído"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
