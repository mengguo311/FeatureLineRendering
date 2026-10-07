import unittest, json, tempfile
import runtime as rt
import numpy as np
from core import rays,project,lift,triangulate,contours,depth_summary,can_match,fuse_tracks,geometry_hash
import cpu_native as cpu
import mesh_tools as mesh

class Tracers(unittest.TestCase):
 def camera(self,x=0):
  V=np.eye(4);V[0,3]=-x
  return dict(K=[[90,7,28],[0,110,30],[0,0,1]],w2c=V.tolist(),width=64,height=64,FoVx=.7,FoVy=.7)
 def test_full_intrinsic(self):
  c=self.camera();p=np.array([[.2,-.1,2.],[.4,.2,3.]])
  uv,z=project(p,c);np.testing.assert_allclose(lift(uv,z,c),p,atol=1e-12)
  o,r=rays(uv,c);np.testing.assert_allclose(np.cross(p-o,r),0,atol=1e-12)
 def test_triangulation_cheirality_condition(self):
  a=self.camera();b=self.camera(.5);p=np.array([[.2,.1,3.]])
  ua,_=project(p,a);ub,_=project(p,b)
  q,status=triangulate(ua[0],a,ub[0],b)
  self.assertEqual(status,'accepted');np.testing.assert_allclose(q,p[0],atol=1e-10)
  self.assertEqual(triangulate(ua[0],a,ua[0],a)[1],'near_parallel')
  u1,_=project(-p,a);u2,_=project(-p,b)
  self.assertEqual(triangulate(u1[0],a,u2[0],b)[1],'behind_camera')
 def test_contours_holes(self):
  a=np.zeros((64,64));a[8:56,8:56]=1;a[24:40,24:40]=0
  cs=contours(a);self.assertEqual(set(c['kind'] for c in cs),{'outer','hole'})
  for c in cs:self.assertLess(np.linalg.norm(c['pixels'][1:]-c['pixels'][:-1],axis=1).max(),3.5)
 def test_depth_provenance(self):
  d=depth_summary(np.array([2.,3.,4.]),np.array([.2,.3,.1]))
  self.assertEqual(d['median'],3.);self.assertAlmostEqual(d['mass'],.6)
  self.assertTrue(np.isnan(depth_summary([],[])['median']))
 def test_sparse_accepted_cpu(self):
  p=dict(width=16,height=16,xy=np.array([[8,8],[8,8],[8,8]],np.float32),conic=np.array([[1,0,1]]*3,np.float32),opacity=np.array([.6,.8,.001],np.float32),depth=np.array([2,3,4],np.float32),rect=np.array([[0,0,1,1]]*3,np.int32),colors=np.ones((3,3),np.float32))
  q=cpu.query_contributors(p,np.array([[8,8],[0,0]],np.int32))
  np.testing.assert_array_equal(q['ids'],[0,1]);np.testing.assert_allclose(q['weights'],[.6,.32],atol=1e-7)
  self.assertEqual(q['offsets'].tolist(),[0,2,2])
  r=cpu.rasterize(p);self.assertAlmostEqual(float(q['weights'].sum()),float(r['alpha'][8,8]),places=6)
 def test_reverse_tangent_and_rolling(self):
  self.assertTrue(can_match([0,0,0],[.001,0,0],[1,0,0],[-1,0,0],.01,.3,0,0))
  self.assertFalse(can_match([0,0,0],[.001,0,0],[1,0,0],[1,0,0],.01,0,0,0))
  self.assertFalse(can_match([0,0,0],[.1,0,0],[1,0,0],[1,0,0],.01,.3,0,0))
 def test_dedup_track_negative_space(self):
  xyz=np.array([[0,0,3],[.1,0,3],[0,.001,3],[.1,.001,3],[.8,0,3],[.9,0,3.]])
  edges=np.array([[0,1],[2,3],[4,5]])
  # clusters 0/2 and 1/3 merge duplicate edges; no bridge to the distant component.
  r=fuse_tracks(xyz,edges,[[0,2],[1,3],[4],[5]],xyz[[0,1,4,5]],min_sources=2,views=np.array([0,0,1,1,2,2]))
  self.assertEqual(len(r['edges']),1);self.assertEqual(len(r['edge_sources'][0]),2)
  self.assertLess(np.linalg.norm(r['xyz'][r['edges'][0,0]]-r['xyz'][r['edges'][0,1]]),.2)
 def test_sealed_export(self):
  p=np.array([[0,0,2],[.1,0,2]],np.float32);e=np.array([[0,1]],np.int32);h=geometry_hash(p,e,.002)
  v,f=mesh.tube_mesh(p,e,.002);v0=v.copy();f0=f.copy()
  folder=rt.OUT/'tmp/test_export';paths=mesh.export_mesh(folder,v,f,'fixture')
  import trimesh
  m=trimesh.load(paths['glb'],force='mesh',process=False)
  np.testing.assert_allclose(m.vertices,v);np.testing.assert_array_equal(m.faces,f)
  m=trimesh.load(paths['obj'],force='mesh',process=False);self.assertEqual(len(m.faces),len(f))
  c=self.camera();c['K']=[[87.66,0,31.5],[0,87.66,31.5],[0,0,1]]
  mesh.render_mesh(v,f,c)
  np.testing.assert_array_equal(v,v0);np.testing.assert_array_equal(f,f0);self.assertEqual(h,geometry_hash(p,e,.002))

if __name__=='__main__':unittest.main(verbosity=2)
