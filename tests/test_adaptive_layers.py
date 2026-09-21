import unittest
import numpy as np


class LayerTests(unittest.TestCase):
    def test_relative_gap_layers_conserve_provenance_and_overflow(self):
        from src.adaptive_layers import compress_layers
        e=dict(offsets=np.array([0,6,6]),ids=np.arange(6),z=np.array([2,2.001,2.1,2.2,2.3,2.4]),
               w=np.array([.2,.2,.2,.1,.1,.01]),rgb=np.ones((6,3)),tail_alpha=np.array([[.1,0]]),tail_rgb=np.ones((1,2,3))*.1)
        result=compress_layers(e,np.array([[.91,0]]))
        np.testing.assert_array_equal(result['assignment'],[0,0,1,2,3,4])
        np.testing.assert_array_equal(result['layer_offsets'],[0,5,5])
        np.testing.assert_allclose(result['layer_mass'],[.4,.2,.1,.1,.01])
        np.testing.assert_allclose(result['overflow_mass'],[[.01,0]])
        np.testing.assert_allclose(result['retained_mass'].sum(-1)+result['overflow_mass'],[[.81,0]])
        self.assertFalse(result['layer_seedable'][-1])
        scaled=compress_layers(dict(e,z=e['z']*10),np.array([[.91,0]]))
        np.testing.assert_array_equal(scaled['assignment'],result['assignment'])
        np.testing.assert_allclose(scaled['local_scale'],result['local_scale']*10,atol=1e-10)
        np.testing.assert_allclose(result['histogram_p'],[.5,.5,1,1,1,1])
