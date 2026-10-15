import json
from pathlib import Path
import tempfile
import unittest
from capture_skills import capture


class CaptureLimitTests(unittest.TestCase):
    def test_zero_count_does_not_publish_empty_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);c=root/'census.json';c.write_text(json.dumps({'roots':[tmp],'skills':[]}))
            with self.assertRaisesRegex(ValueError,'positive count'):capture(c,root/'out','termux',0)
            self.assertFalse((root/'out').exists())

    def test_negative_count_is_rejected_as_invalid_request(self):
        with self.assertRaisesRegex(ValueError,'positive count'):capture('unused','unused','termux',-1)


if __name__=='__main__':unittest.main()
