"""Behavioral grouping checks: no silent review propagation or identity loss."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('group007', Path(__file__).with_name('group_capabilities.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    def row(rid, source, digest, provider, name):
        return {'historical_id': rid, 'source': source, 'sha256': digest * 64,
                'author_provider': provider, 'text_profile': {'name': name}}
    reg = {'format': 'kai.skills.federation/1', 'records': [
        row('ORI-0001', 'originals', 'a', 'provider-a', 'export'),
        row('ORI-0002', 'originals', 'b', 'provider-b', 'export'),
        row('PC-0001', 'pc-asier', 'a', 'NOT_REVIEWED', 'export'),
        row('TMX-0001', 'termux', 'c', 'NOT_REVIEWED', None)]}
    audit = {'rows': [{'id': 1, 'manual_instruction_review': True},
                      {'id': 2, 'manual_instruction_review': False}]}
    families = {'format': 'kai.skills.reviewed-families/1', 'candidate_ids': [1],
                'families': [{'id': 'exports', 'title': 'Exports', 'members': ['ORI-0001'], 'basis': 'Manual'}]}
    return reg, audit, families


class GroupingTests(unittest.TestCase):
    def call(self, r=None, a=None, f=None):
        original = fixture()
        return module.build_groups(r or original[0], a or original[1], f or original[2],
                                   {'originals': 2, 'pc-asier': 1, 'termux': 1})

    def test_exact_document_clone_retains_both_occurrences_without_review_propagation(self):
        x = self.call();g = next(g for g in x['document_byte_groups'] if len(g['members']) == 2)
        self.assertEqual(g['members'], ['ORI-0001', 'PC-0001'])
        self.assertIn('PC-0001', x['pending_deep_review_ids'])
        self.assertFalse(x['whole_capabilities_verified'])

    def test_same_name_different_provider_is_only_a_metadata_hint(self):
        x = self.call();self.assertEqual(len(x['original_provider_groups']), 2)
        self.assertEqual(x['declared_name_groups']['export']['members'], ['ORI-0001', 'ORI-0002', 'PC-0001'])
        self.assertIn('NOT_FUNCTIONAL_EQUIVALENCE', x['declared_name_groups']['export']['scope'])
        self.assertIsNone(x['summary']['unique_functional_capabilities'])

    def test_byte_distinct_documents_remain_separate_and_inputs_unchanged(self):
        r, a, f = fixture();before = copy.deepcopy((r, a, f));x = self.call(r, a, f)
        self.assertEqual(len(x['document_byte_groups']), 3)
        self.assertEqual((r, a, f), before)
        self.assertEqual(x['unnamed_main_ids'], ['TMX-0001'])

    def test_unreviewed_original_cannot_acquire_reviewed_family(self):
        r, a, f = fixture();f['families'][0]['members'].append('ORI-0002')
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):self.call(r, a, f)

    def test_reviewed_original_cannot_be_counted_in_two_families(self):
        r, a, f = fixture();f['families'].append({'id': 'other', 'members': ['ORI-0001']})
        with self.assertRaisesRegex(ValueError, 'exclusive'):self.call(r, a, f)

    def test_no_reviewed_original_may_be_silently_omitted(self):
        r, a, f = fixture();a['rows'][1]['manual_instruction_review'] = True
        with self.assertRaisesRegex(ValueError, 'Every individually'):self.call(r, a, f)

    def test_reassigned_historical_id_is_rejected(self):
        r, a, f = fixture();r['records'][1]['historical_id'] = 'ORI-0999'
        with self.assertRaisesRegex(ValueError, 'reassigned'):self.call(r, a, f)

    def test_missing_or_duplicate_occurrence_is_rejected(self):
        r, a, f = fixture();r['records'][-1]['historical_id'] = 'PC-0001'
        with self.assertRaisesRegex(ValueError, 'historical identity'):self.call(r, a, f)

    def test_unverified_hash_and_inflated_candidate_are_rejected(self):
        r, a, f = fixture();r['records'][2]['sha256'] = None
        with self.assertRaisesRegex(ValueError, 'hash'):self.call(r, a, f)
        r, a, f = fixture();f['candidate_ids'].append(2)
        with self.assertRaisesRegex(ValueError, 'Candidate'):self.call(r, a, f)


if __name__ == '__main__':
    unittest.main(verbosity=2)
