import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from bundle_io import sha
from capture_skills import capture
from federated_registry import read_capture, federate, inspect_text


class FederationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root/'source'; self.source.mkdir()
        self.text = b'---\nname: same\ndescription: synthetic\n---\nBody\n'
        rows = []
        for i in range(2):
            p = self.source/str(i)/'SKILL.md'; p.parent.mkdir(); p.write_bytes(self.text)
            rows.append({'path': str(p), 'bytes': len(self.text), 'sha256': sha(self.text)})
        p = self.root/'census.json'; p.write_text(json.dumps({'roots':[str(self.source)],'skills':rows}))
        self.receipt = capture(p,self.root/'captured','termux',2)
        self.zip = Path(self.receipt['zip']); self.pin = self.receipt['sha256']
        self.catalog = [{'id':1,'namespace':'provider','name':'same','original_path':'originals/same/SKILL.md','original_sha256':sha(self.text)}]
        orig = self.root/self.catalog[0]['original_path']; orig.parent.mkdir(parents=True); orig.write_bytes(self.text)

    def loaded(self): return read_capture(self.zip,self.pin,'termux',2)

    def mutate_zip(self, modify):
        with zipfile.ZipFile(self.zip) as z: files={n:z.read(n) for n in z.namelist()}
        modify(files)
        p=self.root/'changed.zip'
        with zipfile.ZipFile(p,'w') as z:
            for n,b in files.items(): z.writestr(n,b)
        return p,sha(p.read_bytes())

    def test_real_capture_has_two_occurrences_one_object(self):
        m,o=self.loaded(); self.assertEqual(len(m['rows']),2);self.assertEqual(m['unique_captured_objects'],1)

    def test_wrong_pin_rejected(self):
        with self.assertRaises(ValueError):read_capture(self.zip,'0'*64,'termux',2)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):read_capture(self.zip,self.pin,'termux',True)

    def test_wrong_collection_rejected(self):
        with self.assertRaises(ValueError):read_capture(self.zip,self.pin,'pc-asier',2)

    def test_stop_before_read(self):
        p=self.root/'STOP';p.touch()
        with self.assertRaises(RuntimeError):read_capture(self.zip,self.pin,'termux',2,p)

    def test_traversal_member_rejected(self):
        p,pin=self.mutate_zip(lambda f:f.update({'../outside':b'x'}))
        with self.assertRaises(ValueError):read_capture(p,pin,'termux',2)

    def test_unmanifested_payload_rejected(self):
        p,pin=self.mutate_zip(lambda f:f.update({'unexpected.txt':b'x'}))
        with self.assertRaises(ValueError):read_capture(p,pin,'termux',2)

    def test_corrupted_object_rejected(self):
        def f(files):
            k=next(k for k in files if k.startswith('objects/'));files[k]=b'bad'
        p,pin=self.mutate_zip(f)
        with self.assertRaises(ValueError):read_capture(p,pin,'termux',2)

    def test_duplicate_bytes_keep_all_historical_ids(self):
        result=federate(self.root,self.catalog,[self.loaded()])
        self.assertEqual([r['historical_id'] for r in result['records']],['ORI-0001','TMX-0001','TMX-0002'])
        self.assertEqual(result['summary']['distinct_main_text_hashes'],1)
        self.assertEqual(result['summary']['duplicate_occurrences_beyond_first'],2)

    def test_duplicate_bytes_never_certify_capabilities(self):
        d=federate(self.root,self.catalog,[self.loaded()])
        self.assertIsNone(d['summary']['unique_functional_capabilities'])
        self.assertTrue(all(r['understanding_level']=='L1_INVENTORIED' and not r['whole_capability_verified'] for r in d['records']))
        self.assertTrue(all(e['scope']=='DOCUMENT_BYTES_ONLY' for e in d['edges']))

    def test_collection_cannot_be_added_twice(self):
        with self.assertRaises(ValueError):federate(self.root,self.catalog,[self.loaded(),self.loaded()])

    def test_original_hash_cannot_be_substituted(self):
        self.catalog[0]['original_sha256']='0'*64
        with self.assertRaises(ValueError):federate(self.root,self.catalog,[])

    def test_boolean_original_id_rejected(self):
        self.catalog[0]['id']=True
        with self.assertRaises(ValueError):federate(self.root,self.catalog,[])

    def test_line_endings_grouped_without_rewriting_bytes(self):
        a=inspect_text(self.text); b=inspect_text(self.text.replace(b'\n',b'\r\n'))
        self.assertEqual(a['normalized_text_sha256'],b['normalized_text_sha256'])
        self.assertNotEqual(sha(self.text),sha(self.text.replace(b'\n',b'\r\n')))

    def test_case_sensitive_identifiers_never_normalized(self):
        self.assertNotEqual(inspect_text(b'Account A\n')['normalized_text_sha256'],inspect_text(b'Account a\n')['normalized_text_sha256'])

    def test_bad_yaml_is_recorded(self):
        self.assertEqual(inspect_text(b'---\nname: [\n---\n')['frontmatter'],'INVALID_YAML')


if __name__=='__main__':unittest.main()
