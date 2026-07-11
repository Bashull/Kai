from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any


CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".kt",
    ".c", ".cpp", ".cs", ".go", ".rs", ".sh", ".ps1", ".bat",
}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".conf", ".env", ".xml", ".html", ".css", ".csv",
}
DOCUMENT_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".rtf"}
PACKAGE_NAMES = {
    "pyproject.toml", "package.json", "requirements.txt", "setup.py",
    "setup.cfg", "cargo.toml", "go.mod", "pom.xml", "build.gradle",
}

SECRET_FILENAME_SIGNALS = {
    "client_secret": "CLIENT_SECRET_FILENAME",
    "credentials": "CREDENTIALS_FILENAME",
    ".env": "ENV_FILENAME",
    "id_rsa": "PRIVATE_KEY_FILENAME",
    "private_key": "PRIVATE_KEY_FILENAME",
}

SECRET_CONTENT_PATTERNS = (
    ("PRIVATE_KEY_HEADER", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I)),
    ("CLIENT_SECRET_FIELD", re.compile(r"[\"']?client[_-]?secret[\"']?\s*[:=]", re.I)),
    ("API_KEY_FIELD", re.compile(r"[\"']?(?:api[_-]?key|apikey)[\"']?\s*[:=]", re.I)),
    ("TOKEN_FIELD", re.compile(r"[\"']?(?:access[_-]?token|auth[_-]?token|token)[\"']?\s*[:=]", re.I)),
    ("PASSWORD_FIELD", re.compile(r"[\"']?(?:password|passwd|pwd)[\"']?\s*[:=]", re.I)),
)

CAPABILITY_KEYWORDS = {
    "memory": ("memory", "memoria", "diary", "journal", "recuerdo", "snapshot"),
    "repository_mapping": ("mapper", "map_repository", "repo map", "inventory", "deep_map", "repository"),
    "archive_forensics": ("zip", "archive", "autopsy", "forensic", "manifest"),
    "security_audit": ("audit", "secret", "security", "sentinel", "quarantine", "scan"),
    "voice": ("voice", "tts", "audio", "speech", "voz"),
    "vision": ("vision", "image", "ocular", "visual", "imagen"),
    "code_forge": ("forge", "forja", "build", "compiler", "code generation"),
    "infrastructure_connectivity": ("relay", "connector", "ssh", "mcp", "endpoint", "websocket"),
    "governance_protocols": ("protocol", "protocolo", "directive", "directiva", "canon", "prompt"),
}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text(path: Path, max_chars: int = 500_000) -> str | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS | CODE_EXTENSIONS:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except OSError:
        return None

def detect_secret_signals(path: Path, text: str | None) -> list[str]:
    signals: set[str] = set()
    lower_name = path.name.lower()
    for marker, label in SECRET_FILENAME_SIGNALS.items():
        if marker in lower_name:
            signals.add(label)
    if text:
        for label, pattern in SECRET_CONTENT_PATTERNS:
            if pattern.search(text):
                signals.add(label)
    return sorted(signals)

def extract_python_structure(text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        return {
            "functions": [],
            "classes": [],
            "imports": [],
            "parse_error": f"{type(exc).__name__}: {exc}",
        }

    functions: set[str] = set()
    classes: set[str] = set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.add(node.name)
        elif isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    return {
        "functions": sorted(functions),
        "classes": sorted(classes),
        "imports": sorted(imports),
        "parse_error": None,
    }

def infer_capabilities(
    path: Path,
    text: str | None,
    structure: dict[str, Any] | None,
) -> list[str]:
    parts = [path.name.lower(), (text or "").lower()]
    if structure:
        parts.extend(name.lower() for name in structure.get("functions", []))
        parts.extend(name.lower() for name in structure.get("classes", []))
        parts.extend(name.lower() for name in structure.get("imports", []))
    haystack = "\n".join(parts)

    capabilities = [
        capability
        for capability, keywords in CAPABILITY_KEYWORDS.items()
        if any(keyword in haystack for keyword in keywords)
    ]
    return sorted(capabilities)

def classify_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in CODE_EXTENSIONS:
        return "CODE"
    if suffix in DOCUMENT_EXTENSIONS:
        return "DOCUMENT"
    if suffix in TEXT_EXTENSIONS or path.name.lower() in PACKAGE_NAMES:
        return "CONFIG_OR_TEXT"
    if suffix in {".zip", ".tar", ".gz", ".7z", ".rar"}:
        return "ARCHIVE"
    return "BINARY_OR_UNKNOWN"

def choose_decision(
    path: Path,
    artifact_type: str,
    capabilities: list[str],
    secret_signals: list[str],
    is_duplicate: bool,
) -> str:
    if secret_signals:
        return "QUARANTINED"
    if is_duplicate:
        return "DUPLICATE"
    if path.name.lower() == "skill.md":
        return "SKILL_CANDIDATE"
    if path.name.lower() in PACKAGE_NAMES:
        return "LIBRARY_CANDIDATE"
    if artifact_type == "CODE":
        return "TOOL_CANDIDATE"
    if "governance_protocols" in capabilities and artifact_type == "DOCUMENT":
        return "PROTOCOL_CANDIDATE"
    if "memory" in capabilities and artifact_type in {"DOCUMENT", "CONFIG_OR_TEXT"}:
        return "MEMORY_CANDIDATE"
    if "infrastructure_connectivity" in capabilities:
        return "INFRASTRUCTURE_CANDIDATE"
    return "NEEDS_RESEARCH"

def scan_artifact(
    path: Path,
    known_hashes: set[str] | None = None,
) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    digest = sha256_file(path)
    text = _read_text(path)
    artifact_type = classify_artifact_type(path)
    structure = extract_python_structure(text or "") if path.suffix.lower() == ".py" else None
    capabilities = infer_capabilities(path, text, structure)
    secret_signals = detect_secret_signals(path, text)
    duplicate = digest in (known_hashes or set())
    decision = choose_decision(
        path=path,
        artifact_type=artifact_type,
        capabilities=capabilities,
        secret_signals=secret_signals,
        is_duplicate=duplicate,
    )

    return {
        "schema_version": 1,
        "path": str(path.resolve()),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size": path.stat().st_size,
        "sha256": digest,
        "artifact_type": artifact_type,
        "decision": decision,
        "duplicate_basis": "SHA256_EXACT" if duplicate else None,
        "secret_signals": secret_signals,
        "capabilities": capabilities,
        "structure": structure,
        "provenance": {
            "source_type": "LOCAL_FILE",
            "source": str(path.resolve()),
        },
    }
