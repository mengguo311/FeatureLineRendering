import unittest,json
import runtime as rt
class ShapeTests(unittest.TestCase):
 def test_recomputed_native_covariance_and_adjoint(self):
  from shape_arm import make_shape
  from adapter import backend,scene_io,NativeWeights,ShapeWeights,shape_extension,query_extension
  import torch,numpy as np
  rt.guard('shape-native-test');f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());cfg=json.loads((rt.ART/'PROTOCOL.json').read_text());rec=f['scenes']['lego'];c=next(c for c in rec['cameras'] if c['key']=='r_7');m=scene_io.load_model(rec);mod=backend();s=scene_io.make_settings(mod,c);op=NativeWeights(mod,s,m);R,_,_,g,b,i=op.state;xy,cov,conic,rgb=query_extension().geometry(g,op.n);base=ShapeWeights(shape_extension(),s,m,cov);x=torch.full((op.n,),.25,device='cuda')
  self.assertLess(float((base.A(x)-op.A(x)).abs().max()),3e-6)
  e=dict(np.load(rt.ART/'downloads/lego/r_7/evidence.npz'));cov2,rec2=make_shape(op,e,cfg)
  self.assertGreater(len(rec2['edited_original_ids']),0);self.assertLessEqual(rec2['generalized_eigenvalue_max'],1.00001);self.assertGreaterEqual(rec2['generalized_eigenvalue_min'],.24999)
  edited=ShapeWeights(shape_extension(),s,m,cov2);self.assertGreater(float((edited.A(x)-op.A(x)).abs().max()),1e-4)
  gen=torch.Generator(device='cuda').manual_seed(68);y=torch.randn((800,800),device='cuda',generator=gen);lhs=float((edited.A(x).double()*y.double()).sum());rhs=float((x.double()*edited.AT(y).double()).sum());self.assertLess(abs(lhs-rhs)/max(abs(lhs),abs(rhs),1),3e-5)
  self.assertLess(float((edited.ink_rgb(x)[0]-(1-edited.A(x))).abs().max()),3e-6)
  rt.atomic_json(rt.ART/'tests/SHAPE_NATIVE_CONTROLS.json',dict(edited_count=len(rec2['edited_original_ids']),full_native=True,centers_fixed=True,all_opacity_retained=True,baseline_equivalence=True,adjoint_relative_error=abs(lhs-rhs)/max(abs(lhs),abs(rhs),1)))
if __name__=='__main__':unittest.main()
