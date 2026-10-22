"""Material behavior on the real saved Lego asset; output only in unit016."""
import runtime
from runtime import OUTPUT_ROOT,sha,js
from pathlib import Path
import copy,json,tempfile,unittest
from unittest.mock import patch
import numpy as np
from demo import load_asset,edit
from render import render
from geometry import orbit_camera

UNIT=OUTPUT_ROOT/'units/unit_016'
SOURCE=OUTPUT_ROOT/'units/unit_015/portable_demo/examples/lego_bucket_refined'

class InkStrength(unittest.TestCase):
    def setUp(self):
        (UNIT/'test_work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=UNIT/'test_work');self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_01_real_render_local_ink_and_legacy_default(self):
        mesh,paths,meta=load_asset(SOURCE);c=orbit_camera(248,30,5.1,192)
        baseline=render(mesh,paths,meta['styles'],c)
        styles=copy.deepcopy(meta['styles']);styles['1']['ink_strength']=.8
        legacy=render(mesh,paths,styles,c)
        np.testing.assert_array_equal(baseline['image'],legacy['image'])
        styles['1']['ink_strength']=.4
        changed=render(mesh,paths,styles,c)
        np.testing.assert_array_equal(changed['layers'][1],baseline['layers'][1]*.5)
        self.assertGreater(float(np.abs(changed['image']-baseline['image']).sum()),1)
        for key in ('depth','regions','contour'):np.testing.assert_array_equal(changed[key],baseline[key])
        for r in (2,3,4):np.testing.assert_array_equal(changed['layers'][r],baseline['layers'][r])

    def test_02_saved_edit_never_regenerates_and_zero_restores(self):
        with patch('demo.generate_region',side_effect=AssertionError('ink edit regenerated paths')),patch('demo.add_cross_layer',side_effect=AssertionError('ink edit regenerated cross')):
            edit(SOURCE,self.root/'dim',4,dict(ink_strength=.4))
            edit(self.root/'dim',self.root/'zero',4,dict(ink_strength=0.))
            edit(self.root/'zero',self.root/'restored',4,dict(ink_strength=.8))
            loaded=[load_asset(p) for p in (SOURCE,self.root/'dim',self.root/'zero',self.root/'restored')]
        for name in ('dim','zero','restored'):
            for f in SOURCE.iterdir():
                if f.is_file() and f.name!='asset.json':self.assertEqual(sha(f),sha(self.root/name/f.name))
        images=[render(m,s,j['styles'],orbit_camera(338,30,5.1,160)) for m,s,j in loaded]
        for layer in ('4_0','4_1'):
            np.testing.assert_array_equal(images[1]['style_layers'][layer],images[0]['style_layers'][layer]*.5)
            self.assertEqual(float(images[2]['style_layers'][layer].sum()),0)
        np.testing.assert_array_equal(images[0]['image'],images[3]['image'])
        self.assertEqual(loaded[1][2]['edit']['regenerated_layers'],[])

    def test_03_invalid_ink_rejected_before_output_and_on_load(self):
        for i,value in enumerate((-1.,1.01,float('nan'),float('inf'),True,'0.4',None)):
            with self.subTest(value=value),self.assertRaises(ValueError):edit(SOURCE,self.root/str(i),1,dict(ink_strength=value))
            self.assertFalse((self.root/str(i)).exists())
        edit(SOURCE,self.root/'valid',1,dict(ink_strength=.4))
        j=json.loads((self.root/'valid/asset.json').read_text());j['styles']['1']['ink_strength']=-.2;js(self.root/'valid/asset.json',j)
        with self.assertRaises(ValueError):load_asset(self.root/'valid')

if __name__=='__main__':unittest.main(verbosity=2)
