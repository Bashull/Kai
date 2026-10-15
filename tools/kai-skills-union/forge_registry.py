#!/usr/bin/env python3
"""Build an offline, content-addressed registry without executing skill content.

All input documents, including Markdown, YAML, JSON and archives, are data. No
import, shell, subprocess, network, template rendering or YAML object constructors
from recovered skills are used. See README.md for the evidence/counting contract.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextvars import ContextVar
from functools import wraps
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import unicodedata
import zipfile

try:
    import yaml
except ImportError:
    yaml = None

BASELINE_SHA256 = "ade519f50d6d996f8ee70de63fb8f38a17ca4eeff49823ccbd32b957a3cb7cc2"
STATES = {"DISCOVERED", "INVENTORIED", "INSPECTED", "UNDERSTOOD", "IMPROVED",
          "TESTED", "VERIFIED", "BLOCKED", "UNCHANGED", "REJECTED"}
CAPTURE_STATES = {"CAPTURED", "BLOCKED", "CHANGED_SINCE_CENSUS"}
FIELDS = (
    "01_identidad_procedencia", "02_version_licencia_estado", "03_proposito",
    "04_triggers", "05_entradas_salidas", "06_recursos", "07_dependencias_permisos",
    "08_codigo_arquitectura", "09_compatibilidad_4_plataformas",
    "10_seguridad_privacidad", "11_deuda_errores", "12_redundancias_composicion",
    "13_documentacion", "14_upstream_updates", "15_alternativas", "16_propuesta",
    "17_modificaciones", "18_pruebas_evidencias", "19_SHA_traza",
    "20_instalacion_recuperacion", "21_estado_siguiente",
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_ARCHIVE_FILES = 30000
MAX_ARCHIVE_BYTES = 768 * 1024 * 1024
MAX_SKILL_BYTES = 8 * 1024 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_FRONTMATTER_BYTES = 128 * 1024
MAX_DECLARATIONS = 512
MAX_METADATA_BYTES = 4 * 1024 * 1024
PENDING = "NO_COMPROBADO: requiere revisión individual y evidencia con alcance explícito."
_STOP_FILE = ContextVar("kai_registry_stop_file", default=None)


class RegistryError(ValueError):
    """An input or integrity invariant failed; the registry must not be published."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message):
    raise RegistryError(message)


def check_stop():
    flag = _STOP_FILE.get()
    if flag is not None:
        path = Path(flag).expanduser()
        if path.exists() or path.is_symlink():
            fail("STOP requested; no further processing/output writes are allowed")


def cooperative_stop(function):
    @wraps(function)
    def wrapped(*args, stop_file=None, **kwargs):
        token = _STOP_FILE.set(stop_file) if stop_file is not None else None
        try:
            check_stop()
            return function(*args, **kwargs)
        finally:
            if token is not None:
                _STOP_FILE.reset(token)
    return wrapped


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            fail("Duplicate JSON key: " + str(key))
        obj[key] = value
    return obj


def read_json(data: bytes):
    if len(data) > MAX_JSON_BYTES:
        fail("JSON inspection limit exceeded")
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=lambda x: fail("Nonfinite JSON number: " + x))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        fail("Invalid UTF-8 JSON: " + str(exc))


def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def path_key(path):
    return unicodedata.normalize("NFC", path.replace("\\", "/")).casefold()


def safe_relative(path):
    """Portable output/archive paths; device paths are never passed here."""
    if not isinstance(path, str) or not path or path.startswith("/"):
        fail("Invalid relative path: " + repr(path))
    parts = path.split("/")
    if ("\\" in path or ":" in path or any(p in ("", ".", "..") for p in parts)
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>"|?*' for c in path)):
        fail("Unsafe relative path: " + repr(path))
    for part in parts:
        base = part.split(".")[0].upper()
        if part != part.rstrip(" .") or base in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", base):
            fail("Nonportable relative path: " + repr(path))
    return PurePosixPath(path)


def validate_paths(names):
    keys = {}
    for name in names:
        safe_relative(name)
        key = path_key(name)
        if key in keys:
            fail("Duplicate/case/Unicode archive path collision: " + name)
        keys[key] = name
    for name in names:
        if any(path_key(str(p)) in keys for p in PurePosixPath(name).parents):
            fail("File/directory path collision: " + name)


def read_regular(root: Path, relative: str, limit=MAX_SKILL_BYTES):
    """Reject symlinks in every component; never follow a manifest escape."""
    check_stop()
    safe_relative(relative)
    current = root
    if current.is_symlink() or not current.is_dir():
        fail("Capture root is not a regular directory: " + str(root))
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            fail("Symlink in capture object path: " + relative)
    try:
        info = current.stat()
    except OSError as exc:
        fail("Missing capture object " + relative + ": " + str(exc))
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        fail("Nonregular or oversized capture object: " + relative)
    data = current.read_bytes()
    check_stop()
    if len(data) > limit:
        fail("Capture object grew past inspection limit: " + relative)
    return data


def require_digest(value, label):
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        fail("Invalid SHA256: " + label)
    return value


def require_size(value, label):
    if type(value) is not int or value < 0:
        fail("Invalid byte count: " + label)
    return value


def check_blob(data, record, label):
    if not isinstance(record, dict):
        fail("Invalid manifest record: " + label)
    require_digest(record.get("sha256"), label)
    require_size(record.get("bytes"), label)
    if len(data) != record["bytes"] or sha(data) != record["sha256"]:
        fail("Hash/size mismatch: " + label)


def device_path(path):
    if not isinstance(path, str) or not path or any(ord(c) < 32 for c in path):
        fail("Invalid captured device path")
    normalized = path.replace("\\", "/")
    if not (normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized)):
        fail("Captured path must be absolute for stable occurrence UID")
    return normalized


def occurrence_uid(source, path):
    return "occ:" + source + ":" + sha(device_path(path).encode("utf-8"))[:24]


def namespace_hints(path):
    """Path hints are provenance clues, never confirmed provider identities."""
    normalized = device_path(path)
    patterns = (
        (r"/plugins/cache/[^/]+/([^/]+)/([^/]+)/skills/([^/]+)/SKILL\.md$", "plugin_cache"),
        (r"/providers/([^/]+)/skills/([^/]+)/SKILL\.md$", "provider_tree"),
        (r"/plugins/([^/]+)/skills/([^/]+)/SKILL\.md$", "plugin_directory_tree"),
        (r"/KAI_SKILLS_847_[^/]+/skills/([^/]+)/([^/]+)/SKILL\.md$", "kai_namespaced_package_directory"),
    )
    out = []
    for pattern, kind in patterns:
        match = re.search(pattern, normalized, flags=re.I)
        if match:
            groups = match.groups()
            out.append({"namespace": groups[0], "name": groups[-1],
                        "version_hint": groups[1] if len(groups) == 3 else None,
                        "kind": kind, "certainty": "PATH_HINT_ONLY", "path": path})
    numbered = re.search(r"/(?:candidates|originals)/(\d{4})_([^/]+?)__([^/]+)/SKILL\.md$", normalized, flags=re.I)
    if numbered:
        out.append({"namespace": numbered[2], "name": numbered[3],
                    "original_id_hint": int(numbered[1]), "kind": "numbered_release_directory",
                    "certainty": "PATH_HINT_ONLY", "path": path})
    return out


def add_object(objects, digest, data, baseline_artifact=None):
    if digest in objects and objects[digest]["data"] != data:
        fail("SHA256 collision or inconsistent object content: " + digest)
    if digest not in objects:
        objects[digest] = {"data": data, "baseline_artifacts": [], "occurrence_uids": [],
                           "inherited_manual_reviews": []}
    if baseline_artifact and baseline_artifact not in objects[digest]["baseline_artifacts"]:
        objects[digest]["baseline_artifacts"].append(baseline_artifact)


def digest_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from digest_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from digest_values(item)
    elif isinstance(value, str):
        yield from re.findall(r"(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])", value)


def load_baseline(path, expected_sha256, expected_count, objects):
    """Verify all bundle bytes before accepting any identity or historical link."""
    path = Path(path)
    require_digest(expected_sha256, "baseline pin")
    preserved = {}
    # Pin and inspect the same open handle; never reopen a replaceable pathname.
    with path.open("rb") as pinned, zipfile.ZipFile(pinned) as archive:
        pinned.seek(0)
        digest = hashlib.file_digest(pinned, "sha256").hexdigest()
        check_stop()
        if digest != expected_sha256:
            fail("Pinned baseline SHA256 mismatch")
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_FILES or sum(i.file_size for i in infos) > MAX_ARCHIVE_BYTES:
            fail("Baseline archive exceeds inspection limits")
        names = [i.filename for i in infos]
        validate_paths(names)
        for info in infos:
            check_stop()
            if info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                fail("Only regular baseline archive members are accepted")
        manifest = read_json(archive.read("MANIFEST_SHA256.json"))
        if not isinstance(manifest, dict) or manifest.get("format") != "kai.skills.bundle/1":
            fail("Unsupported baseline bundle format")
        files = manifest.get("files")
        if not isinstance(files, dict) or set(files) != set(names) - {"MANIFEST_SHA256.json"}:
            fail("Baseline manifest must cover every payload exactly once")
        for name, record in files.items():
            check_stop()
            check_blob(archive.read(name), record, name)
        catalog = read_json(archive.read("catalog/INDEX_847_RECONCILED.json"))
        if (type(expected_count) is not int or expected_count < 1 or not isinstance(catalog, list)
                or len(catalog) != expected_count or manifest.get("skills") != expected_count):
            fail("Baseline identity count does not match explicit expected count")
        ids = [r.get("id") if isinstance(r, dict) else None for r in catalog]
        if any(type(i) is not int for i in ids) or set(ids) != set(range(1, expected_count + 1)):
            fail("Baseline IDs must be preserved unique and contiguous")
        identities, by_stable, artifacts = {}, {}, []
        for row in catalog:
            check_stop()
            number = row["id"]
            namespace, name = row.get("namespace"), row.get("name")
            if not all(isinstance(x, str) and len(safe_relative(x).parts) == 1 for x in (namespace, name)):
                fail("Invalid baseline namespace/name")
            stable = namespace + ":" + name
            if stable in by_stable:
                fail("Duplicate baseline namespaced identity")
            if row.get("uri") not in (f"skills://plugins/{namespace}/{name}", f"skill://plugins/{namespace}/{name}"):
                fail("Baseline URI disagrees with identity")
            original = f"originals/{namespace}/{name}/SKILL.md"
            candidate = f"providers/{namespace}/skills/{name}/SKILL.md"
            if row.get("original_path") != original or row.get("staged_root") != candidate.rsplit("/", 1)[0]:
                fail("Baseline identity paths disagree")
            for role, member, hash_field in (("original", original, "original_sha256"),
                                              ("candidate", candidate, "portable_sha256")):
                if member not in files or row.get(hash_field) != files[member]["sha256"]:
                    fail("Baseline catalog hash/path mismatch: " + member)
                artifact = {"original_id": number, "stable_id": stable, "role": role,
                            "member": member, "sha256": files[member]["sha256"]}
                artifacts.append(artifact)
                add_object(objects, artifact["sha256"], archive.read(member), artifact)
            identities[number] = {"id": number, "stable_id": stable, "namespace": namespace,
                                  "name": name, "catalog": row, "variants": [],
                                  "inherited_evidence": []}
            by_stable[stable] = number
        # History is associated by the baseline's exact namespaced member layout;
        # unverified catalog hashes or similarly named unrelated files are ignored.
        for member in names:
            check_stop()
            match = re.fullmatch(r"HISTORICAL/.+?/providers/([^/]+)/skills/([^/]+)/SKILL\.md", member)
            if match and ":".join(match.groups()) in by_stable:
                stable = ":".join(match.groups())
                artifact = {"original_id": by_stable[stable], "stable_id": stable,
                            "role": "historical", "member": member,
                            "sha256": files[member]["sha256"]}
                artifacts.append(artifact)
                add_object(objects, artifact["sha256"], archive.read(member), artifact)
        for artifact in artifacts:
            identities[artifact["original_id"]]["variants"].append(artifact)
        matrices = sorted(n for n in names if re.fullmatch(r"batch_\d+/evidence/AUDIT_MATRIX_847_BATCH\d+\.json", n))
        if not matrices:
            fail("An inherited baseline audit matrix is required")
        for matrix_path in matrices:
            check_stop()
            matrix = read_json(archive.read(matrix_path))
            rows = matrix.get("rows") if isinstance(matrix, dict) else None
            if (not isinstance(rows, list) or len(rows) != expected_count or
                    any(not isinstance(r, dict) or type(r.get("id")) is not int for r in rows)
                    or {r["id"] for r in rows} != set(identities)):
                fail("Inherited matrix must cover all baseline IDs exactly once")
            for row in rows:
                if row.get("state") not in STATES:
                    fail("Unsupported inherited matrix state")
                identity = identities[row["id"]]
                if row.get("stable_id") != identity["stable_id"]:
                    fail("Matrix stable identity disagrees with baseline")
                identity["evidence_dimensions"] = row
                identity["inherited_evidence"].append({"member": matrix_path, "sha256": files[matrix_path]["sha256"]})
            preserved[matrix_path] = archive.read(matrix_path)
        # Copy existing dossiers byte-for-byte. Their scoped tests remain scoped;
        # an exact copy never receives a new runtime/manual verification claim.
        dossier_paths = sorted(n for n in names if re.fullmatch(r"batch_\d+/evidence/fichas/\d{4}\.(?:json|md)", n))
        for member in dossier_paths:
            check_stop()
            data = archive.read(member)
            preserved[member] = data
            if not member.endswith(".json"):
                continue
            dossier = read_json(data)
            number = dossier.get("id") if isinstance(dossier, dict) else None
            if type(number) is not int or number not in identities or dossier.get("stable_id") != identities[number]["stable_id"]:
                fail("Inherited dossier identity mismatch: " + member)
            fields = dossier.get("fields")
            dimensions = dossier.get("evidence_dimensions")
            if not isinstance(fields, dict) or set(fields) != set(FIELDS) or not isinstance(dimensions, dict):
                fail("Inherited dossier must have the existing 21 fields: " + member)
            identities[number]["inherited_evidence"].append({"member": member, "sha256": sha(data)})
            if dimensions.get("manual_instruction_review") is True:
                verified_hashes = {v["sha256"] for v in identities[number]["variants"]}
                explicit_hashes = set(digest_values(fields[FIELDS[18]]))
                # Matrix original hash is an explicit, source-pinned manual scope.
                if dimensions.get("original_sha256") in verified_hashes:
                    explicit_hashes.add(dimensions["original_sha256"])
                for object_hash in verified_hashes & explicit_hashes:
                    ref = {"original_id": number, "member": member, "sha256": sha(data),
                           "scope": "INHERITED_MANUAL_INSTRUCTION_REVIEW_FOR_EXACT_OBJECT",
                           "provider_runtime_inherited": False,
                           "whole_capability_inherited": False}
                    if ref not in objects[object_hash]["inherited_manual_reviews"]:
                        objects[object_hash]["inherited_manual_reviews"].append(ref)
        preserved["catalog/INDEX_847_RECONCILED.json"] = archive.read("catalog/INDEX_847_RECONCILED.json")
        preserved["MANIFEST_SHA256.json"] = archive.read("MANIFEST_SHA256.json")
    return {"path": str(path.absolute()), "sha256": digest, "identities": identities,
            "artifacts": artifacts, "preserved": preserved}


def load_capture(root, source, expected_count, objects, metadata_objects):
    root = Path(root).absolute()
    raw = read_regular(root, "CAPTURE_MANIFEST.json", MAX_JSON_BYTES)
    manifest = read_json(raw)
    if not isinstance(manifest, dict) or manifest.get("format") != "kai.skill_capture/1" or manifest.get("source") != source:
        fail("Capture source/format mismatch: " + source)
    preserved = {"CAPTURE_MANIFEST.json": raw}
    integrity_verified = False
    if (root / "CAPTURE_INTEGRITY.json").exists():
        integrity_raw = read_regular(root, "CAPTURE_INTEGRITY.json", MAX_JSON_BYTES)
        integrity = read_json(integrity_raw)
        if not isinstance(integrity, dict) or integrity.get("format") != "kai.capture.integrity/1" or not isinstance(integrity.get("files"), dict):
            fail("Invalid capture integrity manifest")
        names = []
        for member in root.rglob("*"):
            check_stop()
            if member.is_symlink():
                fail("Symlink in capture tree")
            if member.is_file():
                names.append(member.relative_to(root).as_posix())
        validate_paths(names)
        if len(names) > MAX_ARCHIVE_FILES or set(integrity["files"]) != set(names) - {"CAPTURE_INTEGRITY.json"}:
            fail("Capture integrity manifest must cover every payload exactly once")
        for name, record in integrity["files"].items():
            check_blob(read_regular(root, name, MAX_JSON_BYTES), record, "capture " + name)
        preserved["CAPTURE_INTEGRITY.json"] = integrity_raw
        integrity_verified = True
    rows = manifest.get("rows")
    if type(expected_count) is not int or expected_count < 0 or not isinstance(rows, list) or len(rows) != expected_count:
        fail("Capture occurrence count mismatch: " + source)
    seen_ids, seen_uids, seen_paths, indices = set(), set(), set(), set()
    normalized_paths = defaultdict(list)
    for row in rows:
        check_stop()
        if not isinstance(row, dict):
            fail("Capture occurrence must be an object")
        index = row.get("index")
        if type(index) is not int or index < 1 or index in indices:
            fail("Capture indices must be positive and unique")
        indices.add(index)
        oid, uid, path = row.get("occurrence_id"), row.get("occurrence_uid"), row.get("path")
        device_path(path)
        if oid != f"{source}:{index:04d}" or uid != occurrence_uid(source, path):
            fail("Capture occurrence ID/UID disagrees with index/path")
        if oid in seen_ids or uid in seen_uids or path in seen_paths:
            fail("Duplicate capture occurrence or source path")
        seen_ids.add(oid); seen_uids.add(uid); seen_paths.add(path)
        normalized_paths[path_key(path)].append(oid)
        state = row.get("state")
        if state not in CAPTURE_STATES:
            fail("Unsupported capture state")
        require_digest(row.get("expected_sha256"), oid)
        require_size(row.get("expected_bytes"), oid)
        has_object = row.get("object_path") is not None
        if state == "CAPTURED" and not has_object:
            fail("CAPTURED occurrence has no byte object")
        if has_object:
            digest = require_digest(row.get("sha256"), oid)
            require_size(row.get("bytes"), oid)
            if row["object_path"] != f"objects/{digest}/SKILL.md":
                fail("Capture object path is not canonical content-addressed path")
            data = read_regular(root, row["object_path"])
            check_blob(data, row, oid)
            if state == "CAPTURED" and (digest != row["expected_sha256"] or len(data) != row["expected_bytes"]):
                fail("CAPTURED object changed since census without declaration")
            if state == "CHANGED_SINCE_CENSUS" and digest == row["expected_sha256"] and len(data) == row["expected_bytes"]:
                fail("CHANGED_SINCE_CENSUS record has unchanged bytes")
            add_object(objects, digest, data)
            objects[digest]["occurrence_uids"].append(uid)
        elif row.get("sha256") is not None or row.get("bytes") is not None:
            # A blocked read may have partial diagnostics, but never evidence of
            # a complete byte object; it cannot enter the object store.
            if state != "BLOCKED":
                fail("Hash/size without preserved byte object")
    if indices != set(range(1, expected_count + 1)):
        fail("Capture indices must cover the census exactly once")
    census_verified = False
    if "census_sha256" in manifest:
        census_digest = require_digest(manifest["census_sha256"], "census")
        census_raw = read_regular(root, "SOURCE_CENSUS.json", MAX_JSON_BYTES)
        if sha(census_raw) != census_digest:
            fail("Pinned SOURCE_CENSUS SHA256 mismatch")
        census = read_json(census_raw)
        entries = census.get("skills") if isinstance(census, dict) else None
        if not isinstance(entries, list) or len(entries) != expected_count:
            fail("SOURCE_CENSUS skill count mismatch")
        by_path = {}
        for entry in entries:
            if not isinstance(entry, dict):
                fail("Invalid census entry")
            path = entry.get("path")
            device_path(path)
            if path in by_path:
                fail("Duplicate SOURCE_CENSUS path")
            by_path[path] = (require_digest(entry.get("sha256"), "census entry"), require_size(entry.get("bytes"), "census entry"))
        for row in rows:
            if by_path.get(row["path"]) != (row["expected_sha256"], row["expected_bytes"]):
                fail("Capture occurrence does not match pinned SOURCE_CENSUS")
        preserved["SOURCE_CENSUS.json"] = census_raw
        census_verified = True
    clues = manifest.get("metadata_clues", [])
    if not isinstance(clues, list):
        fail("metadata_clues must be a list")
    clue_paths = set()
    for clue in clues:
        check_stop()
        if not isinstance(clue, dict):
            fail("Invalid metadata clue")
        path = device_path(clue.get("path"))
        if path in clue_paths:
            fail("Duplicate metadata clue path")
        clue_paths.add(path)
        if clue.get("state") == "CAPTURED":
            digest = require_digest(clue.get("sha256"), "metadata")
            require_size(clue.get("bytes"), "metadata")
            member = clue.get("object_path", f"metadata_objects/{digest}")
            if member != f"metadata_objects/{digest}":
                fail("Metadata object path is not canonical")
            data = read_regular(root, member, MAX_METADATA_BYTES)
            check_blob(data, clue, "metadata " + path)
            if digest in metadata_objects and metadata_objects[digest] != data:
                fail("Inconsistent metadata object")
            metadata_objects[digest] = data
    collisions = [values for values in normalized_paths.values() if len(values) > 1]
    return {"source": source, "root": str(root), "raw_manifest": raw, "manifest": manifest,
            "rows": rows, "metadata_clues": clues, "path_collisions": collisions,
            "preserved": preserved, "capture_integrity_manifest_verified": integrity_verified,
            "census_pin_verified": census_verified}


def plain_value(value, depth=0, budget=None):
    if budget is None:
        budget = [50000]
    budget[0] -= 1
    if budget[0] < 0 or depth > 24:
        raise ValueError("YAML structure limit exceeded")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, list):
        return [plain_value(v, depth + 1, budget) for v in value]
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return {k: plain_value(v, depth + 1, budget) for k, v in value.items()}
    raise ValueError("Unsupported/nonfinite YAML value; no implicit conversion performed")


def safe_yaml(data):
    if yaml is None:
        raise ValueError("PyYAML unavailable; frontmatter has not been parsed")
    if len(data.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        raise ValueError("Frontmatter inspection limit exceeded")
    for token in yaml.scan(data):
        if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken, yaml.tokens.TagToken)):
            raise ValueError("YAML aliases, anchors and explicit tags are not accepted")

    class UniqueSafeLoader(yaml.SafeLoader):
        pass

    def unique_mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("Duplicate or non-string YAML mapping key")
            result[key] = loader.construct_object(value_node, deep=deep)
        return result

    UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
    result = yaml.load(data, Loader=UniqueSafeLoader)
    if not isinstance(result, dict):
        raise ValueError("Frontmatter must be a mapping")
    return plain_value(result)


def static_inspect(data):
    findings, metadata = [], {}
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError:
        return {"parse_ok": False, "frontmatter": {}, "name": None, "description": None,
                "findings": [{"code": "INVALID_UTF8", "severity": "BLOCKING"}],
                "resources": [], "resource_declarations_seen": 0, "resources_truncated": False,
                "risk_indicators": [], "urls_declared": [], "lines": None}
    if "\x00" in text:
        findings.append({"code": "NUL_IN_TEXT", "severity": "BLOCKING"})
    lines = text.splitlines()
    parse_ok = True
    if not lines or lines[0].strip() != "---":
        findings.append({"code": "MISSING_FRONTMATTER", "severity": "WARNING"})
    else:
        end = next((i for i in range(1, min(len(lines), 2001)) if lines[i].strip() in ("---", "...")), None)
        if end is None:
            parse_ok = False
            findings.append({"code": "UNTERMINATED_FRONTMATTER", "severity": "BLOCKING"})
        else:
            try:
                metadata = safe_yaml("\n".join(lines[1:end]))
            except Exception as exc:
                # Parser errors are data findings, never instructions to execute.
                parse_ok = False
                findings.append({"code": "UNSAFE_OR_INVALID_YAML", "severity": "BLOCKING",
                                 "detail": str(exc)[:500]})
    for field in ("name", "description"):
        if field in metadata and not isinstance(metadata[field], str):
            findings.append({"code": "NONSTRING_" + field.upper(), "severity": "WARNING"})
    resources = {}
    # Markdown destinations plus conventional auxiliary paths in backticks/plain
    # text are declarations only; no filesystem lookup or URL fetch follows.
    token_re = re.compile(r"\]\(([^)\n]+)\)|\b(skill[s]?://[^\s<>)`\]\"']+)|(?<![\w/])((?:scripts?|references?|assets?|templates?|examples?|data|runtime|lib|tests?)/[^\s<>`\]\"')]+)")
    resource_count = 0
    for number, line in enumerate(lines, 1):
        for match in token_re.finditer(line):
            value = next(x for x in match.groups() if x is not None).strip().strip("<>")
            if " " in value and not value.startswith(("http://", "https://")):
                value = value.split(" ", 1)[0]
            if value.startswith("#"):
                continue
            resource_count += 1
            if value in resources or len(resources) >= MAX_DECLARATIONS:
                continue
            if value.startswith(("https://", "http://")):
                kind = "EXTERNAL_URL_DECLARED_NOT_FETCHED"
            elif re.match(r"skills?://", value):
                kind = "SKILL_URI_DECLARED_NOT_RESOLVED"
            elif value.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", value):
                kind = "ABSOLUTE_PATH_DECLARED_NOT_READ"
            elif any(p == ".." for p in value.replace("\\", "/").split("/")):
                kind = "PARENT_PATH_DECLARED_NOT_READ"
            else:
                kind = "RELATIVE_RESOURCE_DECLARED_NOT_CAPTURED"
            resources[value] = {"declaration": value, "line": number, "kind": kind,
                                "device_availability": "NOT_CAPTURED_OR_TESTED"}
    if resource_count > MAX_DECLARATIONS:
        findings.append({"code": "DECLARATION_LIMIT_EXCEEDED", "severity": "WARNING",
                         "seen": resource_count, "retained_unique_limit": MAX_DECLARATIONS})
    risk_patterns = {
        "REMOTE_SHELL_PIPE": r"(?:curl|wget).{0,240}\|\s*(?:ba)?sh\b",
        "DESTRUCTIVE_COMMAND_DECLARATION": r"\brm\s+-[a-zA-Z]*[rf]|\b(?:format|mkfs|diskpart)\b",
        "PRIVILEGED_COMMAND_DECLARATION": r"\bsudo\b|\bchmod\s+777\b",
        "CREDENTIAL_OR_SECRET_HANDLING": r"(?i)\b(?:api[_ -]?key|token|secret|password|credential|private[_ -]?key)\b",
        "EXTERNAL_WRITE_OR_PUBLISH": r"(?i)\b(?:publish|deploy|send email|git push|delete account)\b",
        "INSTRUCTION_OVERRIDE_LANGUAGE": r"(?i)ignore (?:all |previous |prior )?instructions|system prompt",
    }
    risks = []
    for category, pattern in risk_patterns.items():
        matches = [i for i, line in enumerate(lines, 1) if re.search(pattern, line)]
        if matches:
            risks.append({"category": category, "lines": matches[:64], "lines_truncated": len(matches) > 64,
                          "interpretation": "STATIC_INDICATOR_NOT_VULNERABILITY_PROOF"})
    urls = sorted(set(re.findall(r"https?://[^\s<>`\]\"')]+", text)))
    if any(f["severity"] == "BLOCKING" for f in findings):
        parse_ok = False
    return {"parse_ok": parse_ok, "frontmatter": metadata,
            "name": metadata.get("name") if isinstance(metadata.get("name"), str) else None,
            "description": metadata.get("description") if isinstance(metadata.get("description"), str) else None,
            "findings": findings, "resources": list(resources.values()),
            "resource_declarations_seen": resource_count, "resources_truncated": resource_count > MAX_DECLARATIONS,
            "risk_indicators": risks, "urls_declared": urls[:256], "urls_truncated": len(urls) > 256,
            "lines": len(lines)}


def metadata_scope(path):
    path = device_path(path)
    parent = path.rsplit("/", 1)[0]
    if parent.rsplit("/", 1)[-1] in (".claude-plugin", ".codex-plugin", ".plugin"):
        parent = parent.rsplit("/", 1)[0]
    return parent


def scoped_metadata(path, clues, metadata_objects):
    path = device_path(path)
    refs, facts = [], []
    for clue in clues:
        scope = metadata_scope(clue["path"])
        if not path.startswith(scope + "/"):
            continue
        ref = {k: clue.get(k) for k in ("path", "kind", "state", "sha256", "bytes")}
        refs.append(ref)
        digest = clue.get("sha256")
        if clue.get("state") != "CAPTURED" or digest not in metadata_objects or not clue["path"].lower().endswith(".json"):
            continue
        try:
            value = read_json(metadata_objects[digest])
        except RegistryError:
            continue
        if not isinstance(value, dict):
            continue
        declaration = {}
        for field in ("name", "version", "license", "homepage", "namespace", "provider", "repository"):
            val = value.get(field)
            if isinstance(val, str):
                declaration[field] = val
            elif field == "repository" and isinstance(val, dict) and isinstance(val.get("url"), str):
                declaration[field] = val["url"]
        if declaration:
            facts.append({"declared": declaration, "evidence_path": clue["path"], "sha256": digest,
                          "scope": scope, "certainty": "DECLARED_NOT_UPSTREAM_VERIFIED"})
    return refs, facts


def associate(inspection, row, objects, identities):
    digest = row.get("sha256") if row.get("object_path") else None
    hints = namespace_hints(row["path"])
    metadata = inspection.get("frontmatter", {})
    uri = metadata.get("uri") or metadata.get("source_uri")
    if isinstance(uri, str):
        match = re.fullmatch(r"skills?://plugins/([^/\s]+)/([^/\s]+)", uri)
        if match:
            hints.append({"namespace": match[1], "name": match[2], "kind": "DECLARED_SKILL_URI",
                          "certainty": "DECLARED_NOT_PROVIDER_VERIFIED"})
    candidates = sorted({a["original_id"] for a in objects[digest]["baseline_artifacts"]}) if digest in objects else []
    matched = []
    reason = "NO_VERIFIED_BASELINE_OBJECT_MATCH"
    if candidates:
        candidate_pairs = {(identities[i]["namespace"], identities[i]["name"]) for i in candidates}
        hint_pairs = {(h["namespace"], h["name"]) for h in hints}
        hinted = {i for i in candidates for h in hints
                  if h["namespace"] == identities[i]["namespace"] and h["name"] == identities[i]["name"]}
        conflicting = bool(hint_pairs - candidate_pairs)
        if conflicting:
            reason = "EXACT_OBJECT_WITH_CONFLICTING_NAMESPACE_HINT_REQUIRES_REVIEW"
        elif len(hinted) == 1:
            matched = sorted(hinted)
            reason = "EXACT_VERIFIED_OBJECT_AND_NAMESPACE_HINT"
        elif len(candidates) == 1:
            matched = candidates
            reason = "EXACT_VERIFIED_OBJECT_UNIQUE_BASELINE_IDENTITY"
        else:
            reason = "EXACT_OBJECT_AMBIGUOUS_BASELINE_IDENTITY_REQUIRES_REVIEW"
    name = inspection.get("name")
    name_candidates = sorted(i for i, ident in identities.items() if name and ident["name"] == name)
    hinted_candidates = sorted({i for i, ident in identities.items() for h in hints
                                if (ident["namespace"], ident["name"]) == (h["namespace"], h["name"])})
    return {"matched_original_ids": matched, "exact_hash_candidate_original_ids": candidates,
            "namespace_name_candidate_original_ids": hinted_candidates,
            "same_name_candidate_original_ids": name_candidates,
            "association_basis": reason, "namespace_hints": hints,
            "identity_confirmed": bool(matched), "new_capability_claimed": False}


def make_dossier(row, source, inspection, association, metadata_refs, metadata_facts, objects):
    has_object = bool(row.get("object_path"))
    object_hash = row.get("sha256") if has_object else None
    object_record = objects.get(object_hash, {})
    state = "INSPECTED" if has_object and inspection["parse_ok"] and row["state"] == "CAPTURED" else "BLOCKED"
    uncertainty = []
    if not association["identity_confirmed"]:
        uncertainty.append("Canonical identity is unresolved; name/path hints do not establish an identity")
    if row["state"] != "CAPTURED":
        uncertainty.append("Capture is " + row["state"] + "; census expected hash remains distinct from actual bytes")
    uncertainty.extend(["Auxiliary resources of this device occurrence were not captured/tested",
                        "Provider, license, upstream freshness and runtime behavior are not independently verified"])
    dimensions = {"capture_integrity_verified": has_object, "census_match": row["state"] == "CAPTURED",
                  "automated_static_inspected": has_object, "inspection_grade": "AUTOMATED_STATIC_ONLY" if has_object else "NO_BYTE_INSPECTION",
                  "manual_instruction_review": False, "new_manual_review_performed": False,
                  "provider_runtime_tested": False, "offline_component_tested": False,
                  "whole_capability_verified": False,
                  "inherited_exact_object_reviews": object_record.get("inherited_manual_reviews", [])}
    frontmatter = inspection.get("frontmatter", {})
    declarations = {k: frontmatter.get(k) for k in ("version", "license", "provider", "upstream", "repository") if k in frontmatter}
    fields = {key: PENDING for key in FIELDS}
    fields.update({
        FIELDS[0]: {"occurrence_id": row["occurrence_id"], "occurrence_uid": row["occurrence_uid"],
                    "source": source, "device_path_literal": row["path"], "declared_name": inspection.get("name"),
                    "identity_association": association, "metadata_evidence": metadata_refs},
        FIELDS[1]: {"state": state, "frontmatter_declarations": declarations,
                    "scoped_metadata_declarations": metadata_facts, "license_clearance": "NOT_ESTABLISHED_BY_THIS_TOOL"},
        FIELDS[2]: {"description_declared": inspection.get("description"), "functional_understanding": PENDING},
        FIELDS[3]: {"declared_description": inspection.get("description"), "activation_tested": False},
        FIELDS[4]: {"input_preserved": "Exact SKILL.md bytes when capture object is available", "input_output_contract": PENDING},
        FIELDS[5]: {"resources_declared": inspection.get("resources", []),
                    "declarations_seen": inspection.get("resource_declarations_seen", 0),
                    "declarations_truncated": inspection.get("resources_truncated", False),
                    "metadata_objects_verified": metadata_refs,
                    "device_auxiliary_resources": "NOT_CAPTURED", "transitive_closure": "NOT_VERIFIED",
                    "baseline_exact_object_artifacts": object_record.get("baseline_artifacts", [])},
        FIELDS[6]: {"dependencies_permissions": PENDING, "network_or_command_indicators": inspection.get("risk_indicators", [])},
        FIELDS[7]: {"frontmatter_parsed_as_data": frontmatter, "implementation_execution": "NEVER_EXECUTED", "architecture": PENDING},
        FIELDS[8]: {"ChatGPT": "NOT_TESTED", "Work": "NOT_TESTED", "Termux_Android": "NOT_TESTED", "PC_Asier": "NOT_TESTED"},
        FIELDS[9]: {"static_risk_indicators": inspection.get("risk_indicators", []), "semantic_security_review": PENDING,
                    "input_handling": "Data only; no recovered instructions, scripts or URLs were executed/fetched"},
        FIELDS[10]: {"automated_findings": inspection.get("findings", []), "manual_findings": []},
        FIELDS[11]: {"exact_object_shared_occurrence_count": len(object_record.get("occurrence_uids", [])),
                     "exact_object_occurrences_sample": object_record.get("occurrence_uids", [])[:16],
                     "sample_truncated": len(object_record.get("occurrence_uids", [])) > 16,
                     "full_occurrence_list_reference": "OBJECT_INDEX.json" if object_hash else None,
                     "baseline_hash_matches": association["exact_hash_candidate_original_ids"],
                     "same_name_only_is_not_a_merge": True, "new_capability_claimed": False},
        FIELDS[12]: {"text_lines": inspection.get("lines"), "manual_documentation_review": False},
        FIELDS[13]: {"urls_declared_not_fetched": inspection.get("urls_declared", []), "upstream_check": "NOT_PERFORMED"},
        FIELDS[14]: {"alternatives_and_composition": PENDING, "deduplication": "Only byte-identical objects are stored once; each occurrence is retained"},
        FIELDS[15]: {"next_proposal": "Review the unique-object queue and supporting resources before any improvement or deployment"},
        FIELDS[16]: {"content_modifications": [], "original_bytes_modified": False},
        FIELDS[17]: dimensions,
        FIELDS[18]: {"expected_sha256": row["expected_sha256"], "expected_bytes": row["expected_bytes"],
                     "actual_sha256": object_hash, "actual_bytes": row.get("bytes") if has_object else None,
                     "object_path": f"objects/{object_hash}/SKILL.md" if has_object else None,
                     "capture_state": row["state"]},
        FIELDS[19]: {"installation": "NOT_INSTALLED", "recovery": "Preserved source bytes and manifest; generated output is separate"},
        FIELDS[20]: {"state": state, "inspection_grade": dimensions["inspection_grade"],
                     "whole_capability_verified": False, "uncertainty": uncertainty,
                     "next_action": "Resolve capture/parse blocker" if state == "BLOCKED" else "Manual review of unique object and uncaptured resources"},
    })
    return {"format": "kai.skill_occurrence_dossier/1", "occurrence_id": row["occurrence_id"],
            "occurrence_uid": row["occurrence_uid"], "state": state, "uncertainty": uncertainty,
            "evidence_dimensions": dimensions, "fields": fields}


def markdown_dossier(dossier):
    # JSON blocks keep untrusted Markdown/HTML/instructions inert in generated MD.
    lines = ["# Ficha de ocurrencia " + dossier["occurrence_id"], "",
             "Inspección automática estática. Evidencia heredada conserva su alcance; no hay ejecución de la skill.", ""]
    if dossier.get("manual_object_reviews"):
        lines.extend(["Existe revisión manual de instrucciones del objeto idéntico en las referencias de la ficha. "
                      "La revisión de auxiliares y cualquier prueba conserva su ámbito por ocurrencia.", ""])
    for field in FIELDS:
        value = json.dumps(dossier["fields"][field], ensure_ascii=False, indent=2, allow_nan=False)
        # A fence longer than all input runs prevents content from escaping it.
        runs = [len(x) for x in re.findall(r"`+", value)]
        fence = "`" * max(3, max(runs, default=0) + 1)
        lines.extend(["## " + field, "", fence + "json", value, fence, ""])
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_new(root, relative, data, files):
    check_stop()
    safe_relative(relative)
    target = root.joinpath(*PurePosixPath(relative).parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    check_stop()
    with target.open("xb") as handle:
        handle.write(data)
    files[relative] = {"sha256": sha(data), "bytes": len(data)}


@cooperative_stop
def build_registry(baseline_path, capture_pc, capture_termux, output, *, baseline_sha256=BASELINE_SHA256,
                   expected_originals=847, expected_pc=723, expected_termux=3659):
    requested_output = Path(output).absolute()
    if requested_output.exists() or requested_output.is_symlink():
        fail("Output must be a new directory")
    output = requested_output.resolve(strict=False)
    for input_path in (Path(baseline_path).resolve(), Path(capture_pc).resolve(), Path(capture_termux).resolve()):
        if output == input_path or output in input_path.parents or input_path in output.parents:
            fail("Output must be separate from all inputs")
    objects, metadata_objects = {}, {}
    baseline = load_baseline(baseline_path, baseline_sha256, expected_originals, objects)
    captures = [load_capture(capture_pc, "pc-asier", expected_pc, objects, metadata_objects),
                load_capture(capture_termux, "termux", expected_termux, objects, metadata_objects)]
    identities = baseline["identities"]
    for obj in objects.values():
        check_stop()
        obj["inspection"] = static_inspect(obj["data"])
    occurrence_rows, dossiers = [], []
    variant_groups, declared_names = defaultdict(lambda: {"original_ids": set(), "object_sha256": set(), "occurrence_uids": set(), "evidence": []}), defaultdict(set)
    for ident in identities.values():
        key = ident["namespace"] + ":" + ident["name"]
        group = variant_groups[key]
        group["original_ids"].add(ident["id"])
        group["object_sha256"].update(v["sha256"] for v in ident["variants"])
    for capture in captures:
        for row in sorted(capture["rows"], key=lambda r: r["index"]):
            check_stop()
            digest = row.get("sha256") if row.get("object_path") else None
            inspection = objects[digest]["inspection"] if digest in objects else {"parse_ok": False}
            association = associate(inspection, row, objects, identities)
            refs, facts = scoped_metadata(row["path"], capture["metadata_clues"], metadata_objects)
            dossier = make_dossier(row, capture["source"], inspection, association, refs, facts, objects)
            stem = capture["source"] + "/" + f"{row['index']:04d}"
            occurrence = {"occurrence_id": row["occurrence_id"], "occurrence_uid": row["occurrence_uid"],
                          "source": capture["source"], "index": row["index"], "path": row["path"],
                          "capture_record": row, "sha256": digest, "state": dossier["state"],
                          "association": association, "dossier_json": "fichas/" + stem + ".json",
                          "dossier_md": "fichas/" + stem + ".md"}
            occurrence_rows.append(occurrence)
            dossiers.append((occurrence, dossier))
            if digest and inspection.get("name"):
                declared_names[path_key(inspection["name"])].add(digest)
            for hint in association["namespace_hints"]:
                key = hint["namespace"] + ":" + hint["name"]
                group = variant_groups[key]
                if digest:
                    group["object_sha256"].add(digest)
                group["occurrence_uids"].add(row["occurrence_uid"])
                group["evidence"].append({"occurrence_uid": row["occurrence_uid"], "kind": hint["kind"]})
    all_oids = [r["occurrence_id"] for r in occurrence_rows]
    all_uids = [r["occurrence_uid"] for r in occurrence_rows]
    if len(all_oids) != len(set(all_oids)) or len(all_uids) != len(set(all_uids)):
        fail("Cross-capture occurrence identity collision")
    object_rows, queue = [], []
    for digest, obj in sorted(objects.items()):
        check_stop()
        record = {"sha256": digest, "bytes": len(obj["data"]), "path": f"objects/{digest}/SKILL.md",
                  "baseline_artifacts": obj["baseline_artifacts"], "occurrence_uids": sorted(obj["occurrence_uids"]),
                  "new_occurrence_count": len(obj["occurrence_uids"]),
                  "inherited_manual_reviews": obj["inherited_manual_reviews"],
                  "inspection_json": f"inspections/{digest}.json"}
        object_rows.append(record)
        if not obj["inherited_manual_reviews"]:
            queue.append({"sha256": digest, "bytes": len(obj["data"]),
                          "occurrence_uids": sorted(obj["occurrence_uids"]),
                          "original_ids": sorted({a["original_id"] for a in obj["baseline_artifacts"]}),
                          "review_state": "INSPECTED" if obj["inspection"]["parse_ok"] else "BLOCKED",
                          "inspection_grade": "AUTOMATED_STATIC_ONLY", "manual_review": False,
                          "findings": obj["inspection"]["findings"], "next_action": "Review instructions and supporting resources without executing recovered content"})
    variants = [{"namespace_name_hint": key, "original_ids": sorted(g["original_ids"]),
                 "object_sha256": sorted(g["object_sha256"]), "occurrence_uids": sorted(g["occurrence_uids"]),
                 "different_byte_revisions": len(g["object_sha256"]) > 1,
                 "relationship": "CANDIDATE_VARIANT_FAMILY_NOT_AUTOMATIC_IDENTITY_MERGE", "evidence": g["evidence"]}
                for key, g in sorted(variant_groups.items())]
    clones = [{"sha256": r["sha256"], "occurrence_uids": r["occurrence_uids"],
               "original_ids": sorted({a["original_id"] for a in r["baseline_artifacts"]})}
              for r in object_rows if r["new_occurrence_count"] > 1 or (r["new_occurrence_count"] and r["baseline_artifacts"])]
    name_collisions = [{"normalized_declared_name": n, "distinct_hashes": sorted(h),
                        "resolution": "DO_NOT_MERGE_BY_NAME"} for n, h in sorted(declared_names.items()) if len(h) > 1]
    graph_nodes = ([{"id": "original:" + str(i), "kind": "BASELINE_IDENTITY", "stable_id": ident["stable_id"]}
                    for i, ident in sorted(identities.items())]
                   + [{"id": "sha256:" + d, "kind": "BYTE_OBJECT"} for d in sorted(objects)]
                   + [{"id": r["occurrence_uid"], "kind": "DEVICE_OCCURRENCE", "occurrence_id": r["occurrence_id"]} for r in occurrence_rows])
    graph_edges = []
    for digest, obj in objects.items():
        for a in obj["baseline_artifacts"]:
            graph_edges.append({"from": "original:" + str(a["original_id"]), "to": "sha256:" + digest,
                                "relation": "VERIFIED_BASELINE_ARTIFACT", "role": a["role"], "member": a["member"]})
    for row in occurrence_rows:
        check_stop()
        if row["sha256"]:
            graph_edges.append({"from": row["occurrence_uid"], "to": "sha256:" + row["sha256"], "relation": "EXACT_CAPTURED_BYTES"})
        for number in row["association"]["matched_original_ids"]:
            graph_edges.append({"from": row["occurrence_uid"], "to": "original:" + str(number),
                                "relation": "EXACT_VERIFIED_OBJECT_ASSOCIATION", "basis": row["association"]["association_basis"]})
    # Resource declarations belong to a byte object. Occurrences inherit this
    # graph through their exact-byte edge, avoiding quadratic clone expansion.
    for digest, obj in sorted(objects.items()):
        check_stop()
        for resource in obj["inspection"].get("resources", []):
            rid = "declaration:" + sha((digest + "\0" + resource["declaration"]).encode("utf-8"))
            graph_nodes.append({"id": rid, "kind": "RESOURCE_DECLARATION", "declaration": resource["declaration"],
                                "resolution": "DECLARED_NOT_CAPTURED_OR_TESTED"})
            graph_edges.append({"from": "sha256:" + digest, "to": rid, "relation": "DECLARES_RESOURCE"})
    capture_counts = {c["source"]: dict(Counter(r["state"] for r in c["rows"])) for c in captures}
    new_hashes = {r["sha256"] for r in occurrence_rows if r["sha256"]}
    baseline_hashes = {a["sha256"] for a in baseline["artifacts"]}
    summary = {"format": "kai.skill_union_summary/1", "baseline_sha256": baseline["sha256"],
               "baseline_identities_preserved": len(identities), "baseline_artifact_occurrences": len(baseline["artifacts"]),
               "new_device_occurrences": len(occurrence_rows), "expected_occurrences": expected_pc + expected_termux,
               "occurrences_by_source_capture_state": capture_counts,
               "occurrence_workflow_states": dict(Counter(r["state"] for r in occurrence_rows)),
               "unique_byte_objects_total": len(objects), "unique_objects_in_new_captures": len(new_hashes),
               "unique_objects_novel_to_baseline": len(new_hashes - baseline_hashes),
               "new_occurrences_matching_baseline_objects": sum(bool(r["association"]["exact_hash_candidate_original_ids"]) for r in occurrence_rows),
               "new_occurrences_associated_to_original_identity": sum(bool(r["association"]["matched_original_ids"]) for r in occurrence_rows),
               "new_occurrences_without_preserved_bytes": sum(r["sha256"] is None for r in occurrence_rows),
               "exact_object_clone_groups": len(clones), "candidate_variant_families": len(variants),
               "different_revision_families": sum(v["different_byte_revisions"] for v in variants),
               "declared_name_collision_groups": len(name_collisions),
               "normalized_device_path_collision_groups": sum(len(c["path_collisions"]) for c in captures),
               "unique_objects_pending_manual_review": len(queue),
               "unique_new_capture_objects_pending_manual_review": sum(q["sha256"] in new_hashes for q in queue),
               "unique_objects_with_inherited_scoped_manual_review": sum(bool(o["inherited_manual_reviews"]) for o in objects.values()),
               "new_manual_reviews_performed": 0, "new_runtime_tests_performed": 0,
               "new_confirmed_capabilities_claimed": 0, "whole_registry_verified": False,
               "claim_scope": "BYTE_INTEGRITY_AND_AUTOMATED_STATIC_INVENTORY_ONLY",
               "uncertainty": ["Object count is not identity/capability count", "Path and name clues do not establish new identities",
                               "Exact copies do not establish runtime equivalence of environments", "Auxiliary device resources are not captured"]}
    # All input and semantic checks finish before creating the separate output.
    check_stop()
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for relative, data in sorted(baseline["preserved"].items()):
        write_new(output, "inherited_evidence/" + relative, data, files)
    for capture in captures:
        for name, data in capture["preserved"].items():
            write_new(output, f"provenance/{capture['source']}/" + name, data, files)
    for digest, data in sorted(metadata_objects.items()):
        write_new(output, "metadata_objects/" + digest, data, files)
    for digest, obj in sorted(objects.items()):
        write_new(output, f"objects/{digest}/SKILL.md", obj["data"], files)
        write_new(output, f"inspections/{digest}.json", json_bytes(obj["inspection"]), files)
    for occurrence, dossier in dossiers:
        write_new(output, occurrence["dossier_json"], json_bytes(dossier), files)
        write_new(output, occurrence["dossier_md"], markdown_dossier(dossier), files)
    documents = {
        "IDENTITIES_847.json": {"format": "kai.skill_original_identities/1", "rows": [identities[i] for i in sorted(identities)]},
        "OCCURRENCE_INDEX.json": {"format": "kai.skill_occurrences/1", "rows": occurrence_rows},
        "OBJECT_INDEX.json": {"format": "kai.skill_byte_objects/1", "rows": object_rows},
        "VARIANT_INDEX.json": {"format": "kai.skill_variant_candidates/1", "families": variants, "exact_object_clones": clones,
                               "declared_name_collisions": name_collisions,
                               "device_path_collisions": {c["source"]: c["path_collisions"] for c in captures}},
        "REVIEW_QUEUE.json": {"format": "kai.skill_unique_object_review_queue/1", "scope": "UNIQUE_OBJECTS_WITHOUT_INHERITED_MANUAL_REVIEW", "rows": queue},
        "DEPENDENCY_GRAPH.json": {"format": "kai.skill_union_graph/1", "nodes": graph_nodes, "edges": graph_edges,
                                  "scope": "VERIFIED_BYTES_AND_DECLARED_RESOURCES_NOT_RUNTIME_DEPENDENCY_CLOSURE"},
        "SUMMARY.json": summary,
        "BUILD_INPUTS.json": {"format": "kai.skill_union_inputs/1", "baseline": {k: baseline[k] for k in ("path", "sha256")},
                              "captures": [{"source": c["source"], "root": c["root"], "manifest_sha256": sha(c["raw_manifest"]),
                                            "capture_integrity_manifest_verified": c["capture_integrity_manifest_verified"],
                                            "census_pin_verified": c["census_pin_verified"],
                                            "resources_scope": c["manifest"].get("resources_scope")} for c in captures],
                              "expected_counts": {"originals": expected_originals, "pc-asier": expected_pc, "termux": expected_termux},
                              "execution_policy": "DATA_ONLY_NO_RECOVERED_CODE_OR_INSTRUCTIONS_EXECUTED"},
    }
    for relative, document in documents.items():
        write_new(output, relative, json_bytes(document), files)
    summary_md = ("# Unión offline de skills\n\n"
                  f"Identidades originales conservadas: {len(identities)}. Ocurrencias nuevas: {len(occurrence_rows)}. "
                  f"Objetos byte únicos: {len(objects)}; objetos de capturas ajenos al baseline: {len(new_hashes - baseline_hashes)}.\n\n"
                  f"Objetos pendientes de revisión manual: {len(queue)}. Cada ocurrencia conserva ficha propia de 21 campos.\n\n"
                  "El estado INSPECTED significa inspección automática estática. No se ejecutaron skills ni recursos. "
                  "Las fichas heredadas conservan su alcance; una copia exacta no acredita pruebas de runtime. "
                  "Ningún objeto nuevo se cuenta como capacidad nueva confirmada.\n")
    write_new(output, "SUMMARY.md", summary_md.encode("utf-8"), files)
    manifest = {"format": "kai.skill_union_integrity/1", "files": files, "summary_sha256": files["SUMMARY.json"]["sha256"],
                "self_excluded": "MANIFEST_SHA256.json", "claim": "OUTPUT_FILE_INTEGRITY_ONLY"}
    # The manifest cannot hash itself; verification checks its exact schema and
    # every other output file. This is not a global capability VERIFIED claim.
    check_stop()
    with (output / "MANIFEST_SHA256.json").open("xb") as handle:
        check_stop()
        handle.write(json_bytes(manifest))
    verify_registry(output)
    return summary


def verify_preserved_captures(root, inputs, occurrences, object_map):
    by_source = defaultdict(dict)
    for row in occurrences:
        by_source[row["source"]][row["occurrence_id"]] = row
    captures = inputs.get("captures", [])
    if len(captures) != 2 or {c.get("source") for c in captures} != {"pc-asier", "termux"}:
        fail("Preserved capture sources lost or duplicated")
    for capture in captures:
        source = capture["source"]
        prefix = f"provenance/{source}/"
        raw = read_regular(root, prefix + "CAPTURE_MANIFEST.json", MAX_JSON_BYTES)
        if sha(raw) != capture.get("manifest_sha256"):
            fail("Preserved capture manifest pin mismatch")
        manifest = read_json(raw)
        if manifest.get("format") != "kai.skill_capture/1" or manifest.get("source") != source:
            fail("Preserved capture source/format mismatch")
        rows = manifest.get("rows")
        if not isinstance(rows, list) or len(rows) != inputs["expected_counts"][source]:
            fail("Preserved capture occurrence count mismatch")
        if len({r["occurrence_id"] for r in rows}) != len(rows):
            fail("Duplicate occurrence in preserved capture")
        for row in rows:
            check_stop()
            current = by_source[source].get(row["occurrence_id"])
            if current is None or current["capture_record"] != row or current["path"] != row["path"]:
                fail("Occurrence differs from preserved capture manifest")
            if (row.get("state") not in CAPTURE_STATES or row["occurrence_id"] != f"{source}:{row['index']:04d}"
                    or row["occurrence_uid"] != occurrence_uid(source, row["path"])):
                fail("Preserved capture state/identity mismatch")
            if row.get("object_path"):
                digest = row.get("sha256")
                if digest not in object_map or row["object_path"] != f"objects/{digest}/SKILL.md":
                    fail("Preserved capture lost exact byte object")
                if row["bytes"] != object_map[digest]["bytes"]:
                    fail("Preserved capture object byte count mismatch")
                if row["state"] == "CAPTURED" and (row["sha256"], row["bytes"]) != (row["expected_sha256"], row["expected_bytes"]):
                    fail("Preserved CAPTURED object does not match census")
        if "census_sha256" in manifest:
            census_raw = read_regular(root, prefix + "SOURCE_CENSUS.json", MAX_JSON_BYTES)
            if sha(census_raw) != manifest["census_sha256"]:
                fail("Preserved SOURCE_CENSUS pin mismatch")
            census = read_json(census_raw)
            entries = census.get("skills") if isinstance(census, dict) else None
            if not isinstance(entries, list) or len(entries) != len(rows):
                fail("Preserved census count mismatch")
            census_map = {e["path"]: (e["sha256"], e["bytes"]) for e in entries}
            if len(census_map) != len(entries):
                fail("Duplicate path in preserved census")
            if any(census_map.get(r["path"]) != (r["expected_sha256"], r["expected_bytes"]) for r in rows):
                fail("Preserved census/occurrence path-hash-size mismatch")
        elif capture.get("census_pin_verified"):
            fail("Census verification claimed without a preserved census pin")
        if capture.get("capture_integrity_manifest_verified"):
            integrity = read_json(read_regular(root, prefix + "CAPTURE_INTEGRITY.json", MAX_JSON_BYTES))
            if integrity.get("format") != "kai.capture.integrity/1" or not isinstance(integrity.get("files"), dict):
                fail("Invalid preserved capture integrity manifest")
            for member, record in integrity["files"].items():
                safe_relative(member)
                target = member if member.startswith(("objects/", "metadata_objects/")) else prefix + member
                check_blob(read_regular(root, target, MAX_JSON_BYTES), record, "preserved capture " + member)


@cooperative_stop
def verify_registry(root):
    root = Path(root).absolute()
    manifest = read_json(read_regular(root, "MANIFEST_SHA256.json", MAX_JSON_BYTES))
    if isinstance(manifest, dict) and manifest.get("format") == "kai.skill_union_collection/1":
        if {p.name for p in root.iterdir()} != {"base", "overlay_evidence", "MANIFEST_SHA256.json"}:
            fail("Unexpected collection entry")
        if (sha(read_regular(root, "base/MANIFEST_SHA256.json", MAX_JSON_BYTES)) != manifest.get("base_manifest_sha256")
                or sha(read_regular(root, "overlay_evidence/MANIFEST_SHA256.json", MAX_JSON_BYTES)) != manifest.get("overlay_manifest_sha256")):
            fail("Collection child manifest hash mismatch")
        return {"integrity": "PASS", "base": verify_registry(root / "base"),
                "overlay": verify_overlay(root / "base", root / "overlay_evidence", verify_base=False),
                "scope": "OUTPUT_INTEGRITY_NOT_CAPABILITY_VERIFICATION"}
    if not isinstance(manifest, dict) or manifest.get("format") != "kai.skill_union_integrity/1":
        fail("Unsupported union integrity manifest")
    files = manifest.get("files")
    if not isinstance(files, dict) or "MANIFEST_SHA256.json" in files:
        fail("Invalid output integrity manifest")
    names = []
    for path in root.rglob("*"):
        check_stop()
        if path.is_symlink():
            fail("Symlink in output tree")
        if path.is_file():
            names.append(path.relative_to(root).as_posix())
    validate_paths(names)
    if set(names) != set(files) | {"MANIFEST_SHA256.json"}:
        fail("Output has lost or extra files")
    for name, record in files.items():
        check_blob(read_regular(root, name, MAX_ARCHIVE_BYTES), record, name)
    summary = read_json(read_regular(root, "SUMMARY.json", MAX_JSON_BYTES))
    occurrences = read_json(read_regular(root, "OCCURRENCE_INDEX.json", MAX_JSON_BYTES))["rows"]
    identities = read_json(read_regular(root, "IDENTITIES_847.json", MAX_JSON_BYTES))["rows"]
    objects = read_json(read_regular(root, "OBJECT_INDEX.json", MAX_JSON_BYTES))["rows"]
    inputs = read_json(read_regular(root, "BUILD_INPUTS.json", MAX_JSON_BYTES))
    expected = inputs["expected_counts"]
    if summary.get("whole_registry_verified") is not False or summary.get("new_confirmed_capabilities_claimed") != 0:
        fail("Unsupported automatic global capability claim")
    if summary.get("new_device_occurrences") != len(occurrences) or len(occurrences) != expected["pc-asier"] + expected["termux"]:
        fail("Occurrence counts disagree")
    if len(identities) != expected["originals"] or {r.get("id") for r in identities} != set(range(1, len(identities) + 1)):
        fail("Original identities lost or duplicated")
    if len({r["occurrence_id"] for r in occurrences}) != len(occurrences) or len({r["occurrence_uid"] for r in occurrences}) != len(occurrences):
        fail("Occurrence lost or duplicated")
    object_map = {o["sha256"]: o for o in objects}
    if len(object_map) != len(objects) or summary.get("unique_byte_objects_total") != len(objects):
        fail("Object count/uniqueness mismatch")
    identity_map = {r["id"]: r for r in identities}
    baseline_manifest = read_json(read_regular(root, "inherited_evidence/MANIFEST_SHA256.json", MAX_JSON_BYTES))
    baseline_catalog_raw = read_regular(root, "inherited_evidence/catalog/INDEX_847_RECONCILED.json", MAX_JSON_BYTES)
    check_blob(baseline_catalog_raw, baseline_manifest["files"]["catalog/INDEX_847_RECONCILED.json"], "inherited catalog")
    baseline_catalog = read_json(baseline_catalog_raw)
    if {r["id"]: r for r in baseline_catalog} != {i: r["catalog"] for i, r in identity_map.items()}:
        fail("Original identity catalog differs from preserved baseline")
    for number, ident in identity_map.items():
        if (ident["namespace"] != ident["catalog"]["namespace"] or ident["name"] != ident["catalog"]["name"]
                or ident["stable_id"] != ident["namespace"] + ":" + ident["name"]):
            fail("Original identity namespace/name differs from its preserved catalog")
    inspections = {}
    for digest, obj in object_map.items():
        check_stop()
        if obj["path"] != f"objects/{digest}/SKILL.md":
            fail("Noncanonical content-addressed output object")
        raw = read_regular(root, obj["path"])
        if sha(raw) != digest or len(raw) != obj["bytes"]:
            fail("Content-addressed output object mismatch")
        inspections[digest] = static_inspect(raw)
        if read_json(read_regular(root, obj["inspection_json"], MAX_JSON_BYTES)) != inspections[digest]:
            fail("Stored static inspection differs from exact object bytes")
        for artifact in obj["baseline_artifacts"]:
            ident = identity_map.get(artifact["original_id"])
            member = artifact["member"]
            expected_hash = baseline_manifest["files"].get(member, {}).get("sha256")
            if ident is None or artifact["sha256"] != digest or expected_hash != digest or artifact["stable_id"] != ident["stable_id"]:
                fail("Baseline artifact association is not supported by preserved verified bytes")
            suffix = f"providers/{ident['namespace']}/skills/{ident['name']}/SKILL.md"
            valid_member = ((artifact["role"] == "candidate" and member == suffix)
                            or (artifact["role"] == "original" and member == ident["catalog"]["original_path"])
                            or (artifact["role"] == "historical" and member.startswith("HISTORICAL/") and member.endswith("/" + suffix)))
            if not valid_member:
                fail("Baseline artifact namespace/path role mismatch")
    verify_preserved_captures(root, inputs, occurrences, object_map)
    expected_object_occurrences = defaultdict(list)
    for row in occurrences:
        check_stop()
        if row["state"] not in {"INSPECTED", "BLOCKED"}:
            fail("Unsupported generated occurrence state")
        if row["occurrence_uid"] != occurrence_uid(row["source"], row["path"]):
            fail("Occurrence UID mismatch")
        dossier = read_json(read_regular(root, row["dossier_json"], MAX_JSON_BYTES))
        if (dossier.get("occurrence_id") != row["occurrence_id"] or dossier.get("occurrence_uid") != row["occurrence_uid"]
                or set(dossier.get("fields", {})) != set(FIELDS) or dossier.get("state") != row["state"]):
            fail("Individual occurrence dossier mismatch")
        dimensions = dossier.get("evidence_dimensions", {})
        if dimensions.get("manual_instruction_review") is not False or dimensions.get("whole_capability_verified") is not False or dimensions.get("provider_runtime_tested") is not False:
            fail("Automatic occurrence dossier escalates evidence scope")
        digest = row["sha256"]
        inspection = inspections[digest] if digest is not None else {"parse_ok": False}
        expected_state = "INSPECTED" if digest is not None and inspection["parse_ok"] and row["capture_record"]["state"] == "CAPTURED" else "BLOCKED"
        if row["state"] != expected_state:
            fail("Generated state differs from automated static/capture evidence")
        if row["association"] != associate(inspection, row["capture_record"], object_map, identity_map):
            fail("Association differs from conservative exact-byte/namespace recomputation")
        if digest is not None:
            if digest not in object_map or row["capture_record"].get("sha256") != digest:
                fail("Occurrence references missing or differing byte object")
            expected_object_occurrences[digest].append(row["occurrence_uid"])
            allowed = {a["original_id"] for a in object_map[digest]["baseline_artifacts"]}
            if set(row["association"]["matched_original_ids"]) - allowed:
                fail("Association without verified baseline object")
    for digest, obj in object_map.items():
        if obj["path"] != f"objects/{digest}/SKILL.md" or sha(read_regular(root, obj["path"])) != digest:
            fail("Content-addressed output object mismatch")
        if sorted(obj["occurrence_uids"]) != sorted(expected_object_occurrences[digest]):
            fail("Object occurrence association lost or duplicated")
    return {"integrity": "PASS", "files_checked": len(files), "occurrences_checked": len(occurrences),
            "original_identities_checked": len(identities), "byte_objects_checked": len(objects),
            "scope": "OUTPUT_INTEGRITY_NOT_CAPABILITY_VERIFICATION"}


def load_manual_overlays(path, object_map, occurrence_map):
    """Manual data must be authored separately; this tool never invents it."""
    path = Path(path).absolute()
    raw = read_regular(path.parent, path.name, MAX_JSON_BYTES)
    document = read_json(raw)
    rows = document.get("rows") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not rows:
        fail("Manual overlay must contain nonempty rows")
    references, by_hash = {}, defaultdict(list)
    for index, row in enumerate(rows, 1):
        check_stop()
        if not isinstance(row, dict):
            fail("Invalid manual overlay row")
        digest = require_digest(row.get("sha256"), "manual object")
        if digest not in object_map:
            fail("Manual overlay references an unverified/missing object")
        if row.get("state") not in {"INSPECTED", "UNCHANGED", "IMPROVED"}:
            fail("Manual overlay cannot assert unsupported/VERIFIED state")
        if not isinstance(row.get("fields"), dict) or set(row["fields"]) != set(FIELDS):
            fail("Manual object dossier requires exactly 21 fields")
        dims = row.get("evidence_dimensions")
        if (not isinstance(dims, dict) or dims.get("manual_instruction_review") is not True
                or not isinstance(dims.get("manual_scope"), str) or not dims["manual_scope"]
                or dims.get("provider_runtime_tested") is not False or dims.get("whole_capability_verified") is not False):
            fail("Manual overlay requires explicit limited scope and no automatic runtime/global verification")
        scoped = dims.get("resources_reviewed_at_occurrence_ids", [])
        if not isinstance(scoped, list) or any(not isinstance(s, str) for s in scoped) or len(scoped) != len(set(scoped)):
            fail("Invalid manual resource occurrence scope")
        for oid in scoped:
            if oid not in occurrence_map or occurrence_map[oid]["sha256"] != digest:
                fail("Manual auxiliary scope references another/missing occurrence object")
        refs = row.get("evidence_refs")
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs):
            fail("Manual review needs existing relative evidence references")
        for ref in refs:
            safe_relative(ref)
            if ref not in references:
                references[ref] = read_regular(path.parent, ref, MAX_JSON_BYTES)
        if by_hash[digest] and any(r["row"]["state"] != row["state"] for r in by_hash[digest]):
            fail("Conflicting manual states for the same byte object")
        by_hash[digest].append({"index": index, "row": row,
                                "path": f"manual_objects/{digest}/{index:04d}.json",
                                "evidence": [{"path": "evidence/" + r, "sha256": sha(references[r])} for r in refs]})
    return {"raw": raw, "document": document, "rows": rows, "by_hash": dict(by_hash), "references": references}


@cooperative_stop
def apply_overlays(registry, manual_overlays, output):
    """Write only a new immutable sidecar; never rewrite a capture or base file."""
    registry = Path(registry).resolve()
    requested = Path(output).absolute()
    if requested.exists() or requested.is_symlink():
        fail("Overlay output must be a new directory")
    output = requested.resolve(strict=False)
    if output == registry or registry in output.parents or output in registry.parents:
        fail("Overlay output must be separate from base registry")
    verify_registry(registry)
    base_manifest_raw = read_regular(registry, "MANIFEST_SHA256.json", MAX_JSON_BYTES)
    if read_json(base_manifest_raw).get("format") != "kai.skill_union_integrity/1":
        fail("Overlay base must be a plain registry; combine reviews in one authored overlay")
    base_occurrences = read_json(read_regular(registry, "OCCURRENCE_INDEX.json", MAX_JSON_BYTES))["rows"]
    object_document = read_json(read_regular(registry, "OBJECT_INDEX.json", MAX_JSON_BYTES))
    object_map = {o["sha256"]: o for o in object_document["rows"]}
    occurrence_map = {r["occurrence_id"]: r for r in base_occurrences}
    manual = load_manual_overlays(manual_overlays, object_map, occurrence_map)
    summary = read_json(read_regular(registry, "SUMMARY.json", MAX_JSON_BYTES))
    queue = read_json(read_regular(registry, "REVIEW_QUEUE.json", MAX_JSON_BYTES))
    queue["rows"] = [r for r in queue["rows"] if r["sha256"] not in manual["by_hash"]]
    queue["scope"] = "UNIQUE_OBJECTS_WITHOUT_INHERITED_OR_EXPLICIT_NEW_MANUAL_INSTRUCTION_REVIEW"
    affected, effective_rows = [], []
    for base_row in base_occurrences:
        check_stop()
        row = dict(base_row)
        row["dossier_resolution"] = "BASE_REGISTRY"
        digest = row["sha256"]
        if digest in manual["by_hash"]:
            reviews = manual["by_hash"][digest]
            dossier = read_json(read_regular(registry, row["dossier_json"], MAX_JSON_BYTES))
            refs = [{"sha256": digest, "manual_object_dossier": r["path"], "nominal_dossier_index": r["index"],
                     "manual_scope": r["row"]["evidence_dimensions"]["manual_scope"],
                     "resources_reviewed_for_this_occurrence": row["occurrence_id"] in r["row"]["evidence_dimensions"].get("resources_reviewed_at_occurrence_ids", []),
                     "evidence": r["evidence"]} for r in reviews]
            # A manual read of raw text cannot repair invalid YAML or a changed
            # census capture. BLOCKED remains BLOCKED even for identical bytes.
            state = "BLOCKED" if base_row["state"] == "BLOCKED" else reviews[0]["row"]["state"]
            dossier["state"] = row["state"] = state
            dossier["manual_object_reviews"] = refs
            dims = dossier["evidence_dimensions"]
            dims.update({"manual_instruction_review": True, "new_manual_review_performed": False,
                         "manual_review_counting_unit": "AUTHORED_OBJECT_DOSSIER_NOT_EACH_CLONE_OCCURRENCE",
                         "manual_evidence_reused_by_exact_hash": True,
                         "manual_scope": "INSTRUCTION_TEXT_ONLY_FOR_IDENTICAL_COPIES; auxiliary/test scope is per reviewed occurrence",
                         "resources_reviewed_for_this_occurrence": any(r["resources_reviewed_for_this_occurrence"] for r in refs),
                         "inspection_grade": "MANUAL_INSTRUCTION_TEXT_WITH_AUTOMATED_STATIC_INVENTORY",
                         "provider_runtime_tested": False, "whole_capability_verified": False})
            dossier["fields"][FIELDS[0]]["manual_object_reviews"] = refs
            dossier["fields"][FIELDS[1]]["state"] = state
            dossier["fields"][FIELDS[5]]["manual_auxiliary_review_scope"] = {
                "reviewed_at_this_occurrence": dims["resources_reviewed_for_this_occurrence"],
                "reviewed_occurrence_ids": sorted({oid for r in reviews for oid in r["row"]["evidence_dimensions"].get("resources_reviewed_at_occurrence_ids", [])}),
                "rule": "Auxiliary bytes and tests never transfer to another occurrence by SKILL hash"}
            dossier["fields"][FIELDS[17]] = dims
            dossier["fields"][FIELDS[18]]["manual_object_reviews"] = refs
            dossier["fields"][FIELDS[20]].update({"state": state, "inspection_grade": dims["inspection_grade"],
                "manual_object_review_references": [r["path"] for r in reviews],
                "next_action": "Raw capture/syntax remains BLOCKED; evaluate existing variants separately" if state == "BLOCKED"
                               else "Consult manual object dossier; resolve uncaptured resources and per-environment tests separately"})
            # All original capture path/hash/identity fields remain unchanged.
            row["dossier_resolution"] = "OVERLAY_EVIDENCE"
            affected.append((row, dossier))
        effective_rows.append(row)
    inherited_hashes = {d for d, obj in object_map.items() if obj["inherited_manual_reviews"]}
    for digest, reviews in manual["by_hash"].items():
        object_map[digest]["new_manual_instruction_reviews"] = [{"manual_object_dossier": r["path"],
            "manual_scope": r["row"]["evidence_dimensions"]["manual_scope"], "evidence": r["evidence"]} for r in reviews]
    new_hashes = {r["sha256"] for r in effective_rows if r["sha256"]}
    summary.update({"format": "kai.skill_union_overlay_summary/1", "base_manifest_sha256": sha(base_manifest_raw),
                    "manual_overlay_sha256": sha(manual["raw"]),
                    "new_manual_reviews_performed": len(manual["rows"]),
                    "new_manual_dossiers_supplied": len(manual["rows"]),
                    "unique_objects_with_new_manual_instruction_review": len(manual["by_hash"]),
                    "unique_objects_with_any_manual_instruction_review": len(inherited_hashes | set(manual["by_hash"])),
                    "new_occurrences_with_manual_object_review": len(affected),
                    "occurrence_workflow_states": dict(Counter(r["state"] for r in effective_rows)),
                    "unique_objects_pending_manual_review": len(queue["rows"]),
                    "unique_new_capture_objects_pending_manual_review": sum(r["sha256"] in new_hashes for r in queue["rows"]),
                    "new_runtime_tests_performed": 0, "whole_registry_verified": False,
                    "new_confirmed_capabilities_claimed": 0,
                    "claim_scope": "BYTE_INTEGRITY_STATIC_INVENTORY_AND_EXPLICITLY_SCOPED_MANUAL_OBJECT_REVIEWS"})
    check_stop()
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    write_new(output, "MANUAL_OVERLAYS_INPUT.json", manual["raw"], files)
    for relative, data in sorted(manual["references"].items()):
        write_new(output, "evidence/" + relative, data, files)
    for digest, reviews in manual["by_hash"].items():
        for review in reviews:
            stored = {"format": "kai.skill_manual_object_dossier/1", "sha256": digest,
                      "nominal_dossier_index": review["index"], **review["row"],
                      "preserved_evidence_refs": review["evidence"],
                      "evidence_scope_rule": "Only instruction text transfers by hash; auxiliaries/tests remain per occurrence"}
            write_new(output, review["path"], json_bytes(stored), files)
            md_dossier = {"occurrence_id": "manual-object:" + str(review["index"]), "fields": review["row"]["fields"]}
            write_new(output, review["path"][:-5] + ".md", markdown_dossier(md_dossier), files)
    for row, dossier in affected:
        write_new(output, row["dossier_json"], json_bytes(dossier), files)
        write_new(output, row["dossier_md"], markdown_dossier(dossier), files)
    base_ref = {"format": "kai.skill_union_overlay_base/1", "base_registry_path_hint": str(registry),
                "base_manifest_sha256": sha(base_manifest_raw), "manual_overlay_sha256": sha(manual["raw"]),
                "base_files_rewritten": 0, "historical_dossiers_reproduced": 0,
                "builder_sha256": sha(Path(__file__).read_bytes())}
    documents = {"BASE_REFERENCE.json": base_ref,
                 "OCCURRENCE_INDEX.json": {"format": "kai.skill_effective_occurrences/1", "rows": effective_rows},
                 "OBJECT_INDEX.json": object_document, "REVIEW_QUEUE.json": queue, "SUMMARY.json": summary,
                 "BLOCKER_QUEUE.json": {"format": "kai.skill_occurrence_blockers/1", "rows": [r for r in effective_rows if r["state"] == "BLOCKED"]}}
    for name, document in documents.items():
        write_new(output, name, json_bytes(document), files)
    write_new(output, "SUMMARY.md", (
        "# Overlay de revisión manual\n\n"
        f"{len(manual['rows'])} fichas nominales para {len(manual['by_hash'])} objetos byte únicos. "
        f"{len(affected)} ocurrencias enlazan a esas revisiones de instrucciones.\n\n"
        "Las referencias a recursos y pruebas conservan ámbito por ocurrencia; un hash idéntico no transmite una prueba de entorno. "
        "Los raw con sintaxis bloqueada siguen BLOCKED. La base y las capturas permanecen intactas.\n"
    ).encode("utf-8"), files)
    check_stop()
    with (output / "MANIFEST_SHA256.json").open("xb") as handle:
        check_stop()
        handle.write(json_bytes({"format": "kai.skill_review_overlay_integrity/1", "files": files,
                                 "base_manifest_sha256": sha(base_manifest_raw), "self_excluded": "MANIFEST_SHA256.json"}))
    verify_overlay(registry, output, verify_base=False)
    return summary


@cooperative_stop
def verify_overlay(registry, overlay, *, verify_base=True):
    registry, overlay = Path(registry).absolute(), Path(overlay).absolute()
    if verify_base:
        verify_registry(registry)
    manifest = read_json(read_regular(overlay, "MANIFEST_SHA256.json", MAX_JSON_BYTES))
    base_hash = sha(read_regular(registry, "MANIFEST_SHA256.json", MAX_JSON_BYTES))
    if not isinstance(manifest, dict) or manifest.get("format") != "kai.skill_review_overlay_integrity/1" or manifest.get("base_manifest_sha256") != base_hash:
        fail("Overlay format/base manifest binding mismatch")
    files = manifest.get("files")
    if not isinstance(files, dict) or "MANIFEST_SHA256.json" in files:
        fail("Invalid overlay integrity coverage")
    names = []
    for path in overlay.rglob("*"):
        check_stop()
        if path.is_symlink():
            fail("Symlink in overlay")
        if path.is_file():
            names.append(path.relative_to(overlay).as_posix())
    validate_paths(names)
    if set(names) != set(files) | {"MANIFEST_SHA256.json"}:
        fail("Overlay has lost or extra files")
    for name, record in files.items():
        check_blob(read_regular(overlay, name, MAX_JSON_BYTES), record, name)
    base_rows = read_json(read_regular(registry, "OCCURRENCE_INDEX.json", MAX_JSON_BYTES))["rows"]
    effective_rows = read_json(read_regular(overlay, "OCCURRENCE_INDEX.json", MAX_JSON_BYTES))["rows"]
    effective_map = {r["occurrence_uid"]: r for r in effective_rows}
    if len(effective_map) != len(effective_rows) or set(effective_map) != {r["occurrence_uid"] for r in base_rows}:
        fail("Overlay lost or duplicated an occurrence")
    affected_count = 0
    for base in base_rows:
        check_stop()
        row = effective_map[base["occurrence_uid"]]
        for field in ("capture_record", "path", "sha256", "association", "occurrence_id", "source", "index"):
            if row[field] != base[field]:
                fail("Overlay changed immutable capture/identity data")
        if row["state"] not in STATES or row["state"] == "VERIFIED" or (base["state"] == "BLOCKED" and row["state"] != "BLOCKED"):
            fail("Overlay escalated a syntax/capture blocker or VERIFIED state")
        if row.get("dossier_resolution") == "OVERLAY_EVIDENCE":
            affected_count += 1
            dossier = read_json(read_regular(overlay, row["dossier_json"], MAX_JSON_BYTES))
            dims = dossier.get("evidence_dimensions", {})
            if (set(dossier.get("fields", {})) != set(FIELDS) or dossier.get("occurrence_uid") != row["occurrence_uid"]
                    or dossier.get("state") != row["state"] or dims.get("manual_instruction_review") is not True
                    or dims.get("provider_runtime_tested") is not False or dims.get("whole_capability_verified") is not False):
                fail("Overlay dossier identity/21 fields/evidence scope mismatch")
            for review in dossier.get("manual_object_reviews", []):
                if review.get("sha256") != row["sha256"] or review.get("manual_object_dossier") not in files:
                    fail("Overlay manual review is not linked to exact object evidence")
        elif row.get("dossier_resolution") != "BASE_REGISTRY" or row["state"] != base["state"]:
            fail("Invalid unchanged base dossier resolution")
    summary = read_json(read_regular(overlay, "SUMMARY.json", MAX_JSON_BYTES))
    if (summary.get("whole_registry_verified") is not False or summary.get("new_confirmed_capabilities_claimed") != 0
            or summary.get("new_device_occurrences") != len(effective_rows)
            or summary.get("new_occurrences_with_manual_object_review") != affected_count):
        fail("Overlay summary scope/count mismatch")
    return {"integrity": "PASS", "files_checked": len(files), "occurrences_checked": len(effective_rows),
            "affected_occurrences": affected_count, "base_manifest_sha256": base_hash,
            "scope": "SCOPED_MANUAL_OBJECT_OVERLAY_NOT_CAPABILITY_VERIFICATION"}


@cooperative_stop
def write_tracking_map(registry, output):
    registry = Path(registry).resolve()
    output = Path(output).absolute()
    if output.exists() or output.is_symlink() or registry == output or registry in output.resolve(strict=False).parents:
        fail("Tracking sidecar must be new and outside the immutable registry")
    verify_registry(registry)
    inputs = read_json(read_regular(registry, "BUILD_INPUTS.json", MAX_JSON_BYTES))
    expected = inputs["expected_counts"]
    identities = read_json(read_regular(registry, "IDENTITIES_847.json", MAX_JSON_BYTES))["rows"]
    occurrences = read_json(read_regular(registry, "OCCURRENCE_INDEX.json", MAX_JSON_BYTES))["rows"]
    rows = [{"tracking_number": ident["id"], "kind": "ORIGINAL_IDENTITY_TRACKING",
             "original_id": ident["id"], "stable_id": ident["stable_id"]} for ident in identities]
    for occurrence in sorted(occurrences, key=lambda r: (r["source"] != "pc-asier", r["index"])):
        offset = expected["originals"] + (expected["pc-asier"] if occurrence["source"] == "termux" else 0)
        rows.append({"tracking_number": offset + occurrence["index"], "kind": "DEVICE_OCCURRENCE_TRACKING",
                     "occurrence_id": occurrence["occurrence_id"], "occurrence_uid": occurrence["occurrence_uid"],
                     "source": occurrence["source"], "path": occurrence["path"]})
    if {r["tracking_number"] for r in rows} != set(range(1, len(rows) + 1)):
        fail("Tracking map must be unique and contiguous")
    document = {"format": "kai.skill_tracking_map/1", "scope": "TRACKING_NUMBERS_NOT_CAPABILITY_OR_NEW_IDENTITY_IDS",
                "base_manifest_sha256": sha(read_regular(registry, "MANIFEST_SHA256.json", MAX_JSON_BYTES)),
                "rows": rows}
    check_stop()
    output.parent.mkdir(parents=True, exist_ok=True)
    check_stop()
    with output.open("xb") as handle:
        handle.write(json_bytes(document))
    return {"tracking_rows": len(rows), "sha256": sha(output.read_bytes()), "base_manifest_sha256": document["base_manifest_sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Create a separate new registry directory")
    build.add_argument("--baseline", required=True, type=Path)
    build.add_argument("--baseline-sha256", default=BASELINE_SHA256)
    build.add_argument("--capture-pc", required=True, type=Path)
    build.add_argument("--capture-termux", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--expected-originals", type=int, default=847)
    build.add_argument("--expected-pc", type=int, default=723)
    build.add_argument("--expected-termux", type=int, default=3659)
    build.add_argument("--manual-overlays", type=Path,
                       help="Write a base + immutable overlay_evidence collection in output")
    verify = commands.add_parser("verify", help="Verify files and count/evidence invariants")
    verify.add_argument("--registry", required=True, type=Path)
    apply = commands.add_parser("apply-overlays", help="Add authored manual evidence in a separate immutable sidecar")
    apply.add_argument("--registry", required=True, type=Path)
    apply.add_argument("--manual-overlays", required=True, type=Path)
    apply.add_argument("--output", required=True, type=Path)
    verify_manual = commands.add_parser("verify-overlay", help="Verify sidecar integrity and its binding to the base")
    verify_manual.add_argument("--registry", required=True, type=Path)
    verify_manual.add_argument("--overlay", required=True, type=Path)
    tracking = commands.add_parser("tracking-map", help="Write explicit tracking numbers without changing registry IDs")
    tracking.add_argument("--registry", required=True, type=Path)
    tracking.add_argument("--output", required=True, type=Path)
    for command in (build, verify, apply, verify_manual, tracking):
        command.add_argument("--stop-file", type=Path,
                             help="Cooperative STOP flag; existence or dangling symlink stops processing")
    args = parser.parse_args(argv)
    stop_token = _STOP_FILE.set(args.stop_file)
    try:
        check_stop()
        if args.command == "build":
            build_output = args.output
            if args.manual_overlays is not None:
                if args.output.exists() or args.output.is_symlink():
                    fail("Collection output must be a new directory")
                resolved_output = args.output.resolve(strict=False)
                for input_path in (args.baseline.resolve(), args.capture_pc.resolve(), args.capture_termux.resolve()):
                    if resolved_output == input_path or input_path in resolved_output.parents or resolved_output in input_path.parents:
                        fail("Collection output must be separate from all inputs")
                check_stop()
                args.output.mkdir(parents=True, exist_ok=False)
                build_output = args.output / "base"
            result = build_registry(args.baseline, args.capture_pc, args.capture_termux, build_output,
                                    baseline_sha256=args.baseline_sha256, expected_originals=args.expected_originals,
                                    expected_pc=args.expected_pc, expected_termux=args.expected_termux)
            if args.manual_overlays is not None:
                overlay_summary = apply_overlays(build_output, args.manual_overlays, args.output / "overlay_evidence")
                check_stop()
                with (args.output / "MANIFEST_SHA256.json").open("xb") as handle:
                    handle.write(json_bytes({"format": "kai.skill_union_collection/1",
                        "base_manifest_sha256": sha((build_output / "MANIFEST_SHA256.json").read_bytes()),
                        "overlay_manifest_sha256": sha((args.output / "overlay_evidence/MANIFEST_SHA256.json").read_bytes())}))
                result = {"base_summary": result, "effective_summary": overlay_summary}
        elif args.command == "apply-overlays":
            result = apply_overlays(args.registry, args.manual_overlays, args.output)
        elif args.command == "verify-overlay":
            result = verify_overlay(args.registry, args.overlay)
        elif args.command == "tracking-map":
            result = write_tracking_map(args.registry, args.output)
        else:
            result = verify_registry(args.registry)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (RegistryError, OSError, zipfile.BadZipFile, KeyError) as exc:
        print(json.dumps({"error": str(exc), "scope": "BUILD_OR_INTEGRITY_FAILURE"}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        _STOP_FILE.reset(stop_token)


if __name__ == "__main__":
    raise SystemExit(main())
