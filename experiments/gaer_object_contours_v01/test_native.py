import unittest,json
import runtime as rt

class NativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from adapter import backend,scene_io,NativeWeights,query_extension
  import torch
  rt.guard('native-fixture')
  cls.torch=torch;cls.module=backend();cls.query=query_extension();f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());cls.record=f['scenes']['lego'];cls.c=[c for c in cls.record['cameras'] if c['key'] in ['r_7','r_33']];cls.model=scene_io.load_model(cls.record)
  cls.op=NativeWeights(cls.module,scene_io.make_settings(cls.module,cls.c[0]),cls.model)
 def test_zero_white_one_alpha(self):
  t=self.torch;o=self.op;z=t.zeros(o.n,device='cuda');one=t.ones_like(z);alpha=o.A(one)
  self.assertLess(float((o.ink_rgb(z)-1).abs().max()),3e-6)
  self.assertLess(float((o.ink_rgb(one)[0]-(1-alpha)).abs().max()),3e-6)
  self.assertGreater(float(alpha.sum()),10000)
 def test_native_forward_adjoint_and_ray(self):
  t=self.torch;o=self.op;gen=t.Generator(device='cuda').manual_seed(3421);s=t.rand(o.n,device='cuda',generator=gen);y=t.randn((800,800),device='cuda',generator=gen)
  ax=o.A(s);at=o.AT(y);lhs=float((ax.double()*y.double()).sum());rhs=float((s.double()*at.double()).sum())
  self.assertLess(abs(lhs-rhs)/max(abs(lhs),abs(rhs),1),3e-5)
  self.assertLess(float((o.ink_rgb(s)[0]-(1-ax)).abs().max()),3e-6)
  self.assertLess(float((ax-o.A(t.ones_like(s))).max()),3e-6)
  R,_,_,g,b,i=o.state;pix=t.tensor([[300,400],[550,300],[0,0]],dtype=t.int32,device='cuda');offs,ids,w,finalT=self.query.query(g,b,i,o.n,R,800,800,pix)
  for q in range(len(pix)):
   lo,hi=int(offs[q]),int(offs[q+1]);v=float((w[lo:hi].double()*s[ids[lo:hi].long()].double()).sum());a=float(ax[pix[q,0],pix[q,1]])
   self.assertLess(abs(v-a),3e-6)
 def test_same_original_ID_camera_change(self):
  from adapter import scene_io,NativeWeights
  t=self.torch;o=self.op;mass=o.AT(t.ones((800,800),device='cuda'));id=int(mass.argmax());x=t.zeros(o.n,device='cuda');x[id]=1
  other=NativeWeights(self.module,scene_io.make_settings(self.module,self.c[1]),self.model);a=o.A(x);b=other.A(x)
  self.assertEqual(other.n,o.n);self.assertGreater(float((a-b).abs().max()),1e-3)
  rt.atomic_json(rt.ART/'tests/NATIVE_ID_CAMERA.json',dict(original_id=id,cameras=[c['key'] for c in self.c],camera_hashes=[c['camera_sha256'] for c in self.c],identity='same immutable PLY row; camera-dependent projection',max_image_change=float((a-b).abs().max())))

if __name__=='__main__':unittest.main()
