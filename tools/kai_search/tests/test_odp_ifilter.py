import base64
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "kai_search.py"
spec = importlib.util.spec_from_file_location("kai_search_odp", MODULE)
ks = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(ks)

@unittest.skipUnless(os.name == "nt", "Windows IFilter integration")
class WindowsOdpIFilterTests(unittest.TestCase):
    def test_valid_odp_recovers_text(self):
        fixture = Path(__file__).with_name("probe_odp.b64")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "probe.odp"
            target.write_bytes(base64.b64decode(fixture.read_text(encoding="ascii")))
            result = ks.extract_file_isolated(str(target), timeout=4)
            self.assertEqual(result["status"], "OK", result)
            self.assertIn("KAI_IFILTER_SENTINEL_ODP_VALID_77103", result["text"])

if __name__ == "__main__":
    unittest.main()