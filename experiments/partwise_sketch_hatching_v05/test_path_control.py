"""New path selection and opacity behavior, including back-layer revelation."""
import runtime
import unittest
import numpy as np
from link_renderer import Renderer
from path_control import aggregate_path, resolve_path, opacity_copy, match_nonlinear

class PathControlTests(unittest.TestCase):
    def test_duplicate_pixels_rejection_and_unknown(self):
        # Two anchors share a pixel; exposure must not double. Row 1 is back layer.
        ps=dict(offsets=np.array([0,2,4]),sample_index=np.array([8,8]),
                source_index=np.array([0,1,0,1]),weight=np.array([.7,.2,.7,.2]),
                eligible=np.array([True,False,True,False]))
        total,accepted=aggregate_path(4,ps)
        np.testing.assert_array_equal(total,[.7,.2,0,0])
        np.testing.assert_array_equal(accepted,[.7,0,0,0])
        b=dict(region_id=np.array([4,4,0,2]),unknown=np.array([False,False,True,False]))
        q=resolve_path(np.stack([total,total]),np.stack([accepted,accepted]),b)
        self.assertGreater(q['strength'][0],0)
        np.testing.assert_array_equal(q['strength'][1:],0)
        self.assertTrue(q['unknown'][1:].all())
        self.assertEqual(q['reason'][2],'region_unknown')

    def test_one_view_is_unknown_and_conflicting_region_excluded(self):
        totals=np.array([[.1,.1],[0,.1]])
        b=dict(region_id=np.array([4,2]),unknown=np.array([False,False]))
        q=resolve_path(totals,totals,b)
        self.assertTrue(q['unknown'].all())
        self.assertEqual(q['reason'][0],'path_few_views')
        self.assertEqual(q['reason'][1],'other_region')

    def test_opacity_reveals_back_layer_and_recomputes_T(self):
        r=Renderer(runtime.ACTIVE_UNIT/'build')
        c=dict(extrinsic=np.eye(4).tolist(),width=16,height=16,fx=12.,fy=12.,cx=7.,cy=7.)
        a=dict(means=np.array([[0,0,1.],[0,0,2.]]),covariance=np.tile(np.eye(3)*.01,(2,1,1)),
               opacity=np.array([.9,.8]),colors=np.array([[1.,0,0],[0,0,1.]]))
        f,t=r.render(a,c,[[7,7]])
        e=opacity_copy(a,np.array([1.,0.]),.5)
        g,u=r.render(e,c,[[7,7]])
        np.testing.assert_array_equal(a['opacity'],[.9,.8])
        np.testing.assert_allclose(e['opacity'],[.45,.8])
        np.testing.assert_allclose(t['weight'],[.9,.08])
        np.testing.assert_allclose(u['weight'],[.45,.44])
        self.assertFalse(np.array_equal(f['rgb'],g['rgb']))
        self.assertIs(e['means'],a['means'])
        with self.assertRaises(ValueError):opacity_copy(a,np.array([2.,0.]),.5)

    def test_visible_effect_budget_is_matched_not_count(self):
        calls=[]
        def effect(arm,scale):
            calls.append((arm,scale));return (2 if arm=='a' else 5)*scale**2
        scales,receipt=match_nonlinear(['a','b'],effect)
        budgets=[effect(k,v) for k,v in scales.items()]
        self.assertLess((max(budgets)-min(budgets))/receipt['target'],.02)
        self.assertNotEqual(scales['a'],scales['b'])
        self.assertTrue(receipt['valid'])

if __name__=='__main__':unittest.main()
