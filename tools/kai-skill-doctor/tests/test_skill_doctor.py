#!/usr/bin/env python3
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from skill_doctor import audit, inspect_roots, safe_view, sep_manifest, parse_frontmatter


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "skills"
        self.root.mkdir()
        self.skill = self.root / "demo"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text(
            "---\nname: demo\ndescription: Demo offline\n---\n\n# Hello\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_valid(self):
        v = audit(self.skill, self.root)
        self.assertEqual(v["status"], "READY_FOR_REVIEW")
        self.assertEqual(v["files"], 1)

    def test_manifest(self):
        m = sep_manifest(audit(self.skill,self.root), "kai-sample")
        self.assertEqual(m["uri"], "skill://kai-sample/demo/SKILL.md")
        self.assertEqual(len(m["resources"][0]["digest"]), 71)

    def test_name_mismatch(self):
        (self.skill/"SKILL.md").write_text("---\nname: other\ndescription: A valid text\n---\n", encoding="utf-8")
        self.assertIn("DIRECTORY_NAME_MISMATCH", audit(self.skill,self.root)["issues"])

    def test_no_frontmatter(self):
        (self.skill/"SKILL.md").write_text("# No metadata\n")
        self.assertEqual(audit(self.skill,self.root)["status"], "BLOCKED")

    def test_invalid_name(self):
        (self.skill/"SKILL.md").write_text("---\nname: bad name\ndescription: Yes\n---\n")
        self.assertEqual(audit(self.skill,self.root)["status"], "BLOCKED")

    def test_empty_description(self):
        (self.skill/"SKILL.md").write_text("---\nname: demo\ndescription: ''\n---\n")
        self.assertEqual(audit(self.skill,self.root)["status"], "BLOCKED")

    def test_dir_symlink_blocked(self):
        (self.root/"alias").symlink_to(self.skill, target_is_directory=True)
        self.assertEqual(audit(self.root/"alias",self.root)["status"], "LINK_REFERENCE")

    def test_resource_symlink_blocked(self):
        (self.skill/"ref.txt").symlink_to("/etc/passwd")
        self.assertEqual(audit(self.skill,self.root)["status"], "BLOCKED")

    def test_nested_dir_symlink_blocked(self):
        (self.skill/"sub").symlink_to(self.root,target_is_directory=True)
        self.assertEqual(audit(self.skill,self.root)["status"], "BLOCKED")

    def test_sensitive_path_blocked(self):
        (self.skill/".env").write_text("SECRET=DO_NOT_READ")
        v=audit(self.skill,self.root)
        self.assertEqual(v["status"], "BLOCKED")
        self.assertNotIn("DO_NOT_READ",str(safe_view(inspect_roots([self.root]))))

    def test_duplicate_names(self):
        second=self.root/"other"
        second.mkdir()
        (second/"SKILL.md").write_text("---\nname: demo\ndescription: Other\n---\n")
        r=inspect_roots([self.root])
        self.assertEqual(r["summary"]["duplicate_names"],2)

    def test_long_skill_rejected(self):
        (self.skill/"SKILL.md").write_bytes(b"A"*(256*1024+1))
        self.assertEqual(audit(self.skill,self.root)["status"],"BLOCKED")

    def test_large_resource_rejected(self):
        (self.skill/"big.bin").write_bytes(b"x" * (16*1024*1024 + 1))
        self.assertEqual(audit(self.skill,self.root)["status"],"BLOCKED")

    def test_readonly(self):
        before=(self.skill/"SKILL.md").stat().st_mtime_ns
        inspect_roots([self.root])
        self.assertEqual(before,(self.skill/"SKILL.md").stat().st_mtime_ns)

    def test_bad_server_id(self):
        with self.assertRaises(ValueError):
            sep_manifest(audit(self.skill,self.root),"bad host")

    def test_unapproved_cannot_export(self):
        (self.skill/"SKILL.md").write_text("No\n")
        with self.assertRaises(ValueError):
            sep_manifest(audit(self.skill,self.root),"kai-lab")


if __name__=="__main__":
    unittest.main()
