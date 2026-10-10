import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'docs/minecraft/donor-ledger.json'
VALIDATOR = ROOT / 'docs/minecraft/validate_donors.py'


def validator():
    spec = importlib.util.spec_from_file_location('validate_donors', VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DonorLedgerTests(unittest.TestCase):
    def test_pinned_manifest_exists_and_all_entries_have_provenance(self):
        data = json.loads(LEDGER.read_text(encoding='utf-8'))
        count = validator().validate(data)
        self.assertGreaterEqual(count, 15)
        self.assertEqual(count, len(data['donors']))

    def test_invalid_revision_is_rejected(self):
        data = {'donors': [self.good_donor(commit='main')]}
        with self.assertRaisesRegex(ValueError, 'commit'):
            validator().validate(data)

    def test_unknown_license_cannot_be_copy_approved(self):
        data = {'donors': [self.good_donor(license='UNVERIFIED',policy='ADAPT')]}
        with self.assertRaisesRegex(ValueError, 'license'):
            validator().validate(data)

    def test_strong_copyleft_cannot_be_implicitly_merged(self):
        data = {'donors': [self.good_donor(license='AGPL-3.0',policy='ADAPT')]}
        with self.assertRaisesRegex(ValueError, 'copyleft'):
            validator().validate(data)

    def test_duplicate_repos_not_accepted(self):
        a=self.good_donor()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validator().validate({'donors':[a, a]})

    def test_origin_url_matches_repository_and_no_secret_values(self):
        x=self.good_donor(url='https://evil.example.org/repo')
        with self.assertRaisesRegex(ValueError, 'URL'):
            validator().validate({'donors':[x]})

    @staticmethod
    def good_donor(**override):
        a={'repo':'example/test','url':'https://github.com/example/test','branch':'main','commit':'a'*40,
           'license':'MIT','policy':'ADAPT','role':'test fixture','license_evidence':'GitHub license metadata',
           'verified_at':'2026-10-10'}
        return {**a,**override}


if __name__=='__main__':
    unittest.main()
