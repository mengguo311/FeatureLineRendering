import unittest
import numpy as np
import cc
from test_matching import CFG,camera,curve
class Geometry(unittest.TestCase):
 def test_robust_triangulation_and_degenerate_rejection(self):
  cams=[camera([x,0,0]) for x in [-1.5,-.7,0,.7,1.5]];X=np.array([.1,.05,3.])
  uv=np.array([cc.project_jacobian(X[None],c['K'],c['w2c'])[0][0] for c in cams]);uv[2]+=[30,20]
  fit=cc.triangulate(uv,cams,CFG['fit']);self.assertTrue(fit['passed']);self.assertEqual(fit['inliers'],4);self.assertLess(np.linalg.norm(fit['xyz']-X),.04)
  cams=[camera([x,0,0]) for x in [0,.00001,.00002]];uv=np.array([cc.project_jacobian(X[None],c['K'],c['w2c'])[0][0] for c in cams])
  fit=cc.triangulate(uv,cams,CFG['fit']);self.assertFalse(fit['passed']);self.assertIn('baseline',fit['reasons'])
 def test_bundle_adjustment_shared_curve_reduces_error_bounded(self):
  cams=[camera([x,0,0]) for x in [-1.5,0,1.5]];t=np.linspace(-.3,.3,9);truth=np.c_[.08*t*t,t,3+.03*t]
  obs=[cc.project_jacobian(truth,c['K'],c['w2c'])[0] for c in cams];arcs=[cc.arclength(p) for p in obs]
  initial=truth+np.random.default_rng(42).normal(0,.006,truth.shape)
  fit=cc.bundle_adjust(initial,cams,obs,arcs,.01,CFG['fit'])
  self.assertLess(fit['rms_after'],fit['rms_before']*.3);self.assertLess(np.linalg.norm(fit['xyz']-truth,axis=1).mean(),.003)
  self.assertTrue(np.all(abs(fit['xyz']-initial)<=.02000001));self.assertEqual(fit['xyz'].shape,truth.shape)
 def test_support_visibility_has_unknown_not_success(self):
  c=cc.classify_support([.9,.05,.5,.9],[True,True,True,False],[True,True,True,False])
  self.assertEqual(c,['visible_supported','hidden','uncertain','out_of_frame'])
  self.assertEqual(cc.classify_support([.9],[False],[True]),['visible_unsupported'])
 def test_gs_veto_never_fills_gaps(self):
  X=np.c_[np.zeros(9),np.linspace(0,.2,9),np.full(9,3.)];record=dict(id='a',xyz=X,root_arc=np.arange(9)*4.,nodes=['1','2','3'])
  flags=np.ones((9,3),bool);flags[4]=False
  out=cc.support_spans(record,flags,CFG['fit']);self.assertEqual(len(out),2)
  self.assertTrue(all(len(x['xyz'])==4 for x in out));self.assertFalse(any(np.any(np.all(x['xyz']==X[4],axis=1)) for x in out))
  flags[:3]=False;self.assertEqual(cc.support_spans(record,flags,CFG['fit']),[])
 def test_track_fit_joint_geometry_and_identity(self):
  cams={i:camera([x,0,0]) for i,x in enumerate([-1.5,0,1.5],1)};X=np.c_[np.zeros(11),np.linspace(-.3,.3,11),np.full(11,3.)]
  cs={str(i):curve(i,cc.project_jacobian(X,c['K'],c['w2c'])[0]) for i,c in cams.items()}
  root='1';s=cs[root]['arc'];track=dict(nodes=list(cs),root=root,root_arc=s,maps={k:v['arc'] for k,v in cs.items()},cycle_p90=0.,identity_frozen_before_fit=True)
  accepted,rejected=cc.fit_track(track,cs,cams,[[-2,-2,1],[2,2,5]],.01,CFG['fit'])
  self.assertEqual(len(accepted),1);self.assertLess(np.max(abs(accepted[0]['xyz'][:,2]-3)),1e-4);self.assertEqual(accepted[0]['nodes'],list(cs))
if __name__=='__main__':unittest.main()
