import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "kai_search.py"
spec = importlib.util.spec_from_file_location("kai_search", MODULE)
ks = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(ks)


class KaiSearchSmokeTests(unittest.TestCase):
    def test_index_find_and_dupes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "files"
            root.mkdir()
            (root / "alpha-note.txt").write_text("same payload", encoding="utf-8")
            (root / "copy-alpha.txt").write_text("same payload", encoding="utf-8")
            (root / "unique.bin").write_bytes(b"different")

            db = Path(td) / "catalog.db"
            con = ks.connect(db)
            result = ks.index_root(con, str(root), set())
            self.assertEqual(result["files_seen"], 3)

            found = ks.find_files(con, "alpha", limit=10)
            self.assertEqual(len(found), 2)

            groups = ks.duplicate_groups(con, min_size=1)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["count"], 2)
            self.assertEqual(groups[0]["wasted_bytes"], len("same payload"))

            # A second unchanged scan should preserve cached hashes.
            result2 = ks.index_root(con, str(root), set())
            self.assertEqual(result2["changed_or_new"], 0)
            hashed = con.execute(
                "SELECT count(*) FROM files WHERE fullhash IS NOT NULL"
            ).fetchone()[0]
            self.assertEqual(hashed, 2)


if __name__ == "__main__":
    unittest.main()
