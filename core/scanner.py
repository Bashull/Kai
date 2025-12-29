"""Static scanning helpers for Kai's autonomous diagnostics."""
from __future__ import annotations

import fnmatch
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Pattern, Tuple


EXCLUDED_DIRECTORIES = {".git", "node_modules", "dist", "build", "__pycache__"}
DEFAULT_FILE_PATTERNS = ("*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.md")


@dataclass
class RepositoryStats:
    file_count: int
    line_count: int
    extensions: Dict[str, int]


class RepositoryScanner:
    """Analyse a repository for opportunities and risks."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(self.root)

    # ------------------------------------------------------------------
    def iter_files(
        self,
        patterns: Iterable[str] = DEFAULT_FILE_PATTERNS,
        exclude_dirs: Iterable[str] = EXCLUDED_DIRECTORIES,
    ) -> Iterator[Path]:
        """Yield files under ``root`` filtered by ``patterns``."""

        compiled = [re.compile(fnmatch.translate(pattern)) for pattern in patterns]
        excluded = set(exclude_dirs)
        for path in self.root.rglob("*"):
            if any(parent.name in excluded for parent in path.parents):
                continue
            if path.is_file() and any(regex.match(path.name) for regex in compiled):
                yield path

    # ------------------------------------------------------------------
    def collect_stats(self, patterns: Iterable[str] = DEFAULT_FILE_PATTERNS) -> RepositoryStats:
        """Return counts that provide a quick overview of the repository."""

        extension_counter: Counter[str] = Counter()
        file_count = 0
        line_count = 0
        for file in self.iter_files(patterns=patterns):
            file_count += 1
            extension_counter[file.suffix] += 1
            with file.open("r", encoding="utf-8", errors="ignore") as handle:
                line_count += sum(1 for _ in handle)
        return RepositoryStats(file_count=file_count, line_count=line_count, extensions=dict(extension_counter))

    # ------------------------------------------------------------------
    def search_pattern(
        self,
        pattern: str | Pattern[str],
        file_patterns: Iterable[str] = DEFAULT_FILE_PATTERNS,
    ) -> List[Tuple[Path, List[str]]]:
        """Search for ``pattern`` and return matching lines grouped by file."""

        compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
        matches: List[Tuple[Path, List[str]]] = []
        for file in self.iter_files(patterns=file_patterns):
            hits: List[str] = []
            with file.open("r", encoding="utf-8", errors="ignore") as handle:
                for lineno, line in enumerate(handle, start=1):
                    if compiled.search(line):
                        hits.append(f"{lineno}: {line.rstrip()}")
            if hits:
                matches.append((file, hits))
        return matches

    # ------------------------------------------------------------------
    def detect_high_risk_patterns(self) -> Dict[str, List[Tuple[Path, List[str]]]]:
        """Look for code smells that merit a manual review."""

        patterns = {
            "dangerous_eval": r"\beval\s*\(",
            "hardcoded_secret": r"(?i)(api_key|secret|password)\s*[=:]",
            "broad_exception": r"except\s+Exception",
        }
        return {name: self.search_pattern(regex) for name, regex in patterns.items()}

    # ------------------------------------------------------------------
    def load_package_dependencies(self, package_json: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
        """Parse ``package.json`` and return dependency sections."""

        package_file = package_json or (self.root / "package.json")
        if not package_file.exists():
            raise FileNotFoundError(package_file)
        data = json.loads(package_file.read_text())
        return {
            section: dict(sorted(deps.items()))
            for section, deps in data.items()
            if section.endswith("dependencies") and isinstance(deps, dict)
        }


__all__ = ["RepositoryScanner", "RepositoryStats"]
