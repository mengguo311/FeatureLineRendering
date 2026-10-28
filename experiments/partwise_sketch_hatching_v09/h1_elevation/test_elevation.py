import runtime
import unittest
import numpy as np
from elevation import elevation_plan, validate_cache

class ElevationTests(unittest.TestCase):
    def test_exact_existing_cameras_and_order(self):
        from geometry import orbit_camera
        rows=[dict(key='BUILD',camera=orbit_camera(151,36,5.1,384)),dict(key='000',camera=orbit_camera(196,36,5.1,384))]
        rows += [dict(key=f'{i+24:03d}',camera=orbit_camera(241,24+3*i,5.1,384)) for i in range(13)]
        plan=elevation_plan(rows)
        arc=[r for r in plan if 'index' in r]
        self.assertEqual(len(plan),15);self.assertEqual(len(arc),13)
        self.assertEqual([r['prior_key'] for r in arc],[f'{i:03d}' for i in range(24,37)])
        self.assertEqual(arc[-1]['camera'],rows[-1]['camera'])
        bad=[dict(r) for r in rows];bad[-1]=dict(bad[-1],camera=orbit_camera(241,59,5.1,384))
        with self.assertRaises(ValueError):elevation_plan(bad)

    def test_cache_camera_and_shape_are_not_interchangeable(self):
        c=dict(width=4,height=3,extrinsic=np.eye(4).tolist(),fx=5.,fy=5.,cx=1.5,cy=1.)
        a=dict(source=np.ones((3,4,3)),paper=np.ones((3,4,3)),support=np.zeros((3,4)))
        validate_cache(c,c,a)
        shifted=dict(c,fx=6.)
        with self.assertRaises(ValueError):validate_cache(c,shifted,a)
        with self.assertRaises(ValueError):validate_cache(c,c,dict(a,support=np.zeros((4,3))))
        bad=a['support'].copy();bad[0,0]=np.nan
        with self.assertRaises(ValueError):validate_cache(c,c,dict(a,support=bad))

    def test_old_outputs_and_parent_decision_rejected(self):
        with self.assertRaises(ValueError):runtime.output_guard(runtime.ROOT.parent/'unit_003/renders/new')
        with self.assertRaises(ValueError):runtime.output_guard(runtime.ROOT/'DECISION.json')

if __name__=='__main__':unittest.main()
