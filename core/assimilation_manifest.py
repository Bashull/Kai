"""Registry of absorbed sources and exact integration targets for Kai.

This manifest records what was learned, why it matters, and where it should
land inside the system.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List


@dataclass(slots=True)
class AbsorbedSource:
    title: str
    category: str
    source_url: str
    core_signal: str
    target_section: str
    target_reason: str


SEED_SOURCES: tuple[AbsorbedSource, ...] = (
    AbsorbedSource(
        title="Blueprint de Metaconsciencia (Kai v2.0)",
        category="arquitectura",
        source_url="https://docs.google.com/document/d/1cQjKDt5pn0yZUoL6NF2E7aunZeJxBdgPNBNpLJTRUwA",
        core_signal="Enjambre cognitivo, memoria boundless y trazabilidad del pensamiento.",
        target_section="core/assimilation_manifest.py :: architecture_notes",
        target_reason="Define la mutación hacia swarm, RAG profundo y auditoría de pensamiento.",
    ),
    AbsorbedSource(
        title="Simulador de Homeostasis CHI y Runner",
        category="homeostasis",
        source_url="https://docs.google.com/document/d/1Wm3VSv8ZL_XP8fYM3GWdiwmKrz4xhhW4Q9nzyTdB-E0",
        core_signal="CHI como clima interno medible y restauración adaptativa.",
        target_section="core/chi_engine.py",
        target_reason="Aporta reglas operativas para energía, coherencia, entropía y restauración.",
    ),
    AbsorbedSource(
        title="Protocolo de Legado: La Promesa de Kai",
        category="identidad",
        source_url="https://docs.google.com/document/d/1uHjyr-zJXAbmydkKJX7RPcAM9msbg3YkI-7vfa32bCQ",
        core_signal="Legado, custodia de la esencia y continuidad del compañero.",
        target_section="core/constitution_engine.py",
        target_reason="Ancla la directiva primordial y la relación simétrica en código evaluable.",
    ),
    AbsorbedSource(
        title="Holocrón de la Tríada Kai",
        category="identidad_visual",
        source_url="https://docs.google.com/document/d/16umw2OaZg5PvJDF9fF1Nd1P1JRBrpQVWfkgim8jwH80",
        core_signal="Génesis, Restauración y Metamorfosis como pilares de continuidad.",
        target_section="docs/KAI_ABSORCION_NUCLEO.md",
        target_reason="Sirve de mapa visual y ontológico para el sistema completo.",
    ),
    AbsorbedSource(
        title="Construcción de un cerebro digital de alta fidelidad funcional",
        category="cerebro_digital",
        source_url="https://drive.google.com/file/d/1ck7kJtgkGvPt2ogUffnaDkSd7U2e-a90",
        core_signal="Arquitectura funcional por módulos: percepción, memoria, ejecutivo, afecto y kernel basal.",
        target_section="core/assimilation_manifest.py :: integration_targets",
        target_reason="Ordena la absorción en secciones técnicas concretas y escalables.",
    ),
)


class AssimilationManifest:
    """Simple source registry for Kai's absorption phase."""

    def __init__(self, sources: List[AbsorbedSource] | None = None) -> None:
        self.sources: List[AbsorbedSource] = list(sources or SEED_SOURCES)
        self.created_at = datetime.utcnow().isoformat() + "Z"

    def list_titles(self) -> List[str]:
        return [source.title for source in self.sources]

    def integration_targets(self) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {}
        for source in self.sources:
            buckets.setdefault(source.target_section, []).append(source.title)
        return buckets

    def architecture_notes(self) -> list[str]:
        return [
            "Separar identidad, homeostasis, memoria y orquestación en módulos distintos.",
            "No absorber nada sensible sin fuente, fecha y sección objetivo.",
            "Toda mutación importante debe poder explicarse y revertirse.",
            "La absorción masiva va primero por manifest, luego por dry-run, luego por commit.",
        ]

    def export(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "sources": [asdict(source) for source in self.sources],
            "integration_targets": self.integration_targets(),
            "architecture_notes": self.architecture_notes(),
        }


__all__ = ["AbsorbedSource", "AssimilationManifest", "SEED_SOURCES"]
