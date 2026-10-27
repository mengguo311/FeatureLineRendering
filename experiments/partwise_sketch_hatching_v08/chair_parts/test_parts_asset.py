import runtime
import unittest,tempfile
from pathlib import Path
import numpy as np
from geometry import mesh_data
from linked_asset import npz,load_asset
from parts_asset import part_edit,regenerate_paths,source_strength,save_control,load_control

UNIT=runtime.ROOT/'units/unit_005'
class PartsTests(unittest.TestCase):
    def folder(self):
        root=UNIT/'tests';root.mkdir(exist_ok=True)
        return Path(tempfile.mkdtemp(dir=root))
    def test_owner_identity_and_face_anchors_on_disconnected_parts(self):
        v=np.array([[0,0,0],[1,0,0],[1,0,1],[0,0,1],[3,0,0],[4,0,0],[4,0,1],[3,0,1]],float)
        mesh=mesh_data(v,np.array([[0,1,2],[0,2,3],[4,5,6],[4,6,7]]),np.array([5,5,4,4]))
        style=dict(angle=25.,spacing=.2,length=.4,width=1.,plane='xz',ink_strength=.45)
        data,_=regenerate_paths(mesh,5,style,'synthetic-parent',np.array([5_000_000_001]))
        self.assertGreater(len(data['face']),0)
        self.assertTrue(np.isin(data['face'],[0,1]).all())
        np.testing.assert_array_equal(data['visibility_mask'],32)
        np.testing.assert_allclose(data['points'],np.einsum('nij,njk->nik',data['bary'],mesh['tri'][data['face']]),atol=1e-12)
        self.assertFalse(np.isin(data['stroke_id'],[5_000_000_001]).any())
        repeat,_=regenerate_paths(mesh,5,style,'synthetic-parent',np.array([5_000_000_001]))
        for key in data:np.testing.assert_array_equal(data[key],repeat[key])
    def test_noop_save_reload_and_region_rejection(self):
        root=self.folder();src=UNIT/'delivery/assets/history';out=root/'noop'
        part_edit(src,out,5,dict(angle=-25.))
        _,_,meta,_,_=load_asset(out)
        self.assertFalse(meta['edit']['regenerated'])
        for r in range(1,6):self.assertEqual(runtime.sha(src/f'region_{r}.npz'),runtime.sha(out/f'region_{r}.npz'))
        with self.assertRaises(ValueError):part_edit(src,root/'bad',3,dict(angle=25.))
        with self.assertRaises(ValueError):part_edit(src,root/'bad2',5,dict(spacing=float('nan')))
    def test_frozen_original_row_weights_and_control_reload(self):
        b=dict(source_index=np.arange(4),membership=np.array([[.2,0,0,0,0,.8],[.1,0,0,0,0,.9],[.1,0,0,0,.9,0],[1,0,0,0,0,0]]),region_id=np.array([5,5,4,0]),unknown=np.array([False,True,False,True]))
        np.testing.assert_array_equal(source_strength(b,5,.5),[.4,0,0,0])
        with self.assertRaises(ValueError):source_strength(b,5,1.1)
        root=self.folder();asset=UNIT/'delivery/assets/history'
        save_control(asset,root/'control',5,.5,[.02,.4,1.])
        d,m=load_control(asset,root/'control')
        self.assertEqual(int((d['strength']>0).sum()),11576)
        self.assertEqual(m['region'],5)
        np.testing.assert_array_equal(d['source_index'],np.arange(256690))
        (root/'control/WEIGHTS.npz').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):load_control(asset,root/'control')
if __name__=='__main__':unittest.main()
