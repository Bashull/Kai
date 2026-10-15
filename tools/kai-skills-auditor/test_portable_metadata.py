import json
import re
import unittest
import yaml

from portable_metadata import normalize_metadata


class MetadataPortabilityTests(unittest.TestCase):
    def test_nested_values_are_recoverable_and_body_bytes_survive(self):
        body = '## Acción\n\nConservar espacios:  a  b\nUnicode: á 🛠\n'
        raw = ('---\nname: demo\ndescription: Prueba con á y 🛠.\nmetadata:\n  nested:\n    enabled: true\n    retries: 2\n  label: untouched\n---\n' + body).encode()
        result, receipt = normalize_metadata(raw)
        match = re.match(br'^---\n(.*?)\n---\n', result, re.S)
        fm = yaml.safe_load(match[1].decode())
        self.assertTrue(all(isinstance(v, str) for v in fm['metadata'].values()))
        self.assertEqual(json.loads(fm['metadata']['nested']), {'enabled': True, 'retries': 2})
        self.assertEqual(fm['metadata']['label'], 'untouched')
        self.assertEqual(result[match.end():], body.encode())
        self.assertTrue(receipt['body_bytes_unchanged'])

    def test_valid_metadata_is_byte_identical_and_idempotent(self):
        raw = b'---\nname: demo\ndescription: test\nmetadata:\n  author: Kai\n---\nBody\n'
        result, receipt = normalize_metadata(raw)
        self.assertEqual(result, raw)
        self.assertIsNone(receipt)


if __name__ == '__main__':
    unittest.main()
