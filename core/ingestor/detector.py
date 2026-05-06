"""Detector Core — file type identification using magic bytes and extension fallback.

Inspired by Apache Tika pattern: magic bytes beat file extensions.
"""
from __future__ import annotations

from pathlib import Path

from .schemas import BinaryInput, DetectedAsset

# Magic byte signatures  →  (media_type, extension)
_MAGIC: list[tuple[bytes, str, str]] = [
    (b"%PDF", "application/pdf", ".pdf"),
    (b"PK\x03\x04", "application/zip", ".zip"),
    (b"\x89PNG", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"GIF8", "image/gif", ".gif"),
    (b"<!DOCTYPE html", "text/html", ".html"),
    (b"<html", "text/html", ".html"),
]

_EXTENSION_MAP: dict[str, str] = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".ts": "text/typescript",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}

_MODE_MAP: dict[str, str] = {
    "text/x-python": "deep",
    "text/markdown": "partition",
    "text/plain": "quick",
    "application/json": "quick",
    "text/csv": "quick",
    "application/pdf": "partition",
    "application/zip": "partition",
    "text/html": "partition",
    "application/yaml": "quick",
    "text/typescript": "deep",
    "text/javascript": "deep",
    "image/png": "quick",
    "image/jpeg": "quick",
    "image/gif": "quick",
}


class MagicDetector:
    """Identify media type from magic bytes, falling back to extension."""

    name = "magic_detector"

    def detect(self, asset: BinaryInput, *, target: str = "memory") -> DetectedAsset:
        magic_result = self._check_magic(asset.raw_bytes)
        if magic_result:
            media_type, ext = magic_result
            detector = "magic_detector"
        else:
            ext = Path(asset.filename).suffix.lower()
            media_type = _EXTENSION_MAP.get(ext, "application/octet-stream")
            detector = "extension_detector"

        mode = _MODE_MAP.get(media_type, "quick")
        if target == "preview":
            mode = "quick"

        return DetectedAsset(
            media_type=media_type,
            extension=ext,
            detector_name=detector,
            chosen_mode=mode,
        )

    def _check_magic(self, data: bytes) -> tuple[str, str] | None:
        for signature, media_type, ext in _MAGIC:
            if data[: len(signature)].lower().startswith(signature.lower()):
                return media_type, ext
        return None
