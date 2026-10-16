"""Keep the preserved007 view reproducible while supporting a new batch label."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

W=Path(__file__).resolve().parents[3]
SCRIPT=Path(__file__).resolve().parents[1]/'omega007/group_capabilities.py'
PAYLOAD=Path(os.environ['FORGE_PAYLOAD_ROOT']) if os.environ.get('FORGE_PAYLOAD_ROOT') else None
REG=(PAYLOAD/'batch_003/evidence/federation/FEDERATED_REGISTRY.json') if PAYLOAD else W/'federation_omega/FEDERATED_REGISTRY.json'
AUDIT=(PAYLOAD/'batch_007/evidence/AUDIT_MATRIX_847_OMEGA007.json') if PAYLOAD else W/'evidence_omega007/AUDIT_MATRIX_847_OMEGA007.json'
BASELINE=(PAYLOAD/'batch_007/evidence/grouping') if PAYLOAD else W/'evidence_omega007/grouping'
FAMILIES=Path(__file__).resolve().parents[1]/'omega007/reviewed_families.json'
PIN='756e24071a97ad8bf156e0711d69c924615243b4f621e7a301ff04008480eb10'


def run(out,extra):
    return subprocess.run([sys.executable,str(SCRIPT),'--registry',str(REG),'--registry-sha256',PIN,
                           '--audit',str(AUDIT),'--families',str(FAMILIES),'--output',str(out),*extra],capture_output=True,text=True)


class GroupingBatchCompatibility(unittest.TestCase):
    def test_existing_default_view_and_new_batch_filename(self):
        with tempfile.TemporaryDirectory(prefix='kai-groups008-') as d:
            old=Path(d)/'old';new=Path(d)/'new'
            for out,args in [(old,[]),(new,['--batch-id','008'])]:
                result=run(out,args);self.assertEqual(result.returncode,0,result.stderr)
            for ext in ['json','md']:
                self.assertEqual((old/f'AGRUPACION_SKILLS_OMEGA007.{ext}').read_bytes(),(BASELINE/f'AGRUPACION_SKILLS_OMEGA007.{ext}').read_bytes())
            self.assertEqual((old/'AGRUPACION_SKILLS_OMEGA007.json').read_bytes(),(new/'AGRUPACION_SKILLS_OMEGA008.json').read_bytes())
            self.assertTrue((new/'AGRUPACION_SKILLS_OMEGA008.md').read_text().startswith('# Agrupación de skills · OMEGA008\n'))

    def test_invalid_batch_cannot_create_paths(self):
        with tempfile.TemporaryDirectory(prefix='kai-groups008-') as d:
            target=Path(d)/'output';result=run(target,['--batch-id','../008'])
            self.assertNotEqual(result.returncode,0);self.assertIn('Batch ID',result.stderr);self.assertFalse(target.exists())


if __name__=='__main__':unittest.main(verbosity=2)
