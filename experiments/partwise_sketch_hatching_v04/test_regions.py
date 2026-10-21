import runtime
import unittest
import tempfile
from pathlib import Path
import numpy as np
from runtime import OUTPUT_ROOT, sha
from demo import load_asset, edit

SOURCE=OUTPUT_ROOT/'units/unit_003/assets/baseline'
BOUNDS=[-.70,-1.20,.45,.70,-.35,1.10]

class RealModelRegions(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.mesh,cls.strokes,cls.meta=load_asset(SOURCE)

    def test_selection_is_explicit_and_invalid_requests_rejected(self):
        from region_tools import select_faces
        ids=select_faces(self.mesh,BOUNDS,3)
        self.assertGreater(len(ids),100)
        self.assertTrue((self.mesh['regions'][ids]==3).all())
        for bad in ([0,0,0,-1,1,1],[0,0,0,1,1,float('nan')],[9,9,9,10,10,10]):
            with self.assertRaises(ValueError): select_faces(self.mesh,bad,3)
        with self.assertRaises(ValueError): select_faces(self.mesh,BOUNDS,30)
        with self.assertRaises(ValueError): select_faces(self.mesh,[-2,-2,-2,2,2,2],3)

    def test_split_and_local_edit_cold_load(self):
        from region_tools import select_faces, author_region
        with tempfile.TemporaryDirectory(dir=OUTPUT_ROOT/'orchestration/scratch',prefix='region_test_') as tmp:
            # output guard deliberately excludes orchestration: generated assets go in current unit.
            destination=OUTPUT_ROOT/'units/unit_004/test_work'/Path(tmp).name
            a=destination/'authored';b=destination/'edited'
            author_region(SOURCE,a,BOUNDS,3,'Front bucket area')
            mesh,strokes,meta=load_asset(a)
            np.testing.assert_array_equal(mesh['vertices'],self.mesh['vertices'])
            np.testing.assert_array_equal(mesh['faces'],self.mesh['faces'])
            selected=select_faces(self.mesh,BOUNDS,3)
            np.testing.assert_array_equal(np.flatnonzero(mesh['regions']==4),selected)
            for r in (1,2): self.assertEqual(sha(a/f'region_{r}.npz'),sha(SOURCE/f'region_{r}.npz'))
            keep=~np.isin(self.strokes[3]['face'],selected)
            for k in self.strokes[3]:np.testing.assert_array_equal(strokes[3][k],self.strokes[3][k][keep])
            self.assertEqual(meta['styles']['4']['plane'],'xz')
            edit(a,b,4,dict(angle=35.))
            load_asset(b)
            for r in (1,2,3):self.assertEqual(sha(a/f'region_{r}.npz'),sha(b/f'region_{r}.npz'))
            self.assertNotEqual(sha(a/'region_4.npz'),sha(b/'region_4.npz'))
            (b/'selection_4.npz').write_bytes(b'corrupt selection')
            with self.assertRaisesRegex(ValueError,'selection checksum'):load_asset(b)

    def test_fourth_region_is_a_saved_mesh_label(self):
        from geometry import mesh_data
        labels=self.mesh['regions'].copy();labels[:10]=4
        m=mesh_data(self.mesh['vertices'],self.mesh['faces'],labels)
        np.testing.assert_array_equal(m['regions'][:10],np.full(10,4))

if __name__=='__main__':unittest.main(verbosity=2)
