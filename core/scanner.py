from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from .base import KaiModule, ModuleResult


@dataclass(slots=True)
class ScanResult:
    dependencies: List[str]
    todos: List[str]
    files_scanned: int


class CodeScanner(KaiModule):
    """Lightweight static analysis utilities."""

    def run(self, context, path: Path, *, include_tests: bool = False) -> ModuleResult:  # type: ignore[override]
        if not path.exists():
            return ModuleResult(success=False, messages=[f"Path {path} does not exist"], data={"files": 0})

        dependencies: List[str] = []
        todos: List[str] = []
        files_scanned = 0

        for file_path in path.rglob("*.py"):
            if not include_tests and "test" in file_path.name:
                continue
            files_scanned += 1
            source = file_path.read_text(encoding="utf-8")
            todos.extend(self._extract_todos(source, file_path))
            dependencies.extend(self._extract_imports(source))

        context.add_log(f"scanner: processed {files_scanned} python files")
        return ModuleResult(
            success=True,
            data={
                "dependencies": sorted(set(dependencies)),
                "todos": todos,
                "files": files_scanned,
            },
            messages=[f"Analysed {files_scanned} files"],
        )

    def _extract_imports(self, source: str) -> List[str]:
        imports: List[str] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return imports

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module.split(".")[0])
        return imports

    def _extract_todos(self, source: str, path: Path) -> List[str]:
        todos: List[str] = []
        for idx, line in enumerate(source.splitlines(), start=1):
            if "TODO" in line or "FIXME" in line:
                todos.append(f"{path}:{idx} -> {line.strip()}")
        return todos
