import unittest, json
from pathlib import Path
import numpy as np
from src.independent_rgbd.render import render_asset
from src.independent_rgbd.core import edit_asset

class RenderTests(unittest.TestCase):
 def test_fixed_world_asset_all_views_and_occlusion(self):
  asset={'curves':[{'id':'a','points':[[-.1,0,1],[.1,0,1]],'width':.007,'edges':[[0,1]]}]}; before=json.dumps(asset)
  K=np.array([[100,0,40],[0,100,30],[0,0,1.]])
  for shift in [0,.05,-.05]:
   c=np.eye(4);c[0,3]=shift
   mask,stats=render_asset(asset,K,c,np.ones((60,80)))
   self.assertGreater(mask.sum(),0);self.assertEqual(stats['ids'],['a']);self.assertEqual(json.dumps(asset),before)
   hidden,stats=render_asset(asset,K,c,np.full((60,80),.5));self.assertEqual(hidden.sum(),0)
  edited=edit_asset(asset,'a',[.02,0,0],2)
  m1,_=render_asset(asset,K,np.eye(4),np.ones((60,80)));m2,_=render_asset(edited,K,np.eye(4),np.ones((60,80)))
  self.assertGreater(abs(m1-m2).sum(),0)
 def test_frozen_alignment_metadata(self):
  root=Path(__file__).resolve().parents[2];a=root/'artifacts/independent_rgbd_asset_probe';cfg=json.loads((a/'INPUTS.json').read_text());poses=json.loads((a/'DEPTH_TIME_POSES.json').read_text())['poses']
  self.assertEqual(cfg['counts']['F'],92);self.assertEqual(cfg['counts']['C'],460);self.assertEqual(len({f['depth'] for f in cfg['frames']}),552)
  delta=[]
  for f in cfg['frames']:
   self.assertLessEqual(f['association_dt'],.02);self.assertLessEqual(f['pose_bracket_gap'],.05)
   p=np.array(poses[f['id']]);np.testing.assert_allclose(p[:3,:3].T@p[:3,:3],np.eye(3),atol=1e-8);delta.append(np.linalg.norm(p[:3,3]-np.array(f['c2w'])[:3,3]))
  self.assertGreater(max(delta),.001) # RGB/depth timestamps must not be treated as identical.
if __name__=='__main__':unittest.main()
