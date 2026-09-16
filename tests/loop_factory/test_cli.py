import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from core.loop_factory.cli import main
from core.loop_factory.writeback import render_drive_checkpoint_markdown


class CliTests(unittest.TestCase):
    def test_init_creates_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.loopfactory.db"
            self.assertEqual(main(["init", "--db", str(db)]), 0)
            self.assertTrue(db.exists())

    def test_workers_output_is_json(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["workers"])
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(stream.getvalue()), list)

    def test_checkpoint_markdown_has_next_action(self):
        text = render_drive_checkpoint_markdown({
            "job_id": "demo",
            "next_exact_action": "review evidence",
        })
        self.assertIn("demo", text)
        self.assertIn("review evidence", text)

    def test_create_and_show_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "state.loopfactory.db"
            manifest = root / "job.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "job_id": "cli-demo",
                "project": "KAI_LOOP_FACTORY",
                "cell_type": "BUILD",
                "goal": "cli round trip",
                "current_authority_refs": [],
                "input_refs": [],
                "input_hashes": {},
                "dependencies": [],
                "allowed_tools": ["demo-file"],
                "write_scope": [str(root / "sandbox")],
                "autonomy_level": "A2",
                "budget": {
                    "currency": "EUR", "max_cost_eur": 0.0,
                    "max_iterations": 2, "max_retries": 1, "timeout_seconds": 30,
                },
                "state": "QUEUED", "worker": None, "attempt": 0,
                "evidence_refs": [], "last_error_class": None,
                "next_exact_action": None,
                "created_at": "2026-09-16T00:00:00Z",
                "updated_at": "2026-09-16T00:00:00Z",
            }), encoding="utf-8")
            self.assertEqual(main(["init", "--db", str(db)]), 0)
            self.assertEqual(main(["create", "--db", str(db), "--manifest", str(manifest)]), 0)
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(["show", "--db", str(db), "cli-demo"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stream.getvalue())["job_id"], "cli-demo")
