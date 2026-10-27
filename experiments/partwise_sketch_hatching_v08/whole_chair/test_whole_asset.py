import runtime
import unittest,tempfile,json
from pathlib import Path
import numpy as np
from whole_asset import save_preset,load_preset,compose_whole,edit_whole,PRESET
from linked_asset import load_asset

UNIT=runtime.ROOT/'units/unit_002'
class WholeTests(unittest.TestCase):
    def test_saved_preset_and_noop_edit_preserve_payload(self):
        root=UNIT/'tests';root.mkdir(exist_ok=True)
        folder=Path(tempfile.mkdtemp(dir=root));source=UNIT/'delivery/assets/baseline'
        dst=folder/'preset';save_preset(source,dst)
        self.assertEqual(load_preset(dst),PRESET)
        for name in ('mesh.npz','SOURCE_LINK.npz',*[f'region_{r}.npz' for r in (1,2,3,4,5)]):
            self.assertEqual(runtime.sha(source/name),runtime.sha(dst/name))
        edit_whole(dst,folder/'noop',dict(spacing=.045))
        self.assertEqual(load_preset(folder/'noop'),PRESET)
        for r in (1,2,3,4,5):self.assertEqual(runtime.sha(dst/f'region_{r}.npz'),runtime.sha(folder/'noop'/f'region_{r}.npz'))
        with self.assertRaises(ValueError):save_preset(source,folder/'bad',dict(PRESET,paper_color=[1,0,0]))

    def test_seat_gate_not_applied_to_other_parts_or_contour(self):
        layers={1:np.array([[.8,0],[0,0]],np.float32),4:np.array([[0,.6],[.6,0]],np.float32)}
        contour=np.array([[0,0],[0,.85]],np.float32)
        paper=np.full((2,2,3),.95,np.float32)
        out=compose_whole(paper,layers,contour,np.zeros((2,2)),1)
        np.testing.assert_allclose(out['combined_ink'],[[.8,0],[0,.85]])
        self.assertEqual(out['seat_linked_ink'].sum(),0)
        one=compose_whole(paper,layers,contour,np.ones((2,2)),1)
        np.testing.assert_array_equal(one['combined_ink'],one['ungated_ink'])
        self.assertTrue((one['hybrid'][0,1]<out['hybrid'][0,1]).all())
        # Disjoint subpixel strokes must union BEFORE antialias reduction.
        disjoint={1:np.array([[1,0],[0,0]],np.float32),4:np.array([[0,1],[0,0]],np.float32)}
        aa=compose_whole(np.ones((1,1,3)),disjoint,np.zeros((2,2)),np.ones((1,1)),2)
        self.assertEqual(float(aa['combined_ink'][0,0]),.5)
        with self.assertRaises(ValueError):compose_whole(paper,layers,contour,np.full((2,2),2.),1)

if __name__=='__main__':unittest.main()
