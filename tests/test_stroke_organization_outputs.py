import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from stroke_organization_outputs import densify_fixed,metrics
from src.stroke_relations import draw_paths

class OutputTest(unittest.TestCase):
    def test_sampling_independent_of_other_paths(self):
        p=np.array([[0.,0,0],[1.,0,0],[1.,1,0]])
        a=densify_fixed([p],.1)[0]
        b=densify_fixed([p,np.array([[0.,0,0],[100.,0,0]])],.1)[0]
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(a[0],p[0]);np.testing.assert_array_equal(a[-1],p[-1])

    def test_visibility_fragments_not_concatenated_for_gate(self):
        pp=[[np.array([[0.,1.],[8.,1.]]),np.array([[20.,1.],[28.,1.]])]]
        im=draw_paths(pp,np.ones(1,bool),(32,32));m=metrics(pp,np.ones(1,bool),im)
        self.assertEqual(m['median_visible_fragment_px'],8.)
        self.assertEqual(m['median_visible_path_px'],16.)
        self.assertEqual(m['short_fragment_fraction_lt12px'],1.)

if __name__=='__main__':unittest.main()
