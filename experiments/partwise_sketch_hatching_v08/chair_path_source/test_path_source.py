import runtime
import unittest
import numpy as np
import run_evidence
import source_query
from path_source import stencil,make_csr,select_highlights,query_arrays

class PathSourceTests(unittest.TestCase):
    def test_shared_pixels_and_borders(self):
        xy,offset,sid,beta=stencil(np.array([[1.25,2.5],[1.25,2.5],[3.,3.],[-.1,1.]]),np.array([True,True,True,False]),4,4)
        self.assertEqual(len(xy),5)
        np.testing.assert_array_equal(offset,[0,4,8,9,9])
        np.testing.assert_array_equal(sid[:4],sid[4:8])
        self.assertAlmostEqual(beta[:4].sum(),1)
        self.assertEqual(beta[-1],1)
    def fixture(self):
        xy=np.array([[1,1],[2,1]])
        trace=dict(sample_index=np.array([0,0,1]),source_index=np.array([4,8,4]),
            alpha=np.array([.2,.5,.3]),T=np.array([1.,.8,1.]),weight=np.array([.2,.4,.3]),
            depth=np.array([2.,3.,2.]),center_z=np.array([2.,3.,2.]),culled_local_index=np.array([0,1,0]))
        anchors=[dict(stroke_id=10,key='4:10',fraction=.2),dict(stroke_id=20,key='4:20',fraction=.5)]
        return make_csr(anchors,np.array([0,2,4]),np.array([0,1,0,1]),np.array([.5,.5,.5,.5]),trace,
            np.array(['visible','visible']),np.array([[.35,.35],[0.,0.]]),np.array([True,True]),np.array([2.,2.]),
            np.array([0,0,0,0,1,0,0,0,0,0.]),.06)
    def test_no_borrowing_and_raw_rejected_events(self):
        d=self.fixture()
        np.testing.assert_array_equal(d['offsets'],[0,3,6])
        np.testing.assert_array_equal(d['eligible'],[True,False,True,False,False,False])
        self.assertEqual(len(d['source_index']),6)
        self.assertAlmostEqual(d['weighted_mass'][0],.45)
        self.assertAlmostEqual(d['eligible_mass'][0],.25)
        self.assertEqual(d['eligible_mass'][1],0.)
        np.testing.assert_allclose(d['weight'],d['alpha']*d['T'])
    def test_highlight_unique_ids_and_unknown_query(self):
        d=self.fixture();h=select_highlights(d,[10,20],10)
        np.testing.assert_array_equal(h[10],[4]);self.assertEqual(len(h[20]),0)
        q=query_arrays(d,999,.2);self.assertEqual(q['state'],'not_sampled')
        q=query_arrays(d,10,.2);self.assertEqual(q['accepted_events'],3)
        self.assertEqual(q['eligible_events'],2)
        with self.assertRaises(ValueError):query_arrays(d,10,.7)
        bad={**d,'source_index':d['source_index'].copy()};bad['source_index'][0]=10
        with self.assertRaises(ValueError):select_highlights(bad,[10],10)

if __name__=='__main__':unittest.main()
