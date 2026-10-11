import tempfile,unittest
from pathlib import Path
from depth_seals import seal_stage,verify_seal
class Tests(unittest.TestCase):
 def test_depth_seal_hash_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);f=p/'result';f.write_text('original');s=p/'seal.json';seal_stage(s,'depth_review',{'a':1},[f]);self.assertTrue(verify_seal(s,'depth_review',{'a':1}));f.write_text('changed');self.assertFalse(verify_seal(s,'depth_review',{'a':1}))
 def test_removed_stages_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);f=p/'result';f.write_text('value')
   for s in ('tsdf','eval','mesh'):
    with self.assertRaises(ValueError):seal_stage(p/'seal.json',s,{},[f])
if __name__=='__main__':unittest.main(verbosity=2)
