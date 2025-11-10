"""Automated refactoring helpers used by Kai's forge agents."""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class RefactorReport:
    file_path: Path
    before: str
    after: str

    @property
    def diff(self) -> str:
        lines = difflib.unified_diff(
            self.before.splitlines(),
            self.after.splitlines(),
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
            lineterm="",
        )
        return "\n".join(lines)


class Refactorer:
    """Apply structural edits to source files."""

    def rename_symbol(self, file_path: Path | str, old: str, new: str) -> RefactorReport:
        path = Path(file_path)
        before = path.read_text()
        after = before.replace(old, new)
        path.write_text(after)
        return RefactorReport(file_path=path, before=before, after=after)

    def apply_replacements(self, file_path: Path | str, replacements: Dict[str, str]) -> RefactorReport:
        path = Path(file_path)
        before = path.read_text()
        after = before
        for old, new in replacements.items():
            after = after.replace(old, new)
        path.write_text(after)
        return RefactorReport(file_path=path, before=before, after=after)

    def inject_block(
        self,
        file_path: Path | str,
        marker: str,
        block: str,
        offset: int = 1,
    ) -> RefactorReport:
        """Insert ``block`` after the first occurrence of ``marker``."""

        path = Path(file_path)
        before = path.read_text()
        lines = before.splitlines()
        try:
            index = next(i for i, line in enumerate(lines) if marker in line)
        except StopIteration as exc:  # pragma: no cover - best effort path
            raise ValueError(f"Marker '{marker}' not found in {file_path}") from exc
        insertion_point = index + offset
        new_lines = lines[:insertion_point] + [block] + lines[insertion_point:]
        after = "\n".join(new_lines) + "\n"
        path.write_text(after)
        return RefactorReport(file_path=path, before=before, after=after)


__all__ = ["Refactorer", "RefactorReport"]
