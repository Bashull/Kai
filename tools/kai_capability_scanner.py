from __future__ import annotations

import argparse
import ast
import hashlib
import json
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


SECRET_FIELD_LABELS = {
    "client_secret": "CLIENT_SECRET_FIELD",
    "api_key": "API_KEY_FIELD",
    "apikey": "API_KEY_FIELD",
    "access_token": "TOKEN_FIELD",
    "auth_token": "TOKEN_FIELD",
    "token": "TOKEN_FIELD",
    "password": "PASSWORD_FIELD",
    "passwd": "PASSWORD_FIELD",
    "pwd": "PASSWORD_FIELD",
}


def _normalized_secret_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _is_internal_security_label(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", value))


def _constant_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

def _python_secret_assignment_signals(text: str) -> list[str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []

    signals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                key = _constant_string(key_node)
                value = _constant_string(value_node)
                if key is None:
                    continue
                label = SECRET_FIELD_LABELS.get(_normalized_secret_key(key))
                if label and value is not None and not _is_internal_security_label(value):
                    signals.add(label)

        elif isinstance(node, ast.Assign):
            value = _constant_string(node.value)
            if value is None or _is_internal_security_label(value):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    label = SECRET_FIELD_LABELS.get(_normalized_secret_key(target.id))
                    if label:
                        signals.add(label)

        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = _constant_string(node.value)
            if value is None or _is_internal_security_label(value):
                continue
            label = SECRET_FIELD_LABELS.get(_normalized_secret_key(node.target.id))
            if label:
                signals.add(label)

    return sorted(signals)

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
        private_key_pattern = SECRET_CONTENT_PATTERNS[0][1]
        if private_key_pattern.search(text):
            signals.add("PRIVATE_KEY_HEADER")

        if path.suffix.lower() == ".py":
            signals.update(_python_secret_assignment_signals(text))
        else:
            for label, pattern in SECRET_CONTENT_PATTERNS[1:]:
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


def _load_known_hashes(path: Path | None) -> set[str]:
    if path is None:
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"sha256", "artifact_sha256"} and isinstance(item, str):
                    if re.fullmatch(r"[0-9a-fA-F]{64}", item):
                        hashes.add(item.lower())
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    return hashes


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kai static capability scanner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Statically scan one artifact")
    scan.add_argument("--path", type=Path, required=True)
    scan.add_argument("--out", type=Path, required=True)
    scan.add_argument("--known-manifest", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    if args.command == "scan":
        known_hashes = _load_known_hashes(args.known_manifest)
        result = scan_artifact(args.path, known_hashes=known_hashes)
        _write_json_atomic(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
