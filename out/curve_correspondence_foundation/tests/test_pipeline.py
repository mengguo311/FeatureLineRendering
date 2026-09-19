import unittest, pathlib, tempfile, json
import numpy as np
import cc
from test_matching import CFG,camera,curve
class Pipeline(unittest.TestCase):
 def test_three_view_pipeline_positive_and_null_records(self):
  cams={i:camera([x,0,0]) for i,x in enumerate([-1.5,0,1.5],1)};X=np.c_[np.zeros(21),np.linspace(-.3,.3,21),np.full(21,3.)]
  cs={str(i):curve(i,cc.project_jacobian(X,c['K'],c['w2c'])[0]) for i,c in cams.items()}
  edges,stats=cc.match_all(cs,cams,[[-2,-2,1],[2,2,5]],CFG['matching'])
  self.assertEqual(sum(r['selected'] for r in edges),3);self.assertEqual(stats['curve_pairs'],3)
  result=cc.reconstruct(cs,cams,edges,[[-2,-2,1],[2,2,5]],.01,CFG)
  self.assertEqual(len(result['accepted']),1);self.assertEqual(result['identity_hypotheses'],1)
  self.assertTrue(result['accepted'][0]['identity_frozen_before_fit'])
  control=cc.reconstruct(cs,cams,edges,[[-2,-2,1],[2,2,5]],.01,CFG,pairwise=True)
  self.assertEqual(len(control['accepted']),3)
 def test_gs_evaluation_tracks_all_classifications(self):
  c=camera([0,0,0]);x=np.c_[np.zeros(5),np.linspace(0,.2,5),np.full(5,3.)]
  record=dict(id='x',xyz=x,root_arc=np.arange(5)*4.,nodes=['1','2','3'],views=[1,2,3])
  class Layers:
   def query(self,uv,z,delta):return np.ones(len(uv)),np.ones(len(uv),bool)
  accepted,detail=cc.apply_gs([record],{1:c,2:c,3:c},{1:Layers(),2:Layers(),3:Layers()},.01,CFG['fit'])
  self.assertEqual(len(accepted),1);self.assertEqual(detail['visible_supported'],15)
  accepted,detail=cc.apply_gs([record],{1:c,2:c},{1:Layers(),2:Layers()},.01,CFG['fit']);self.assertEqual(len(accepted),0)
 def test_serialization_freeze_detects_mutation_and_nonfinite(self):
  import cc_io
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'a.json.gz';cc_io.write_json(p,dict(x=np.arange(3),bad=np.inf));q=cc_io.read_json(p);self.assertEqual(q,dict(x=[0,1,2],bad=None))
   with self.assertRaises(FileExistsError):cc_io.write_json(p,{})
   seal=cc_io.seal(pathlib.Path(td));self.assertTrue(cc_io.verify_seal(pathlib.Path(td),seal));p.write_bytes(b'changed');self.assertFalse(cc_io.verify_seal(pathlib.Path(td),seal))
 def test_confinement_split_allowlist_has_no_other_photo(self):
  import cc_io
  c=cc_io.scene_inputs(CFG,'lego','F')
  self.assertEqual({p['index'] for p in c['cameras'].values()},set(CFG['splits']['F']))
  self.assertFalse(any('/r_2.png' in p for p in c['photos']))
  with self.assertRaises(ValueError):cc_io.scene_inputs(CFG,'lego','TEST')
if __name__=='__main__':unittest.main()
