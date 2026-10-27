import runtime
import unittest,tempfile,json
from pathlib import Path
import numpy as np
from style_asset import create_style
from whole_asset import compose_whole,load_preset,STYLE_PRESET
from linked_asset import load_asset,npz
from parts_asset import part_edit
UNIT=runtime.ROOT/'units/unit_006'
class StyleTests(unittest.TestCase):
    def test_active_region_mask_keeps_contour_and_seat_source_gate(self):
        paper=np.ones((1,2,3))*.95;contour=np.array([[.2,.1]],np.float32)
        layers={1:np.array([[1.,1.]],np.float32),4:np.array([[.8,.8]],np.float32),5:np.array([[.3,0]],np.float32)}
        out=compose_whole(paper,layers,contour,np.array([[0.,.5]]),1,active_regions=[4,5])
        np.testing.assert_allclose(out['combined_ink'],[[.3,.4]],atol=1e-7)
        np.testing.assert_array_equal(out['layer_1'],0)
        np.testing.assert_array_equal(out['contour'],contour)
        np.testing.assert_allclose(out['ungated_ink'],[[.8,.8]],atol=1e-7)
    def test_saved_style_and_retained_editor_on_real_asset(self):
        root=UNIT/'tests';root.mkdir(exist_ok=True);tmp=Path(tempfile.mkdtemp(dir=root))
        src=UNIT/'delivery/assets/reference';out=tmp/'style';create_style(src,out)
        mesh,paths,meta,_,_=load_asset(out);old=load_asset(src)[1]
        self.assertEqual(load_preset(out),STYLE_PRESET)
        for r in (1,2,3):self.assertEqual(runtime.sha(src/f'region_{r}.npz'),runtime.sha(out/f'region_{r}.npz'))
        for r in (4,5):
            self.assertEqual(meta['styles'][str(r)]['length'],.44)
            self.assertEqual(meta['styles'][str(r)]['spacing'],.0675)
            self.assertFalse(np.intersect1d(paths[r]['stroke_id'],np.concatenate([x['stroke_id'] for x in old.values()])).size)
            np.testing.assert_array_equal(paths[r]['visibility_mask'],1<<r)
            np.testing.assert_allclose(paths[r]['points'],np.einsum('nij,njk->nik',paths[r]['bary'],mesh['tri'][paths[r]['face']]),atol=1e-10)
        part_edit(out,tmp/'edited',5,dict(length=.5))
        self.assertEqual(load_preset(tmp/'edited'),STYLE_PRESET)
        for r in (1,2,3,4):self.assertEqual(runtime.sha(out/f'region_{r}.npz'),runtime.sha(tmp/'edited'/f'region_{r}.npz'))
        self.assertEqual(runtime.sha(src/'SOURCE_LINK.npz'),runtime.sha(out/'SOURCE_LINK.npz'))
        self.assertEqual(runtime.sha(src/'mesh.npz'),runtime.sha(out/'mesh.npz'))
        part_edit(out,tmp/'noop',4,dict(length=.44))
        for r in range(1,6):self.assertEqual(runtime.sha(out/f'region_{r}.npz'),runtime.sha(tmp/'noop'/f'region_{r}.npz'))
    def test_invalid_preset_not_silently_accepted(self):
        from whole_asset import validate_preset
        with self.assertRaises(ValueError):validate_preset({**STYLE_PRESET,'active_regions':[5]})
if __name__=='__main__':unittest.main()
