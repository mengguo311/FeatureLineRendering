import unittest,numpy as np
from provenance import primitive_arc
from test_geometry import segment
from primitive import curve_eval
class Provenance(unittest.TestCase):
    def test_partial_chain_arc_is_not_merged_primitive_arc(self):
        g=segment();g['control'][:,0]=np.linspace(-.08,.12,4)
        p=np.array([[-.08,0,2],[0,0,2],[.08,0,2]])
        np.testing.assert_allclose(primitive_arc(p,g),[0,.4,.8],atol=1e-12)
    def test_bezier_known_parameter_roundtrip(self):
        g=segment(curve=True);t=np.linspace(.03,.97,19);p=curve_eval(g['control'],g['type'],t)
        np.testing.assert_allclose(primitive_arc(p,g),t,atol=1e-7)
if __name__=='__main__':unittest.main(verbosity=2)
