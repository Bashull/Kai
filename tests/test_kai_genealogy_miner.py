from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_genealogy_miner import compare_files


class GenealogyMinerTests(unittest.TestCase):
    def test_exact_copy_requires_sha256_equality(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left.py"
            right = root / "right.py"
            source = "def pulse():\n    return 'kai'\n"
            left.write_text(source, encoding="utf-8")
            right.write_text(source, encoding="utf-8")
            result = compare_files(left, right)
            self.assertEqual(result["relation"], "EXACT_COPY")
            self.assertTrue(result["same_sha256"])

    def test_zero_byte_variant_is_corrupted_placeholder(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "kai_mapper.py"
            right = root / "other" / "kai_mapper.py"
            right.parent.mkdir()
            left.write_bytes(b"")
            right.write_text("def map_repo():\n    return True\n", encoding="utf-8")
            result = compare_files(left, right)
            self.assertEqual(result["relation"], "CORRUPTED_PLACEHOLDER")
            self.assertEqual(result["placeholder_side"], "left")

    def test_changed_python_version_is_functional_ancestor_candidate(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left_dir = root / "old"
            right_dir = root / "new"
            left_dir.mkdir()
            right_dir.mkdir()
            left = left_dir / "kai_mapper.py"
            right = right_dir / "kai_mapper.py"
            left.write_text(
                "import json\nclass Mapper:\n    pass\ndef map_repo():\n    return 1\n",
                encoding="utf-8",
            )
            right.write_text(
                "import json\nclass Mapper:\n    pass\ndef map_repo():\n    return 2\ndef scan_repo():\n    return 3\n",
                encoding="utf-8",
            )
            os.utime(left, (1000, 1000))
            os.utime(right, (2000, 2000))
            result = compare_files(left, right)
            self.assertEqual(result["relation"], "FUNCTIONAL_ANCESTOR_CANDIDATE")
            self.assertEqual(result["suggested_direction"], "LEFT_TO_RIGHT")
            self.assertGreaterEqual(result["python_comparison"]["symbol_jaccard"], 0.5)

    def test_same_timestamp_order_without_structure_does_not_claim_ancestry(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left.py"
            right = root / "right.py"
            left.write_text("def alpha():\n    return 1\n", encoding="utf-8")
            right.write_text("def beta():\n    return 2\n", encoding="utf-8")
            os.utime(left, (1000, 1000))
            os.utime(right, (2000, 2000))
            result = compare_files(left, right)
            self.assertEqual(result["relation"], "UNRELATED_OR_UNKNOWN")
            self.assertEqual(result["suggested_direction"], "UNKNOWN")

    def test_parse_failure_is_preserved_as_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "broken.py"
            right = root / "valid.py"
            left.write_text("def broken(:\n", encoding="utf-8")
            right.write_text("def valid():\n    return True\n", encoding="utf-8")
            result = compare_files(left, right)
            self.assertIsNotNone(result["left"]["structure"]["parse_error"])
            self.assertIsNone(result["right"]["structure"]["parse_error"])


if __name__ == "__main__":
    unittest.main()
