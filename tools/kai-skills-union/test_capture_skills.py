"""Synthetic collector checks, without real credentials or remote state changes."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from capture_skills import capture,digest


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kai-capture-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.source.mkdir()

    def census(self,content):
        path=self.root/'census.json'
        path.write_text(json.dumps({'roots':[str(self.source)],'skills':content}))
        return path

    def row(self,name,data=b'---\nname: synthetic\ndescription: fixture\n---\n'):
        p=self.source/name/'SKILL.md';p.parent.mkdir();p.write_bytes(data)
        return {'path':str(p),'bytes':len(data),'sha256':digest(data)}

    def test_every_occurrence_and_changed_version_preserved_with_exact_byte_objects(self):
        rows=[self.row('one'),self.row('two'),self.row('changed')]
        Path(rows[-1]['path']).write_bytes(b'current bytes\r\n')
        before={r['path']:Path(r['path']).read_bytes() for r in rows}
        result=capture(self.census(rows),self.root/'out','termux',3)
        self.assertEqual(result['rows'],3);self.assertEqual(result['objects'],2)
        self.assertEqual(result['counts'],{'CAPTURED':2,'CHANGED_SINCE_CENSUS':1,'BLOCKED':0})
        with zipfile.ZipFile(result['zip']) as z:
            manifest=json.loads(z.read('CAPTURE_MANIFEST.json'))
            self.assertEqual(len({r['occurrence_uid'] for r in manifest['rows']}),3)
            for row in manifest['rows']:
                self.assertEqual(z.read(row['object_path']),before[row['path']])
        self.assertEqual(before,{r['path']:Path(r['path']).read_bytes() for r in rows})

    def test_missing_link_and_credential_patterns_get_individual_blocked_records(self):
        rows=[self.row('missing'),self.row('secret',b'gh'+b'p_'+b'A'*36)]
        Path(rows[0]['path']).unlink()
        if hasattr(Path,'symlink_to'):
            p=self.source/'link';p.mkdir();target=p/'SKILL.md';target.symlink_to(Path(rows[1]['path']))
            rows.append({'path':str(target),'bytes':rows[1]['bytes'],'sha256':rows[1]['sha256']})
        result=capture(self.census(rows),self.root/'out','termux',len(rows))
        self.assertEqual(result['counts']['BLOCKED'],len(rows));self.assertEqual(result['objects'],0)
        with zipfile.ZipFile(result['zip']) as z:
            self.assertFalse(any(n.startswith('objects/') for n in z.namelist()))
            for row in json.loads(z.read('CAPTURE_MANIFEST.json'))['rows']:
                self.assertNotIn('object_path',row)

    def test_stop_and_existing_outputs_fail_before_writes(self):
        rows=[self.row('one')];census=self.census(rows);target=self.root/'out'
        stop=self.root/'STOP';stop.touch()
        with self.assertRaises(RuntimeError):capture(census,target,'termux',1,stop)
        self.assertFalse(target.exists())
        stop.unlink();target.with_name('out.zip').write_bytes(b'preserved')
        with self.assertRaises(ValueError):capture(census,target,'termux',1)
        self.assertFalse(target.exists());self.assertEqual((self.root/'out.zip').read_bytes(),b'preserved')


if __name__=='__main__':unittest.main()
