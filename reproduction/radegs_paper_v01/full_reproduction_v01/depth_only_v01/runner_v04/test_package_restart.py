import tempfile,unittest
from pathlib import Path
from package_restart import preserve_incomplete
class Tests(unittest.TestCase):
 def test_absent_destination_no_archive(self):
  with tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01') as t:
   p=Path(t)/'scene';self.assertIsNone(preserve_incomplete(p));self.assertFalse(p.exists())
 def test_restart_preserves_every_prior_byte(self):
  with tempfile.TemporaryDirectory(dir='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_only_v01') as t:
   p=Path(t)/'scene';p.mkdir();(p/'partial').write_bytes(b'previous evidence');q=preserve_incomplete(p)
   self.assertFalse(p.exists());self.assertEqual((q/'partial').read_bytes(),b'previous evidence')
   p.mkdir();(p/'partial').write_bytes(b'new evidence');r=preserve_incomplete(p)
   self.assertNotEqual(r,q);self.assertEqual((q/'partial').read_bytes(),b'previous evidence');self.assertEqual((r/'partial').read_bytes(),b'new evidence')
if __name__=='__main__':unittest.main(verbosity=2)
