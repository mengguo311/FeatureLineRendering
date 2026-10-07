"""Post-build expanded contract tests. Does not alter production geometry."""
import unittest,tempfile,json,copy
from pathlib import Path
import numpy as np
import runtime as rt
import cpu_native as cpu
import pipeline as pp
from core import *

class Expanded(unittest.TestCase):
 def projected(self,op,depth):
  n=len(op)
  return dict(width=16,height=16,xy=np.full((n,2),8,np.float32),conic=np.tile(np.array([1,0,1],np.float32),(n,1)),opacity=np.array(op,np.float32),depth=np.array(depth,np.float32),rect=np.tile(np.array([0,0,1,1],np.int32),(n,1)),colors=np.ones((n,3),np.float32))
 def test_conditional_median_differs_from_half_T(self):
  q=cpu.query_contributors(self.projected([.3,.4],[2,3]),np.array([[8,8]],np.int32));w=q['weights'];self.assertAlmostEqual(float(w.sum()),.58,places=6)
  self.assertEqual(depth_summary([2,3],w)['median'],2.) # Absolute T=.5 crossing would be depth3.
  self.assertEqual(depth_summary([2,3],[.2,.1])['median'],2.) # No absolute crossing at all.
 def test_rejected_termination_contributor(self):
  q=cpu.query_contributors(self.projected([.99,.99,.99],[2,3,4]),np.array([[8,8]],np.int32));self.assertEqual(q['ids'].tolist(),[0]) # second test T about .0001 falls below float32 gate
 def test_stable_depth_tie_and_cutoff(self):
  q=cpu.query_contributors(self.projected([.5,.4,.001],[2,2,2]),np.array([[8,8]],np.int32));self.assertEqual(q['ids'].tolist(),[0,1]);np.testing.assert_allclose(q['weights'],[.5,.2])
 def test_hierarchy_nested_island(self):
  a=np.zeros((100,100));a[5:95,5:95]=1;a[20:80,20:80]=0;a[35:65,35:65]=1
  cs=contours(a);self.assertEqual([c['kind'] for c in cs],['outer','hole','outer'])
 def test_source_path_no_bridge(self):
  p=np.array([[0,0,0],[1,0,0],[5,0,0],[6,0,0.]])
  e=np.array([[0,1],[2,3]]);paths=pp.graph_paths(e);self.assertEqual(paths,[[0,1],[2,3]])
 def fixture(self):
  # Actual build_fusion, calibrated rays, proxy perturbation, full support, three source views.
  cams=[];src=[];true=np.c_[np.linspace(-.24,.24,9),np.zeros(9),np.full(9,3.)]
  for j in range(3):
   V=np.eye(4);V[0,3]=-.6*j;c=dict(K=[[100,0,32],[0,110,32],[0,0,1]],w2c=V.tolist());cams.append(c);pix,z=project(true,c);xyz=lift(pix,z+.002*(j-1),c)
   src.append(dict(xyz=xyz.astype(np.float32),pixels=pix,tangent=np.tile([1.,0,0],(9,1)),chain=np.zeros(9,np.int32),local=np.arange(9),kind=np.zeros(9,np.int32),world_pixel=np.full(9,.03),edges=np.c_[np.arange(8),np.arange(1,9)],accepted_offsets=np.arange(10),accepted_ids=np.zeros(9,np.int32),accepted_weights=np.ones(9)))
  off=np.arange(4)*9;data={k:np.concatenate([s[k] for s in src]) for k in ('xyz','pixels','tangent','chain','local','kind','world_pixel')};data['view']=np.repeat(np.arange(3),9);data['edges']=np.concatenate([s['edges']+off[i] for i,s in enumerate(src)])
  return src,off,data,cams
 def test_full_production_pair_cluster_fusion(self):
  self.fixture_run(*self.fixture())
 def test_actual_rolling_distinct_support_refused(self):
  src,off,data,cams=self.fixture()
  for j,s in enumerate(src):s['accepted_ids'][:]=j
  self.fixture_run(src,off,data,cams,expected_nodes=0,expected_edges=0)
 def test_actual_near_parallel_refused(self):
  src,off,data,cams=self.fixture()
  cams=[cams[0]]*3
  for s in src:s['pixels']=src[0]['pixels'].copy();s['xyz']=src[0]['xyz'].copy()
  data['xyz']=np.concatenate([s['xyz'] for s in src]);data['pixels']=np.concatenate([s['pixels'] for s in src])
  self.fixture_run(src,off,data,cams,expected_nodes=0,expected_edges=0)
 def test_actual_reverse_order_matches(self):
  src,off,data,cams=self.fixture()
  s=src[-1]
  for k in ('xyz','pixels'):s[k]=s[k][::-1].copy()
  s['tangent']=-s['tangent']
  for k in ('xyz','pixels','tangent'):data[k]=np.concatenate([s[k] for s in src])
  self.fixture_run(src,off,data,cams)
 def fixture_run(self,src,off,data,cams,expected_nodes=9,expected_edges=8):
  oldart=rt.ART;oldresume=rt.resume;oldcollect=pp.collect;oldcamera=pp.camera;oldseal=pp.seal
  with tempfile.TemporaryDirectory(dir=rt.OUT/'tmp',prefix='tracer_') as td:
   try:
    rt.ART=Path(td);(rt.ART/'logs').mkdir();rt.resume=lambda x:False;pp.collect=lambda n:(['a','b','c'],src,off,data);pp.camera=lambda n,k:cams[['a','b','c'].index(k)];pp.seal=lambda *args:None
    pp.build_fusion('fixture');a=dict(np.load(rt.ART/'fusion/fixture/fused.npz'));p=json.loads((rt.ART/'fusion/fixture/fused.json').read_text())
    self.assertEqual(len(a['xyz']),expected_nodes);self.assertEqual(len(a['edges']),expected_edges);self.assertTrue(all(len(s)==3 for s in p['node_sources']));self.assertTrue(all(len(s)==3 for s in p['edge_sources']));self.assertLess(max(p['all_source_reprojection_px'],default=0),1e-4)
   finally:rt.ART=oldart;rt.resume=oldresume;pp.collect=oldcollect;pp.camera=oldcamera;pp.seal=oldseal
 def test_endpoint_support_is_not_edge_support(self):
  # Deliberate boundary characterization, not a certification of multisource edges.
  xyz=np.array([[0,0,0],[1,0,0],[0,0,0],[1,0,0.]])
  r=fuse_tracks(xyz,np.array([[0,1]]),[[0,2],[1,3]],xyz[:2],2,np.array([0,0,1,2]))
  self.assertEqual(len(r['edges']),1);self.assertEqual(r['edge_sources'],[[0]])

if __name__=='__main__':unittest.main(verbosity=2)
