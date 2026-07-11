from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def python_structure(text: str) -> dict[str, Any]:
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

def fingerprint(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    stat = path.stat()
    structure = None
    if path.suffix.lower() == ".py":
        text = path.read_text(encoding="utf-8", errors="ignore")
        structure = python_structure(text)

    return {
        "path": str(path.resolve()),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
        "structure": structure,
    }


def _symbol_set(structure: dict[str, Any]) -> set[str]:
    symbols: set[str] = set()
    for kind in ("functions", "classes", "imports"):
        symbols.update(f"{kind}:{name}" for name in structure.get(kind, []))
    return symbols


def compare_python_structure(left_text: str, right_text: str) -> dict[str, Any]:
    left = python_structure(left_text)
    right = python_structure(right_text)
    left_symbols = _symbol_set(left)
    right_symbols = _symbol_set(right)
    union = left_symbols | right_symbols
    shared = left_symbols & right_symbols
    jaccard = len(shared) / len(union) if union else 1.0

    return {
        "left": left,
        "right": right,
        "shared_symbols": sorted(shared),
        "symbol_jaccard": round(jaccard, 6),
        "shared_functions": sorted(set(left["functions"]) & set(right["functions"])),
        "shared_classes": sorted(set(left["classes"]) & set(right["classes"])),
        "shared_imports": sorted(set(left["imports"]) & set(right["imports"])),
    }

def _lineage_key(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"(?:[_-]?v(?:ersion)?[_-]?\d+(?:[._-]\d+)*)$", "", stem)
    stem = re.sub(r"(?:[_-]?(?:old|new|final|fixed|copy|backup))$", "", stem)
    return stem


def _suggest_direction(left: dict[str, Any], right: dict[str, Any], relation: str) -> str:
    if relation != "FUNCTIONAL_ANCESTOR_CANDIDATE":
        return "UNKNOWN"
    if left["mtime_ns"] < right["mtime_ns"]:
        return "LEFT_TO_RIGHT"
    if right["mtime_ns"] < left["mtime_ns"]:
        return "RIGHT_TO_LEFT"
    return "UNKNOWN"


def compare_files(left_path: Path, right_path: Path) -> dict[str, Any]:
    left_path = Path(left_path)
    right_path = Path(right_path)
    left = fingerprint(left_path)
    right = fingerprint(right_path)
    same_sha256 = left["sha256"] == right["sha256"]
    relation = "UNRELATED_OR_UNKNOWN"
    placeholder_side: str | None = None
    basis: list[str] = []
    python_comparison: dict[str, Any] | None = None

    if same_sha256:
        relation = "EXACT_COPY"
        basis.append("SHA256_EXACT")
    elif left["size"] == 0 or right["size"] == 0:
        relation = "CORRUPTED_PLACEHOLDER"
        placeholder_side = "left" if left["size"] == 0 else "right"
        basis.append("ZERO_BYTE_VARIANT")
    elif left["suffix"] == right["suffix"] == ".py":
        left_text = left_path.read_text(encoding="utf-8", errors="ignore")
        right_text = right_path.read_text(encoding="utf-8", errors="ignore")
        python_comparison = compare_python_structure(left_text, right_text)
        shared_core = bool(
            python_comparison["shared_functions"] or python_comparison["shared_classes"]
        )
        same_lineage_key = _lineage_key(left_path) == _lineage_key(right_path)
        overlap = float(python_comparison["symbol_jaccard"])

        if overlap >= 0.5 and (same_lineage_key or shared_core):
            relation = "FUNCTIONAL_ANCESTOR_CANDIDATE"
            basis.extend(["PYTHON_STRUCTURE_OVERLAP", "DIRECTION_REQUIRES_PROVENANCE"])
        elif overlap >= 0.2 or shared_core:
            relation = "DIVERGED_BRANCH"
            basis.append("PARTIAL_PYTHON_STRUCTURE_OVERLAP")

    suggested_direction = _suggest_direction(left, right, relation)

    return {
        "schema_version": 1,
        "left": left,
        "right": right,
        "same_sha256": same_sha256,
        "relation": relation,
        "placeholder_side": placeholder_side,
        "suggested_direction": suggested_direction,
        "basis": basis,
        "python_comparison": python_comparison,
        "caution": "Timestamps alone never prove ancestry; use provenance, hashes and structural evidence.",
    }


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kai evidence-first genealogy miner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare = subparsers.add_parser("compare", help="Compare two artifacts without executing them")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    compare.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    if args.command == "compare":
        result = compare_files(args.left, args.right)
        _write_json_atomic(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
