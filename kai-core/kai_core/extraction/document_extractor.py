from __future__ import annotations

from collections import Counter
import re

from kai_core.models.extraction import ExtractionResult

THEME_KEYWORDS = {
    "identidad": ["alma", "identidad", "origen"],
    "memoria/restauración": ["memoria", "restaur", "backup"],
    "FusionAI": ["fusionai", "arquitectura"],
    "metaconsciencia/CHI": ["chi", "coherencia", "homeostasis"],
    "KaiOS/código": ["código", "python", "typescript", "api"],
    "voz": ["voz", "audio", "tts"],
    "cuerpo/visual": ["cuerpo", "avatar", "visual"],
    "observabilidad": ["observabilidad", "auditoría", "log"],
    "EntherEye/proyectos especiales": ["enthereye", "especial"],
}

CANON_MARKERS = ("debe", "siempre", "nunca", "obligatorio", "regla")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _top_concepts(text: str, n: int = 8) -> list[str]:
    tokens = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_-]{4,}", text.lower())
    common = Counter(tokens).most_common(n)
    return [k for k, _ in common]


def find_related_duplicates(text: str, candidates: list[str]) -> list[str]:
    base = set(_top_concepts(text, n=12))
    related = []
    for candidate in candidates:
        overlap = base.intersection(_top_concepts(candidate, n=12))
        if len(overlap) >= 3:
            related.append(candidate[:120])
    return related


def detect_themes(text: str) -> list[str]:
    lowered = text.lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            themes.append(theme)
    return themes or ["KaiOS/código"]


def extract_document(text: str, related_docs: list[str] | None = None) -> ExtractionResult:
    related_docs = related_docs or []
    sents = _sentences(text)
    summary = " ".join(sents[:2])[:400] if sents else ""
    canon = [s for s in sents if any(m in s.lower() for m in CANON_MARKERS)][:8]
    technical = [c for c in _top_concepts(text) if c in {"python", "typescript", "json", "drive", "github", "api", "hash"}]
    symbolic = [c for c in _top_concepts(text) if c in {"alma", "identidad", "origen", "coherencia", "chi"}]
    contradictions = [s for s in sents if "pero" in s.lower() and "no" in s.lower()][:5]
    directives = [s for s in sents if any(x in s.lower() for x in ["debe", "obligatorio", "requiere", "aprobación"])][:8]

    return ExtractionResult(
        summary_short=summary,
        useful_ideas=sents[:8],
        canonical_candidates=canon,
        symbolic_concepts=symbolic,
        technical_concepts=technical,
        operational_directives=directives,
        contradictions=contradictions,
        related_duplicates=find_related_duplicates(text, related_docs),
        affected_themes=detect_themes(text),
        recommended_actions=[
            "actualizar_maestro_tematico",
            "registrar_en_memoria_operativa",
            "revisar_aprobacion_si_hay_escritura",
        ],
    )
