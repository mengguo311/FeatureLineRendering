import unittest,json,numpy as np
from pathlib import Path
import runtime as rt
from contracts import camera_for,validate_partition
class ContractTest(unittest.TestCase):
 def test_partition_and_filename(self):
  f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text())
  for n,s in f['scenes'].items():
   validate_partition(s)
   self.assertEqual(s['cameras']['r_14']['metadata_index'],12)
   for c in s['cameras'].values():
    meta=json.loads(Path(c['metadata_path']).read_text());frame=next(f for f in meta['frames'] if f['file_path']==c['frame_file']);m=np.asarray(frame['transform_matrix']).copy();m[:3,1:3]*=-1
    w=np.asarray(c['w2c']);self.assertTrue(np.allclose(w@m,np.eye(4),atol=1e-12))
   with self.assertRaises(PermissionError):camera_for(s,'r_1','extract',False)
   with self.assertRaises(PermissionError):camera_for(s,'r_1','eval',False)
   self.assertEqual(camera_for(s,'r_1','eval',True)['key'],'r_1')
 def test_duplicate_rejected(self):
  s=dict(cameras={'a':{}},roles=dict(construction=['a'],dev=['a'],reserved=[]))
  with self.assertRaises(ValueError):validate_partition(s)
if __name__=='__main__':unittest.main()
