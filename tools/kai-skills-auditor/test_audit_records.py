"""Evidence boundaries and original identity coverage are non-negotiable."""
import copy
import unittest

from audit_records import FIELDS, generate_records


class AuditRecordTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [{'id': i, 'namespace': provider, 'name': 'same-name',
            'uri': f'skills://plugins/{provider}/same-name',
            'original_path': f'originals/{provider}/same-name/SKILL.md',
            'original_sha256': str(i)*64, 'portable_sha256': str(i)*64,
            'staged_root': f'providers/{provider}/skills/same-name'}
            for i, provider in ((1, 'one'), (2, 'two'))]
        self.matrix = [{'id': i, 'state': 'INSPECTED',
            'automated_static_inspected': True, 'manual_instruction_review': False,
            'whole_capability_verified': False} for i in (1, 2)]

    def test_duplicate_names_keep_provider_identity_and_static_is_not_understood(self):
        records = generate_records(self.catalog, self.matrix, {}, 2)
        self.assertEqual([r['stable_id'] for r in records], ['one:same-name', 'two:same-name'])
        for record in records:
            self.assertEqual(len(record['fields']), 21)
            self.assertEqual(record['fields'][FIELDS[-1]]['grado_inspeccion'], 'AUTOMATED_STATIC_ONLY')
            self.assertIn('NO_COMPROBADO', record['fields'][FIELDS[3]])
            self.assertEqual(record['fields'][FIELDS[17]]['prueba_funcional'], 'NO_COMPROBADO')

    def test_no_missing_duplicate_or_unknown_original_ids_are_accepted(self):
        for catalog in (self.catalog[:1], self.catalog + self.catalog[:1],
                        [self.catalog[0], dict(self.catalog[1], id=1)]):
            with self.subTest(catalog=catalog), self.assertRaises(ValueError):
                generate_records(catalog, self.matrix, {}, 2)
        with self.assertRaises(ValueError):
            generate_records(self.catalog, [self.matrix[0]]*2, {}, 2)
        with self.assertRaises(ValueError):
            generate_records(self.catalog, self.matrix, {3: {}}, 2)

    def test_manual_and_verification_claims_need_evidence_never_inferred_from_count(self):
        matrix = copy.deepcopy(self.matrix)
        matrix[0]['manual_instruction_review'] = True
        with self.assertRaises(ValueError):
            generate_records(self.catalog, matrix, {}, 2)
        with self.assertRaises(ValueError):
            generate_records(self.catalog, matrix, {1: {FIELDS[0]: 'partial'}}, 2)
        manual = {1: dict.fromkeys(FIELDS, 'Explicit synthetic manual evidence')}
        records = generate_records(self.catalog, matrix, manual, 2)
        self.assertEqual(records[0]['fields'], manual[1])
        matrix[0]['state'] = 'VERIFIED'
        with self.assertRaises(ValueError):
            generate_records(self.catalog, matrix, manual, 2)


if __name__ == '__main__':
    unittest.main()
