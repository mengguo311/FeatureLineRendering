import unittest
from env import *
from graph import find_regions,boundary_evidence,transfer_region
class GraphTests(unittest.TestCase):
 def square(self,z=1.):
  V=np.array([[20,20],[40,20],[40,40],[20,40],[20,20]],float);fs=[]
  for i in range(4):
   t=np.linspace(.05,.95,19);uv=V[i]+t[:,None]*(V[i+1]-V[i]);fs.append(dict(uv=uv,z=np.full(len(t),z),parent=i,indices=np.arange(len(t)),end_ok=[True,True],closed=False))
  return fs
 def raw(self):return dict(rgb=np.zeros((64,64,3)),alpha=np.ones((64,64)),median_camera_z=np.ones((64,64)))
 def cam(self):return dict(fx=100.,fy=100.,cx=32.,cy=32.,width=64,height=64,extrinsic=np.eye(4).tolist())
 def test_legal_region(self):
  # Scale proxy is 1/100: same layer, exact synthetic corner fragments.
  rs,ledger=find_regions(self.square(),self.raw(),self.cam());self.assertGreaterEqual(len(rs),1);self.assertGreater(rs[0]['area'],300)
 def test_cross_layer(self):
  fs=self.square();fs[1]['z']*=2;rs,l=find_regions(fs,self.raw(),self.cam());self.assertEqual(len(rs),0)
 def test_occlusion_no_bridge(self):
  fs=self.square();fs[1]['end_ok']=[False,False];rs,l=find_regions(fs,self.raw(),self.cam());self.assertEqual(len(rs),0)
 def test_no_self_cross_region(self):
  fs=self.square();fs[0]['uv']=np.array([[20,20],[40,40],[20,40],[40,20],[20,20]]);fs=fs[:1];fs[0]['closed']=True;fs[0]['z']=np.ones(5);rs,l=find_regions(fs,self.raw(),self.cam());self.assertEqual(len(rs),0)
 def test_uniform_rgb_not_self_evidence(self):
  r=boundary_evidence(np.array([[20,20],[40,20],[40,40],[20,40],[20,20]]),self.raw(),self.cam());self.assertEqual(r['support_fraction'],0)
 def test_transfer_same_camera(self):
  m=np.zeros((64,64),bool);m[20:40,20:40]=True;x=transfer_region(m,self.raw(),self.cam(),self.raw(),self.cam(),[m]);self.assertAlmostEqual(x['iou'],1);self.assertAlmostEqual(x['comparable_fraction'],1)
if __name__=='__main__':unittest.main()
