#!/usr/bin/env python3
"""KAI Skill Doctor 0.1.0. Offline, read-only survey of installed skill roots.

Does not follow skill symlinks, run any bundled code, contact networks, read secrets,
alter active skills, or promote candidates. Export is ONLY to stdout on request.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import quote

VERSION = "0.1.0"
MAX_SKILL_MD = 256 * 1024
MAX_RESOURCE = 16 * 1024 * 1024
MAX_SKILL_RESOURCES = 512
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SENSITIVE_RE = re.compile(
    r"(^|/)(\.env(?:\..*)?|\.git|\.ssh|id_rsa|id_ed25519|.*\.(?:key|pem|p12|pfx|keystore))$", re.I
)
HOME = Path.home()
DEFAULT_ROOTS = [HOME / ".agents/skills", HOME / ".claude/skills", HOME / ".codex/skills"]


def hash_regular(path: Path, limit: int) -> tuple[str, int]:
    """Reject symlinks; read a bounded opened regular file, not a path after validation."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > limit:
            raise ValueError("unsafe file kind or oversize")
        digest = hashlib.sha256()
        n = 0
        while True:
            data = os.read(fd, min(65536, limit + 1 - n))
            if not data:
                break
            n += len(data)
            if n > limit:
                raise ValueError("file exceeds size limit")
            digest.update(data)
        return digest.hexdigest(), n
    finally:
        os.close(fd)


def parse_frontmatter(path: Path):
    try:
        import yaml  # preinstalled dependency on verified Termux
    except ImportError:
        raise ValueError("PyYAML is not installed")
    if path.is_symlink():
        raise ValueError("SKILL.md is a symlink")
    size = path.lstat().st_size
    if size > MAX_SKILL_MD:
        raise ValueError("SKILL.md over 256KiB")
    # O_NOFOLLOW on the actual read, not just prior lstat
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_SKILL_MD:
            raise ValueError("invalid SKILL.md type/size")
        data = os.read(fd, MAX_SKILL_MD + 1)
    finally:
        os.close(fd)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("SKILL.md not UTF-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("unterminated frontmatter")
    try:
        meta = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError:
        raise ValueError("invalid YAML frontmatter")
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be an object")
    name, desc = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError("invalid skill name")
    if not isinstance(desc, str) or not desc.strip():
        raise ValueError("missing description")
    return meta


def audit(path: Path, root: Path) -> dict:
    result = {"root": str(root), "folder": path.name, "status": "BLOCKED",
              "issues": [], "files": 0, "bytes": 0, "skill_sha256": None}
    issues = result["issues"]
    try:
        if path.is_symlink():
            result["status"] = "LINK_REFERENCE"
            issues.append("SYMLINK_SKILL_REQUIRES_OWNER_REVIEW")
            return result
        if not path.is_dir():
            issues.append("NOT_DIRECTORY")
            return result
        entry = path / "SKILL.md"
        if not entry.exists() or entry.is_symlink():
            issues.append("MISSING_OR_LINKED_SKILL_MD")
            return result
        try:
            meta = parse_frontmatter(entry)
        except (OSError, ValueError) as e:
            issues.append("SKILL_MD: " + str(e))
            return result
        result["name"] = meta["name"]
        if meta["name"] != path.name:
            issues.append("DIRECTORY_NAME_MISMATCH")
        manifest = []
        total = 0
        for base, dirs, files in os.walk(path, followlinks=False):
            dirs.sort()
            files.sort()
            for d in dirs:
                sub = Path(base) / d
                if sub.is_symlink():
                    issues.append("LINK_DIRECTORY:" + sub.relative_to(path).as_posix())
            dirs[:] = [d for d in dirs if not (Path(base) / d).is_symlink() and d != ".git"]
            for f in files:
                file = Path(base) / f
                rel = file.relative_to(path).as_posix()
                if SENSITIVE_RE.search(rel):
                    issues.append("SENSITIVE_PATH_BLOCKED:" + rel)
                    continue
                if file.is_symlink():
                    issues.append("LINK_FILE:" + rel)
                    continue
                if not file.is_file():
                    issues.append("NONREGULAR_FILE:" + rel)
                    continue
                try:
                    digest, size = hash_regular(file, MAX_RESOURCE)
                except (OSError, ValueError) as e:
                    issues.append("UNREADABLE_OR_OVERSIZE:" + rel)
                    continue
                total += size
                manifest.append({"relative": rel, "digest": "sha256:" + digest, "size": size})
                if len(manifest) > MAX_SKILL_RESOURCES or total > MAX_RESOURCE:
                    issues.append("EXCEEDS_MCP_PORTABLE_LIMITS")
                    break
            if "EXCEEDS_MCP_PORTABLE_LIMITS" in issues:
                break
        result["files"] = len(manifest)
        result["bytes"] = total
        for item in manifest:
            if item["relative"] == "SKILL.md":
                result["skill_sha256"] = item["digest"]
        result["status"] = "READY_FOR_REVIEW" if not issues else "BLOCKED"
        # Manifest held only in this process; never write it to active skill roots.
        result["_manifest"] = manifest
        result["_frontmatter"] = meta
    except (OSError, ValueError) as e:
        issues.append("READ_ERROR:" + type(e).__name__)
    return result


def inspect_roots(roots: list[Path]) -> dict:
    rows = []
    missing = []
    for root in roots:
        if not root.exists() or not root.is_dir() or root.is_symlink():
            missing.append(str(root))
            continue
        for entry in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
            if entry.name.startswith("."):
                continue
            rows.append(audit(entry, root))
    names = {}
    for row in rows:
        name = row.get("name", row["folder"])
        names.setdefault(name.casefold(), []).append(row)
    for group in names.values():
        if len(group) > 1:
            for row in group:
                row["duplicates"] = len(group)
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"schema": "kai-skill-doctor/v1", "version": VERSION,
            "roots_checked": [str(x) for x in roots], "roots_missing": missing,
            "summary": {"entries": len(rows), "states": counts,
                        "duplicate_names": sum(len(g) for g in names.values() if len(g) > 1)},
            "entries": rows}


def safe_view(report: dict) -> dict:
    """Do not expose skill body, full frontmatter or secret contents in reports."""
    return {**report, "entries": [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in report["entries"]]}


def sep_manifest(row: dict, server_id: str):
    if row["status"] != "READY_FOR_REVIEW":
        raise ValueError("skill has unresolved issues")
    if not NAME_RE.fullmatch(server_id):
        raise ValueError("server-id must be a lowercase slug")
    name = row["name"]
    resources = [{"uri": f"skill://{server_id}/{name}/{quote(item['relative'], safe='/')}",
                  "digest": item["digest"], "size": item["size"]}
                 for item in row["_manifest"]]
    return {
        "uri": f"skill://{server_id}/{name}/SKILL.md",
        "frontmatter": row["_frontmatter"],
        "resources": resources
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="KAI Skill Doctor: offline read-only skills audit")
    parser.add_argument("--root", action="append", help="explicit skill root (repeatable)")
    parser.add_argument("--json", action="store_true", help="emit sanitized JSON report")
    parser.add_argument("--sep-preview", help="skill name to print a SEP-2640 manifest candidate")
    parser.add_argument("--server-id", default="kai-termux-lab")
    args = parser.parse_args(argv)
    roots = [Path(x).expanduser() for x in args.root] if args.root else DEFAULT_ROOTS
    report = inspect_roots(roots)
    if args.sep_preview:
        candidates = [r for r in report["entries"] if r.get("name") == args.sep_preview]
        if len(candidates) != 1:
            parser.error("skill must resolve uniquely across selected roots")
        try:
            print(json.dumps(sep_manifest(candidates[0], args.server_id), ensure_ascii=False, indent=2))
        except ValueError as exc:
            parser.error(str(exc))
        return 0
    if args.json:
        print(json.dumps(safe_view(report), ensure_ascii=False, indent=2))
    else:
        print("KAI Skill Doctor", VERSION, "(READ-ONLY; no skill executed)")
        print("Entries:", report["summary"]["entries"], "States:", report["summary"]["states"])
        print("Duplicate-name occurrences:", report["summary"]["duplicate_names"])
        for r in report["entries"]:
            if r["status"] != "READY_FOR_REVIEW":
                print(f"[{r['status']}] {r['root']}/{r['folder']}: {', '.join(r['issues'][:3])}")
        if report["roots_missing"]:
            print("Missing roots:", len(report["roots_missing"]))
        print("READY_FOR_REVIEW means format/integrity checks, NOT runtime approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
