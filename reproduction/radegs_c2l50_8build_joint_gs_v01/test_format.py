from common import *
import unittest,tempfile
from format import merge_native,activate,portable,write_ply,read_ply,mapping
def fixture(n=2,sh=True,fil=True):
 fields=['x','y','z','nx','ny','nz']+[f'f_dc_{i}' for i in range(3)]+([f'f_rest_{i}' for i in range(45)] if sh else [])+['opacity']+[f'scale_{i}' for i in range(3)]+[f'rot_{i}' for i in range(4)]+(['filter_3D'] if fil else [])
 a=np.zeros(n,[(k,'<f4') for k in fields]);a['z']=2;a['rot_0']=1
 for k in ['scale_0','scale_1','scale_2']:a[k]=np.log(.02)
 if fil:a['filter_3D']=.01
 return a
class FormatTests(unittest.TestCase):
 def test_native_prefix_and_black_sh(self):
  s=fixture();s['opacity'][0]=np.inf;s['f_rest_17']=.3;l=fixture(3,False,False)
  for i in range(3):l[f'f_dc_{i}']=-.5/.28209479177387814
  m=merge_native(s,l)
  for k in s.dtype.names:self.assertEqual(m[k][:len(s)].tobytes(),s[k].tobytes())
  for k in l.dtype.names:self.assertEqual(m[k][len(s):].tobytes(),l[k].tobytes())
  self.assertTrue((m['filter_3D'][2:]==0).all());self.assertTrue((m['f_rest_17'][2:]==0).all());self.assertEqual(len(m),5)
 def test_filter_inf_and_covariance(self):
  s=fixture();s['opacity'][0]=np.inf;a=activate(s)
  self.assertTrue(np.isfinite(a['opacity']).all());self.assertAlmostEqual(a['opacity'][0],(.0004/.0005)**1.5,7)
  np.testing.assert_allclose(a['covariance'][0],np.eye(3)*.0005,rtol=1e-6,atol=1e-12)
 def test_portable_effective_and_sh(self):
  s=fixture();s['opacity'][0]=np.inf;s['f_rest_44']=.8;p,stats=portable(s,1e-7);a,b=activate(s),activate(p)
  self.assertNotIn('filter_3D',p.dtype.names);self.assertTrue(np.isfinite(p['opacity']).all());self.assertEqual(s['f_rest_44'].tobytes(),p['f_rest_44'].tobytes());np.testing.assert_allclose(a['covariance'],b['covariance'],rtol=2e-6,atol=1e-12);np.testing.assert_allclose(a['opacity'],b['opacity'],atol=2e-7,rtol=0)
 def test_finite_logit_disclosed_clip(self):
  s=fixture(fil=False);s['opacity']=[np.inf,-np.inf];p,r=portable(s,1e-7);self.assertEqual(r['clip_count'],2);self.assertTrue(np.isfinite(p['opacity']).all());np.testing.assert_allclose(activate(p)['opacity'],[1-1e-7,1e-7],atol=1e-12)
 def test_group_mapping(self):
  d=mapping(2,dict(primitive_id=np.array([3,5,3]),internal_piece_id=np.array([7,8,9]),arc_t=np.array([.1,.5,.9])))
  np.testing.assert_array_equal(d['group_id'],[0,0,1,1,1]);np.testing.assert_array_equal(d['source_index'],[0,1,-1,-1,-1]);np.testing.assert_array_equal(d['primitive_id'],[-1,-1,3,5,3])
 def test_reload_exact_fields(self):
  s=fixture();s['opacity'][1]=np.inf;m=merge_native(s,fixture(1,False,False));(ROOT/'scratch').mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=ROOT/'scratch') as d:
   p=Path(d)/'a.ply';write_ply(p,m);a=read_ply(p)
   for k in m.dtype.names:self.assertEqual(a[k].tobytes(),m[k].tobytes())
 def test_rotation_preserves_full_covariance(self):
  s=fixture();s['rot_0']=np.cos(.4);s['rot_3']=np.sin(.4);s['scale_0']=np.log(.07);p,r=portable(s);np.testing.assert_allclose(activate(s)['covariance'],activate(p)['covariance'],rtol=2e-6,atol=1e-12)
if __name__=='__main__':unittest.main()
