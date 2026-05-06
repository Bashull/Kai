"""EXTRACCIÓN MAESTRA+ — structured chat extraction engine.

Implements the 13-section canonical format defined in the Protocolo de
Extracción de Chats · FusionAI.

Given raw chat text, produces a ChatExtractionResult with all 13 sections
populated, plus a SHA-256 fingerprint for traceability (Tríada+ §31).

Usage:
    extractor = ChatExtractor()
    result = extractor.extract(raw_text, title="RESUMEN_CHAT_...")
    bundle = result.to_bundle()          # integrates with FusionIngestorRouter
    print(result.to_markdown())          # human-readable export
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .schemas import MemoryNode


# ---------------------------------------------------------------------------
# Section dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IdeaClave:
    nombre: str
    descripcion: str = ""
    objetivo: str = ""
    utilidad: str = ""
    estado: str = ""  # decidido / en desarrollo / pendiente / descartado


@dataclass
class ProyectoDetectado:
    nombre: str
    descripcion: str = ""
    estado: str = ""
    piezas: list[str] = field(default_factory=list)


@dataclass
class DecisionTomada:
    descripcion: str
    permanente: bool = True


@dataclass
class Pendiente:
    descripcion: str
    siguiente_paso: bool = False


@dataclass
class Tesoro:
    nombre: str
    descripcion: str


@dataclass
class FichaArchivo:
    tema: str
    estado: str = "en progreso"
    valor: str = "medio"
    proyectos_relacionados: list[str] = field(default_factory=list)
    requiere_seguimiento: bool = True
    prioridad: str = "media"


# ---------------------------------------------------------------------------
# Main extraction result
# ---------------------------------------------------------------------------

@dataclass
class ChatExtractionResult:
    # Section 1
    titulo: str
    tema_principal: str = ""
    temas_secundarios: list[str] = field(default_factory=list)
    tipo_chat: str = ""
    estado_chat: str = ""

    # Section 2
    que_se_quiso: str = ""
    que_se_consiguio: str = ""
    que_quedo_medias: str = ""
    que_se_descarto: str = ""
    problemas: list[str] = field(default_factory=list)
    decisiones_resumen: list[str] = field(default_factory=list)

    # Section 3
    ideas_clave: list[IdeaClave] = field(default_factory=list)

    # Section 4
    proyectos: list[ProyectoDetectado] = field(default_factory=list)

    # Section 5
    herramientas: list[str] = field(default_factory=list)
    formatos: list[str] = field(default_factory=list)

    # Section 6
    relacion_usuario: str = ""
    memoria_permanente: list[str] = field(default_factory=list)
    filosofia: str = ""

    # Section 7
    prompts: dict[str, str] = field(default_factory=dict)

    # Section 8
    decisiones: list[DecisionTomada] = field(default_factory=list)

    # Section 9
    materiales: list[str] = field(default_factory=list)

    # Section 10
    cronologia: dict[str, str] = field(default_factory=dict)

    # Section 11
    conocimiento_reutilizable: list[str] = field(default_factory=list)

    # Section 12
    pendientes: list[Pendiente] = field(default_factory=list)

    # Section 13
    esencia: str = ""
    tesoros: list[Tesoro] = field(default_factory=list)
    ficha: FichaArchivo = field(default_factory=lambda: FichaArchivo(tema=""))

    # Metadata
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash_value: str = ""
    source_hash: str = ""

    def __post_init__(self) -> None:
        if not self.hash_value:
            payload = json.dumps(self._to_dict(), sort_keys=True, default=str)
            self.hash_value = hashlib.sha256(payload.encode()).hexdigest()

    def _to_dict(self) -> dict[str, Any]:
        return {
            "titulo": self.titulo,
            "tema_principal": self.tema_principal,
            "ideas_clave": [vars(i) for i in self.ideas_clave],
            "tesoros": [vars(t) for t in self.tesoros],
            "esencia": self.esencia,
            "extracted_at": self.extracted_at,
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_markdown(self) -> str:
        lines: list[str] = [
            f"# EXTRACCIÓN MAESTRA+ · {self.titulo}",
            f"\n**Extraído:** {self.extracted_at}",
            f"**Hash:** `{self.hash_value[:16]}...`\n",
            "---\n",
            "## 1. IDENTIFICACIÓN DEL CHAT\n",
            f"- **Título:** {self.titulo}",
            f"- **Tema principal:** {self.tema_principal}",
            f"- **Temas secundarios:** {', '.join(self.temas_secundarios)}",
            f"- **Tipo:** {self.tipo_chat}",
            f"- **Estado:** {self.estado_chat}\n",
            "## 2. RESUMEN ESTRUCTURAL\n",
            f"- **Qué se quiso:** {self.que_se_quiso}",
            f"- **Qué se consiguió:** {self.que_se_consiguio}",
            f"- **Quedó a medias:** {self.que_quedo_medias}",
            f"- **Se descartó:** {self.que_se_descarto}\n",
        ]

        if self.ideas_clave:
            lines.append("## 3. IDEAS CLAVE\n")
            for idea in self.ideas_clave:
                lines.append(f"### {idea.nombre}")
                if idea.descripcion:
                    lines.append(f"- *Descripción:* {idea.descripcion}")
                if idea.objetivo:
                    lines.append(f"- *Objetivo:* {idea.objetivo}")
                if idea.estado:
                    lines.append(f"- *Estado:* {idea.estado}")
                lines.append("")

        if self.decisiones:
            lines.append("## 8. DECISIONES TOMADAS\n")
            for d in self.decisiones:
                permanencia = "Permanente" if d.permanente else "Provisional"
                lines.append(f"- **{d.descripcion}** · {permanencia}")
            lines.append("")

        if self.conocimiento_reutilizable:
            lines.append("## 11. CONOCIMIENTO REUTILIZABLE\n")
            for k in self.conocimiento_reutilizable:
                lines.append(f"- {k}")
            lines.append("")

        if self.pendientes:
            lines.append("## 12. PENDIENTES\n")
            for p in self.pendientes:
                prefix = "→ **Siguiente paso:**" if p.siguiente_paso else "-"
                lines.append(f"{prefix} {p.descripcion}")
            lines.append("")

        lines.extend([
            "## 13. SALIDA FINAL OBLIGATORIA\n",
            "### A) Esencia\n",
            self.esencia or "*(sin definir)*",
            "\n### B) Inventario de Tesoros\n",
        ])
        for i, t in enumerate(self.tesoros, 1):
            lines.append(f"{i}. **{t.nombre}:** {t.descripcion}")

        lines.extend([
            "\n### C) Ficha de Archivo\n",
            f"- **Tema:** {self.ficha.tema}",
            f"- **Estado:** {self.ficha.estado}",
            f"- **Valor:** {self.ficha.valor}",
            f"- **Proyectos:** {', '.join(self.ficha.proyectos_relacionados)}",
            f"- **Requiere seguimiento:** {'SÍ' if self.ficha.requiere_seguimiento else 'NO'}",
            f"- **Prioridad:** {self.ficha.prioridad}",
        ])

        return "\n".join(lines)

    def to_memory_nodes(self, stability: str = "stable") -> list[MemoryNode]:
        """Convert extraction sections to MemoryNodes for FusionMemoryCore."""
        nodes: list[MemoryNode] = []
        base_meta = {
            "source": self.titulo,
            "type": "chat_extraction",
            "memory_stability": stability,
            "fusion_tags": ["chat_extraction", stability],
        }

        # Esencia node — always first
        if self.esencia:
            nodes.append(MemoryNode(
                id=str(uuid.uuid4()),
                text=f"[ESENCIA] {self.titulo}: {self.esencia}",
                metadata={**base_meta, "section": "esencia", "priority": "high"},
            ))

        # Ideas clave
        for idea in self.ideas_clave:
            text = f"[IDEA] {idea.nombre}: {idea.descripcion}"
            if idea.objetivo:
                text += f" Objetivo: {idea.objetivo}"
            nodes.append(MemoryNode(
                id=str(uuid.uuid4()),
                text=text,
                metadata={**base_meta, "section": "ideas_clave", "estado": idea.estado},
            ))

        # Decisiones permanentes
        for d in self.decisiones:
            if d.permanente:
                nodes.append(MemoryNode(
                    id=str(uuid.uuid4()),
                    text=f"[DECISION_PERMANENTE] {d.descripcion}",
                    metadata={**base_meta, "section": "decisiones", "permanente": True},
                ))

        # Tesoros
        for t in self.tesoros:
            nodes.append(MemoryNode(
                id=str(uuid.uuid4()),
                text=f"[TESORO] {t.nombre}: {t.descripcion}",
                metadata={**base_meta, "section": "tesoros", "priority": "high"},
            ))

        # Conocimiento reutilizable
        for k in self.conocimiento_reutilizable:
            nodes.append(MemoryNode(
                id=str(uuid.uuid4()),
                text=f"[CONOCIMIENTO] {k}",
                metadata={**base_meta, "section": "conocimiento_reutilizable"},
            ))

        # Pendientes
        for p in self.pendientes:
            tag = "siguiente_paso" if p.siguiente_paso else "pendiente"
            nodes.append(MemoryNode(
                id=str(uuid.uuid4()),
                text=f"[PENDIENTE] {p.descripcion}",
                metadata={**base_meta, "section": "pendientes", "tag": tag},
            ))

        return nodes


# ---------------------------------------------------------------------------
# ChatExtractor engine
# ---------------------------------------------------------------------------

class ChatExtractor:
    """Parse raw chat text into a structured ChatExtractionResult.

    For automated extraction, it applies heuristic pattern matching.
    For fully structured extractions (already formatted with the 13-section
    template), it parses the headings directly.

    In both cases, the result is fingerprinted (SHA-256) for Tríada+.
    """

    def extract(
        self,
        raw_text: str,
        *,
        title: str = "",
        tema: str = "",
        tipo: str = "",
        stability: str = "stable",
    ) -> ChatExtractionResult:
        """Extract structured information from raw chat text."""
        source_hash = hashlib.sha256(raw_text.encode()).hexdigest()

        # If the text already follows the 13-section EXTRACCIÓN MAESTRA+ format,
        # parse it directly; otherwise apply heuristic extraction.
        if self._is_structured(raw_text):
            result = self._parse_structured(raw_text, title=title)
        else:
            result = self._heuristic_extract(raw_text, title=title, tema=tema, tipo=tipo)

        result.source_hash = source_hash
        # Recompute hash now that source_hash is set
        payload = json.dumps(result._to_dict(), sort_keys=True, default=str)
        result.hash_value = hashlib.sha256(payload.encode()).hexdigest()

        return result

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _is_structured(self, text: str) -> bool:
        markers = [
            "IDENTIFICACIÓN DEL CHAT",
            "RESUMEN ESTRUCTURAL",
            "EXTRACCIÓN DE IDEAS",
            "SALIDA FINAL OBLIGATORIA",
        ]
        return sum(1 for m in markers if m in text.upper()) >= 3

    # ------------------------------------------------------------------
    # Structured parser (for pre-formatted extractions)
    # ------------------------------------------------------------------

    def _parse_structured(self, text: str, *, title: str) -> ChatExtractionResult:
        result = ChatExtractionResult(titulo=title or self._extract_field(text, "Título aproximado del chat"))
        result.tema_principal = self._extract_field(text, "Tema principal")
        result.tipo_chat = self._extract_field(text, "Tipo de chat")
        result.estado_chat = self._extract_field(text, "Estado general del chat")
        result.que_se_quiso = self._extract_field(text, "Qué se quiso hacer")
        result.que_se_consiguio = self._extract_field(text, "Qué se acabó consiguiendo")
        result.que_quedo_medias = self._extract_field(text, "Qué quedó a medias")
        result.que_se_descarto = self._extract_field(text, "Qué se descartó")
        result.esencia = self._extract_section(text, "A) ESENCIA DEL CHAT", "B)")
        result.relacion_usuario = self._extract_field(text, "Relación con")

        # Tesoros — look for numbered list after "INVENTARIO DE TESOROS"
        tesoro_section = self._extract_section(text, "B) INVENTARIO DE TESOROS", "C)")
        result.tesoros = self._parse_tesoros(tesoro_section)

        # Ficha de archivo
        ficha_section = self._extract_section(text, "C) FICHA DE ARCHIVO", None)
        result.ficha = self._parse_ficha(ficha_section, fallback_tema=result.titulo)

        return result

    # ------------------------------------------------------------------
    # Heuristic extractor (for raw / unstructured chat text)
    # ------------------------------------------------------------------

    def _heuristic_extract(self, text: str, *, title: str, tema: str, tipo: str) -> ChatExtractionResult:
        lines = text.splitlines()
        word_count = len(text.split())

        result = ChatExtractionResult(
            titulo=title or "CHAT_EXTRAIDO_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
            tema_principal=tema,
            tipo_chat=tipo or self._guess_type(text),
            estado_chat="extraído",
        )

        # Heuristic: decisions are lines with "decidido", "permanente", "definitivo"
        decision_patterns = re.compile(
            r'(decidido|permanente|definitivo|prohibido|aprobado|confirmado)', re.I
        )
        for line in lines:
            if decision_patterns.search(line) and len(line.strip()) > 10:
                result.decisiones.append(DecisionTomada(
                    descripcion=line.strip()[:200],
                    permanente="permanente" in line.lower(),
                ))

        # Heuristic: pending items
        pending_patterns = re.compile(r'^(pending|pendiente|siguiente paso|todo|falta)', re.I)
        for line in lines:
            stripped = line.strip()
            if pending_patterns.match(stripped) and len(stripped) > 10:
                result.pendientes.append(Pendiente(
                    descripcion=stripped[:200],
                    siguiente_paso="siguiente" in stripped.lower(),
                ))

        # Esencia fallback
        result.esencia = (
            f"Chat sobre {tema or 'tema no especificado'} "
            f"({'~' + str(word_count) + ' palabras'}). "
            "Extracción automática — revisar manualmente para enriquecer."
        )

        result.ficha = FichaArchivo(
            tema=tema or title,
            estado="extraído",
            valor="medio",
            requiere_seguimiento=True,
            prioridad="media",
        )

        return result

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _extract_field(self, text: str, label: str) -> str:
        pattern = re.compile(
            r'(?:' + re.escape(label) + r')[:\s*●\-]+([^\n]+)', re.I
        )
        m = pattern.search(text)
        return m.group(1).strip() if m else ""

    def _extract_section(self, text: str, start_marker: str, end_marker: str | None) -> str:
        start = text.upper().find(start_marker.upper())
        if start == -1:
            return ""
        start = text.find("\n", start)
        if end_marker:
            end = text.upper().find(end_marker.upper(), start)
            return text[start:end].strip() if end != -1 else text[start:].strip()
        return text[start:].strip()

    def _parse_tesoros(self, section: str) -> list[Tesoro]:
        tesoros: list[Tesoro] = []
        pattern = re.compile(r'^\s*\d+\.\s+\*\*(.+?)\*\*[:\s]+(.+)$', re.M)
        for m in pattern.finditer(section):
            tesoros.append(Tesoro(nombre=m.group(1).strip(), descripcion=m.group(2).strip()))
        return tesoros

    def _parse_ficha(self, section: str, *, fallback_tema: str) -> FichaArchivo:
        ficha = FichaArchivo(tema=self._extract_field(section, "Tema") or fallback_tema)
        estado = self._extract_field(section, "Estado")
        if estado:
            ficha.estado = estado
        valor = self._extract_field(section, "Valor")
        if valor:
            ficha.valor = valor.lower()
        seguimiento = self._extract_field(section, "Requiere seguimiento")
        ficha.requiere_seguimiento = "sí" in seguimiento.lower() if seguimiento else True
        prioridad = self._extract_field(section, "Prioridad")
        if prioridad:
            ficha.prioridad = prioridad.lower()
        return ficha

    def _guess_type(self, text: str) -> str:
        counts = {
            "técnico": len(re.findall(r'\b(código|función|módulo|clase|test|error|bug|api)\b', text, re.I)),
            "arquitectura": len(re.findall(r'\b(arquitectura|diseño|patrón|módulo|bloque|schema)\b', text, re.I)),
            "canon": len(re.findall(r'\b(canon|decisión|protocolo|ley|regla|definición)\b', text, re.I)),
            "ideación": len(re.findall(r'\b(idea|concepto|visión|propuesta|plan|futuro)\b', text, re.I)),
        }
        return max(counts, key=lambda k: counts[k]) if any(counts.values()) else "general"
