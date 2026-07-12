from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from tools.kai_federation_bootstrap import build_adapter
from tools.kai_source_adapters import KaiMasterInventoryAdapter, LocalGitAdapter


class FederationBootstrapTests(unittest.TestCase):
    def test_factory_builds_known_adapter_and_rejects_unknown(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "inventory.sqlite3"
            source = {
                "source_id": "pc:kai-master",
                "kind": "KAI_MASTER_INVENTORY",
                "adapter": "kai_master_inventory",
                "path": str(db),
            }
            self.assertIsInstance(build_adapter(source), KaiMasterInventoryAdapter)
            with self.assertRaisesRegex(ValueError, "unsupported adapter"):
                build_adapter({"source_id": "bad", "adapter": "arbitrary_python"})

    def test_local_git_factory_reads_roots_path(self):
        with TemporaryDirectory() as tmp:
            roots_path = Path(tmp) / "roots.json"
            roots_path.write_text(json.dumps({"roots": [str(Path(tmp) / "repo")]}), encoding="utf-8")
            source = {
                "source_id": "pc:git-repos",
                "kind": "GIT_LOCAL",
                "adapter": "local_git",
                "roots_path": str(roots_path),
            }
            adapter = build_adapter(source)
            self.assertIsInstance(adapter, LocalGitAdapter)
            self.assertEqual(len(adapter.roots), 1)


if __name__ == "__main__":
    unittest.main()
