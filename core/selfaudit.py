"""Ethical and safety checks for Kai's self-governance."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .scanner import RepositoryScanner


@dataclass
class AuditIssue:
    severity: str
    message: str
    location: Optional[str] = None


class SelfAuditor:
    """Run lightweight safety and coherence audits."""

    def __init__(self, repository_root: Path | str) -> None:
        self.scanner = RepositoryScanner(repository_root)

    # ------------------------------------------------------------------
    def run_static_checks(self) -> List[AuditIssue]:
        results = self.scanner.detect_high_risk_patterns()
        issues: List[AuditIssue] = []
        for category, matches in results.items():
            for path, lines in matches:
                issues.append(
                    AuditIssue(
                        severity="high" if category == "dangerous_eval" else "medium",
                        message=f"{category} detected",
                        location=f"{path}:{lines[0] if lines else ''}",
                    )
                )
        return issues

    # ------------------------------------------------------------------
    def verify_mandatory_files(self, required: Iterable[str]) -> List[AuditIssue]:
        missing = []
        for relative in required:
            if not (self.scanner.root / relative).exists():
                missing.append(
                    AuditIssue(
                        severity="high",
                        message=f"Required file '{relative}' is missing.",
                    )
                )
        return missing

    # ------------------------------------------------------------------
    def audit(self, required_files: Optional[Iterable[str]] = None) -> List[AuditIssue]:
        issues = self.run_static_checks()
        if required_files:
            issues.extend(self.verify_mandatory_files(required_files))
        return issues


__all__ = ["SelfAuditor", "AuditIssue"]
