import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('kai_skill_auditor',Path(__file__).with_name('kai_skill_auditor.py'))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AuditorTests(unittest.TestCase):
    def test_847_synthetic_read_audit_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); inp=base/'raw'; inp.mkdir()
            records=[]
            for i in range(1,848):
                slug=f'skill-{i:04d}'
                body=f'---\nname: {slug}\ndescription: Used for synthetic test {i}. Use when asked explicitly.\n---\n# {slug}\nCheck results and verify provenance.\n'
                records.append({'index':i,'uri':f'skills://plugins/synthetic/{slug}','description':f'Use when testing {slug}.','resources':[{'uri':f'skills://plugins/synthetic/{slug}','content':body}]})
            for start in range(0,847,24):
                arr=records[start:start+24]
                (inp/f'skills_{start+1:04d}_{start+len(arr):04d}.json').write_text(json.dumps(arr))
            # A duplicate exact payload must not count twice.
            (inp/'skills_0010_0010.json').write_text(json.dumps([records[9]]))
            result=module.main(['--source',str(inp),'--out',str(base/'out')])
            self.assertEqual(result,0)
            info=json.loads((base/'out'/'RESULTADO.json').read_text())
            self.assertEqual(info['count'],847)
            self.assertEqual(info['missing'],[])
            self.assertEqual(info['conflicts'],0)
            with zipfile.ZipFile(info['zip']) as z:
                self.assertIsNone(z.testzip())
                contents=z.namelist()
                self.assertEqual(len([x for x in contents if x.startswith('originals/')]),847)
                self.assertEqual(len([x for x in contents if x.startswith('candidates/')]),847)
                self.assertEqual(len([x for x in contents if x.startswith('reviews/')]),847)
                metadata=json.loads(z.read('MANIFEST.json'))
                for record in metadata['files']:
                    self.assertEqual(hashlib.sha256(z.read(record['path'])).hexdigest(),record['sha256'])
    def test_conflict_detected(self):
        a={'index':1,'uri':'skills://plugins/x/test','resources':[{'uri':'skills://plugins/x/test','content':'---\nname: test\ndescription: A\n---\nA'}]}
        b=json.loads(json.dumps(a));b['resources'][0]['content']='---\nname: test\ndescription: B\n---\nB'
        a['_archive_file']='A.json';b['_archive_file']='B.json'
        rows,conflicts,missing=module.deduplicate([a,b],2)
        self.assertEqual(len(rows),1)
        self.assertEqual(len(conflicts),1)
        self.assertEqual(missing,[2])
    def test_security_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            (base/'raw').mkdir()
            with self.assertRaises(SystemExit):
                module.main(['--source',str(base/'raw'),'--out',str(base/'raw'/'out')])

if __name__=='__main__': unittest.main()
