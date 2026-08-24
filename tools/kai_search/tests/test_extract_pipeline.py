import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "kai_search.py"
spec = importlib.util.spec_from_file_location("kai_search_pipeline", MODULE)
ks = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(ks)


class ExtractPipelineTests(unittest.TestCase):
    def test_pending_pipeline_extracts_once_and_reuses_cache(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            root = td / "files"; root.mkdir()
            (root / "alpha.txt").write_text("alpha", encoding="utf-8")
            (root / "beta.txt").write_text("beta", encoding="utf-8")
            calls = td / "calls.log"
            worker = td / "worker.py"
            worker.write_text(
                "import json,sys\n"
                f"calls={str(calls)!r}\n"
                "open(calls,'a',encoding='utf-8').write(sys.argv[1]+'\\n')\n"
                "print(json.dumps({'status':'OK','text':'PIPELINE_NEEDLE '+sys.argv[1],'values':[],"
                "'extractor_id':'test-worker','extractor_profile':'v1'}))\n",
                encoding="utf-8",
            )
            con = ks.connect(td / "catalog.db")
            try:
                ks.index_root(con, str(root), set())
                run = getattr(ks, "extract_pending", None)
                self.assertTrue(callable(run), "missing API: extract_pending")
                first = run(con, timeout=1, worker_script=worker,
                            extractor_id="test-worker", extractor_profile="v1")
                self.assertEqual(first["processed"], 2)
                self.assertEqual(first["statuses"], {"OK": 2})
                self.assertEqual(len(calls.read_text(encoding="utf-8").splitlines()), 2)
                self.assertEqual(len(ks.find_files(con, "PIPELINE_NEEDLE", limit=10)), 2)

                second = run(con, timeout=1, worker_script=worker,
                             extractor_id="test-worker", extractor_profile="v1")
                self.assertEqual(second["processed"], 0)
                self.assertEqual(second["cached"], 2)
                self.assertEqual(len(calls.read_text(encoding="utf-8").splitlines()), 2)
            finally:
                con.close()

    def test_profile_change_marks_cached_rows_pending(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); root = td / "files"; root.mkdir()
            target = root / "one.txt"; target.write_text("one", encoding="utf-8")
            worker = td / "worker.py"
            worker.write_text(
                "import json\nprint(json.dumps({'status':'OK','text':'PROFILE_NEEDLE','values':[],"
                "'extractor_id':'test-worker','extractor_profile':'v2'}))\n",
                encoding="utf-8",
            )
            con = ks.connect(td / "catalog.db")
            try:
                ks.index_root(con, str(root), set())
                fid = con.execute("SELECT id FROM files").fetchone()[0]
                ks.store_extraction_result(con, fid, {"status":"OK","text":"OLD","values":[],
                    "extractor_id":"test-worker","extractor_profile":"v1"})
                result = ks.extract_pending(
                    con, timeout=1, worker_script=worker,
                    extractor_id="test-worker", extractor_profile="v2",
                )
                self.assertEqual(result["processed"], 1)
                row = con.execute(
                    "SELECT extractor_profile,status FROM file_content WHERE file_id=?", (fid,)
                ).fetchone()
                self.assertEqual(tuple(row), ("v2", "OK"))
                self.assertEqual(len(ks.find_files(con, "PROFILE_NEEDLE", limit=10)), 1)
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
