import concurrent.futures,json,math,multiprocessing,sqlite3,tempfile,time,unittest
from pathlib import Path
from kai_nerve.freshness import ReplayLedger,temporal_decision
from kai_nerve.models import *
from kai_nerve.normalize import Normalizer
from kai_nerve.consumption import at_consumption
from kai_nerve.parsers import parse_line
from kai_nerve.pipeline import IngestPipeline
from kai_nerve.worldmodel import WorldModel
from kai_nerve.worldbus import WorldBusAdapter
from kai_nerve.evidence import EvidenceStore
from kai_nerve.perception_clock import health

def claim(path):
    l=ReplayLedger(path)
    try:return l.classify_and_advance('source','session',7)
    finally:l.close()
def env(payload=None,seq=1,level=ProvenanceLevel.FIXTURE):
    t=time.time()*1000
    return Normalizer(ReplayLedger()).normalize(ParsedObservation('minecraft.kai_nerve','STATE',payload or {},'session',seq,t),evidence=ProvenanceEvidence(level,'test','fixture',{}),received_wall_ms=t)
def db(path):
    with sqlite3.connect(path) as c:c.execute('CREATE TABLE events(id INTEGER PRIMARY KEY,ts REAL,source TEXT,type TEXT,severity INTEGER,dedupe_key TEXT,payload TEXT)')

class Regressions(unittest.TestCase):
 def test_single_accept_across_processes(self):
  with tempfile.TemporaryDirectory() as t:
   p=str(Path(t)/'r.db');ReplayLedger(p).close()
   with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:self.assertEqual(sum(pool.map(claim,[p]*16)),1)
 def test_invalid_age_does_not_consume_sequence(self):
  r=ReplayLedger();kw=dict(session_id='s',seq=1,source='x',replay=r,received_wall_ms=100,published_wall_ms=100,consumed_wall_ms=100)
  self.assertEqual(temporal_decision(observed_wall_ms=None,**kw).freshness,Freshness.UNKNOWN)
  self.assertEqual(temporal_decision(observed_wall_ms=99,**kw).freshness,Freshness.FRESH)
 def test_bad_sequence_types_do_not_advance(self):
  for seq in [True,1.0,1.5,'1',-1,2**63]:
   o=parse_line('KAINERVE|4|STATE|'+json.dumps({'seq':seq}));self.assertIsNone(o.source_seq)
 def test_nonfinite_age_and_bool_fail_closed(self):
  for v in [True,float('nan'),float('inf'),-1]:
   r=temporal_decision(session_id='s',seq=1,source='x',replay=ReplayLedger(),observed_wall_ms=None,received_wall_ms=100,published_wall_ms=100,consumed_wall_ms=100,frame_age_at_publish_ms=v)
   self.assertEqual(r.freshness,Freshness.UNKNOWN)
 def test_parser_isolates_and_protocol_cannot_be_forged(self):
  for x in ['KAINERVE|4|STATE|[]','KAINERVE|4|STATE|{oops','KAI_EYES:null','KAINERVE|4|STATE|'+('x'*65536)]:self.assertIsNone(parse_line(x))
  self.assertEqual(parse_line('KAINERVE|3|STATE|{"_protocol_version":"4"}').payload['_protocol_version'],'3')
 def test_consumer_ages_and_unknown_clock(self):
  e=env();self.assertEqual(at_consumption(e,now_mono_ms=e.receipt_monotonic_ms+4905)['freshness'],'stale')
  e.clock_instance='other';self.assertEqual(at_consumption(e)['freshness'],'unknown')
 def test_sensor_vnext_entities_reach_model(self):
  m=WorldModel();e=env({'entity_scan':{'entities':[{'id':'ghost1','typeId':'addon:ghost','distance':0}],'truncated':False}})
  self.assertEqual(m.ingest(e)[0]['entity_id'],'ghost1');self.assertEqual(m.snapshot()[0]['distance'],0)
 def test_scan_error_is_not_empty_and_tracks_expire(self):
  m=WorldModel(ttl_s=.01);m.ingest(env({'entity_scan':{'entities':[{'id':'a','typeId':'addon:a'}]}}));m.ingest(env({'entity_scan':{'entities':[],'error':'failed'}},2));self.assertEqual(m.scan_state,'ERROR');self.assertEqual(len(m.tracks),1)
  m.tracks['a'].last_seen_mono-=1;self.assertEqual(m.snapshot(),[])
 def test_partial_scan_preserves_unseen_and_complete_clears(self):
  m=WorldModel();m.ingest(env({'entities':[{'id':'a'}]}));m.ingest(env({'entity_scan':{'entities':[],'truncated':True}},2));self.assertIn('a',m.tracks);m.ingest(env({'entities':[]},3));self.assertEqual(m.tracks,{})
 def test_fixture_does_not_label_worldbus_minecraft(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'w';db(p);a=WorldBusAdapter(p);e=env();a.insert(e);self.assertEqual(a.get_by_event_id(e.event_id)['source'],'fixture')
 def test_worldbus_missing_is_not_created(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'missing'
   with self.assertRaises(sqlite3.OperationalError):WorldBusAdapter(p).verify_schema()
   self.assertFalse(p.exists())
 def test_raw_occurrences_and_capacity(self):
  with tempfile.TemporaryDirectory() as t:
   s=EvidenceStore(Path(t)/'r',max_bytes=3,max_occurrences=2);a=s.add(b'abc',{});b=s.add(b'abc',{});self.assertEqual(a['sha256'],b['sha256']);self.assertNotEqual(a['occurrence_id'],b['occurrence_id'])
   with self.assertRaises(RuntimeError):s.add(b'abc',{})
 def test_malformed_raw_persisted_before_parser(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);db(p/'w');pipe=IngestPipeline(nerve_db=p/'n',replay_db=p/'r',worldbus_db=p/'w');e=ProvenanceEvidence(ProvenanceLevel.FIXTURE,'t','fixture',{})
   result=pipe.process_line(b'KAINERVE|4|STATE|{oops',e,time.time()*1000);self.assertTrue(result['parse_error']);self.assertTrue(result['raw']['sha256']);pipe.close()
 def test_runtime_frame_rewrite_does_not_rejuvenate(self):
  p={'ok':True,'seq':7,'session_id':'p','boot_id':'b','captured_mono_s':5.095,'published_mono_s':9.999,'detection_observed_mono_s':5.095,'detection_seq':7}
  self.assertFalse(health(p,now=10,boot_id='b')['fresh']);p['captured_mono_s']=9.99;self.assertTrue(health(p,now=10,boot_id='b')['fresh']);self.assertFalse(health(p,now=10,boot_id='b')['detection_fresh'])
 def test_boot_missing_future_never_fresh(self):
  p={'ok':True,'seq':1,'session_id':'s','boot_id':'b','captured_mono_s':11,'published_mono_s':9.99};self.assertFalse(health(p,now=10,boot_id='b')['fresh']);p['captured_mono_s']=9.99;self.assertFalse(health(p,now=10,boot_id='other')['fresh'])

class Delivery(unittest.TestCase):
 def test_retry_after_worldbus_failure_survives_restart(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);db(p/'w');kw=dict(nerve_db=p/'n',replay_db=p/'r',worldbus_db=p/'w');pipe=IngestPipeline(**kw);raw=('KAINERVE|4|STATE|'+json.dumps({'session_id':'s','seq':1,'observed_wall_ms':time.time()*1000})).encode();e=ProvenanceEvidence(ProvenanceLevel.FIXTURE,'t','fixture',{})
   with patch.object(pipe.worldbus,'insert',side_effect=sqlite3.OperationalError('locked')):
    with self.assertRaises(sqlite3.OperationalError):pipe.process_line(raw,e,time.time()*1000)
   pending=pipe.store.pending();self.assertEqual(len(pending),1);original_time=pending[0]['received_wall_ms'];pipe.close()
   other=IngestPipeline(**kw);self.assertEqual(other.drain_pending(),1);self.assertEqual(other.store.pending(),[]);row=other.worldbus.get_by_event_id(pending[0]['event_id']);self.assertEqual(row['payload']['received_wall_ms'],original_time);self.assertFalse(row['payload']['actuation_eligible']);self.assertEqual(row['source'],'fixture');other.close()

class CollectorLifecycle(unittest.TestCase):
 def test_once_accepts_observation_without_physical_eligibility(self):
  from unittest.mock import patch
  from kai_nerve.pipeline import collect_logcat
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);db(p/'w');raw=('KAINERVE|4|STATE|'+json.dumps({'session_id':'s','seq':1,'observed_wall_ms':time.time()*1000})).encode()
   evidence=ProvenanceEvidence(ProvenanceLevel.PROCESS_BOUND,'fake','logcat',{})
   with patch('kai_nerve.pipeline.iterate',return_value=iter([(raw,evidence,time.time()*1000)])):
    results=list(collect_logcat(serial='fixture',nerve_db=p/'n',replay_db=p/'r',worldbus_db=p/'w',expected_challenge='x',once=True))
   self.assertEqual(len(results),1);self.assertTrue(results[0]['worldbus_readback']);self.assertFalse(results[0]['event'].actuation_eligible)
 def test_once_empty_collector_finishes(self):
  from unittest.mock import patch
  from kai_nerve.pipeline import collect_logcat
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);db(p/'w')
   with patch('kai_nerve.pipeline.iterate',return_value=iter([])):
    result=list(collect_logcat(serial='fixture',nerve_db=p/'n',replay_db=p/'r',worldbus_db=p/'w',expected_challenge='x',once=True))
   self.assertEqual(result[0]['collector_error'],'timeout_or_eof')
 def test_no_invented_capture_sequence(self):
  from kai_nerve.perception_clock import parse_frame_sequence
  for value in [None,'','1.5','-1',True,'١',str(2**63)]:
   with self.assertRaises(ValueError):parse_frame_sequence(value)
  self.assertEqual(parse_frame_sequence('0'),0)
 def test_stale_runtime_view_removes_tracks(self):
  import ast,threading
  from kai_nerve.consumption import CLOCK_INSTANCE
  path=Path(__file__).resolve().parents[2]/'runtime/kai_worldbus.py'
  module=ast.parse(path.read_text());fn=next(x for x in module.body if isinstance(x,ast.FunctionDef) and x.name=='latest_view')
  ns={'_lock':threading.Lock(),'_latest':{'nerve':{'tracks':[{'id':'old'}],'freshness':'fresh','effective_age_ms':0,'receipt_monotonic_ms':time.monotonic()*1000-5000,'clock_instance':CLOCK_INSTANCE}},'_nerve_status':{},'health':health,'at_consumption':at_consumption}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'runtime_latest_view','exec'),ns)
  value=ns['latest_view']()['nerve'];self.assertEqual(value['freshness'],'stale');self.assertEqual(value['tracks'],[])
