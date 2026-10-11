import unittest
from kai_nerve.freshness import SequenceTracker,perception_ages
from kai_nerve.models import Freshness

class FreshnessTests(unittest.TestCase):
 def test_rewritten_file_does_not_rejuvenate_old_frame(self):
  src,trans=perception_ages(frame_age_ms=4905,file_age_ms=105)
  d=SequenceTracker().classify(source="perception",session_id="s1",seq=95087,
   source_age_ms=src,transport_age_ms=trans,process_ok=True,max_age_ms=750)
  self.assertEqual(d.freshness,Freshness.STALE);self.assertAlmostEqual(d.effective_age_ms,5010)
 def test_same_seq_is_replay(self):
  t=SequenceTracker();t.classify(source="x",session_id="s",seq=10,source_age_ms=20,transport_age_ms=10,process_ok=True)
  d=t.classify(source="x",session_id="s",seq=10,source_age_ms=1,transport_age_ms=1,process_ok=True)
  self.assertEqual(d.freshness,Freshness.REPLAY);self.assertFalse(d.allow_actuation)
 def test_new_session_may_restart_sequence(self):
  t=SequenceTracker();t.classify(source="x",session_id="old",seq=900,source_age_ms=1,transport_age_ms=1,process_ok=True)
  self.assertEqual(t.classify(source="x",session_id="new",seq=1,source_age_ms=1,transport_age_ms=1,process_ok=True).freshness,Freshness.FRESH)
 def test_missing_origin_age_is_unknown(self):
  d=SequenceTracker().classify(source="x",session_id="s",seq=1,source_age_ms=None,transport_age_ms=1,process_ok=True)
  self.assertEqual(d.freshness,Freshness.UNKNOWN);self.assertFalse(d.allow_actuation)
 def test_missing_session_never_grants_actuation(self):
  d=SequenceTracker().classify(source="x",session_id=None,seq=1,source_age_ms=1,transport_age_ms=1,process_ok=True)
  self.assertEqual(d.freshness,Freshness.UNKNOWN);self.assertFalse(d.allow_actuation)

if __name__=="__main__":unittest.main()
