from free_io import *
import unittest
import image_path_core as e
import graph_birth_core as g
from test_graph_birth import GraphBirthTests
class ImageTests(unittest.TestCase):
 def test_project(self):
  c=dict(w2c=np.eye(4).tolist(),fx=2.,fy=2.,cx=3.,cy=3.,width=8,height=8)
  xy,z=e.project_camera(np.array([[1.,0,2]]),c);np.testing.assert_allclose(xy,[[4,3]])
 def test_unknown_and_edge(self):
  gx=np.zeros((8,8));gy=np.full((8,8),.2);p=np.array([[[2.,3.],[3.,3.],[4.,3.]],[[2.,3.],[3.,3.],[4.,3.]]]);depth=np.array([[1,1,1],[-1,1,1]])
  s=e.view_support(p,depth,gx,gy);self.assertEqual(s.tolist(),[1,2]);self.assertEqual(e.view_support(p[:1],depth[:1],gx,gx).tolist(),[0])
 def test_fixed_R_and_zero_reward(self):
  a=dict(source=np.array([0,1]),target=np.array([1,2]),weight=np.array([40.,40.]),length=np.ones(2),state_count=3)
  b=dict(a,weight=np.array([20.,20.]),base_weight=a['weight']);d,p=e.shortest(b,0);self.assertFalse(np.isfinite(d[2]));self.assertEqual(d[1],20)
  b['weight']=a['weight'];dd,pp=e.shortest(b,0);od,op=g.shortest(a,0);np.testing.assert_array_equal(dd,od);np.testing.assert_array_equal(pp,op)
 def test_real_loader_phase(self):
  from free_io import load
  phases=[]
  def guard(ph):phases.append(ph);raise TimeoutError(ph)
  self.assertRaisesRegex(TimeoutError,'readiness',load,{},guard);self.assertEqual(phases,['readiness'])
 def test_zero_reward_paths(self):
  t=GraphBirthTests();d=t.data();z=g.build_modes(d,np.full(63,-1));a=g.build_graph(z);seeds,_,_=g.select_seeds(z,a)
  p,r=g.propose(z,a,seeds);pp,rr=e.propose(z,dict(a,base_weight=a['weight']),seeds);self.assertEqual(r,rr)
 def test_new_runner_real_loader_and_checkpoint(self):
  import image_path_runner as runner
  from unittest.mock import patch
  import tempfile
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);c=GraphBirthTests().runner_fixture(p);d=load(c,lambda phase:None);_,aa,_=cold_stage(c['predecessor_stage'],c['predecessor_config_sha256']);z=g.build_modes(d,aa['edge_id']);a=g.build_graph(z);seeds,_,meta=g.select_seeds(z,a);paths,receipts=g.propose(z,a,seeds);bank=p/'saved_graph';bank.mkdir();nz(bank/'MODES.npz',**z);nz(bank/'GRAPH.npz',**a);js(bank/'SEED_SELECTION.json',meta);js(bank/'PATHS.json',dict(paths=[dict(candidate_id=i,**{k:v for k,v in x.items() if k!='q'}) for i,x in enumerate(paths)],seed_receipts=receipts));js(bank/'CHECKPOINT.json',dict(fixture=True));c.update(evidence_images={},saved_graph=str(bank),expected_modes=len(z['position']),expected_edges=len(a['source']),expected_seeds=len(seeds))
   with patch.object(runner.e,'evidence',return_value=(np.zeros((len(a['source']),2),np.uint8),np.zeros(len(a['source']),bool))),patch.object(runner,'deliver',return_value={}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0,(Path(c['unit_root'])/'RUN_RESULT.json').read_text());out=Path(c['unit_root']);cold_stage(out/'scenes/fixture/stages/BIRTH_FINAL','fixture');self.assertTrue((out/'graph/CONTROL_REPLAY.json').exists());self.assertEqual(len(list((out/'graph/reachable').glob('*.npz'))),2*len(seeds))
 def test_real_image_calibration_val_binding(self):
  import tempfile
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);img=p/'blank.png';Image.fromarray(np.zeros((800,800,4),np.uint8)).save(img);angle=.6911112070083618;fx=.5*800/np.tan(angle/2);cam=dict(view='test_r_1',original_c2w_gl=np.eye(4).tolist(),extrinsic=np.eye(4).tolist(),width=800,height=800,fx=fx,fy=fx,cx=399.5,cy=399.5);js(p/'cams.json',dict(fixture=[cam]));tr=dict(camera_angle_x=angle,frames=[dict(file_path='./val/r_1',transform_matrix=np.eye(4).tolist())]);js(p/'tr.json',tr);c=dict(cameras=str(p/'cams.json'),scene='fixture',image_transforms=str(p/'tr.json'),evidence_images={'test_r_1':str(img)},p=1.);z=dict(position=np.array([[0.,0,3.],[.1,0,3.]]));a=dict(source=np.array([0,3]),target=np.array([2,1]));status,support=e.evidence(c,z,a);self.assertFalse(support.any());self.assertTrue((status==0).all())
   tr['frames'][0]['transform_matrix'][0][3]=1.;js(p/'wrong.json',tr);c['image_transforms']=str(p/'wrong.json');self.assertRaises(AssertionError,e.evidence,c,z,a)
if __name__=='__main__':unittest.main()
