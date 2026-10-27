import runtime
import unittest
import tempfile
from pathlib import Path
import json
import numpy as np
from linked_asset import initialize,load_asset,edit_asset

UNIT=runtime.ROOT/'units/unit_001'

class LinkedAssetTests(unittest.TestCase):
    def setUp(self):
        (UNIT/'tests').mkdir(exist_ok=True)
        self.folder=Path(tempfile.mkdtemp(dir=UNIT/'tests'))
        self.base=self.folder/'base'
        initialize(UNIT/'inputs/historical_asset',UNIT/'delivery/data/chair',self.base)

    def test_roundtrip_non_target_and_new_identity(self):
        out=self.folder/'spacing'
        edit_asset(self.base,out,dict(spacing=.0675))
        m,s,meta,link,b=load_asset(out)
        _,old,_,_,_=load_asset(self.base)
        self.assertEqual(meta['styles']['4']['spacing'],.0675)
        for r in (1,2,3,5):
            self.assertEqual(runtime.sha(self.base/f'region_{r}.npz'),runtime.sha(out/f'region_{r}.npz'))
        self.assertFalse(np.intersect1d(old[4]['stroke_id'],s[4]['stroke_id']).size)
        np.testing.assert_array_equal(s[4]['visibility_mask'],16)
        np.testing.assert_allclose(s[4]['points'],np.einsum('nij,njk->nik',s[4]['bary'],m['tri'][s[4]['face']]),atol=1e-9,rtol=0)
        self.assertEqual(link['paper_effect'],1.)
        again=self.folder/'again'
        edit_asset(out,again,dict(angle=125.,length=.3))
        _,ss,_,_,_=load_asset(again)
        self.assertFalse(np.intersect1d(s[4]['stroke_id'],ss[4]['stroke_id']).size)

    def test_paper_edit_keeps_all_paths_and_binding(self):
        out=self.folder/'paper'
        edit_asset(self.base,out,{},paper_effect=.5)
        _,_,_,link,_=load_asset(out)
        self.assertEqual(link['paper_effect'],.5)
        for r in (1,2,3,4,5):
            self.assertEqual(runtime.sha(self.base/f'region_{r}.npz'),runtime.sha(out/f'region_{r}.npz'))
        self.assertEqual(link['source_count'],256690)
        self.assertEqual(link['unknown_rows'],170281)

    def test_noop_and_bad_inputs(self):
        out=self.folder/'noop'
        edit_asset(self.base,out,dict(spacing=.045),paper_effect=1.)
        self.assertEqual(runtime.sha(self.base/'region_4.npz'),runtime.sha(out/'region_4.npz'))
        for changes,paper in [(dict(spacing=0),None),({},1.1),({},float('nan'))]:
            with self.assertRaises(ValueError):edit_asset(self.base,self.folder/'invalid',changes,paper)
        with self.assertRaises(ValueError):runtime.output_guard('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/illegal')

if __name__=='__main__':unittest.main()
