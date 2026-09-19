import unittest
import numpy as np
import cc
from test_matching import CFG,camera,curve,edge
class Evaluation(unittest.TestCase):
 def test_repeatability_without_ids_or_alignment_rejects_shift_and_empty(self):
  x=np.c_[np.linspace(0,.5,31),np.zeros(31),np.full(31,3.)]
  a=[dict(id='wrong_id',xyz=x)];b=[dict(id='unrelated',xyz=x[::-1]+[0,.001,0])]
  r=cc.match_geometry(a,b,.01,CFG['gates']);self.assertTrue(r['passed']);self.assertGreater(r['forward'],.95)
  b[0]['xyz']+=np.array([0,.1,0]);self.assertFalse(cc.match_geometry(a,b,.01,CFG['gates'])['passed'])
  self.assertFalse(cc.match_geometry([],[],.01,CFG['gates'])['passed'])
 def test_competing_parallel_tubes_are_ambiguous(self):
  x=np.c_[np.linspace(0,.5,31),np.zeros(31),np.full(31,3.)]
  a=[dict(xyz=x)];b=[dict(xyz=x+[0,.003,0]),dict(xyz=x-[0,.003,0])]
  r=cc.match_geometry(a,b,.01,CFG['gates']);self.assertEqual(r['forward'],0)
 def test_controls_preserve_counts_and_no_identity_reuse(self):
  cs={str(i):curve(i,np.c_[np.full(11,20+i),np.arange(0,22,2.)]) for i in [1,2,3]}
  out=cc.shift_curves(cs,[1,2,3],CFG['controls']);self.assertEqual(len(cs),len(out));self.assertTrue(all(np.array_equal(cs[k]['descriptor'],out[k]['descriptor']) for k in cs))
  self.assertTrue(all(np.array_equal(np.diff(cs[k]['points'],axis=0),np.diff(out[k]['points'],axis=0)) for k in cs))
  es=[edge(1,2),edge(1,3),edge(2,3)];r=cc.random_graph(es,cs,CFG['controls']['random_seed']);self.assertEqual(len(r),len(es))
  self.assertEqual(len(cc.pair_tracks(es)),3);self.assertEqual(len(cc.pair_tracks(es)[0]['nodes']),2)
 def test_prediction_counts_empty_and_true_frozen_curve(self):
  from src.multiscene_probe import edge_field
  cams={1:camera([0,0,0],[[100,0,50],[0,100,50],[0,0,1.]])}
  rgb=np.ones((100,100,3));rgb[:,50:]=0;fields={1:edge_field(rgb,CFG)}
  x=np.c_[np.full(20,-.01),np.linspace(-.25,.25,20),np.ones(20)]
  r=cc.predict([dict(id='x',xyz=x)],cams,fields,.01,CFG['gates']);self.assertGreater(r['joint_fraction'],.95);self.assertLess(r['distance_median'],1)
  self.assertEqual(r['track_count'],1);self.assertEqual(r['per_view']['1']['out_of_frame'],0)
  r=cc.predict([],cams,fields,.01,CFG['gates']);self.assertFalse(r['passed']);self.assertEqual(r['track_count'],0)
 def test_gates_zero_denominator_no_null_success_and_gs_benefit(self):
  empty=cc.predict([],{}, {},.01,CFG['gates']);self.assertFalse(cc.null_gate(empty,{'shifted':empty,'random_graph':empty,'pairwise':empty,'no_order':empty},CFG['gates']))
  self.assertFalse(cc.gs_benefit(empty,empty,CFG['gates'])['passed'])
  image=dict(supported_length=100.,unsupported_length=40.,joint_fraction=.7)
  gs=dict(supported_length=95.,unsupported_length=20.,joint_fraction=.83)
  self.assertTrue(cc.gs_benefit(image,gs,CFG['gates'])['passed'])
  self.assertEqual(cc.decision(True,True,False,False),'PIVOT_IMAGE_ONLY')
  self.assertEqual(cc.decision(True,False,False,False),'STOP_CORRESPONDENCE')
  self.assertEqual(cc.decision(False,False,False,False),'ENGINEERING_NOT_READY')
  self.assertEqual(cc.decision(True,True,True,True),'CURVE_CORRESPONDENCE_GO_MANUAL_PENDING')
 def test_yield_counts_tracks_not_knots_and_spatial_diversity(self):
  cams={i:camera([x,0,0]) for i,x in enumerate([-1.5,0,1.5],1)}
  x=np.c_[np.linspace(0,.5,101),np.zeros(101),np.full(101,3.)]
  records=[dict(xyz=x,id=str(i),views=[1,2,3],fit_rms=0.,fit_tangent_median=0.) for i in range(30)]
  r=cc.yield_metrics(records,cams,.01,CFG['gates']);self.assertEqual(r['separated_tracks'],1);self.assertFalse(r['passed'])
if __name__=='__main__':unittest.main()
