import copy
import unittest
from quality_checks import profile_keys, profile_freshness, profile_join


class QualityChecksTests(unittest.TestCase):
    def test_duplicate_denominators_and_nulls(self):
        d=profile_keys([{'id':'A'},{'id':'A'},{'id':None},{'id':'B'}],['id'])
        self.assertEqual(d['missing_key_rows'],1)
        self.assertEqual(d['duplicate_excess_rows'],1)
        self.assertEqual(d['duplicate_affected_rows'],2)
        self.assertEqual(d['duplicate_affected_share_all_rows'],0.5)

    def test_normalization_collisions_are_separate(self):
        d=profile_keys([{'id':'A'},{'id':'a'},{'id':' A '}],['id'],normalize_strings=True)
        self.assertEqual(d['duplicate_excess_rows'],0)
        self.assertEqual(d['normalization_collision_groups'],1)

    def test_empty_denominator_is_unknown(self):
        d=profile_keys([],['id']);self.assertIsNone(d['missing_key_share_all_rows']);self.assertEqual(d['status'],'EMPTY')

    def test_input_never_modified(self):
        rows=[{'id':' A '}];old=copy.deepcopy(rows);profile_keys(rows,['id'],normalize_strings=True);self.assertEqual(rows,old)

    def test_composite_key(self):
        d=profile_keys([{'a':1,'b':2},{'a':1,'b':3}],['a','b']);self.assertEqual(d['duplicate_excess_rows'],0)

    def test_missing_fields_are_not_valid_keys(self):
        self.assertEqual(profile_keys([{},{}],['id'])['missing_key_rows'],2)

    def test_nulls_are_not_duplicate_business_keys(self):
        self.assertEqual(profile_keys([{'id':None},{'id':None}],['id'])['duplicate_excess_rows'],0)

    def test_no_implicit_key(self):
        with self.assertRaises(ValueError):profile_keys([{'id':1}],[])

    def test_timestamp_requires_timezone(self):
        d=profile_freshness([{'t':'2026-10-15T09:00:00'}],'t','2026-10-15T10:00:00Z')
        self.assertEqual(d['invalid_or_timezone_missing_rows'],1);self.assertIsNone(d['age_seconds'])

    def test_timezone_offsets_compared_as_instants(self):
        d=profile_freshness([{'t':'2026-10-15T12:00:00+02:00'}],'t','2026-10-15T11:00:00Z')
        self.assertEqual(d['age_seconds'],3600)

    def test_future_timestamp_cannot_fake_freshness(self):
        d=profile_freshness([{'t':'2026-10-15T12:00:00Z'},{'t':'2026-10-14T10:00:00Z'}],'t','2026-10-15T10:00:00Z')
        self.assertEqual(d['future_rows'],1);self.assertEqual(d['age_seconds'],86400)

    def test_all_future_is_unknown(self):
        d=profile_freshness([{'t':'2099-01-01T00:00:00Z'}],'t','2026-01-01T00:00:00Z');self.assertIsNone(d['age_seconds'])

    def test_join_expansion_orphans_and_nulls(self):
        l=[{'k':'A'},{'k':'B'},{'k':None}];r=[{'k':'A'},{'k':'A'},{'k':None}]
        d=profile_join(l,r,['k'],['k']);self.assertEqual(d['left_join_rows'],4);self.assertEqual(d['inner_join_rows'],2)
        self.assertEqual(d['unmatched_nonmissing_left_rows'],1);self.assertEqual(d['missing_left_key_rows'],1)

    def test_null_join_keys_do_not_match(self):
        d=profile_join([{'k':None}],[{'k':None}],['k'],['k']);self.assertEqual(d['inner_join_rows'],0)

    def test_join_contract_same_number_of_fields(self):
        with self.assertRaises(ValueError):profile_join([],[],['a'],['a','b'])

    def test_row_shape_is_validated(self):
        with self.assertRaises(ValueError):profile_keys([['A']],['id'])


if __name__=='__main__':unittest.main()
