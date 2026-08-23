import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "kai_search.py"
spec = importlib.util.spec_from_file_location("kai_search_content", MODULE)
ks = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(ks)


class KaiSearchContentTests(unittest.TestCase):
    def require(self, name):
        fn = getattr(ks, name, None)
        self.assertTrue(callable(fn), f"missing API: {name}")
        return fn

    def test_schema_v2_has_content_state_and_fts_content(self):
        with tempfile.TemporaryDirectory() as td:
            con = ks.connect(Path(td) / "catalog.db")
            try:
                tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("file_content", tables)
                cols = {r[1] for r in con.execute("PRAGMA table_info(file_content)")}
                required = {"file_id", "text", "status", "extractor_id", "extractor_profile", "source_mtime_ns"}
                self.assertTrue(required <= cols)
                fts_cols = {r[1] for r in con.execute("PRAGMA table_info(file_fts)")}
                self.assertIn("content", fts_cols)
            finally:
                con.close()

    def test_isolated_worker_reports_ok_timeout_and_crash(self):
        run = self.require("extract_file_isolated")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            worker = td / "worker.py"
            worker.write_text(
                "import json,sys,time\n"
                "p=sys.argv[1]\n"
                "if p.endswith('hang'): time.sleep(5)\n"
                "elif p.endswith('crash'): raise SystemExit(7)\n"
                "else: print(json.dumps({'status':'OK','text':'needle-content','values':['meta'],'extractor_id':'test-worker','extractor_profile':'v1'}))\n",
                encoding="utf-8",
            )
            ok = run(str(td / "ok"), timeout=1, worker_script=worker)
            self.assertEqual(ok["status"], "OK")
            self.assertEqual(ok["text"], "needle-content")
            timeout = run(str(td / "hang"), timeout=0.1, worker_script=worker)
            self.assertEqual(timeout["status"], "TIMEOUT")
            crash = run(str(td / "crash"), timeout=1, worker_script=worker)
            self.assertEqual(crash["status"], "CRASH")

    def test_ok_content_becomes_searchable_then_invalidates_on_change(self):
        store = self.require("store_extraction_result")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "files"
            root.mkdir()
            target = root / "opaque.bin"
            target.write_bytes(b"first payload")
            con = ks.connect(Path(td) / "catalog.db")
            try:
                ks.index_root(con, str(root), set())
                file_id = con.execute("SELECT id FROM files WHERE path=?", (ks.norm_path(target),)).fetchone()[0]
                store(con, file_id, {
                    "status": "OK",
                    "text": "KAI_CONTENT_NEEDLE_551",
                    "values": ["author-meta"],
                    "extractor_id": "test-worker",
                    "extractor_profile": "v1",
                })
                found = ks.find_files(con, "KAI_CONTENT_NEEDLE_551", limit=10)
                self.assertEqual([r["path"] for r in found], [ks.norm_path(target)])
                target.write_bytes(b"second payload with changed size")
                ks.index_root(con, str(root), set())
                self.assertIsNone(con.execute("SELECT 1 FROM file_content WHERE file_id=?", (file_id,)).fetchone())
                self.assertEqual(ks.find_files(con, "KAI_CONTENT_NEEDLE_551", limit=10), [])
            finally:
                con.close()

    def test_failure_details_are_never_indexed_as_content(self):
        store = self.require("store_extraction_result")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "files"
            root.mkdir()
            target = root / "broken.bin"
            target.write_bytes(b"x")
            con = ks.connect(Path(td) / "catalog.db")
            try:
                ks.index_root(con, str(root), set())
                file_id = con.execute("SELECT id FROM files").fetchone()[0]
                store(con, file_id, {
                    "status": "HANDLER_ERROR",
                    "text": "SHOULD_NOT_BE_SEARCHABLE_991",
                    "values": ["SHOULD_NOT_BE_SEARCHABLE_992"],
                    "error": "SHOULD_NOT_BE_SEARCHABLE_993",
                    "extractor_id": "test-worker",
                    "extractor_profile": "v1",
                })
                self.assertEqual(ks.find_files(con, "SHOULD_NOT_BE_SEARCHABLE", limit=10), [])
                row = con.execute("SELECT status,error FROM file_content WHERE file_id=?", (file_id,)).fetchone()
                self.assertEqual(tuple(row), ("HANDLER_ERROR", "SHOULD_NOT_BE_SEARCHABLE_993"))
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
