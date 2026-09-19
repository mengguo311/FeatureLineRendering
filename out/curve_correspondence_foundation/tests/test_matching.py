import unittest,json,pathlib
import numpy as np
import cc
CFG=json.loads((pathlib.Path(__file__).parents[1]/'config.json').read_text())
def camera(center,K=None):
 w=np.eye(4);w[:3,3]=-np.array(center)
 return dict(K=np.array(K if K is not None else [[220,7,91],[0,270,103],[0,0,1.]]),w2c=w)
def curve(view,points,id=None):
 p=np.asarray(points,float);s=cc.arclength(p)
 return dict(id=id or str(view),view=view,points=p,pixels=p,arc=s,length=s[-1],tangent=cc.tangents(p),descriptor=np.tile(np.array([[[.2,.3,.4],[.6,.4,.2]]]),(len(p),1,1)))
def edge(a,b,offset=0,reverse=False):
 s=np.linspace(0,20,11);t=20-s if reverse else s+offset
 return dict(a=str(a),b=str(b),sa=s,tb=t,reverse=reverse,score=.01,reasons=[],selected=True,margin_a=.1,margin_b=.1,ratio_a=.1,ratio_b=.1)
class Matching(unittest.TestCase):
 def test_full_K_epipolar_geometry(self):
  ca=camera([0,0,0]);cb=camera([.8,.2,0],[[260,-9,121],[0,180,80],[0,0,1.]])
  X=np.array([[.1,.2,3.],[-.5,.4,4.],[.3,-.2,2.]])
  a=cc.project_jacobian(X,ca['K'],ca['w2c'])[0];b=cc.project_jacobian(X,cb['K'],cb['w2c'])[0]
  F=cc.fundamental(ca,cb)
  residual=np.einsum('ni,ij,nj->n',np.c_[b,np.ones(3)],F,np.c_[a,np.ones(3)])
  np.testing.assert_allclose(residual,0,atol=1e-10)
 def test_epipolar_intersections_tangency_multiple_and_reversal(self):
  lines=np.array([[0,1,-5],[0,1,-8.]])
  c=curve(2,[[6,0],[6,10]])
  s,why=cc.intersections(lines,c,CFG['matching']);np.testing.assert_allclose(s,[5,8])
  r=curve(2,c['points'][::-1]);s,_=cc.intersections(lines,r,CFG['matching']);np.testing.assert_allclose(s,[5,2])
  s,why=cc.intersections(lines,curve(2,[[1,0],[1,10],[9,10],[9,0]]),CFG['matching']);self.assertTrue(np.isnan(s).all());self.assertEqual(why['multiple'],2)
  s,why=cc.intersections(np.array([[0,1,-5.]]),curve(2,[[0,5],[10,5]]),CFG['matching']);self.assertTrue(np.isnan(s).all())
 def test_monotone_run_rejects_crossing_many_to_one_accepts_reverse(self):
  s=np.arange(0,22,2.)
  r=cc.align_arcs(s,20-s,20,20,CFG['matching']);self.assertTrue(r['passed']);self.assertTrue(r['reverse'])
  for b in [np.zeros(11),np.array([0,2,4,6,8,6,4,2,0,2,4.])]:
   self.assertFalse(cc.align_arcs(s,b,20,20,CFG['matching'])['passed'])
  r=cc.align_arcs(s,np.array([0,2,4,6,8,6,12,14,16,18,20.]),20,20,CFG['matching'],False);self.assertTrue(r['passed'])
 def test_pair_candidate_recovers_true_curve_full_K(self):
  a=camera([0,0,0]);b=camera([.7,0,0]);X=np.c_[np.linspace(-.2,.1,21),np.linspace(-.3,.3,21),np.full(21,3.)]
  ca=curve(1,cc.project_jacobian(X,a['K'],a['w2c'])[0]);cb=curve(2,cc.project_jacobian(X,b['K'],b['w2c'])[0])
  r=cc.pair_candidate(ca,cb,a,b,CFG['matching']);self.assertFalse(r['reasons']);self.assertLess(r['score'],.01)
 def test_mutual_ambiguity_rejects_ties_and_many_to_one(self):
  rows=[dict(a='a',b='b',score=.1,reasons=[]),dict(a='a',b='c',score=.11,reasons=[])]
  out=cc.select_mutual([dict(r,views=[1,2]) for r in rows],CFG['matching']);self.assertFalse(any(r['selected'] for r in out))
  rows=[dict(a='a',b='b',score=.05,reasons=[]),dict(a='a',b='c',score=.2,reasons=[]),dict(a='z',b='b',score=.2,reasons=[])]
  out=cc.select_mutual([dict(r,views=[1,2]) for r in rows],CFG['matching']);self.assertEqual(sum(r['selected'] for r in out),1)
 def test_triangle_cycle_parity_and_arc_closure(self):
  e=[edge(1,2),edge(2,3),edge(1,3)]
  self.assertTrue(cc.cycle_certificate(e,CFG['matching'])['passed'])
  e[2]=edge(1,3,reverse=True);self.assertFalse(cc.cycle_certificate(e,CFG['matching'])['passed'])
  e[2]=edge(1,3,offset=5);self.assertFalse(cc.cycle_certificate(e,CFG['matching'])['passed'])
 def test_track_identity_before_geometry_no_two_view_truth(self):
  curves={str(i):curve(i,np.c_[np.full(11,i*2),np.arange(0,22,2.)]) for i in [1,2,3]}
  tracks,rejected=cc.build_tracks(curves,[edge(1,2),edge(2,3),edge(1,3)],CFG['matching'])
  self.assertEqual(len(tracks),1);self.assertEqual(len(tracks[0]['nodes']),3);self.assertNotIn('xyz',tracks[0])
  tracks,_=cc.build_tracks(curves,[edge(1,2),edge(2,3)],CFG['matching']);self.assertEqual(tracks,[])
if __name__=='__main__':unittest.main()
