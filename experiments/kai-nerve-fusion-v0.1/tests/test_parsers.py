import unittest,json
from kai_nerve.parsers import parse_line,parse_mcwss_frame
class ParserTests(unittest.TestCase):
 def test_kai_eyes(self):
  x=parse_line("foo KAI_EYES:"+json.dumps({"session_id":"s","seq":2,"tick":4}));self.assertEqual(x.source_seq,2)
 def test_hyperbridge(self):
  x=parse_line("KAIHB|STATE|"+json.dumps({"session_id":"s","seq":3}));self.assertEqual(x.kind,"STATE")
 def test_nerve(self):
  x=parse_line("KAINERVE|1|EVENT|"+json.dumps({"session_id":"s","seq":4}));self.assertEqual(x.source,"minecraft.kai_nerve")
 def test_mcwss_embedded(self):
  line="KAINERVE|1|STATE|"+json.dumps({"session_id":"s","seq":7})
  self.assertEqual(parse_mcwss_frame({"body":{"properties":{"Message":line}}}).source_seq,7)
if __name__=="__main__":unittest.main()
