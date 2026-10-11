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
if __name__=="__main__":unittest.main()
