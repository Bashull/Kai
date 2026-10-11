import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kai_harvester.dag import inspect_dag, message_text, markdown_current_path
from kai_harvester.store import Store,sha
from kai_harvester.importer import ingest_file, ingest_json_bytes


def example():
    def m(id,parent,role,text):
        return {'id':id,'parent':parent,'children':[], 'message':{'author':{'role':role},'content':{'parts':[text]}}}
    return {'id':'abcd-1234','title':'Prueba _< > & 中文 🐼','current_node':'a2','mapping':{
        'root':m('root',None,'system',''), 'u1':m('u1','root','user','Hola'),
        'a1':m('a1','u1','assistant','snake_case'), 'a2':m('a2','u1','assistant','literal &lt; > 🐼') }}

class Dag(unittest.TestCase):
    def test_parent_only_branches(self):
        x=inspect_dag(example());self.assertEqual(x['branch_count'],2)
        self.assertEqual(x['active_path'],['root','u1','a2'])
    def test_no_mutation_and_text(self):
        conv=example();before=json.dumps(conv,sort_keys=True)
        md=markdown_current_path(conv)
        self.assertIn('literal &lt; > 🐼',md)
        self.assertEqual(json.dumps(conv,sort_keys=True),before)
    def test_cycle_detected(self):
        x=example();x['mapping']['root']['parent']='a2'
        g=inspect_dag(x)
        self.assertTrue(any('cycle' in t for t in g['anomalies']))
    def test_dangling(self):
        x=example();x['mapping']['a2']['parent']='vanished'
        self.assertTrue(any('dangling_parent' in t for t in inspect_dag(x)['anomalies']))
    def test_node_missing(self):
        x=example();x['current_node']='nonexistent'
        self.assertIn('current_node_missing',inspect_dag(x)['anomalies'])
    def test_mapping_missing_not_complete(self):
        x={'id':'hi12','messages':[{'id':'m1'}]}
        self.assertFalse(inspect_dag(x)['mapping_present'])

class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=Store(self.root/'corpus')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_idempotent_import(self):
        raw=json.dumps([example()]).encode()
        a,n=ingest_json_bytes(self.store,'source.json',raw)
        b,m=ingest_json_bytes(self.store,'source.json',raw)
        self.assertEqual((a,n,b,m),(a,1,a,1))
        self.assertEqual(self.store.stats()['conversation_records'],1)
        self.assertTrue(self.store.audit()['integrity_pass'])
    def test_modified_raw_new_revision(self):
        x=example();ingest_json_bytes(self.store,'x',json.dumps([x]).encode())
        x['mapping']['a2']['message']['content']['parts']=['edited']
        ingest_json_bytes(self.store,'x',json.dumps([x]).encode())
        self.assertEqual(self.store.stats()['conversation_records'],2)
    def test_corruption_detected(self):
        sid,c=ingest_json_bytes(self.store,'x',json.dumps([example()]).encode())
        rawhash=self.store.db.execute('SELECT raw_sha256 FROM conversations').fetchone()[0]
        (self.store.root/'objects'/rawhash[:2]/rawhash[2:]).write_bytes(b'bad')
        self.assertFalse(self.store.audit()['integrity_pass'])
    def test_unknown_json_scope_not_certified(self):
        ingest_json_bytes(self.store,'x',b'{"hello":"world"}')
        self.assertEqual(self.store.stats()['conversation_records'],0)
        self.assertFalse(self.store.stats()['inventory_complete'])
    def test_manifest_and_reader(self):
        ingest_json_bytes(self.store,'x',json.dumps([example()]).encode())
        self.assertTrue(self.store.manifest().exists())
        p=Path(self.store.export_reader());self.assertTrue(p.exists())
        self.assertIn('índice offline',p.read_text())
    def test_zip_asset_and_conv(self):
        z=self.root/'input.zip'
        with zipfile.ZipFile(z,'w') as f:
            f.writestr('conversations.json',json.dumps([example()]))
            f.writestr('assets/test.png',b'abc')
        self.assertEqual(ingest_file(self.store,z),1)
        self.assertEqual(self.store.stats()['assets_physical'],1)
    def test_zip_traversal(self):
        z=self.root/'unsafe.zip'
        with zipfile.ZipFile(z,'w') as f:f.writestr('../foo.png',b'abc')
        ingest_file(self.store,z)
        self.assertFalse((self.root/'foo.png').exists())
        self.assertEqual(self.store.stats()['assets_physical'],0)
    def test_bridge_raw_envelope(self):
        envelope={'schema':'kai-bridge-batch-v1','conversations':[{'id':'abcd-1234','raw':example(),'graph_status':'RAW_MAPPING_PRESENT'}]}
        sid,n=ingest_json_bytes(self.store,'batch',json.dumps(envelope).encode())
        self.assertEqual(n,1)
    def test_large_rejected(self):
        from unittest.mock import patch
        with patch('kai_harvester.importer.MAX_INPUT',20):
            with self.assertRaises(ValueError):ingest_json_bytes(self.store,'too-big',b' '*21)
    def test_names_safe(self):
        from kai_harvester.store import safe_slug
        self.assertNotIn('/',safe_slug('../../test name'))

if __name__=='__main__':unittest.main()

class Assets(unittest.TestCase):
    def test_asset_refs_not_same_as_physical(self):
        from kai_harvester.assets import find_references
        x=example()
        x['mapping']['u1']['message']['metadata']={'attachments':[{'id':'file-123','name':'muestra.pdf'}]}
        x['mapping']['a2']['message']['content']['parts'].append({'asset_pointer':'sediment://private-file'})
        refs=find_references(x)
        self.assertEqual(len(refs),2)
        self.assertNotIn('sediment://',json.dumps(refs))
    def test_asset_refs_counted(self):
        from kai_harvester.store import Store
        with tempfile.TemporaryDirectory() as td:
            s=Store(td)
            x=example();x['metadata']={'attachments':[{'id':'abc','name':'documento.pdf'}]}
            ingest_json_bytes(s,'test',json.dumps([x]).encode())
            self.assertEqual(s.stats()['asset_references_discovered'],1)
            self.assertEqual(s.stats()['assets_physical'],0)
            s.close()
