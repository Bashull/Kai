import base64
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "kai_search.py"
spec = importlib.util.spec_from_file_location("kai_search_ifilter", MODULE)
ks = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(ks)


@unittest.skipUnless(os.name == "nt", "Windows IFilter integration")
class WindowsIFilterTests(unittest.TestCase):
    def test_default_worker_extracts_plain_text_without_searchindexer(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sentinel.txt"
            sentinel = "KAISEARCH_IFILTER_TEST_44117 direct text extraction"
            target.write_text(sentinel, encoding="utf-8")
            result = ks.extract_file_isolated(str(target), timeout=3)
            self.assertEqual(result["status"], "OK", result)
            self.assertIn(sentinel, result["text"])
            self.assertEqual(result["extractor_id"], "windows-ifilter")
            self.assertTrue(result["extractor_profile"].startswith("init0"))


@unittest.skipUnless(os.name == "nt", "Windows IFilter integration")
class WindowsIFilterFailureTests(unittest.TestCase):
    def test_missing_file_fails_closed_without_searchable_text(self):
        result = ks.extract_file_isolated(r"C:\definitely_missing_kai_44117.zzz", timeout=3)
        self.assertNotEqual(result["status"], "OK", result)
        self.assertEqual(result["text"], "")

    def test_unknown_extension_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "opaque.kaiunknown"
            target.write_bytes(b"KAI_UNKNOWN_HANDLER_SENTINEL_44118")
            result = ks.extract_file_isolated(str(target), timeout=3)
            self.assertNotEqual(result["status"], "OK", result)
            self.assertNotIn("KAI_UNKNOWN_HANDLER_SENTINEL_44118", result["text"])

    def test_corrupt_docx_does_not_crash_supervisor(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "broken.docx"
            target.write_bytes(b"not a zip package KAI_CORRUPT_44119")
            result = ks.extract_file_isolated(str(target), timeout=3)
            self.assertIn(result["status"], {"UNSUPPORTED", "HANDLER_ERROR", "OK"}, result)
            if result["status"] != "OK":
                self.assertEqual(result["text"], "")


@unittest.skipUnless(os.name == "nt", "Windows IFilter integration")
class WindowsPdfIFilterTests(unittest.TestCase):
    def test_pdf_uses_registered_filter_and_recovers_text(self):
        fixture = Path(__file__).with_name("probe_pdf.b64")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "probe.pdf"
            target.write_bytes(base64.b64decode(fixture.read_text(encoding="ascii")))
            result = ks.extract_file_isolated(str(target), timeout=4)
            self.assertEqual(result["status"], "OK", result)
            self.assertIn("KAI_IFILTER_SENTINEL_PDF_86440", result["text"])
            self.assertEqual(result["extractor_id"], "windows-ifilter")
            self.assertEqual(result["extractor_profile"], ks.WINDOWS_IFILTER_PROFILE)

if __name__ == "__main__":
    unittest.main()

