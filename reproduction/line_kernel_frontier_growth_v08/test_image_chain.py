import runtime_io
import unittest,tempfile,json
from pathlib import Path
import numpy as np
from PIL import Image
import image_chain_core as ic
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_012/tests')
class ImageChainTests(unittest.TestCase):
 def test_row_major_equal_cost_tie_and_phase_guard(self):
  xy=np.array([[0,0],[1,-1],[1,1],[2,0]])
  edges=[[0,2,1.],[2,3,1.],[0,1,1.],[1,3,1.]]
  self.assertEqual(ic.ordered_path(xy,[0,1,1,2],edges,[0],[1,2],[3]),[0,1,3])
  def fail():raise RuntimeError('resource guard')
  with self.assertRaisesRegex(RuntimeError,'resource guard'):ic.ordered_path(np.c_[np.arange(600),np.zeros(600)],list(range(600)),[[i,i+1,1.] for i in range(599)],[0],[300],[599],fail)
 def test_shared_ambiguity_precedes_image_confirmation(self):
  records=[dict(common=True,gap=g,history={'eligible':True},observed_history={'eligible':True},paired_history={'eligible':True},image_chain={'eligible':i==1}) for i,g in enumerate([.2,.3])]
  self.assertEqual(ic.choices(records),dict(BASE=None,PAIRED=None,IMAGE_CHAIN=None,reason='ambiguous_gap'))
 def test_candidate_projection_reversal_and_both_views(self):
  q=np.array([[0.,0,1],[3.,0,1],[4.,0,1],[8.,0,1]]);a=q[:3]
  cam=dict(extrinsic=np.eye(4).tolist(),fx=2.,fy=2.,cx=4.,cy=10.);g=np.zeros((25,25));h=g.copy();h[10,:]=.2
  ev={k:dict(camera=cam,gx=g,gy=h) for k in ('a','b')};d={'p':1.};st={'curves':{0:a.tolist()}};z={'q':q.tolist()}
  got=ic.candidate_evidence(d,st,0,1,z,ev);self.assertTrue(got['eligible']);self.assertEqual(got['frontier_s_p'],4.)
  self.assertEqual(got,ic.candidate_evidence(d,{'curves':{0:a[::-1].tolist()}},0,0,{'q':q[::-1].tolist()},ev))
  ev['b']=dict(camera=cam,gx=g,gy=g);self.assertFalse(ic.candidate_evidence(d,st,0,1,z,ev)['eligible'])
 def test_real_geometry_image_choice_two_transactions_and_rollback(self):
  import copy,test_overlap as f,seam_repair_core as repair,switch_core as sc,overlap_core as oc
  from frontier_core import endpoint_index
  d=f.data();d['asset']['arc_t']=d['asset']['means'][:,0]/20.;st=f.state(d);idx=oc.SegmentIndex(d['leaves']);end=endpoint_index(d['leaves']);g=np.zeros((40,40));h=g.copy();h[10,:]=.2
  e=np.eye(4);e[2,3]=1.;cam=dict(extrinsic=e.tolist(),fx=2.,fy=2.,cx=4.,cy=10.);ev={k:dict(camera=cam,gx=g,gy=h) for k in ('a','b')};c={'switch':{'max_combined_prefixes':256,'max_endpoint_donors':3}};budget=repair.Budget();saved=[]
  for donor in [1,2]:
   lib=repair.library(d,st,0,1,idx,end,'REPAIR',lambda:None,c,budget);ic.annotate(d,st,0,1,lib,ev);pick=ic.choices(lib['records'])['IMAGE_CHAIN'];self.assertIsNotNone(pick);z=lib['records'][pick];self.assertEqual(z['donor'],donor)
   before=copy.deepcopy(st)
   def fail(_):raise RuntimeError('save failure')
   with self.assertRaisesRegex(RuntimeError,'save failure'):sc.commit(st,0,z,fail)
   self.assertEqual(st,before);st=sc.commit(st,0,z,lambda state:saved.append(copy.deepcopy(state)))
  self.assertEqual(len(saved),2);self.assertEqual(st['accepted'][0],2)
 def test_scattered_anchor_hits_are_not_a_chain(self):
  self.assertEqual(ic.ordered_path(np.array([[0,0],[4,0],[8,0]]),[0,4,8],[],[0],[1],[2]),[])
 def test_connected_ordered_chain(self):
  self.assertEqual(ic.ordered_path(np.c_[np.arange(5),np.zeros(5)],[0,1,2,3,4],[[i,i+1,1.] for i in range(4)],[0],[2],[4]),[0,1,2,3,4])
 def test_wrong_direction_cannot_reach_anchor(self):
  self.assertEqual(ic.ordered_path(np.c_[np.arange(5),np.zeros(5)],[0,1,2,3,4],[[i+1,i,1.] for i in range(4)],[0],[2],[4]),[])
 def test_at_least_three_distinct_pixels(self):
  self.assertEqual(ic.ordered_path(np.array([[0,0],[1,0]]),[0,1],[[0,1,1.]],[0],[0],[1]),[])
 def test_full_graph_keeps_branches(self):
  gx=np.zeros((20,20));gy=np.zeros_like(gx);gy[9:12,2:17]=.2
  z=ic.view_chain([[2,10],[9,10],[16,10]],[1,1,1],1,gx,gy)
  self.assertTrue(z['eligible']);self.assertGreater(len(z['nodes']),len(z['path']));self.assertGreater(len(z['edges']),len(z['nodes']))
  for i,j,_ in z['edges']:self.assertGreaterEqual(z['nodes'][j]['arc_px']+1e-8,z['nodes'][i]['arc_px'])
 def test_resolution_and_missing_evidence(self):
  g=np.zeros((20,20));z=ic.view_chain([[2,10],[3,10],[6,10]],[1,1,1],1,g,g);self.assertEqual(z['reason'],'insufficient_projected_resolution')
  self.assertFalse(ic.view_chain([[2,10],[9,10],[16,10]],[1,1,1],1,g,g)['eligible'])
  self.assertEqual(ic.view_chain([[2,10],[9,10],[16,10]],[-1,1,1],1,g,g)['status'],'UNKNOWN')
 def test_segment_tie_uses_lower_index(self):
  g=np.zeros((20,20));h=g.copy();h[10,:]=.2;z=ic.view_chain([[2,10],[9,10],[16,10]],[1,1,1],1,g,h)
  self.assertEqual(next(n['segment'] for n in z['nodes'] if n['pixel']==[9,10]),0)
 def test_projection_gl_conversion(self):
  cam=dict(extrinsic=np.diag([1,-1,-1,1]).tolist(),fx=100,fy=100,cx=399.5,cy=399.5)
  uv,d=ic.project_camera([[0,0,-2],[1,1,-2]],cam);np.testing.assert_allclose(uv,[[399.5,399.5],[449.5,349.5]]);np.testing.assert_allclose(d,[2,2])
 def test_real_calibration_loader_and_phase_exception(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as td:
   r=Path(td);c=fixture_images(r);ph=[];ev,receipt=ic.load_evidence(c,ph.append);self.assertEqual(set(ev),{'a','b'});self.assertTrue(all(x=='readiness' for x in ph));self.assertEqual(len(receipt),2)
   def fail(phase):raise RuntimeError('phase '+phase)
   with self.assertRaisesRegex(RuntimeError,'phase readiness'):ic.load_evidence(c,fail)
   cams=json.loads((r/'image_cameras.json').read_text());cams['fixture'][0]['cx']=400;(r/'image_cameras.json').write_text(json.dumps(cams))
   with self.assertRaises(AssertionError):ic.load_evidence(c,lambda x:None)

def fixture_images(r):
 frames=[];cams=[];imgs={};f=400/np.tan(.5)
 for view in ('a','b'):
  path=r/(view+'.png');Image.fromarray(np.full((800,800,4),255,np.uint8)).save(path);imgs[view]=str(path);frames.append(dict(file_path='val/'+view,transform_matrix=np.eye(4).tolist()))
  cams.append(dict(view=view,original_c2w_gl=np.eye(4).tolist(),extrinsic=np.diag([1,-1,-1,1]).tolist(),fx=f,fy=f,cx=399.5,cy=399.5,width=800,height=800))
 (r/'image_calibration.json').write_text(json.dumps(dict(camera_angle_x=1.,frames=frames)));(r/'image_cameras.json').write_text(json.dumps(dict(fixture=cams)))
 return dict(scene='fixture',views=['a','b'],cameras=str(r/'image_cameras.json'),image_calibration=str(r/'image_calibration.json'),image_inputs=imgs)
