import concurrent.futures,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from kai_harvester.store import Store
from kai_harvester.importer import ingest_json_bytes
from kai_harvester.advanced import search_messages
from kai_harvester.cli import main

def convo():return {'id':'chat1234','mapping':{'a':{'parent':None,'children':[],'message':{'author':{'role':'user'},'content':{'parts':['needleword']}}}},'current_node':'a'}
class Integrity(unittest.TestCase):
 def test_concurrent_cas_same_process(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t)
   with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:hs=list(ex.map(s.put_blob,[b'evidence'*1000]*32))
   self.assertEqual(len(set(hs)),1);self.assertEqual(s.read_blob(hs[0]),b'evidence'*1000);s.close()
 def test_existing_corrupt_cas_not_overwritten(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);h=s.put_blob(b'original');(s.root/'objects'/h[:2]/h[2:]).write_bytes(b'corrupt')
   with self.assertRaises(ValueError):s.put_blob(b'original')
   s.close()
 def test_audit_exit_failure(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);s.source('test',b'raw','txt');h=next((s.root/'objects').glob('*/*'));h.write_bytes(b'corrupt');s.close();self.assertEqual(main(['--root',t,'audit']),2)
 def test_malformed_graph_does_not_block_next_record(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);bad=convo();bad['id']='chatbad1';bad['mapping']['a']['parent']=[];bad['mapping']['a']['children']=[{}];bad['current_node']={};_,n=ingest_json_bytes(s,'batch',json.dumps([bad,convo()]).encode());self.assertEqual(n,2);self.assertEqual(s.stats()['conversation_records'],2);s.close()
 def test_duplicate_sources_keep_history_search_once(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);raw=json.dumps(convo()).encode();ingest_json_bytes(s,'a',raw);ingest_json_bytes(s,'b',raw);self.assertEqual(search_messages(s,'needleword')['returned'],1);self.assertEqual(s.stats()['sources'],2);self.assertEqual(s.stats()['conversation_records'],2);s.close()
 def test_invalid_author_does_not_abort_search(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);c=convo();c['mapping']['a']['message']['author']='bad';ingest_json_bytes(s,'a',json.dumps(c).encode());self.assertEqual(search_messages(s,'needleword')['returned'],1);s.export_views();s.close()
