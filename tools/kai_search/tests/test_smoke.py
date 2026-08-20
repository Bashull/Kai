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
            try:
                result = ks.index_root(con, str(root), set())
                self.assertEqual(result["files_seen"], 3)

                found = ks.find_files(con, "alpha", limit=10)
                self.assertEqual(len(found), 2)

                groups = ks.duplicate_groups(con, min_size=1)
                self.assertEqual(len(groups), 1)
                self.assertEqual(groups[0]["count"], 2)
                self.assertEqual(groups[0]["wasted_bytes"], len("same payload"))

                result2 = ks.index_root(con, str(root), set())
                self.assertEqual(result2["changed_or_new"], 0)
                hashed = con.execute(
                    "SELECT count(*) FROM files WHERE fullhash IS NOT NULL"
                ).fetchone()[0]
                self.assertEqual(hashed, 2)
            finally:
                con.close()

    def test_catalog_can_be_skipped_inside_indexed_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "wanted.txt").write_text("hello", encoding="utf-8")
            db = root / "catalog.db"
            con = ks.connect(db)
            try:
                db_abs = ks.norm_path(db)
                skip = {db_abs, db_abs + "-wal", db_abs + "-shm"}
                result = ks.index_root(con, str(root), set(), skip)
                self.assertEqual(result["files_seen"], 1)
                paths = [r[0] for r in con.execute("SELECT path FROM files")]
                self.assertEqual(paths, [ks.norm_path(root / "wanted.txt")])
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
