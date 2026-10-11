import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from kai_harvester.store import Store
from kai_harvester.importer import ingest_json_bytes
from kai_harvester.advanced import doctor, index_messages, search_messages, asset_gaps, compare_manifests, scan_zip
from kai_harvester.rate_policy import retry_after_seconds,decide_retry


def sample():
    def node(p,role,text):return {'parent':p,'children':[],'message':{'author':{'role':role},'content':{'parts':[text]}}}
    return {'id':'conv-example', 'title':'History', 'current_node':'a2', 'mapping':{
      'root':node(None,'system',''), 'u1':node('root','user','Hola qué tal'),
      'a1':node('u1','assistant','snake_case primera generación'),
      'a2':node('u1','assistant','respuesta actual 🐼')}}

class Advanced(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=Store(self.root/'private');ingest_json_bytes(self.store,'test.json',json.dumps([sample()],ensure_ascii=False).encode('utf-8'))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_doctor(self):self.assertIn('commands_present',doctor())
    def test_index(self):
        x=index_messages(self.store)
        if x['fts5']:
            self.assertEqual(x['messages_newly_indexed'],3)
            self.assertEqual(index_messages(self.store)['messages_newly_indexed'],0)
    def test_search_regenerated_branch(self):
        res=search_messages(self.store,'snake_case')
        self.assertEqual(res['returned'],1)
        self.assertEqual(res['results'][0]['node_id'],'a1')
    def test_search_literals(self):
        res=search_messages(self.store,'respuesta actual')
        self.assertEqual(res['results'][0]['node_id'],'a2')
    def test_search_invalid(self):
        with self.assertRaises(ValueError): search_messages(self.store,'')
        with self.assertRaises(ValueError): search_messages(self.store,'hi',1000)
    def test_asset_status_unknown(self):self.assertIn('UNKNOWN',asset_gaps(self.store)['linked_or_complete'])
    def test_compare(self):
        current=self.store.manifest();obj=json.loads(current.read_text())
        self.assertEqual(compare_manifests(self.store,obj)['matching_ids'],1)
        obj['records'][0]['raw_sha256']='0'*64
        self.assertEqual(compare_manifests(self.store,obj)['same_ids_different_revision_sets'],['conv-example'])
    def test_compare_invalid(self):
        with self.assertRaises(ValueError): compare_manifests(self.store,{'junk':123})
    def test_no_raw_mutation(self):
        before=self.store.db.execute('SELECT raw_sha256 FROM conversations').fetchone()[0]
        search_messages(self.store,'snake_case')
        self.assertEqual(self.store.db.execute('SELECT raw_sha256 FROM conversations').fetchone()[0],before)
        self.assertTrue(self.store.audit()['integrity_pass'])
    def test_scan_metadata_only(self):
        import zipfile
        arc=self.root/'large-scan.zip'
        with zipfile.ZipFile(arc,'w') as z:
            z.writestr('conversations.json',json.dumps([sample()]))
        x=scan_zip(arc)
        self.assertEqual(x['candidate_text_members'],1)
        self.assertFalse(x['all_bytes_verified'])
    def test_scan_symlink_flagged(self):
        import zipfile,stat
        arc=self.root/'symlink.zip'
        with zipfile.ZipFile(arc,'w') as z:
            inf=zipfile.ZipInfo('target.txt');inf.create_system=3
            inf.external_attr=(stat.S_IFLNK | 0o777) << 16
            z.writestr(inf,'../../danger')
        result=scan_zip(arc)
        self.assertFalse(result['safe_to_extract'])
        self.assertEqual(result['suspicious'][0]['kind'],'ZIP_SYMLINK')
    def test_scan_traversal_flagged(self):
        import zipfile
        arc=self.root/'traversal.zip'
        with zipfile.ZipFile(arc,'w') as z:z.writestr('../evil.json','{}')
        x=scan_zip(arc)
        self.assertFalse(x['safe_to_extract'])

    def test_mcp_malformed_request_after_success(self):
        payload='{"jsonrpc":"2.0","id":1,"method":"ping"}\nnot-json\n'
        out=subprocess.run([sys.executable,'-m','kai_harvester.mcp_bridge','--root',str(self.root/'private')],input=payload,text=True,capture_output=True,timeout=10)
        self.assertEqual(out.returncode,0)
        self.assertEqual(len(out.stdout.splitlines()),1)
    def test_mcp_stdio(self):
        data='\n'.join(json.dumps(x) for x in [
           {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
           {'jsonrpc':'2.0','method':'notifications/initialized'},
           {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
           {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'kai_harvest_stats','arguments':{}}},
           {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'kai_harvest_search','arguments':{'query':'snake_case'}}},
           {'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'kai_fake_tool','arguments':{}}}
        ])+'\n'
        r=subprocess.run([sys.executable,'-m','kai_harvester.mcp_bridge','--root',str(self.root/'private')],input=data,text=True,capture_output=True,timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)
        responses=[json.loads(x) for x in r.stdout.splitlines()]
        self.assertEqual(len(responses),5)
        self.assertIn('kai_harvest_search',[x['name'] for x in responses[1]['result']['tools']])
        self.assertEqual(responses[2]['result']['content'][0]['type'],'text')
        self.assertIn('snake_case',responses[3]['result']['content'][0]['text'])
        self.assertIn('error',responses[4])

class Rate(unittest.TestCase):
    def test_seconds(self):self.assertEqual(retry_after_seconds('90'),90)
    def test_invalid(self):self.assertIsNone(retry_after_seconds('soon'))
    def test_429_is_not_eof(self):
        d=decide_retry(429,0,'15');self.assertTrue(d['retry']);self.assertFalse(d['inventory_terminated'])
    def test_exhaustion(self):self.assertFalse(decide_retry(429,8,'90')['retry'])
    def test_non_retryable(self):self.assertFalse(decide_retry(403,0)['retry'])
    def test_jitter_bound(self):
        with self.assertRaises(ValueError):decide_retry(429,0,seed=2)

if __name__=='__main__':unittest.main()
