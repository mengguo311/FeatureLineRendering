"""Independent tiny fixtures for stage attribution; no lamp outcomes."""
import temporal_audit as ta
import argparse
import unittest
import numpy as np

PARSER = argparse.ArgumentParser()
PARSER.add_argument('--backend', choices=['broken', 'new'], default='new')
ARGS = PARSER.parse_args()
if ARGS.backend == 'new':
    import stage_attribution as sa


def classify(flags):
    if ARGS.backend == 'broken':
        return 'supported'  # Deliberately ignores actual observed support loss.
    return sa.classify_stages(flags)


class StageTests(unittest.TestCase):
    def test_z_rejection(self):
        flags = [True, True, True, False, False, False, False, False]
        self.assertEqual(classify(flags), 'mesh_z_test_local_rejection')

    def test_AA_loss(self):
        self.assertEqual(classify([True]*5+[False]*3), 'quantization_or_LANCZOS_support_loss')

    def test_identity_loss(self):
        self.assertEqual(classify([True]*7+[False]), 'identity_filter_loss')

    def test_recovery_then_loss_is_mixed(self):
        self.assertEqual(classify([True, True, True, False, True, True, True, False]), 'unknown_or_mixed')

    @unittest.skipIf(ARGS.backend == 'broken', 'New trace implementation only')
    def test_known_front_back_geometry(self):
        # Camera looking along +z, screen origin at center, front z=2/rear z=3.
        c = {'R': np.eye(3), 't': np.zeros(3), 'eye': np.zeros(3),
             'focal': 16., 'center': np.array([16.,16.]), 'size': 32}
        v = np.array([[-1,-1,2],[1,-1,2],[1,1,2],[-1,1,2],
                      [-1,-1,3],[1,-1,3],[1,1,3],[-1,1,3]],float)
        mesh = ta.core.finalize_mesh(v, [[0,1,2],[0,2,3],[4,5,6],[4,6,7]], [1,1,2,2])
        depth, parts = ta.core.raster_surface(mesh,c)
        x = np.array([[.2,.1,2],[.2,.1,3]])
        trace = sa.trace_points(x,c,depth,parts,.006,mesh,None)
        np.testing.assert_array_equal(trace['accepted'], [True,False])
        np.testing.assert_allclose(trace['exact_mesh_depth'], 2, atol=1e-12)
        np.testing.assert_array_equal(trace['exact_mesh_part'], [1,1])
        self.assertGreater(trace['z'][1]-trace['exact_mesh_depth'][1], .9)

    @unittest.skipIf(ARGS.backend == 'broken', 'New trace implementation only')
    def test_overlap_and_final_influence(self):
        parts=np.ones((32,32),np.int32)
        a=np.zeros((32,32)); a[16,16]=.6
        stages=sa.layer_stages(a,parts,2,2)
        layer=stages['downsample']; yy,xx=np.nonzero(layer/255>.04)
        self.assertGreater(len(xx),0)
        count=2*(layer>0).astype(np.uint16)
        support=(layer/255>.04)&(count==1)
        self.assertFalse(support.any())
        same=sa.layer_stages(np.maximum(a,a),parts,2,2)['downsample']
        np.testing.assert_array_equal(same,layer)
        weaker=sa.layer_stages(a*.5,parts,2,2)['downsample']
        self.assertGreater(np.max(abs(layer.astype(int)-weaker.astype(int))),0)

    @unittest.skipIf(ARGS.backend == 'broken', 'New trace implementation only')
    def test_quantization_and_crop_equality(self):
        parts=np.ones((64,64),np.int32); raw=np.zeros((64,64));raw[31,32]=.001
        out=sa.layer_stages(raw,parts,2,2)
        self.assertTrue(out['clipped'].any()); self.assertFalse(out['quantized'].any())
        raw[31,32]=.6; out=sa.layer_stages(raw,parts,2,2)
        x0,y0,small,_=ta.layer_crop(np.array([[32,31]]),.6,parts,2,2)
        full=np.zeros((32,32),np.uint8);full[y0:y0+len(small),x0:x0+small.shape[1]]=small
        np.testing.assert_array_equal(full,out['downsample'])


if __name__ == '__main__':
    unittest.main(argv=['test_stage_attribution'],verbosity=2)
