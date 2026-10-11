import json,tempfile,unittest
from pathlib import Path
from kai_nerve.parsers import parse_line
from kai_nerve.collector_logcat import _auth
from kai_nerve.leases import LeaseStore
from kai_nerve.generation import GenerationClock
from kai_nerve.budget import BudgetGovernor
from kai_nerve.port_registry import PortRegistry,PortClaim
from kai_nerve.reviewer import DecisionLedger
from kai_nerve.runtime_probe import _safe_env_value
from kai_nerve.models import ParsedObservation,ProvenanceEvidence,ProvenanceLevel
from kai_nerve.normalize import Normalizer
from kai_nerve.freshness import ReplayLedger

class ParserHardening(unittest.TestCase):
    def test_fractional_seq_rejected(self):
        o=parse_line('KAINERVE|4|STATE|'+json.dumps({'session_id':'s','seq':1.5,'observed_wall_ms':10,'challenge':'c'}));self.assertIsNone(o.source_seq)
    def test_fractional_string_rejected(self):
        o=parse_line('KAINERVE|4|STATE|'+json.dumps({'session_id':'s','seq':'1.5','observed_wall_ms':10,'challenge':'c'}));self.assertIsNone(o.source_seq)
    def test_bad_session_rejected(self):
        o=parse_line('KAINERVE|4|STATE|'+json.dumps({'session_id':'bad session\n','seq':1,'observed_wall_ms':10}));self.assertIsNone(o.session_id)
    def test_v4_auth_source_bound(self):
        n=parse_line('KAINERVE|4|STATE|'+json.dumps({'session_id':'s','seq':1,'challenge':'abc'}));self.assertTrue(_auth(n,'abc')[0])
        e=parse_line('KAI_EYES:'+json.dumps({'session_id':'s','seq':1,'challenge':'abc'}));self.assertFalse(_auth(e,'abc')[0])
        old=parse_line('KAINERVE|3|STATE|'+json.dumps({'session_id':'s','seq':1,'challenge':'abc'}));self.assertFalse(_auth(old,'abc')[0])

class Eligibility(unittest.TestCase):
    def test_old_protocol_not_eligible(self):
        o=ParsedObservation('minecraft.kai_nerve','STATE',{'challenge':'abc'},'s',1,1000,1)
        e=ProvenanceEvidence(ProvenanceLevel.ENGINE_BOUNDARY,'pid','logcat',{'sensor_authenticated':True,'protocol':'3'})
        r=Normalizer(ReplayLedger()).normalize(o,evidence=e,received_wall_ms=1010,published_wall_ms=1010,consumed_wall_ms=1010)
        self.assertFalse(r.actuation_eligible)

class Ownership(unittest.TestCase):
    def test_single_live_lease(self):
        with tempfile.TemporaryDirectory() as td:
            s=LeaseStore(Path(td)/'l.db');a=s.acquire('physical_actuator','a',ttl_ms=1000,now_ms=100);self.assertIsNotNone(a);self.assertIsNone(s.acquire('physical_actuator','b',ttl_ms=1000,now_ms=200));self.assertIsNotNone(s.acquire('physical_actuator','b',ttl_ms=1000,now_ms=1200))
    def test_renew_token(self):
        with tempfile.TemporaryDirectory() as td:
            s=LeaseStore(Path(td)/'l.db');a=s.acquire('r','a',ttl_ms=1000,now_ms=100);b=s.renew(a,ttl_ms=1000,now_ms=500);self.assertIsNotNone(b);self.assertTrue(s.valid(b,now_ms=600))

class AsyncSafety(unittest.TestCase):
    def test_generation_invalidates_old_result(self):
        c=GenerationClock();a=c.next('world');self.assertTrue(c.current(a));b=c.next('world');self.assertFalse(c.current(a));self.assertTrue(c.current(b))

class Budget(unittest.TestCase):
    def test_foreign_load_counts(self):
        g=BudgetGovernor(tick_ms=50,reserve_ratio=.35);s=g.snapshot(20,20);self.assertTrue(s.over_budget);self.assertGreater(g.interval_multiplier(s),1)

class Ports(unittest.TestCase):
    def test_collision_rejected(self):
        r=PortRegistry();r.add(PortClaim('worldbus','worldbus',7191));
        with self.assertRaises(RuntimeError):r.add(PortClaim('other','http',7191))
    def test_role_collision_rejected(self):
        r=PortRegistry();r.add(PortClaim('a','minecraft_ingress',6464));
        with self.assertRaises(RuntimeError):r.add(PortClaim('b','minecraft_ingress',19137))

class Review(unittest.TestCase):
    def test_veto_persists(self):
        with tempfile.TemporaryDirectory() as td:
            d=DecisionLedger(Path(td)/'d.db');d.record('x','validator',False,'terrain_unknown');self.assertTrue(d.vetoed('x'))

class ProbeSecrets(unittest.TestCase):
    def test_secret_redacted(self):
        x=_safe_env_value('KAI_TOKEN',b'supersecret');self.assertTrue(x['redacted']);self.assertNotIn('supersecret',json.dumps(x))
    def test_safe_config_visible(self):self.assertEqual(_safe_env_value('KAI_LIVE_PORT',b'7190'),'7190')

class SensorV4(unittest.TestCase):
    def test_contract(self):
        root=Path(__file__).resolve().parents[1];js=(root/'bedrock_pack/KAI_NERVE_Sensor_BP/scripts/main.js').read_text()
        self.assertIn('KAINERVE|4',js);self.assertIn('let enabled=false',js);self.assertIn('missing_challenge',js);self.assertIn('actuation:false',js);self.assertNotIn('applyImpulse',js);self.assertNotIn('.teleport(',js)

if __name__=='__main__':unittest.main()
