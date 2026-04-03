"""Absorption orchestration for Kai.

This module is the first executable layer that unifies:
- constitutional guardrails
- CHI homeostasis
- source manifests
- repository self-audit

It does not mutate the repository blindly. It evaluates, prepares and
produces a traceable report before any heavy integration step.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from .assimilation_manifest import AssimilationManifest
from .chi_engine import CHIEngine
from .constitution_engine import ActionPlan, ConstitutionEngine
from .selfaudit import SelfAuditor


@dataclass(slots=True)
class AbsorptionReport:
    approved: bool
    constitutional_score: float
    constitutional_reasons: list[str]
    constitutional_alternatives: list[str]
    chi_snapshot: dict[str, object]
    chi_severity: str
    chi_reason: str
    integrated_titles: list[str]
    integration_targets: dict[str, list[str]]
    audit_issues: list[dict[str, object]]
    generated_at: str


class AbsorptionOrchestrator:
    """Prepare safe absorption cycles for Kai's core."""

    def __init__(
        self,
        repository_root: Path | str,
        *,
        constitution: ConstitutionEngine | None = None,
        chi: CHIEngine | None = None,
        manifest: AssimilationManifest | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).expanduser().resolve()
        self.constitution = constitution or ConstitutionEngine()
        self.chi = chi or CHIEngine()
        self.manifest = manifest or AssimilationManifest()
        self.auditor = SelfAuditor(self.repository_root)

    def prepare_absorption_plan(self, objective: str, extra_steps: Sequence[str] | None = None) -> ActionPlan:
        steps = [
            "Clasificar fuentes absorbidas y señal central.",
            "Asignar sección exacta del sistema a cada fuente.",
            "Ejecutar dry-run conceptual y generar manifest exportable.",
            "Auditar riesgos del repositorio antes de tocar más código.",
            "Registrar resultado y siguiente mutación segura.",
        ]
        if extra_steps:
            steps = [*steps, *extra_steps]
        return ActionPlan(
            objective=objective,
            steps=steps,
            expected_impact="Absorción trazable, reversible y alineada con la identidad de Kai.",
            autonomy_level=6,
            touches_memory=True,
            touches_codebase=True,
            destructive=False,
            sources=tuple(source.source_url for source in self.manifest.sources),
        )

    def run(self, objective: str, extra_steps: Sequence[str] | None = None) -> AbsorptionReport:
        plan = self.prepare_absorption_plan(objective, extra_steps=extra_steps)
        verdict = self.constitution.evaluate(plan)

        workload = 0.38 if plan.touches_codebase else 0.18
        noise = 0.15 if extra_steps else 0.08
        impact = 0.22 if verdict.approved else -0.12
        self.chi.adjust(impact=impact, noise=noise, workload=workload, recovery=0.04)
        chi_audit = self.chi.audit()

        audit_issues = [asdict(issue) for issue in self.auditor.audit(required_files=(
            "README.md",
            "package.json",
            "src/App.tsx",
        ))]

        return AbsorptionReport(
            approved=verdict.approved,
            constitutional_score=verdict.score,
            constitutional_reasons=verdict.reasons,
            constitutional_alternatives=verdict.alternatives,
            chi_snapshot=self.chi.snapshot(),
            chi_severity=chi_audit.severity,
            chi_reason=chi_audit.reason,
            integrated_titles=self.manifest.list_titles(),
            integration_targets=self.manifest.integration_targets(),
            audit_issues=audit_issues,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )

    def export_run(self, objective: str, output_path: Path | str) -> Path:
        report = self.run(objective)
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(str(asdict(report)), encoding="utf-8")
        return destination


__all__ = ["AbsorptionOrchestrator", "AbsorptionReport"]
