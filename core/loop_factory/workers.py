"""Worker contracts and deterministic CELL-000 demo worker."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .evidence import sha256_file
from .model import JobManifest


@dataclass(frozen=True, slots=True)
class StepContext:
    job: JobManifest
    run_id: str
    sandbox: Path
    input_hash: str


@dataclass(frozen=True, slots=True)
class StepOutcome:
    output_hash: str
    evidence_summary: str
    cost_eur: float = 0.0
    verified: bool = True


class Worker(Protocol):
    worker_id: str

    def run(self, context: StepContext) -> StepOutcome: ...


class DemoFileWorker:
    worker_id = "demo-file"
    estimated_cost_eur = 0.0

    def __init__(
        self,
        sandbox: Path,
        on_write: Callable[[], None] | None = None,
    ) -> None:
        self.sandbox = Path(sandbox)
        self.on_write = on_write

    def output_path(self) -> Path:
        return self.sandbox / "demo.txt"

    def run(self, context: StepContext) -> StepOutcome:
        self.sandbox.mkdir(parents=True, exist_ok=True)
        target = self.output_path()
        temp = target.with_suffix(target.suffix + ".tmp")
        content = f"{context.job.job_id}\n{context.job.goal}\n{context.input_hash}\n"
        temp.write_text(content, encoding="utf-8")
        temp.replace(target)
        if self.on_write is not None:
            self.on_write()
        digest = sha256_file(target)
        return StepOutcome(digest, "deterministic demo marker", verified=True)

    def verify(self, context: StepContext, output_hash: str) -> bool:
        target = self.output_path()
        return target.exists() and sha256_file(target) == output_hash
