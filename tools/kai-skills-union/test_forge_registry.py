"""Adversarial offline invariants; no recovered skill code is executed."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import forge_registry as reg


SKILL_A = b"---\nname: alpha\ndescription: Read data and produce a report.\n---\nUse `references/guide.md`.\n"
SKILL_B = b"---\nname: alpha\ndescription: Different revision with the same name.\n---\nChanged instruction.\n"
SKILL_NEW = b"---\nname: beta\ndescription: Newly captured text, not a proven new capability.\n---\nHello.\n"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(reg.json_bytes(value))


def make_bundle(path, skills=None, manual=False, extra=None, transform=None):
    skills = skills or [("provider", "alpha", SKILL_A)]
    files, catalog, rows = {}, [], []
    for number, (namespace, name, data) in enumerate(skills, 1):
        stable = namespace + ":" + name
        digest = reg.sha(data)
        original = f"originals/{namespace}/{name}/SKILL.md"
        root = f"providers/{namespace}/skills/{name}"
        files[original] = data
        files[root + "/SKILL.md"] = data
        catalog.append({"id": number, "namespace": namespace, "name": name,
                        "uri": f"skills://plugins/{namespace}/{name}", "original_path": original,
                        "original_sha256": digest, "staged_root": root, "portable_sha256": digest,
                        "description": "fixture", "aux_expected": 0, "aux_recovered": 0, "aux_missing": []})
        dimensions = {"id": number, "stable_id": stable, "original_sha256": digest,
                      "state": "UNDERSTOOD" if manual else "INSPECTED", "manual_instruction_review": manual,
                      "whole_capability_verified": False, "provider_runtime_tested": False}
        rows.append(dimensions)
        fields = {key: "fixture evidence; no provider runtime" for key in reg.FIELDS}
        fields[reg.FIELDS[18]] = {"original_sha256": digest}
        dossier = {"id": number, "stable_id": stable, "fields": fields, "evidence_dimensions": dimensions}
        files[f"batch_002/evidence/fichas/{number:04d}.json"] = reg.json_bytes(dossier)
        files[f"batch_002/evidence/fichas/{number:04d}.md"] = b"Inherited dossier.\n"
    files["catalog/INDEX_847_RECONCILED.json"] = reg.json_bytes(catalog)
    files["batch_002/evidence/AUDIT_MATRIX_847_BATCH002.json"] = reg.json_bytes({"rows": rows})
    if extra:
        files.update(extra)
    if transform:
        transform(files)
    manifest = {"format": "kai.skills.bundle/1", "skills": len(skills),
                "files": {name: {"sha256": reg.sha(data), "bytes": len(data)} for name, data in files.items()}}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("MANIFEST_SHA256.json", reg.json_bytes(manifest))
    return reg.sha(path.read_bytes())


def make_capture(root, source, items=(), metadata=None):
    root.mkdir(parents=True)
    rows = []
    for index, item in enumerate(items, 1):
        data, path = item[:2]
        options = item[2] if len(item) > 2 else {}
        digest = reg.sha(data) if data is not None else None
        row = {"index": index, "occurrence_id": f"{source}:{index:04d}",
               "occurrence_uid": reg.occurrence_uid(source, path), "path": path,
               "expected_sha256": digest or "a" * 64, "expected_bytes": len(data) if data else 0,
               "state": "CAPTURED" if data is not None else "BLOCKED",
               "sha256": digest, "bytes": len(data) if data is not None else None,
               "object_path": f"objects/{digest}/SKILL.md" if digest else None}
        row.update(options)
        if digest:
            target = root / "objects" / digest / "SKILL.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        rows.append(row)
    clues = []
    for path, data in metadata or []:
        digest = reg.sha(data)
        target = root / "metadata_objects" / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        clues.append({"path": path, "kind": "package_metadata", "bytes": len(data),
                      "sha256": digest, "state": "CAPTURED"})
    manifest = {"format": "kai.skill_capture/1", "source": source, "rows": rows,
                "metadata_clues": clues, "resources_scope": "SKILL_MD_AND_NAMED_METADATA_ONLY"}
    dump(root / "CAPTURE_MANIFEST.json", manifest)
    return manifest


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "baseline.zip"
        self.pin = make_bundle(self.bundle)
        self.pc = self.root / "capture_pc"
        self.termux = self.root / "capture_termux"
        self.out = self.root / "output"

    def captures(self, pc=(), termux=(), pc_metadata=None):
        self.pc_manifest = make_capture(self.pc, "pc-asier", pc, pc_metadata)
        self.termux_manifest = make_capture(self.termux, "termux", termux)

    def build(self, **overrides):
        args = dict(baseline_sha256=self.pin, expected_originals=1,
                    expected_pc=len(self.pc_manifest["rows"]), expected_termux=len(self.termux_manifest["rows"]))
        args.update(overrides)
        return reg.build_registry(self.bundle, self.pc, self.termux, self.out, **args)

    def read(self, name):
        return json.loads((self.out / name).read_text())

    def mutate_capture(self, action, termux=False):
        root = self.termux if termux else self.pc
        manifest = self.termux_manifest if termux else self.pc_manifest
        action(manifest)
        dump(root / "CAPTURE_MANIFEST.json", manifest)

    def pin_pc_census(self, census_rows=None, with_integrity=False):
        rows = census_rows if census_rows is not None else [
            {"path": r["path"], "sha256": r["expected_sha256"], "bytes": r["expected_bytes"]}
            for r in self.pc_manifest["rows"]]
        raw = reg.json_bytes({"skills": rows, "parent_census_sha256": "a" * 64, "excerpt": True})
        (self.pc / "SOURCE_CENSUS.json").write_bytes(raw)
        self.mutate_capture(lambda m: m.update(census_sha256=reg.sha(raw)))
        if with_integrity:
            files = {}
            for path in self.pc.rglob("*"):
                if path.is_file():
                    data = path.read_bytes()
                    files[path.relative_to(self.pc).as_posix()] = {"sha256": reg.sha(data), "bytes": len(data)}
            dump(self.pc / "CAPTURE_INTEGRITY.json", {"format": "kai.capture.integrity/1", "files": files})
        return raw

    def manual_input(self, digest=None, state="INSPECTED", scoped=None, rows=None):
        folder = self.root / "manual_inputs"
        folder.mkdir(exist_ok=True)
        (folder / "REVIEW.md").write_text("Human-authored instruction-text review. No runtime tests.\n")
        fields = {key: "Manual nominal dossier; auxiliary scope remains explicit" for key in reg.FIELDS}
        fields[reg.FIELDS[18]] = {"sha256": digest or reg.sha(SKILL_NEW)}
        row = {"sha256": digest or reg.sha(SKILL_NEW), "state": state, "fields": fields,
               "evidence_dimensions": {"manual_instruction_review": True,
                   "manual_scope": "INSTRUCTION_TEXT_ONLY_FOR_IDENTICAL_COPIES; auxiliary/test scope per reviewed occurrence",
                   "resources_reviewed_at_occurrence_ids": scoped or [],
                   "provider_runtime_tested": False, "whole_capability_verified": False},
               "evidence_refs": ["REVIEW.md"]}
        path = folder / "MANUAL_OVERLAYS.json"
        dump(path, {"rows": rows if rows is not None else [row]})
        return path

    def rehash_output_file(self, relative):
        manifest = self.read("MANIFEST_SHA256.json")
        path = self.out / relative
        if path.exists():
            data = path.read_bytes()
            manifest["files"][relative] = {"sha256": reg.sha(data), "bytes": len(data)}
        else:
            del manifest["files"][relative]
        dump(self.out / "MANIFEST_SHA256.json", manifest)

    def test_duplicate_bytes_preserve_each_occurrence_and_original_id(self):
        self.captures([(SKILL_A, r"C:\skills\alpha\SKILL.md")],
                      [(SKILL_A, "/data/skills/alpha/SKILL.md"), (SKILL_NEW, "/data/skills/beta/SKILL.md")])
        summary = self.build()
        self.assertEqual(summary["new_device_occurrences"], 3)
        self.assertEqual(summary["unique_byte_objects_total"], 2)
        self.assertEqual(summary["new_confirmed_capabilities_claimed"], 0)
        self.assertEqual(self.read("IDENTITIES_847.json")["rows"][0]["id"], 1)
        rows = self.read("OCCURRENCE_INDEX.json")["rows"]
        self.assertEqual([r["association"]["matched_original_ids"] for r in rows], [[1], [1], []])
        self.assertEqual(rows[0]["path"], r"C:\skills\alpha\SKILL.md")
        self.assertNotEqual(rows[0]["dossier_json"], rows[1]["dossier_json"])
        for row in rows:
            dossier = self.read(row["dossier_json"])
            self.assertEqual(set(dossier["fields"]), set(reg.FIELDS))
            self.assertFalse(dossier["evidence_dimensions"]["manual_instruction_review"])
            self.assertFalse(dossier["evidence_dimensions"]["provider_runtime_tested"])
        self.assertEqual(reg.verify_registry(self.out)["occurrences_checked"], 3)

    def test_same_name_revisions_do_not_associate_without_hash(self):
        self.captures([(SKILL_B, "/plugins/cache/registry/provider/2.0/skills/alpha/SKILL.md"),
                       (SKILL_A, "/plugins/cache/registry/provider/1.0/skills/alpha/SKILL.md")])
        self.build()
        rows = self.read("OCCURRENCE_INDEX.json")["rows"]
        self.assertEqual(rows[0]["association"]["matched_original_ids"], [])
        self.assertEqual(rows[0]["association"]["namespace_name_candidate_original_ids"], [1])
        family = self.read("VARIANT_INDEX.json")["families"][0]
        self.assertTrue(family["different_byte_revisions"])
        self.assertEqual(len(family["object_sha256"]), 2)

    def test_blocked_occurrence_is_not_lost(self):
        self.captures([(None, "/unreadable/SKILL.md", {"error": "permission denied"})])
        summary = self.build()
        self.assertEqual(summary["new_occurrences_without_preserved_bytes"], 1)
        row = self.read("OCCURRENCE_INDEX.json")["rows"][0]
        self.assertEqual(row["state"], "BLOCKED")
        self.assertIsNone(row["sha256"])
        self.assertEqual(row["capture_record"]["error"], "permission denied")

    def test_changed_occurrence_preserves_actual_and_expected(self):
        self.captures([(SKILL_B, "/changed/SKILL.md", {"state": "CHANGED_SINCE_CENSUS",
                         "expected_sha256": reg.sha(SKILL_A), "expected_bytes": len(SKILL_A)})])
        self.build()
        row = self.read("OCCURRENCE_INDEX.json")["rows"][0]
        self.assertEqual(row["state"], "BLOCKED")
        self.assertEqual(row["sha256"], reg.sha(SKILL_B))
        self.assertEqual(row["capture_record"]["expected_sha256"], reg.sha(SKILL_A))
        self.assertEqual((self.out / f"objects/{reg.sha(SKILL_B)}/SKILL.md").read_bytes(), SKILL_B)

    def test_changed_bytes_cannot_claim_captured(self):
        self.captures([(SKILL_B, "/changed/SKILL.md", {"expected_sha256": reg.sha(SKILL_A)})])
        with self.assertRaisesRegex(reg.RegistryError, "changed since census"):
            self.build()
        self.assertFalse(self.out.exists())

    def test_missing_byte_object_fails_before_writes(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        (self.pc / f"objects/{reg.sha(SKILL_A)}/SKILL.md").unlink()
        with self.assertRaisesRegex(reg.RegistryError, "Missing capture object"):
            self.build()
        self.assertFalse(self.out.exists())

    def test_duplicate_occurrence_not_counted_twice(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        self.mutate_capture(lambda m: m["rows"].append(copy.deepcopy(m["rows"][0])))
        with self.assertRaisesRegex(reg.RegistryError, "indices.*unique"):
            self.build()

    def test_capture_index_gap_is_detected(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        def change(m):
            m["rows"][0]["index"] = 2
            m["rows"][0]["occurrence_id"] = "pc-asier:0002"
        self.mutate_capture(change)
        with self.assertRaisesRegex(reg.RegistryError, "census exactly once"):
            self.build()

    def test_uid_is_exact_separator_normalization_not_casefold(self):
        path = r"C:\Users\Ásier\skills\SKILL.md"
        self.assertEqual(reg.occurrence_uid("pc-asier", path), "occ:pc-asier:" + reg.sha(path.replace("\\", "/").encode())[:24])
        self.assertNotEqual(reg.occurrence_uid("pc-asier", path), reg.occurrence_uid("pc-asier", path.lower()))
        self.captures([(SKILL_A, path)])
        self.mutate_capture(lambda m: m["rows"][0].update(occurrence_uid="occ:pc-asier:" + "0" * 24))
        with self.assertRaisesRegex(reg.RegistryError, "ID/UID"):
            self.build()

    def test_hash_mismatch_is_detected(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        (self.pc / f"objects/{reg.sha(SKILL_A)}/SKILL.md").write_bytes(SKILL_B)
        with self.assertRaisesRegex(reg.RegistryError, "Hash/size mismatch"):
            self.build()

    def test_object_path_escape_rejected(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        self.mutate_capture(lambda m: m["rows"][0].update(object_path="../outside/SKILL.md"))
        with self.assertRaisesRegex(reg.RegistryError, "canonical"):
            self.build()

    def test_symlink_object_rejected(self):
        self.captures([(SKILL_A, "/skill/SKILL.md")])
        target = self.pc / f"objects/{reg.sha(SKILL_A)}/SKILL.md"
        target.unlink()
        outside = self.root / "external.md"
        outside.write_bytes(SKILL_A)
        target.symlink_to(outside)
        with self.assertRaisesRegex(reg.RegistryError, "Symlink"):
            self.build()

    def test_invalid_utf8_bytes_preserved_and_blocked(self):
        data = b"---\nname: invalid\n---\n\xff\xfe"
        self.captures([(data, "/invalid/SKILL.md")])
        self.build()
        self.assertEqual(self.read("OCCURRENCE_INDEX.json")["rows"][0]["state"], "BLOCKED")
        self.assertEqual((self.out / f"objects/{reg.sha(data)}/SKILL.md").read_bytes(), data)

    def test_unsafe_yaml_and_duplicate_keys_never_execute(self):
        marker = self.root / "MUST_NOT_EXIST"
        malicious = f"---\nname: !!python/object/apply:os.system ['touch {marker}']\n---\n".encode()
        duplicate = b"---\nname: first\nname: second\n---\n"
        aliases = b"---\nname: &a [x,x]\nmore: [*a,*a]\n---\n"
        for data in (malicious, duplicate, aliases):
            inspection = reg.static_inspect(data)
            self.assertFalse(inspection["parse_ok"])
            self.assertEqual(inspection["findings"][0]["code"], "UNSAFE_OR_INVALID_YAML")
        self.assertFalse(marker.exists())

    def test_excessive_resource_declarations_are_bounded_and_reported(self):
        data = b"---\nname: many\ndescription: bounded scan\n---\n" + b"\n".join(f"[r](references/{i}.md)".encode() for i in range(700))
        result = reg.static_inspect(data)
        self.assertEqual(result["resource_declarations_seen"], 700)
        self.assertEqual(len(result["resources"]), reg.MAX_DECLARATIONS)
        self.assertTrue(result["resources_truncated"])
        self.assertIn("DECLARATION_LIMIT_EXCEEDED", [f["code"] for f in result["findings"]])

    def test_wrong_baseline_pin_rejected(self):
        self.captures()
        with self.assertRaisesRegex(reg.RegistryError, "baseline SHA256"):
            self.build(baseline_sha256="f" * 64)

    def test_baseline_catalog_hash_mismatch_rejected(self):
        def transform(files):
            catalog = json.loads(files["catalog/INDEX_847_RECONCILED.json"])
            catalog[0]["original_sha256"] = "a" * 64
            files["catalog/INDEX_847_RECONCILED.json"] = reg.json_bytes(catalog)
        self.pin = make_bundle(self.bundle, transform=transform)
        self.captures()
        with self.assertRaisesRegex(reg.RegistryError, "catalog hash/path"):
            self.build()

    def test_baseline_archive_path_collision_rejected(self):
        self.pin = make_bundle(self.bundle, extra={"Docs/a.txt": b"a", "docs/A.txt": b"b"})
        self.captures()
        with self.assertRaisesRegex(reg.RegistryError, "path collision"):
            self.build()

    def test_baseline_archive_escape_rejected(self):
        self.pin = make_bundle(self.bundle, extra={"../escape": b"outside"})
        self.captures()
        with self.assertRaisesRegex(reg.RegistryError, "Unsafe relative path"):
            self.build()

    def test_matrix_cannot_use_unknown_workflow_state(self):
        def transform(files):
            key = "batch_002/evidence/AUDIT_MATRIX_847_BATCH002.json"
            matrix = json.loads(files[key])
            matrix["rows"][0]["state"] = "UNKNOWN"
            files[key] = reg.json_bytes(matrix)
        self.pin = make_bundle(self.bundle, transform=transform)
        self.captures()
        with self.assertRaisesRegex(reg.RegistryError, "Unsupported inherited matrix state"):
            self.build()

    def test_inherited_manual_evidence_only_exact_object_and_no_runtime(self):
        self.pin = make_bundle(self.bundle, manual=True)
        self.captures([(SKILL_A, "/exact/SKILL.md"), (SKILL_B, "/revision/SKILL.md")])
        summary = self.build()
        self.assertEqual(summary["unique_objects_with_inherited_scoped_manual_review"], 1)
        self.assertEqual(summary["unique_objects_pending_manual_review"], 1)
        self.assertEqual(summary["new_manual_reviews_performed"], 0)
        rows = self.read("OCCURRENCE_INDEX.json")["rows"]
        first = self.read(rows[0]["dossier_json"])["evidence_dimensions"]
        second = self.read(rows[1]["dossier_json"])["evidence_dimensions"]
        self.assertEqual(len(first["inherited_exact_object_reviews"]), 1)
        self.assertEqual(len(second["inherited_exact_object_reviews"]), 0)
        self.assertFalse(first["manual_instruction_review"])
        self.assertFalse(first["provider_runtime_tested"])
        self.assertEqual(self.read("REVIEW_QUEUE.json")["rows"][0]["sha256"], reg.sha(SKILL_B))
        inherited = self.out / "inherited_evidence/batch_002/evidence/fichas/0001.json"
        with zipfile.ZipFile(self.bundle) as archive:
            self.assertEqual(inherited.read_bytes(), archive.read("batch_002/evidence/fichas/0001.json"))

    def test_ambiguous_equal_hash_needs_namespace_hint(self):
        self.pin = make_bundle(self.bundle, skills=[("provider", "alpha", SKILL_A), ("other", "alpha", SKILL_A)])
        self.captures([(SKILL_A, "/plain/alpha/SKILL.md"),
                       (SKILL_A, "/providers/provider/skills/alpha/SKILL.md"),
                       (SKILL_A, "/providers/unrelated/skills/alpha/SKILL.md")])
        self.build(expected_originals=2)
        rows = self.read("OCCURRENCE_INDEX.json")["rows"]
        self.assertEqual([r["association"]["matched_original_ids"] for r in rows], [[], [1], []])
        self.assertIn("CONFLICTING_NAMESPACE", rows[2]["association"]["association_basis"])

    def test_real_device_layout_hints_resolve_exact_hash_only(self):
        cases = [
            (r"C:\Users\ASIER\.codex\.tmp\plugins\plugins\provider\skills\alpha\SKILL.md", "provider", "alpha"),
            ("/home/KAI_SKILLS_847_AUDITED_PACKAGE/skills/provider/alpha/SKILL.md", "provider", "alpha"),
            ("/home/release/originals/0001_provider__alpha/SKILL.md", "provider", "alpha"),
        ]
        for path, namespace, name in cases:
            hint = reg.namespace_hints(path)[0]
            self.assertEqual((hint["namespace"], hint["name"]), (namespace, name))
            self.assertEqual(hint["certainty"], "PATH_HINT_ONLY")

    def test_metadata_facts_have_hash_scope_and_are_not_certified(self):
        data = reg.json_bytes({"name": "fixture-package", "license": "MIT", "repository": {"url": "https://example.invalid/repo"}})
        self.captures([(SKILL_NEW, "/plugin/skills/beta/SKILL.md")], pc_metadata=[("/plugin/package.json", data)])
        self.build()
        row = self.read("OCCURRENCE_INDEX.json")["rows"][0]
        dossier = self.read(row["dossier_json"])
        version = dossier["fields"][reg.FIELDS[1]]
        self.assertEqual(version["scoped_metadata_declarations"][0]["declared"]["license"], "MIT")
        self.assertEqual(version["scoped_metadata_declarations"][0]["sha256"], reg.sha(data))
        self.assertEqual(version["license_clearance"], "NOT_ESTABLISHED_BY_THIS_TOOL")
        self.assertEqual((self.out / "metadata_objects" / reg.sha(data)).read_bytes(), data)

    def test_duplicate_json_keys_rejected(self):
        self.captures()
        (self.pc / "CAPTURE_MANIFEST.json").write_bytes(b'{"source":"pc-asier","source":"termux"}')
        with self.assertRaisesRegex(reg.RegistryError, "Duplicate JSON key"):
            self.build()

    def test_pinned_census_and_capture_integrity_preserved_exactly(self):
        self.captures([(SKILL_A, "/skills/a/SKILL.md")])
        raw_census = self.pin_pc_census(with_integrity=True)
        raw_integrity = (self.pc / "CAPTURE_INTEGRITY.json").read_bytes()
        self.build()
        prefix = self.out / "provenance/pc-asier"
        self.assertEqual((prefix / "SOURCE_CENSUS.json").read_bytes(), raw_census)
        self.assertEqual((prefix / "CAPTURE_INTEGRITY.json").read_bytes(), raw_integrity)
        capture = self.read("BUILD_INPUTS.json")["captures"][0]
        self.assertTrue(capture["capture_integrity_manifest_verified"])
        self.assertTrue(capture["census_pin_verified"])

    def test_census_tamper_rejected(self):
        self.captures([(SKILL_A, "/skills/a/SKILL.md")])
        self.pin_pc_census()
        (self.pc / "SOURCE_CENSUS.json").write_bytes(b"{}")
        with self.assertRaisesRegex(reg.RegistryError, "SOURCE_CENSUS SHA256 mismatch"):
            self.build()
        self.assertFalse(self.out.exists())

    def test_census_path_hash_correspondence_rejected(self):
        self.captures([(SKILL_A, "/skills/a/SKILL.md")])
        self.pin_pc_census(census_rows=[{"path": "/skills/unrelated/SKILL.md", "sha256": reg.sha(SKILL_A), "bytes": len(SKILL_A)}])
        with self.assertRaisesRegex(reg.RegistryError, "does not match pinned SOURCE_CENSUS"):
            self.build()

    def test_extra_capture_payload_not_silently_ignored(self):
        self.captures([(SKILL_A, "/skills/a/SKILL.md")])
        self.pin_pc_census(with_integrity=True)
        (self.pc / "UNINDEXED.md").write_bytes(b"extra")
        with self.assertRaisesRegex(reg.RegistryError, "cover every payload exactly once"):
            self.build()

    def test_normalized_device_path_collision_keeps_both_rows(self):
        self.captures([(SKILL_A, "/skills/Alpha/SKILL.md"), (SKILL_B, "/skills/alpha/SKILL.md")])
        summary = self.build()
        self.assertEqual(summary["normalized_device_path_collision_groups"], 1)
        self.assertEqual(summary["new_device_occurrences"], 2)

    def test_output_inside_capture_refused(self):
        self.captures()
        self.out = self.pc / "output"
        with self.assertRaisesRegex(reg.RegistryError, "separate from all inputs"):
            self.build()

    def test_output_path_alias_cannot_bypass_input_separation(self):
        self.captures()
        self.out = self.root / "nonexistent" / ".." / "capture_pc" / "output"
        with self.assertRaisesRegex(reg.RegistryError, "separate from all inputs"):
            self.build()

    def test_disagreeing_path_and_declared_uri_prevent_identity_merge(self):
        data = b"---\nname: alpha\nuri: skills://plugins/other/alpha\n---\n"
        self.pin = make_bundle(self.bundle, skills=[("provider", "alpha", data)])
        self.captures([(data, "/providers/provider/skills/alpha/SKILL.md")])
        self.build()
        association = self.read("OCCURRENCE_INDEX.json")["rows"][0]["association"]
        self.assertEqual(association["matched_original_ids"], [])
        self.assertIn("CONFLICTING_NAMESPACE", association["association_basis"])

    def test_output_deletion_addition_and_mutation_are_detected(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        self.build()
        path = self.out / "SUMMARY.md"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(reg.RegistryError, "lost or extra"):
            reg.verify_registry(self.out)
        path.write_bytes(original)
        extra = self.out / "UNINDEXED.txt"
        extra.write_text("extra")
        with self.assertRaisesRegex(reg.RegistryError, "lost or extra"):
            reg.verify_registry(self.out)
        extra.unlink()
        path.write_bytes(original + b"mutation")
        with self.assertRaisesRegex(reg.RegistryError, "Hash/size mismatch"):
            reg.verify_registry(self.out)

    def test_semantic_duplicate_detected_even_if_integrity_manifest_rehashed(self):
        self.captures([(SKILL_A, "/skills/a/SKILL.md"), (SKILL_NEW, "/skills/b/SKILL.md")])
        self.build()
        index_path = self.out / "OCCURRENCE_INDEX.json"
        index = self.read("OCCURRENCE_INDEX.json")
        index["rows"][1] = copy.deepcopy(index["rows"][0])
        dump(index_path, index)
        manifest = self.read("MANIFEST_SHA256.json")
        data = index_path.read_bytes()
        manifest["files"]["OCCURRENCE_INDEX.json"] = {"sha256": reg.sha(data), "bytes": len(data)}
        dump(self.out / "MANIFEST_SHA256.json", manifest)
        with self.assertRaisesRegex(reg.RegistryError, "Occurrence lost or duplicated"):
            reg.verify_registry(self.out)

    def test_rehashed_ambiguous_hash_cannot_be_forced_to_one_original(self):
        self.pin = make_bundle(self.bundle, skills=[("provider", "alpha", SKILL_A), ("other", "alpha", SKILL_A)])
        self.captures([(SKILL_A, "/plain/alpha/SKILL.md")])
        self.build(expected_originals=2)
        index = self.read("OCCURRENCE_INDEX.json")
        index["rows"][0]["association"]["matched_original_ids"] = [1]
        dump(self.out / "OCCURRENCE_INDEX.json", index)
        self.rehash_output_file("OCCURRENCE_INDEX.json")
        with self.assertRaisesRegex(reg.RegistryError, "conservative exact-byte/namespace recomputation"):
            reg.verify_registry(self.out)

    def test_rehashed_automatic_state_cannot_be_promoted_to_understood(self):
        self.captures([(SKILL_A, "/skills/alpha/SKILL.md")])
        self.build()
        index = self.read("OCCURRENCE_INDEX.json")
        index["rows"][0]["state"] = "UNDERSTOOD"
        dump(self.out / "OCCURRENCE_INDEX.json", index)
        self.rehash_output_file("OCCURRENCE_INDEX.json")
        with self.assertRaisesRegex(reg.RegistryError, "Unsupported generated occurrence state"):
            reg.verify_registry(self.out)

    def test_rehashed_manifest_cannot_drop_required_preserved_census(self):
        self.captures([(SKILL_A, "/skills/alpha/SKILL.md")])
        self.pin_pc_census()
        self.build()
        relative = "provenance/pc-asier/SOURCE_CENSUS.json"
        (self.out / relative).unlink()
        self.rehash_output_file(relative)
        with self.assertRaisesRegex(reg.RegistryError, "Missing capture object.*SOURCE_CENSUS"):
            reg.verify_registry(self.out)

    def test_stop_precheck_blocks_build_and_dangling_stop_symlink(self):
        self.captures()
        flag = self.root / "STOP"
        flag.write_text("requested")
        with self.assertRaisesRegex(reg.RegistryError, "STOP requested"):
            self.build(stop_file=flag)
        self.assertFalse(self.out.exists())
        flag.unlink()
        flag.symlink_to(self.root / "missing_stop_target")
        with self.assertRaisesRegex(reg.RegistryError, "STOP requested"):
            self.build(stop_file=flag)
        self.assertFalse(self.out.exists())

    def test_stop_during_writes_does_not_continue_or_change_inputs(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        flag = self.root / "STOP"
        original = reg.write_new
        writes = []
        before = (self.pc / "CAPTURE_MANIFEST.json").read_bytes()
        def intercept(*args):
            original(*args)
            writes.append(args[1])
            flag.write_text("cooperative stop after one write")
        with mock.patch.object(reg, "write_new", side_effect=intercept):
            with self.assertRaisesRegex(reg.RegistryError, "STOP requested"):
                self.build(stop_file=flag)
        self.assertEqual(len(writes), 1)
        self.assertEqual((self.pc / "CAPTURE_MANIFEST.json").read_bytes(), before)
        self.assertFalse((self.out / "MANIFEST_SHA256.json").exists())

    def test_manual_overlay_is_object_scoped_and_preserves_base(self):
        self.captures([(SKILL_NEW, "/pc/beta/SKILL.md")], [(SKILL_NEW, "/termux/beta/SKILL.md")])
        self.build()
        base_manifest = (self.out / "MANIFEST_SHA256.json").read_bytes()
        manual = self.manual_input(scoped=["pc-asier:0001"])
        target = self.root / "overlay"
        summary = reg.apply_overlays(self.out, manual, target)
        self.assertEqual(summary["new_manual_dossiers_supplied"], 1)
        self.assertEqual(summary["unique_objects_with_new_manual_instruction_review"], 1)
        self.assertEqual(summary["new_occurrences_with_manual_object_review"], 2)
        self.assertFalse((target / "inherited_evidence").exists())
        self.assertFalse((target / "objects").exists())
        self.assertEqual((self.out / "MANIFEST_SHA256.json").read_bytes(), base_manifest)
        for source, expected in (("pc-asier", True), ("termux", False)):
            dossier = json.loads((target / f"fichas/{source}/0001.json").read_bytes())
            self.assertEqual(dossier["evidence_dimensions"]["resources_reviewed_for_this_occurrence"], expected)
            self.assertFalse(dossier["evidence_dimensions"]["provider_runtime_tested"])
            self.assertEqual(dossier["fields"][reg.FIELDS[8]]["PC_Asier"], "NOT_TESTED")
        self.assertEqual(reg.verify_overlay(self.out, target)["affected_occurrences"], 2)

    def test_manual_review_cannot_unblock_raw_yaml(self):
        bad = b"---\nname: alpha\ndescription: bad: colon\n---\n"
        self.captures([(bad, "/raw/SKILL.md")])
        self.build()
        target = self.root / "overlay"
        summary = reg.apply_overlays(self.out, self.manual_input(digest=reg.sha(bad), state="UNCHANGED"), target)
        row = json.loads((target / "OCCURRENCE_INDEX.json").read_bytes())["rows"][0]
        self.assertEqual(row["state"], "BLOCKED")
        self.assertEqual(summary["occurrence_workflow_states"], {"BLOCKED": 1})

    def test_manual_overlay_rejects_scope_escalation_and_missing_fields(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        self.build()
        for case in ("VERIFIED", "runtime", "missing_field", "another_hash_scope", "path_escape"):
            path = self.manual_input()
            manual = json.loads(path.read_bytes())
            row = manual["rows"][0]
            if case == "VERIFIED": row["state"] = "VERIFIED"
            elif case == "runtime": row["evidence_dimensions"]["provider_runtime_tested"] = True
            elif case == "missing_field": del row["fields"][reg.FIELDS[0]]
            elif case == "another_hash_scope": row["evidence_dimensions"]["resources_reviewed_at_occurrence_ids"] = ["termux:9999"]
            else: row["evidence_refs"] = ["../escape.txt"]
            dump(path, manual)
            with self.subTest(case=case):
                with self.assertRaises(reg.RegistryError):
                    reg.apply_overlays(self.out, path, self.root / ("overlay_" + case))

    def test_nominal_dossiers_and_unique_reviewed_hashes_count_separately(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        self.build()
        path = self.manual_input()
        doc = json.loads(path.read_bytes()); doc["rows"].append(copy.deepcopy(doc["rows"][0])); dump(path, doc)
        summary = reg.apply_overlays(self.out, path, self.root / "overlay")
        self.assertEqual(summary["new_manual_dossiers_supplied"], 2)
        self.assertEqual(summary["unique_objects_with_new_manual_instruction_review"], 1)

    def test_overlay_stop_precheck_and_stale_base_binding(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")]); self.build()
        path = self.manual_input(); target = self.root / "overlay"
        flag = self.root / "STOP"; flag.write_text("stop")
        with self.assertRaisesRegex(reg.RegistryError, "STOP requested"):
            reg.apply_overlays(self.out, path, target, stop_file=flag)
        self.assertFalse(target.exists()); flag.unlink()
        reg.apply_overlays(self.out, path, target)
        manifest = self.out / "MANIFEST_SHA256.json"; manifest.write_bytes(manifest.read_bytes() + b"\n")
        with self.assertRaisesRegex(reg.RegistryError, "base manifest binding mismatch"):
            reg.verify_overlay(self.out, target)

    def test_build_with_manual_overlays_creates_verifiable_collection(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        manual = self.manual_input()
        with redirect_stdout(io.StringIO()):
            result = reg.main(["build", "--baseline", str(self.bundle), "--baseline-sha256", self.pin,
                "--capture-pc", str(self.pc), "--capture-termux", str(self.termux), "--output", str(self.out),
                "--expected-originals", "1", "--expected-pc", "1", "--expected-termux", "0", "--manual-overlays", str(manual)])
        self.assertEqual(result, 0)
        self.assertEqual(reg.verify_registry(self.out)["integrity"], "PASS")

    def test_tracking_sidecar_preserves_occurrence_ids(self):
        self.captures([(SKILL_A, "/pc/a/SKILL.md")], [(SKILL_NEW, "/termux/b/SKILL.md")]); self.build()
        target = self.root / "TRACKING.json"
        result = reg.write_tracking_map(self.out, target)
        self.assertEqual(result["tracking_rows"], 3)
        doc = json.loads(target.read_bytes())
        self.assertEqual([r["tracking_number"] for r in doc["rows"]], [1,2,3])
        self.assertEqual(doc["rows"][1]["occurrence_id"], "pc-asier:0001")
        self.assertEqual(doc["rows"][2]["occurrence_id"], "termux:0001")

    def test_deterministic_builds(self):
        self.captures([(SKILL_NEW, "/skills/beta/SKILL.md")])
        self.build()
        first = (self.out / "MANIFEST_SHA256.json").read_bytes()
        self.out = self.root / "second_output"
        self.build()
        self.assertEqual(first, (self.out / "MANIFEST_SHA256.json").read_bytes())

    def test_markdown_fence_cannot_be_closed_by_untrusted_content(self):
        fields = {key: "```\n<script>alert('x')</script>\n```" for key in reg.FIELDS}
        result = reg.markdown_dossier({"occurrence_id": "termux:0001", "fields": fields}).decode()
        self.assertIn("````json", result)
        self.assertEqual(result.count("## "), 21)


if __name__ == "__main__":
    unittest.main(verbosity=2)
