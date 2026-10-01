import unittest, tempfile, json, subprocess, sys
from pathlib import Path
import numpy as np
from src.independent_rgbd.core import project, unproject, visibility, associate, edit_asset, asset_arrays, depth_metres, allowed_raw, restrict_filesystem

class CoreTests(unittest.TestCase):
 def test_projection_nonidentity_and_behind(self):
  K=np.array([[100,0,50],[0,120,40],[0,0,1.]])
  c=np.eye(4); c[:3,3]=[1,2,3]
  uv,z=project(np.array([[2,4,5],[1,2,2]]),K,c)
  np.testing.assert_allclose(uv[0],[100,160]); self.assertEqual(z[1],-1); self.assertTrue(np.isnan(uv[1]).all())
 def test_backproject_pose_and_units(self):
  K=np.array([[100,0,50],[0,120,40],[0,0,1.]])
  c=np.eye(4); c[:3,3]=[1,2,3]
  p=unproject(np.array([[100,160.]]),np.array([2.]),K,c)
  np.testing.assert_allclose(p,[[2,4,5]])
  np.testing.assert_allclose(depth_metres(np.array([[0,5000,10000]],np.uint16)),[[0,1,2]])
 def test_occlusion_unknown_contradiction(self):
  d=np.ones((4,4)); d[0,0]=0
  label=visibility(np.array([[1,1],[1,1],[1,1],[0,0],[9,9]]),np.array([1,2,.5,1,1]),d)
  self.assertEqual(label.tolist(),['consistent','occluded','contradiction','unknown','unknown'])
 def test_association_unique_bounded(self):
  self.assertEqual(associate([1.,1.01,2.],[1.005,2.1],.02),[(0,0)])
 def test_role_boundary(self):
  f={'split':'F','rgb':'rgb/a.png','depth':'depth/a.png'}; c=dict(f,split='C',rgb='rgb/b.png',depth='depth/b.png')
  self.assertEqual(allowed_raw([f,c],'train'),{'rgb/a.png'})
  self.assertEqual(allowed_raw([f,c],'build'),{'depth/a.png'})
  self.assertEqual(allowed_raw([f,c],'eval'),{'rgb/a.png','rgb/b.png','depth/a.png','depth/b.png'})
  with self.assertRaises(ValueError): allowed_raw([f,c],'unknown')
 def test_edit_identity_topology_serialize(self):
  a={'curves':[{'id':'x','points':[[0,0,1],[1,0,1]],'width':.007,'edges':[[0,1]]}]}
  before=json.dumps(a,sort_keys=True); b=edit_asset(a,'x',[.02,0,0],2)
  self.assertEqual(json.dumps(a,sort_keys=True),before); self.assertEqual(b['curves'][0]['id'],'x'); self.assertEqual(b['curves'][0]['edges'],[[0,1]])
  self.assertEqual(b['curves'][0]['width'],.014)
  ar=asset_arrays(b); self.assertEqual(ar['ids'].tolist(),['x']); self.assertEqual(ar['offsets'].tolist(),[0,2])
  for x in [0.,.3]:
   c=np.eye(4); c[0,3]=x
   uv,_=project(ar['points'],np.eye(3),c)
   np.testing.assert_allclose(uv[:,0],[.02-x,1.02-x])
 def test_native_boundary(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td); (p/'allowed').write_text('a'); (p/'denied').write_text('secret')
   code="from src.independent_rgbd.core import restrict_filesystem; import os; restrict_filesystem(["+repr(str(p/'allowed'))+"],[]); assert open("+repr(str(p/'allowed'))+").read()=='a';\ntry: os.open("+repr(str(p/'denied'))+",os.O_RDONLY)\nexcept PermissionError: pass\nelse: raise AssertionError('native boundary leaked')"
   r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
if __name__=='__main__': unittest.main()
