"""Processing modes — Quick, Deep, Partition.

Quick  → fast text extraction, no structural analysis.
Deep   → full structural parse with metadata enrichment.
Partition → chunked document with element classification.
"""
from __future__ import annotations

import ast
import csv
import io
import json
import uuid
import zipfile
from pathlib import Path
from typing import Any

from .schemas import BinaryInput, DetectedAsset, DocumentElement, FusionDocument


# ---------------------------------------------------------------------------
# Quick Mode (MarkItDown pattern)
# ---------------------------------------------------------------------------

class QuickMode:
    def process(self, asset: BinaryInput, detection: DetectedAsset) -> FusionDocument:
        text = self._decode(asset)
        chunks = self._chunk(text, size=800)
        elements = [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=text)]
        return FusionDocument(
            id=str(uuid.uuid4()),
            source=asset.filename,
            media_type=detection.media_type,
            text=text,
            elements=elements,
            chunks=chunks,
            metadata={"mode": "quick"},
        )

    def _decode(self, asset: BinaryInput) -> str:
        try:
            return asset.raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            return repr(asset.raw_bytes[:200])

    def _chunk(self, text: str, size: int = 800) -> list[str]:
        return [text[i: i + size] for i in range(0, max(len(text), 1), size)] or [text]


# ---------------------------------------------------------------------------
# Deep Mode (Docling pattern)
# ---------------------------------------------------------------------------

class DeepMode:
    def process(self, asset: BinaryInput, detection: DetectedAsset) -> FusionDocument:
        text = asset.raw_bytes.decode("utf-8", errors="replace")
        meta: dict[str, Any] = {"mode": "deep"}
        elements: list[DocumentElement] = []

        if detection.media_type == "text/x-python":
            meta.update(self._analyze_python(text))
            elements = self._python_elements(text)
        elif detection.media_type == "text/typescript":
            elements = [DocumentElement(id=str(uuid.uuid4()), category="Code", text=text)]
        elif detection.media_type == "text/javascript":
            elements = [DocumentElement(id=str(uuid.uuid4()), category="Code", text=text)]
        else:
            elements = [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=text)]

        chunks = [text[i: i + 600] for i in range(0, max(len(text), 1), 600)]
        return FusionDocument(
            id=str(uuid.uuid4()),
            source=asset.filename,
            media_type=detection.media_type,
            text=text,
            elements=elements,
            chunks=chunks or [text],
            metadata=meta,
        )

    def _analyze_python(self, source: str) -> dict[str, Any]:
        try:
            ast.parse(source)
            valid = True
        except SyntaxError:
            valid = False
        lines = source.splitlines()
        return {
            "python_valid": valid,
            "line_count": len(lines),
            "has_classes": "class " in source,
            "has_functions": "def " in source,
        }

    def _python_elements(self, source: str) -> list[DocumentElement]:
        elements = []
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("class "):
                cat = "ClassDef"
            elif stripped.startswith("def ") or stripped.startswith("async def "):
                cat = "FunctionDef"
            elif stripped.startswith("#"):
                cat = "Comment"
            elif stripped:
                cat = "Code"
            else:
                continue
            elements.append(DocumentElement(
                id=str(uuid.uuid4()),
                category=cat,
                text=line,
                metadata={"line": i},
            ))
        return elements or [DocumentElement(id=str(uuid.uuid4()), category="Code", text=source)]


# ---------------------------------------------------------------------------
# Partition Mode (Unstructured pattern)
# ---------------------------------------------------------------------------

class PartitionMode:
    def process(self, asset: BinaryInput, detection: DetectedAsset) -> FusionDocument:
        mt = detection.media_type
        if mt == "text/markdown":
            return self._partition_markdown(asset)
        if mt == "application/json":
            return self._partition_json(asset)
        if mt == "text/csv":
            return self._partition_csv(asset)
        if mt == "application/zip":
            return self._partition_zip(asset)
        if mt == "application/pdf":
            return self._partition_pdf(asset, detection)
        # Fallback: treat as plain text
        text = asset.raw_bytes.decode("utf-8", errors="replace")
        return self._generic(asset, detection, text)

    def _partition_markdown(self, asset: BinaryInput) -> FusionDocument:
        text = asset.raw_bytes.decode("utf-8", errors="replace")
        elements: list[DocumentElement] = []
        for line in text.splitlines():
            if line.startswith("#"):
                cat = "Title"
            elif line.startswith("- ") or line.startswith("* "):
                cat = "ListItem"
            elif line.startswith("```"):
                cat = "CodeBlock"
            elif line.strip():
                cat = "NarrativeText"
            else:
                continue
            elements.append(DocumentElement(id=str(uuid.uuid4()), category=cat, text=line))
        chunks = self._split_by_heading(text)
        return FusionDocument(
            id=str(uuid.uuid4()),
            source=asset.filename,
            media_type="text/markdown",
            text=text,
            elements=elements or [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=text)],
            chunks=chunks or [text],
            metadata={"mode": "partition", "heading_count": sum(1 for e in elements if e.category == "Title")},
        )

    def _partition_json(self, asset: BinaryInput) -> FusionDocument:
        text = asset.raw_bytes.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
            elements = [DocumentElement(id=str(uuid.uuid4()), category="JSON", text=json.dumps(data, indent=2)[:2000])]
        except json.JSONDecodeError as e:
            elements = [DocumentElement(id=str(uuid.uuid4()), category="Error", text=str(e))]
        return FusionDocument(
            id=str(uuid.uuid4()), source=asset.filename,
            media_type="application/json", text=text,
            elements=elements, chunks=[text], metadata={"mode": "partition"},
        )

    def _partition_csv(self, asset: BinaryInput) -> FusionDocument:
        text = asset.raw_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        elements = [
            DocumentElement(id=str(uuid.uuid4()), category="TableRow", text=",".join(r))
            for r in rows
        ]
        return FusionDocument(
            id=str(uuid.uuid4()), source=asset.filename,
            media_type="text/csv", text=text,
            elements=elements or [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=text)],
            chunks=[text],
            metadata={"mode": "partition", "row_count": len(rows)},
        )

    def _partition_zip(self, asset: BinaryInput) -> FusionDocument:
        elements: list[DocumentElement] = []
        chunks: list[str] = []
        full_text_parts: list[str] = []
        try:
            with zipfile.ZipFile(io.BytesIO(asset.raw_bytes)) as zf:
                for name in zf.namelist():
                    elements.append(DocumentElement(
                        id=str(uuid.uuid4()),
                        category="EmbeddedResource",
                        text=name,
                        metadata={"filename": name},
                    ))
                    try:
                        content = zf.read(name).decode("utf-8", errors="replace")[:500]
                        chunks.append(f"# {name}\n{content}")
                        full_text_parts.append(content)
                    except Exception:
                        pass
        except Exception as e:
            elements = [DocumentElement(id=str(uuid.uuid4()), category="Error", text=str(e))]
        return FusionDocument(
            id=str(uuid.uuid4()), source=asset.filename,
            media_type="application/zip",
            text="\n".join(full_text_parts),
            elements=elements or [DocumentElement(id=str(uuid.uuid4()), category="Archive", text=asset.filename)],
            chunks=chunks or [asset.filename],
            metadata={"mode": "partition"},
        )

    def _partition_pdf(self, asset: BinaryInput, detection: DetectedAsset) -> FusionDocument:
        # Lightweight PDF text extraction without external dependencies
        text = asset.raw_bytes.decode("latin-1", errors="replace")
        # Extract text between stream markers (basic)
        import re
        streams = re.findall(r"stream\r?\n(.*?)\r?\nendstream", text, re.DOTALL)
        visible = [s for s in streams if len(s) > 10]
        content = "\n".join(visible[:20]) if visible else "(PDF: contenido no extraíble sin pdfminer)"
        elements = [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=content[:2000])]
        return FusionDocument(
            id=str(uuid.uuid4()), source=asset.filename,
            media_type="application/pdf", text=content[:4000],
            elements=elements, chunks=[content[:4000]],
            metadata={"mode": "partition", "page_hint": len(visible)},
        )

    def _generic(self, asset: BinaryInput, detection: DetectedAsset, text: str) -> FusionDocument:
        elements = [DocumentElement(id=str(uuid.uuid4()), category="NarrativeText", text=text[:2000])]
        return FusionDocument(
            id=str(uuid.uuid4()), source=asset.filename,
            media_type=detection.media_type, text=text,
            elements=elements, chunks=[text],
            metadata={"mode": "partition"},
        )

    def _split_by_heading(self, text: str, max_chunk: int = 800) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        for line in text.splitlines(keepends=True):
            if line.startswith("#") and current:
                chunks.append("".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            chunks.append("".join(current))
        # Split oversized chunks
        result: list[str] = []
        for chunk in chunks:
            if len(chunk) <= max_chunk:
                result.append(chunk)
            else:
                result.extend(chunk[i: i + max_chunk] for i in range(0, len(chunk), max_chunk))
        return result or [text]
