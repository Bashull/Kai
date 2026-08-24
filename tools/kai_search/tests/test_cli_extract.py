import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "kai_search.py"

class KaiSearchCliExtractTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def test_index_extract_find_content(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            root = td / "files"
            root.mkdir()
            target = root / "note.txt"
            sentinel = "KAISEARCH_CLI_CONTENT_88102"
            target.write_text(sentinel + " contenido directo", encoding="utf-8")
            db = td / "catalog.db"
            indexed = self.run_cli("--db", db, "index", root)
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            extracted = self.run_cli("--db", db, "extract", "--limit", "10", "--timeout", "3")
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            summary = json.loads(extracted.stdout)
            self.assertEqual(summary["processed"], 1)
            self.assertEqual(summary["statuses"].get("OK"), 1)
            found = self.run_cli("--db", db, "find", sentinel)
            self.assertEqual(found.returncode, 0, found.stderr)
            rows = json.loads(found.stdout)
            self.assertEqual([r["path"] for r in rows], [str(target).lower()])

if __name__ == "__main__":
    unittest.main()