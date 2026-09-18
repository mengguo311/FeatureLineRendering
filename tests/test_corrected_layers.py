import unittest
import numpy as np

class AreaLayersTests(unittest.TestCase):
    def test_area_mixture_keeps_disjoint_depths_and_averages_transmittance(self):
        from src.corrected_layers import AreaLayers
        # Four native pixels: opacity .9 at z2; .5 at z4; none; .6 at z6.
        d=np.array([2,4,6],dtype='f4');weights=np.array([.9,.5,.6],dtype='f4')
        offsets=np.array([0,1,2,2,3],dtype='i8')
        layer=AreaLayers.from_native_arrays(offsets,d,weights,2,2)
        e=layer.events(0,0)
        np.testing.assert_allclose(e['depth'],[2,4,6])
        np.testing.assert_allclose(e['weight'],[.225,.125,.15])
        front,support=layer.query(np.zeros((5,2)),np.array([1,2,3,4,7]),.02)
        np.testing.assert_allclose(front,[1,1,.775,.775,.5],atol=1e-7)
        np.testing.assert_array_equal(support,[False,True,False,True,False])
        np.testing.assert_allclose(layer.quantiles()[0,0],[2,4,6])
        self.assertEqual(layer.height,1);self.assertEqual(layer.width,1)

    def test_native800_area_layers_calibrate_alpha_and_serialization(self):
        from src.corrected_layers import AreaLayers
        from src.corrected_sampling import area_downsample
        from src.foundation import native_render
        from test_multiscene import asset_fixture
        import tempfile
        from pathlib import Path
        a=asset_fixture();K=np.array([[800.,0,399.5],[0,900.,399.5],[0,0,1]])
        state=native_render(a,K,np.eye(4),800,800,1)
        layer=AreaLayers(state,800,800)
        alpha=layer.alpha()
        np.testing.assert_allclose(alpha,area_downsample(1-state['final_T']),atol=1e-6)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'layers.npz';layer.save(p);again=AreaLayers.load(p)
            np.testing.assert_array_equal(again.quantiles(),layer.quantiles())
            np.testing.assert_array_equal(again.depth,layer.depth)

class QueryOptimizationTests(unittest.TestCase):
    def test_small_query_optimization_matches_original_bit_for_bit(self):
        from src.corrected_layers import AreaLayers,bind_fast_query
        from src.foundation import native_render
        from test_multiscene import asset_fixture
        a=asset_fixture();K=np.array([[80.,0,31.5],[0,60.,31.5],[0,0,1]])
        layer=AreaLayers(native_render(a,K,np.eye(4),64,64,1),64,64)
        rng=np.random.default_rng(42);uv=rng.uniform(-2,34,(2300,2));z=rng.uniform(1,6,2300)
        old=layer.query(uv,z,.02);bind_fast_query(layer)
        new=layer.query(uv,z,.02)
        np.testing.assert_array_equal(old[0],new[0]);np.testing.assert_array_equal(old[1],new[1])
        for i in [0,123,500]:
            one=layer.query(uv[i:i+1],z[i:i+1],.02)
            np.testing.assert_array_equal(one[0],old[0][i:i+1]);np.testing.assert_array_equal(one[1],old[1][i:i+1])
