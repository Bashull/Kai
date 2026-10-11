import unittest,tempfile
from kai_nerve.models import ParsedObservation
from kai_nerve.normalize import Normalizer
from kai_nerve.store import EventStore
class StoreTests(unittest.TestCase):
 def test_dedupe_event_id(self):
  with tempfile.TemporaryDirectory() as d:
   s=EventStore(d+"/x.db");o=ParsedObservation("minecraft.kai_nerve","STATE",{"x":1},"s",1,1000,1,{"transport":"fixture"})
   e=Normalizer().normalize(o,received_wall_ms=1010,published_wall_ms=1015)
   self.assertTrue(s.insert(e));self.assertFalse(s.insert(e))
 def test_same_source_session_seq_kind_rejected_even_if_payload_changes(self):
  with tempfile.TemporaryDirectory() as d:
   s=EventStore(d+"/x.db");n=Normalizer()
   a=ParsedObservation("minecraft.kai_nerve","STATE",{"x":1},"s",7,1000,1,{"transport":"fixture"})
   b=ParsedObservation("minecraft.kai_nerve","STATE",{"x":999},"s",7,1001,2,{"transport":"fixture"})
   self.assertTrue(s.insert(n.normalize(a,received_wall_ms=1010,published_wall_ms=1010)))
   e2=Normalizer().normalize(b,received_wall_ms=1011,published_wall_ms=1011)
   self.assertFalse(s.insert(e2))
if __name__=="__main__":unittest.main()
