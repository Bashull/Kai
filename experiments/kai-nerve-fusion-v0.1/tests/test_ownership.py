import unittest,tempfile
from kai_nerve.ownership import ControlOwnership
class OwnershipTests(unittest.TestCase):
 def test_exclusive_lease(self):
  with tempfile.TemporaryDirectory() as d:
   c=ControlOwnership(d+"/lease.json");a=c.acquire("reflex",ttl_s=30,now_ms=1000)
   with self.assertRaises(RuntimeError):c.acquire("chat",ttl_s=30,now_ms=1001)
   self.assertTrue(c.valid(a,now_ms=1002));c.release(a)
if __name__=="__main__":unittest.main()
