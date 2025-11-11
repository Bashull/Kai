from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .base import KaiModule, ModuleResult
from .exceptions import ModuleExecutionError

try:  # Optional dependency; network may not be available.
    import requests
except Exception:  # pragma: no cover - requests might not be installed.
    requests = None  # type: ignore


@dataclass(slots=True)
class FetchRequest:
    source: str
    destination: Path
    description: str = ""
    kind: str = "artifact"


class RepositoryFetcher(KaiModule):
    """Download or copy resources for Kai."""

    def run(self, context, request: FetchRequest, *, overwrite: bool = False) -> ModuleResult:  # type: ignore[override]
        target = request.destination
        if target.exists() and overwrite:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        elif target.exists() and not overwrite:
            self.emit(f"Destination {target} already exists; skipping fetch")
            context.add_log(f"fetch: reused existing artefact at {target}")
            return ModuleResult(success=True, data={"path": str(target)})

        parsed = urlparse(request.source)
        if parsed.scheme in {"http", "https"}:
            if requests is None:
                raise ModuleExecutionError("requests dependency missing; cannot fetch remote resources")
            response = requests.get(request.source, timeout=30)
            response.raise_for_status()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.content)
            message = f"Descargado recurso remoto desde {request.source}"
            self.emit(message)
            context.add_log(message)
            return ModuleResult(success=True, data={"path": str(target), "kind": request.kind})

        source_path = Path(request.source).expanduser().resolve()
        if not source_path.exists():
            raise ModuleExecutionError(f"Source {request.source!r} not found")

        if source_path.is_dir():
            shutil.copytree(source_path, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)

        message = f"Copiado recurso local desde {source_path}"
        self.emit(message)
        context.add_log(message)
        return ModuleResult(success=True, data={"path": str(target), "kind": request.kind})
