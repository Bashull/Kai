import json, math, tempfile, unittest
from pathlib import Path
from kai_nerve.models import *
from kai_nerve.freshness import *
from kai_nerve.normalize import Normalizer
from kai_nerve.parsers import parse_line
from kai_nerve.store import EventStore
from kai_nerve.worldbus import WorldBusAdapter
from kai_nerve.policy import *
from kai_nerve.worldmodel import WorldModel
from kai_nerve.bridge_audit import audit, ports
from kai_nerve.collector_logcat import MinecraftProcess,logcat_command,evidence_for
from kai_nerve.registry import Component,ComponentRegistry
from kai_nerve.gates import GateInput,evaluate
from kai_nerve.runtime_probe import target_from_run_script,target_from_cmdline
from kai_nerve.pipeline import IngestPipeline

class Fresh(unittest.TestCase):
 def test_old_frame_rewrite_stale(self):
  r=ReplayLedger(); d=temporal_decision(session_id='s',seq=1,source='p',replay=r,observed_wall_ms=None,received_wall_ms=1000,published_wall_ms=1000,consumed_wall_ms=1105,frame_age_at_publish_ms=4905,max_age_ms=750);self.assertEqual(d.freshness,Freshness.STALE);self.assertEqual(d.effective_age_ms,5010)
 def test_future_origin_unknown(self):
  d=temporal_decision(session_id='s',seq=1,source='x',replay=ReplayLedger(),observed_wall_ms=2000,received_wall_ms=1000,published_wall_ms=1000,consumed_wall_ms=1000);self.assertEqual(d.freshness,Freshness.UNKNOWN)
 def test_nan_unknown(self):
  d=temporal_decision(session_id='s',seq=1,source='x',replay=ReplayLedger(),observed_wall_ms=float('nan'),received_wall_ms=1000,published_wall_ms=1000,consumed_wall_ms=1000);self.assertEqual(d.freshness,Freshness.UNKNOWN)
 def test_missing_origin_unknown(self):
  d=temporal_decision(session_id='s',seq=1,source='x',replay=ReplayLedger(),observed_wall_ms=None,received_wall_ms=1000,published_wall_ms=1000,consumed_wall_ms=1000);self.assertEqual(d.freshness,Freshness.UNKNOWN)
 def test_replay_persists(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'r.db';a=ReplayLedger(p);self.assertTrue(a.classify_and_advance('x','s',7));a.close();b=ReplayLedger(p);self.assertFalse(b.classify_and_advance('x','s',7));b.close()
 def test_new_session_resets(self):
  r=ReplayLedger();self.assertTrue(r.classify_and_advance('x','a',99));self.assertTrue(r.classify_and_advance('x','b',1))

class Provenance(unittest.TestCase):
 def obs(self):return ParsedObservation('minecraft.kai_nerve','STATE',{'x':1,'challenge':'abc'},'s',1,1000,2,{'level':'engine_boundary'})
 def test_payload_cannot_self_certify(self):
  e=Normalizer(ReplayLedger()).normalize(self.obs(),evidence=ProvenanceEvidence(ProvenanceLevel.FIXTURE,'test','fixture',{'sensor_authenticated':True,'protocol':'4'}),received_wall_ms=1010,published_wall_ms=1010,consumed_wall_ms=1010);self.assertFalse(e.actuation_eligible);self.assertEqual(e.provenance['level'],'fixture')
 def test_engine_boundary_without_challenge_not_eligible(self):
  e=Normalizer(ReplayLedger()).normalize(self.obs(),evidence=ProvenanceEvidence(ProvenanceLevel.ENGINE_BOUNDARY,'pid','logcat',{'pid_filter':True,'sensor_authenticated':False,'protocol':'4'}),received_wall_ms=1010,published_wall_ms=1010,consumed_wall_ms=1010);self.assertFalse(e.actuation_eligible)
 def test_engine_boundary_authenticated_can_be_eligible(self):
  e=Normalizer(ReplayLedger()).normalize(self.obs(),evidence=ProvenanceEvidence(ProvenanceLevel.ENGINE_BOUNDARY,'pid','logcat',{'pid_filter':True,'sensor_authenticated':True,'protocol':'4'}),received_wall_ms=1010,published_wall_ms=1010,consumed_wall_ms=1010);self.assertTrue(e.actuation_eligible)

class Parsers(unittest.TestCase):
 def test_v3(self):
  x=parse_line('xxx KAINERVE|3|STATE|'+json.dumps({'session_id':'s','seq':3,'observed_wall_ms':10}));self.assertEqual(x.source_seq,3);self.assertEqual(x.payload['_protocol_version'],'3')
 def test_eyes(self):self.assertEqual(parse_line('KAI_EYES:'+json.dumps({'session_id':'s','seq':1})).source,'minecraft.kai_eyes')
 def test_hyper(self):self.assertEqual(parse_line('KAIHB|STATE|'+json.dumps({'session_id':'s','seq':1})).source,'minecraft.hyperbridge')

class Persistence(unittest.TestCase):
 def event(self):
  o=ParsedObservation('minecraft.kai_nerve','STATE',{'x':1,'challenge':'abc'},'s',1,1000,2);return Normalizer(ReplayLedger()).normalize(o,evidence=ProvenanceEvidence(ProvenanceLevel.ENGINE_BOUNDARY,'c','logcat',{'sensor_authenticated':True,'protocol':'4'}),received_wall_ms=1010,published_wall_ms=1010,consumed_wall_ms=1010)
 def test_store_dedupe(self):
  with tempfile.TemporaryDirectory() as td:
   s=EventStore(Path(td)/'e.db');e=self.event();self.assertTrue(s.insert(e));self.assertFalse(s.insert(e))
 def test_worldbus_adapter(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'w.db';cx=sqlite3.connect(p);cx.execute('CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,source TEXT,type TEXT,severity INTEGER,dedupe_key TEXT,payload TEXT)');cx.commit();cx.close();a=WorldBusAdapter(p);self.assertTrue(a.verify_schema()['ok']);e=self.event();self.assertTrue(a.insert(e));self.assertFalse(a.insert(e));row=a.get_by_event_id(e.event_id);self.assertEqual(row['source'],'minecraft');self.assertEqual(row['dedupe_key'],e.event_id);self.assertIn('engine_boundary',json.dumps(row['payload']))
 def test_pipeline_persists_same_event_id(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as td:
   w=Path(td)/'w.db';cx=sqlite3.connect(w);cx.execute('CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,source TEXT,type TEXT,severity INTEGER,dedupe_key TEXT,payload TEXT)');cx.commit();cx.close()
   pipe=IngestPipeline(nerve_db=Path(td)/'n.db',replay_db=Path(td)/'r.db',worldbus_db=w)
   obs=ParsedObservation('minecraft.kai_nerve','STATE',{'challenge':'abc'},'s',1,1000,1)
   ev=ProvenanceEvidence(ProvenanceLevel.ENGINE_BOUNDARY,'pid','adb.logcat.pid',{'sensor_authenticated':True,'protocol':'4'})
   r=pipe.process(obs,ev,1010);pipe.close();self.assertTrue(r['worldbus_inserted']);self.assertEqual(r['event'].event_id,r['worldbus_readback']['dedupe_key'])

class Safety(unittest.TestCase):
 def test_policy_fixture_denied(self):
  c=PolicyContext(True,True,True,'fresh',0,True,True,True,{'typeId':'minecraft:creeper'});self.assertFalse(PolicyEngine().decide(c).allowed)
 def test_policy_unauthenticated_denied(self):
  c=PolicyContext(True,True,True,'fresh',40,False,True,True,{'typeId':'minecraft:creeper'});self.assertFalse(PolicyEngine().decide(c).allowed)
 def test_policy_all_still_dryrun(self):
  c=PolicyContext(True,True,True,'fresh',40,True,True,True,{'typeId':'minecraft:creeper'});d=PolicyEngine().decide(c);self.assertFalse(d.allowed);self.assertEqual(d.reason,'observation_required_at_consumption');self.assertTrue(d.dry_run)
 def test_single_owner(self):
  r=ComponentRegistry();r.register(Component('a','minecraft_ingress','nerve'))
  with self.assertRaises(RuntimeError):r.register(Component('b','minecraft_ingress','other'))
 def test_port_parser_avoids_random_year(self):
  self.assertEqual(ports('year=2026; KAI_HTTP_PORT=7192; listen(6464); http://127.0.0.1:19137'),{7192,6464,19137})
 def test_bridge_collision_and_unknown_blocks_restart(self):
  x={'a':{'run_script':'PORT=7192','desired_target':{'path':'a','text':'const HTTP_PORT=7192','sha256':'x'},'running_target':{'path':'a','text':'const HTTP_PORT=7192','sha256':'x'},'target_identity_match':True,'listeners':['LISTEN 0 128 127.0.0.1:7192 0.0.0.0:* users:(("node",pid=1,fd=1))']},'b':{'run_script':'PORT=7192','desired_target':{'path':'b','text':'const HTTP_PORT=7192','sha256':'y'},'running_target':{'path':'b','text':'const HTTP_PORT=7192','sha256':'y'},'target_identity_match':True,'listeners':['LISTEN 0 128 127.0.0.1:7192 0.0.0.0:* users:(("node",pid=2,fd=1))']}};self.assertFalse(audit(x)['safe_to_restart']);self.assertTrue(audit(x)['configured_port_collisions'])
 def test_runtime_target_resolution(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'a.js').write_text('x');run='cd '+td+'\nexec /usr/bin/node ./a.js\n';self.assertEqual(target_from_run_script(run,root),root/'a.js');self.assertEqual(target_from_cmdline('/usr/bin/node ./a.js',root),root/'a.js')
 def test_pid_filtered_logcat_and_challenge(self):
  p=MinecraftProcess('127.0.0.1:12345',321);cmd=logcat_command(p);self.assertIn('--pid=321',cmd);e=evidence_for(p,'c',sensor_authenticated=True,challenge='abc');self.assertEqual(e.level,ProvenanceLevel.PROCESS_BOUND);self.assertTrue(e.evidence['sensor_authenticated'])
 def test_gate(self):
  g=evaluate(GateInput(tests_pass=True,static_sensor_ok=True,runtime_identity_captured=True,runtime_target_match=True,bridge_contract_clean=True,freshness_vector_verified=True));self.assertFalse(g.pass_gate);self.assertEqual(g.level,'sensor_e2e');self.assertIn('sensor_challenge_verified',g.blockers)

class Model(unittest.TestCase):
 def env(self,sid,seq,ents):
  return EventEnvelope('e','s','minecraft.kai_nerve','STATE',sid,seq,0,0,0,0,0,0,0,0,None,0,Freshness.FRESH,'ok',{'level':'engine_boundary','level_value':40},True,{'player_state':{'entities':ents}},__import__('time').monotonic()*1000,__import__('kai_nerve.consumption',fromlist=['CLOCK_INSTANCE']).CLOCK_INSTANCE)
 def test_unknown_tracks_and_session_reset(self):
  m=WorldModel();r=m.ingest(self.env('s1',1,[{'id':'u1','typeId':'addon:ghost','distance':3}]));self.assertTrue(r[0]['unknown']);m.ingest(self.env('s2',1,[]));self.assertEqual(m.tracks,{})

class SensorStatic(unittest.TestCase):
 def test_sensor_contract(self):
  root=Path(__file__).resolve().parents[1];js=(root/'bedrock_pack/KAI_NERVE_Sensor_BP/scripts/main.js').read_text()
  self.assertIn('let enabled=false',js);self.assertIn('enabled=false;emit("DISABLED"',js);self.assertIn('entity_scan_error',js);self.assertIn('sessionChallenge',js);self.assertIn('String(ev.message||"").trim()',js);self.assertNotIn('applyImpulse',js);self.assertNotIn('.teleport(',js)

if __name__=='__main__':unittest.main()
