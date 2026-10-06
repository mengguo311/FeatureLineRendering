import hashlib,json,struct,tempfile,unittest
from pathlib import Path
import numpy as np
from mesh_tools import render_mesh,export_mesh,tube_mesh,write_viewer
import runtime as rt

class MeshTests(unittest.TestCase):
 def setUp(self):
  self.camera=dict(width=80,height=80,FoVx=2*np.arctan(.5),FoVy=2*np.arctan(.5),w2c=np.eye(4).tolist())
 def test_perspective_depth_and_overlap(self):
  # Two overlapping triangles; depth must be perspective corrected, closest wins.
  v=np.array([[-.5,-.5,2],[.5,-.5,2],[0,.5,2],[-1,-1,4],[1,-1,4],[0,1,4]])
  f=np.array([[3,4,5],[0,1,2]])
  r=render_mesh(v,f,self.camera)
  self.assertTrue(r['mask'][39,39]);self.assertAlmostEqual(float(r['depth'][39,39]),2,places=5)
  self.assertTrue(np.all(r['rgb'][~r['mask']]==255))
  self.assertGreater(int(r['mask'].sum()),700)
  slant=np.array([[-.5,-.5,1],[1,-1,2],[0,2,4]])
  q=render_mesh(slant,[[0,1,2]],self.camera)
  uv=slant[:,:2]/slant[:,2,None]*80+39.5
  p=np.array([39.,39.]);ab=uv[1]-uv[0];ac=uv[2]-uv[0];b,c=np.linalg.solve(np.stack([ab,ac],axis=1),p-uv[0]);expected=1/((1-b-c)/1+b/2+c/4)
  self.assertAlmostEqual(float(q['depth'][39,39]),expected,places=5)
 def test_real_world_width_and_static_geometry(self):
  xyz=np.array([[-.4,0,2],[.4,0,2]],np.float32);e=np.array([[0,1]])
  v,f=tube_mesh(xyz,e,.04);h=hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest()
  area=render_mesh(v,f,self.camera)['mask'].sum()
  wide,ff=tube_mesh(xyz,e,.12);self.assertGreater(render_mesh(wide,ff,self.camera)['mask'].sum(),2*area)
  for tx in [-.2,0,.2]:
   c=dict(self.camera);m=np.eye(4);m[0,3]=tx;c['w2c']=m.tolist();render_mesh(v,f,c)
  self.assertEqual(h,hashlib.sha256(v.tobytes()+f.tobytes()).hexdigest())
 def test_near_clip_and_external_depth_explicit(self):
  # Nondegenerate projected plane; the first fixture accidentally lay y=-3*z.
  v=np.array([[-.3,-.3,.1],[.3,-.3,.1],[0,.5,-.1]])
  r=render_mesh(v,[[0,1,2]],self.camera);self.assertGreater(r['mask'].sum(),0)
  self.assertTrue(np.all(r['depth'][r['mask']]>=.01-1e-6))
  z=np.full((80,80),.005,np.float32)
  o=render_mesh(v,[[0,1,2]],self.camera,occluder_depth=z,occlusion_tolerance=0)
  self.assertFalse(o['mask'].any());self.assertEqual(o['visibility'],'external_depth_operator')
 def test_export_triangle_roundtrip_and_offline(self):
  with tempfile.TemporaryDirectory(dir=rt.OUT/'tmp') as d:
   v,f=tube_mesh(np.array([[0,0,2],[1,0,2]]),[[0,1]],.05)
   p=export_mesh(d,v,f,'outer');data=Path(p['glb']).read_bytes();magic,ver,n=struct.unpack_from('<III',data)
   self.assertEqual((magic,ver,n),(0x46546c67,2,len(data)))
   jlen,jtype=struct.unpack_from('<II',data,12);doc=json.loads(data[20:20+jlen]);self.assertEqual(doc['meshes'][0]['primitives'][0]['mode'],4)
   self.assertEqual(doc['accessors'][1]['count'],f.size)
   import trimesh
   mesh=trimesh.load(p['glb'],force='mesh',process=False)
   np.testing.assert_array_equal(mesh.vertices,v);self.assertEqual(len(mesh.faces),len(f))
   obj=trimesh.load(p['obj'],force='mesh',process=False);self.assertEqual(len(obj.faces),len(f))
   page=Path(d)/'viewer.html';write_viewer(page,{'test':{'vertices':v,'faces':f}})
   html=page.read_text();self.assertNotIn('https://',html);self.assertIn('drawElements',html);self.assertIn('atob(',html)

if __name__=='__main__':unittest.main()
