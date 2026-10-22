"""Actual frozen Lego manual bucket, reusing existing runtime controls."""
import runtime
from runtime import OUTPUT_ROOT, sha
from pathlib import Path
import json, shutil, tempfile, unittest
from unittest.mock import patch
import numpy as np
from demo import edit, load_asset
from geometry import orbit_camera
from hatching import layer_ids
from render import render

UNIT=OUTPUT_ROOT/'units/unit_014'
P=json.loads((UNIT/'PROTOCOL.json').read_text());SOURCE=Path(P['asset']);R=4
CHANGE={k:v for k,v in P['local_edit'].items() if k!='region'}

class LegoComposition(unittest.TestCase):
    def setUp(self):
        (UNIT/'test_work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=UNIT/'test_work');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def create(self):
        edit(SOURCE,self.root/'single',R,P['base_edit'])
        edit(self.root/'single',self.root/'on',R,CHANGE)

    def test_composed_short_cross_preserves_selection_and_other_regions(self):
        self.create();mesh,paths,meta=load_asset(self.root/'on');original=load_asset(SOURCE)[1]
        self.assertEqual(int((mesh['regions']==R).sum()),2030)
        for name in ('mesh.npz','selection_4.npz','region_1.npz','region_2.npz','region_3.npz'):
            self.assertEqual(sha(SOURCE/name),sha(self.root/'on'/name))
        base=load_asset(self.root/'single')[1][R];ids=layer_ids(paths[R])
        for key in base:np.testing.assert_array_equal(base[key],paths[R][key][ids==0])
        self.assertFalse(np.array_equal(original[R]['points'],base['points']))
        self.assertEqual(set(ids),{0,1});self.assertEqual(meta['styles']['4']['plane'],'xz')
        for layer in (0,1):
            pick=ids==layer;_,indices=np.unique(paths[R]['stroke_id'][pick],return_inverse=True)
            length=np.linalg.norm(np.diff(paths[R]['points'][pick],axis=1),axis=2).ravel()
            self.assertLessEqual(np.bincount(indices,weights=length).max(),.12+1e-8)

    def test_disabled_layer_edits_then_cold_reload_equal_fresh_composition(self):
        self.create();edit(self.root/'on',self.root/'off',R,dict(cross_enabled=False))
        self.assertEqual(sha(self.root/'on/region_4.npz'),sha(self.root/'off/region_4.npz'))
        edit(self.root/'off',self.root/'changed_off',R,dict(length=.16))
        edit(self.root/'changed_off',self.root/'again',R,dict(cross_enabled=True))
        edit(SOURCE,self.root/'fresh',R,dict(P['base_edit'],**CHANGE,length=.16))
        again=load_asset(self.root/'again')[1][R];fresh=load_asset(self.root/'fresh')[1][R]
        for key in again:np.testing.assert_array_equal(again[key],fresh[key])
        with patch('demo.generate_region',side_effect=AssertionError('cold load must use saved paths')):
            results=[]
            for asset in (self.root/'single',self.root/'on',self.root/'off',self.root/'again',self.root/'fresh'):
                m,s,j=load_asset(asset);results.append(render(m,s,j['styles'],orbit_camera(233,30,5.1,192)))
        np.testing.assert_array_equal(results[0]['image'],results[2]['image'])
        np.testing.assert_array_equal(results[3]['image'],results[4]['image'])
        self.assertGreater(np.abs(results[0]['image']-results[1]['image']).sum(),1)
        for r in (1,2,3):np.testing.assert_array_equal(results[0]['layers'][r],results[1]['layers'][r])

    def test_saved_manual_selection_missing_or_corrupt_is_rejected(self):
        shutil.copytree(SOURCE,self.root/'bad');selection=self.root/'bad/selection_4.npz'
        selection.write_bytes(b'not the frozen selection')
        with self.assertRaisesRegex(ValueError,'selection checksum'):load_asset(self.root/'bad')
        selection.unlink()
        with self.assertRaises(FileNotFoundError):load_asset(self.root/'bad')

if __name__=='__main__':unittest.main(verbosity=2)
