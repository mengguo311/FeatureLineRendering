import runtime
import unittest
import numpy as np
from observations import interval_samples,observe,transition
from test_association import fixture,path,AssociationTest
from geometry import orbit_camera
from render import RenderCache,render

class MotionTest(unittest.TestCase):
    def test_exact_interval_weight_and_planned_trim(self):
        m=fixture();p=path(m,0,[[.8,.1,.1],[.2,.7,.1]],sid=7)
        rec={'intervals':[{'parent_segment':0,'removed_t':[[.25,.75]]}]}
        s=interval_samples(p,rec,.07)
        self.assertAlmostEqual(s['weight'].sum(),.6)
        self.assertAlmostEqual(s['weight'][s['planned']].sum(),.3)
        self.assertAlmostEqual(s['weight'][~s['planned']].sum(),.3)
        a={'visible':np.ones(len(s['weight']),bool),'own':np.ones(len(s['weight'])),'increment':np.ones(len(s['weight']))}
        b={**a,'own':np.where(s['planned'],0.,1.)}
        t=transition(s,a,b)
        self.assertEqual(t['own_dropout_count'],0)
        self.assertAlmostEqual(t['joint_retained_visible_length'],.3)
    def test_same_id_ink_and_real_occluder(self):
        m=fixture();p=path(m,0,[[.6,.2,.2],[.2,.6,.2]],sid=7)
        s=interval_samples(p,{},.04);c=orbit_camera(180,89,3,64,target=(.5,.5,0))
        style={'5':{'angle':0.,'spacing':.1,'length':.4,'width':1.,'ink_strength':.45}}
        rc=RenderCache(track_ids=('5:7','5:99'));render(m,{5:p},style,c,2,{},rc)
        obs=observe(m,s,c,rc.value['tracked'],np.ones((64,64)),.45)
        self.assertTrue(obs['visible'].all());self.assertTrue((obs['own']>0).any())
        wrong={**s,'parent':np.full(len(s['weight']),99,np.int64)}
        o=observe(m,wrong,c,rc.value['tracked'],np.ones((64,64)),.45)
        self.assertEqual(o['own'].sum(),0)
        front=fixture(True);front['vertices'][4:,2]=.2
        from geometry import mesh_data
        front=mesh_data(front['vertices'],front['faces'],front['regions'])
        hidden=observe(front,s,c,rc.value['tracked'],np.ones((64,64)),.45)
        self.assertFalse(hidden['visible'].any())
        self.assertEqual(transition(s,obs,hidden)['own_dropout_count'],0)
    def test_dropout_vs_composite_cancellation(self):
        s={'weight':np.array([.1,.2,.3]),'planned':np.array([False,False,True])}
        a={'visible':np.ones(3,bool),'own':np.ones(3),'increment':np.ones(3)}
        b={'visible':np.ones(3,bool),'own':np.array([0.,1.,0.]),'increment':np.zeros(3)}
        q=transition(s,a,b)
        self.assertEqual(q['own_dropout_count'],1)
        self.assertAlmostEqual(q['own_dropout_length'],.1)
        self.assertEqual(q['composite_cancellation_count'],1)
        self.assertAlmostEqual(q['composite_cancellation_length'],.2)

if __name__=='__main__':unittest.main()
