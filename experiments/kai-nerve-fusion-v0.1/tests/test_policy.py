import unittest
from kai_nerve.policy import PolicyEngine,PolicyContext
T={"typeId":"minecraft:creeper","distance":3.0}
class PolicyTests(unittest.TestCase):
 def test_stale_denied(self):self.assertFalse(PolicyEngine().decide(PolicyContext(True,True,True,"stale",True,True,T)).allowed)
 def test_unarmed_denied(self):self.assertEqual(PolicyEngine().decide(PolicyContext(False,True,True,"fresh",True,True,T)).reason,"not_armed")
 def test_owner_required(self):self.assertEqual(PolicyEngine().decide(PolicyContext(True,False,True,"fresh",True,True,T)).reason,"control_owner_invalid")
 def test_terrain_required(self):self.assertEqual(PolicyEngine().decide(PolicyContext(True,True,True,"fresh",True,False,T)).reason,"escape_corridor_unverified")
 def test_all_preconditions_dry_run(self):
  d=PolicyEngine().decide(PolicyContext(True,True,True,"fresh",True,True,T));self.assertTrue(d.allowed);self.assertTrue(d.dry_run)
if __name__=="__main__":unittest.main()
