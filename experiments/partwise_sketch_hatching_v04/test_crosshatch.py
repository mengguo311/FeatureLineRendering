"""Behavior checks on saved, model-derived Chair geometry; writes only unit013."""
import runtime
from runtime import OUTPUT_ROOT,sha
from pathlib import Path
import json,unittest,tempfile
from unittest.mock import patch
import numpy as np
from demo import edit,load_asset
from geometry import orbit_camera
from render import render

SOURCE=OUTPUT_ROOT/'units/unit_012/portable_demo/assets/chair'
UNIT=OUTPUT_ROOT/'units/unit_013'
CHANGE=dict(cross_enabled=True,cross_angle=60.,cross_spacing=.06)

class RealChairCrosshatch(unittest.TestCase):
    def setUp(self):
        (UNIT/'test_work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=UNIT/'test_work')
        self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_cross_edit_keeps_base_and_other_regions(self):
        edit(SOURCE,self.root/'on',2,CHANGE)
        mesh,paths,meta=load_asset(self.root/'on')
        self.assertIn('layer_id',paths[2], 'cross edit must create a saved second layer')
        self.assertEqual(set(paths[2]['layer_id']),{0,1})
        original=load_asset(SOURCE)[1][2];base=paths[2]['layer_id']==0
        for key in original:np.testing.assert_array_equal(paths[2][key][base],original[key])
        for region in (1,3):self.assertEqual(sha(SOURCE/f'region_{region}.npz'),sha(self.root/f'on/region_{region}.npz'))
        self.assertEqual(sha(SOURCE/'mesh.npz'),sha(self.root/'on/mesh.npz'))
        a=set(paths[2]['stroke_id'][base]);b=set(paths[2]['stroke_id'][~base])
        self.assertFalse(a&b)
        self.assertTrue(meta['styles']['2']['cross_enabled'])
        self.assertEqual(meta['edit']['regenerated_layers'],[1])

    def test_toggle_cold_load_and_pixel_restoration(self):
        edit(SOURCE,self.root/'on',2,CHANGE)
        edit(self.root/'on',self.root/'off',2,dict(cross_enabled=False))
        edit(self.root/'off',self.root/'again',2,dict(cross_enabled=True))
        for name in ('off','again'):
            self.assertEqual(sha(self.root/'on/region_2.npz'),sha(self.root/name/'region_2.npz'))
        c=orbit_camera(47,25,5.2,192)
        with patch('demo.generate_region',side_effect=AssertionError('cold reload may not regenerate')):
            images=[]
            for a in (SOURCE,self.root/'on',self.root/'off',self.root/'again'):
                m,s,j=load_asset(a);images.append(render(m,s,j['styles'],c))
        np.testing.assert_array_equal(images[0]['image'],images[2]['image'])
        np.testing.assert_array_equal(images[1]['image'],images[3]['image'])
        self.assertGreater(float(np.abs(images[0]['image']-images[1]['image']).sum()),1)
        for r in (1,3):np.testing.assert_array_equal(images[0]['layers'][r],images[1]['layers'][r])
        np.testing.assert_array_equal(images[0]['layers'][2],images[1]['style_layers']['2_0'])

    def test_cross_angle_and_width_have_separate_revision_rules(self):
        edit(SOURCE,self.root/'on',2,CHANGE)
        edit(self.root/'on',self.root/'angle',2,dict(cross_angle=75.))
        old=load_asset(self.root/'on')[1][2];new=load_asset(self.root/'angle')[1][2]
        for key in old:np.testing.assert_array_equal(old[key][old['layer_id']==0],new[key][new['layer_id']==0])
        self.assertFalse(np.array_equal(old['points'][old['layer_id']==1],new['points'][new['layer_id']==1]))
        edit(self.root/'angle',self.root/'width',2,dict(width=1.4))
        self.assertEqual(sha(self.root/'angle/region_2.npz'),sha(self.root/'width/region_2.npz'))
        edit(self.root/'width',self.root/'base',2,dict(angle=45.))
        self.assertEqual(load_asset(self.root/'base')[2]['edit']['regenerated_layers'],[0,1])

    def test_invalid_cross_settings_fail_before_output(self):
        for i,changes in enumerate((dict(cross_enabled='yes'),dict(cross_angle=float('nan')),
                                  dict(cross_angle=0.),dict(cross_spacing=0.))):
            with self.assertRaises(ValueError):edit(SOURCE,self.root/str(i),2,changes)
            self.assertFalse((self.root/str(i)).exists())

    def test_corrupt_layer_identity_is_rejected(self):
        edit(SOURCE,self.root/'on',2,CHANGE)
        file=self.root/'on/region_2.npz'
        with np.load(file) as d:data={k:d[k] for k in d.files}
        data['layer_id'][-1]=7
        np.savez_compressed(file,**data)
        with self.assertRaisesRegex(ValueError,'layer'):load_asset(self.root/'on')

    def test_authoring_preserves_unselected_segments_in_both_layers(self):
        from region_tools import author_face_selection
        edit(SOURCE,self.root/'on',2,CHANGE)
        mesh,paths,meta=load_asset(self.root/'on')
        centers=mesh['tri'].mean(1)
        selected=np.flatnonzero((mesh['regions']==2)&(centers[:,0]>0))
        record=author_face_selection(self.root/'on',self.root/'split',selected,2,'Right half',dict(operation='test_saved_faces'))
        after=load_asset(self.root/'split')[1];keep=~np.isin(paths[2]['face'],selected)
        for key in paths[2]:np.testing.assert_array_equal(paths[2][key][keep],after[2][key])
        self.assertEqual(set(after[record['new_region']]['layer_id']),{0,1})

    def test_authoring_cannot_leave_only_hidden_cross_paths(self):
        from region_tools import author_face_selection
        edit(SOURCE,self.root/'on',2,CHANGE)
        paths=load_asset(self.root/'on')[1][2]
        selected=np.unique(paths['face'][paths['layer_id']==0])
        with self.assertRaisesRegex(ValueError,'without any base hatch paths'):
            author_face_selection(self.root/'on',self.root/'bad',selected,2,'All base faces',dict(operation='test'))
        self.assertFalse((self.root/'bad').exists())

if __name__=='__main__':unittest.main(verbosity=2)
