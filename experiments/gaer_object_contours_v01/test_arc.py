import unittest,json
import runtime as rt
class ArcTests(unittest.TestCase):
 def test_actual_prior33_identity_and_no_stills(self):
  from evaluate import arc_manifest
  f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text())
  for scene in ['lego','chair']:
   m=arc_manifest(f['scenes'][scene]);self.assertEqual(m['frame_count'],33);self.assertEqual(m['unique_camera_count'],33);self.assertEqual(m['fit_reset'],'zero each camera; no warm starts');self.assertEqual(m['width'],800)
if __name__=='__main__':unittest.main()
