"""Small real-Ficus regressions for independent saved contour display."""
import runtime
from runtime import OUTPUT_ROOT,sha,js
import unittest,json,tempfile,shutil
from pathlib import Path
import numpy as np
import demo
from geometry import resize_camera
from render import render

class ContourDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.asset=OUTPUT_ROOT/'units/unit_010/portable_demo/assets/ficus'
        cls.mesh,cls.paths,cls.meta=demo.load_asset(cls.asset)
        cls.camera=resize_camera(cls.meta['cameras'][0],128)
        cls.args=(cls.mesh,cls.paths,cls.meta['styles'],cls.camera)
        cls.baseline=render(*cls.args)

    def test_real_model_strength_preserves_hatches(self):
        reduced=render(*self.args,display={'contour_strength':.35,'contours_visible':True})
        for key in ('hatch','depth','regions','proxy','region_rgb'):
            np.testing.assert_array_equal(reduced[key],self.baseline[key])
        for region in self.paths:np.testing.assert_array_equal(reduced['layers'][region],self.baseline['layers'][region])
        np.testing.assert_allclose(reduced['contour'],self.baseline['contour']*.35,atol=4e-8)
        self.assertGreater(float(np.abs(reduced['image']-self.baseline['image']).sum()),1)

    def test_hidden_matches_zero_and_retains_hatch(self):
        hidden=render(*self.args,display={'contour_strength':.35,'contours_visible':False})
        zero=render(*self.args,display={'contour_strength':0.,'contours_visible':True})
        self.assertEqual(float(hidden['contour'].sum()),0.)
        np.testing.assert_array_equal(hidden['image'],zero['image'])
        np.testing.assert_allclose(hidden['image'],1-self.baseline['hatch'],atol=6e-8)

    def test_legacy_default_exact(self):
        explicit=render(*self.args,display={'contour_strength':1.,'contours_visible':True})
        for key in ('image','hatch','contour','regions','depth'):np.testing.assert_array_equal(explicit[key],self.baseline[key])

    def test_invalid_display_rejected_before_output(self):
        from display_settings import validate_display
        for bad in (-.01,1.01,float('nan'),float('inf'),True,'0.3',None):
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_display({'contour_strength':bad})
        for bad in (0,1,'false',None):
            with self.subTest(visible=bad),self.assertRaises(ValueError):validate_display({'contours_visible':bad})
        with self.assertRaises(ValueError):validate_display({'contour_strenght':.3})

    def test_saved_display_preserves_all_geometry_and_cold_loads(self):
        root=OUTPUT_ROOT/'units/unit_011/tests';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            dest=Path(tmp)/'reduced'
            demo.set_display(self.asset,dest,{'contour_strength':.35,'contours_visible':False})
            _,_,meta=demo.load_asset(dest)
            self.assertEqual(meta['display'],{'contour_strength':.35,'contours_visible':False})
            self.assertEqual(meta['styles'],self.meta['styles'])
            for p in self.asset.iterdir():
                if p.is_file() and p.name!='asset.json':self.assertEqual(sha(p),sha(dest/p.name))
            meta['display']['contour_strength']=float('inf')
            # Deliberately malformed input, no valid artifact claim.
            (dest/'asset.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):demo.load_asset(dest)

if __name__=='__main__':unittest.main(verbosity=2)
