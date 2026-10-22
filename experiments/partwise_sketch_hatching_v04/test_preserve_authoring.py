"""Real Chair regression: creating a region must not silently restyle it."""
import runtime
from runtime import OUTPUT_ROOT, js, sha
from pathlib import Path
import json, tempfile, unittest
import shutil
import numpy as np
from unit021_run import U, ASSET, protocol
from demo import load_asset, edit
from region_tools import author_face_selection
from selection_draft import replay_recipe
from geometry import orbit_camera
from render import render
from hatching import layer_ids, visibility_masks


class PreserveAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=U)
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.mesh, self.paths, self.meta = load_asset(ASSET)
        recipe = json.loads((U/'SELECTION_RECIPE.json').read_text())
        self.draft = replay_recipe(self.mesh, self.meta['mesh_sha256'], recipe)
        author_face_selection(ASSET, self.out/'authored', self.draft.face_ids, 2,
                              recipe['name'], self.draft.provenance())
        self.newmesh, self.newpaths, self.newmeta = load_asset(self.out/'authored')

    def test_selected_and_remaining_segments_keep_original_identity(self):
        selected = np.isin(self.paths[2]['face'], self.draft.face_ids)
        for key, original in self.paths[2].items():
            np.testing.assert_array_equal(self.newpaths[4][key], original[selected])
            np.testing.assert_array_equal(self.newpaths[2][key], original[~selected])
        np.testing.assert_array_equal(self.mesh['vertices'], self.newmesh['vertices'])
        np.testing.assert_array_equal(self.mesh['faces'], self.newmesh['faces'])
        for region in (1, 3):
            self.assertEqual(sha(ASSET/f'region_{region}.npz'),
                             sha(self.out/f'authored/region_{region}.npz'))

    def test_author_only_is_pixel_exact_on_real_chair(self):
        c = orbit_camera(**protocol()['viewer_camera'])
        before = render(self.mesh, self.paths, self.meta['styles'], c)
        after = render(self.newmesh, self.newpaths, self.newmeta['styles'], c)
        for key in ('image', 'hatch', 'contour', 'depth'):
            np.testing.assert_array_equal(before[key], after[key], err_msg=key)
        self.assertFalse(np.array_equal(before['regions'], after['regions']))
        edit(self.out/'authored', self.out/'noop', 4, {'angle': 95.})
        self.assertEqual(sha(self.out/'authored/region_4.npz'), sha(self.out/'noop/region_4.npz'))

    def test_repeat_split_and_cross_edit_composition(self):
        faces = np.unique(self.newpaths[4]['face'])[::2]
        author_face_selection(self.out/'authored', self.out/'split_again', faces, 4, 'Seat subset', {})
        m, s, j = load_asset(self.out/'split_again')
        c = orbit_camera(29, 28, 4.9, 192)
        before = render(self.newmesh, self.newpaths, self.newmeta['styles'], c)
        after = render(m, s, j['styles'], c)
        np.testing.assert_array_equal(before['image'], after['image'])
        edit(self.out/'authored', self.out/'cross', 4, {'cross_enabled': True})
        cross = load_asset(self.out/'cross')[1][4]
        for key, v in self.newpaths[4].items():
            np.testing.assert_array_equal(v, cross[key][layer_ids(cross)==0])
        self.assertTrue((visibility_masks(cross,4)[layer_ids(cross)==1] == 1 << 4).all())
        # Spacing changes only the base geometry; retain cached cross support.
        edit(self.out/'cross', self.out/'spacing', 4, {'spacing': .05})
        spaced = load_asset(self.out/'spacing')[1][4]
        self.assertTrue((visibility_masks(spaced,4)[layer_ids(spaced)==0] == 1 << 4).all())
        for key in ('points','face','bary','stroke_id','visibility_mask'):
            np.testing.assert_array_equal(spaced[key][layer_ids(spaced)==1], cross[key][layer_ids(cross)==1])
        edit(self.out/'cross', self.out/'angle', 4, {'angle': 65.})
        angle = load_asset(self.out/'angle')[1][4]
        self.assertTrue((visibility_masks(angle,4) == 1 << 4).all())

    def test_saved_masks_parent_mapping_and_archive_validation(self):
        from asset_archive import export_archive, unpack_archive
        with np.load(self.out/'authored/selection_4.npz') as z:
            np.testing.assert_array_equal(self.newpaths[4]['stroke_id'], z['parent_stroke_id'])
            np.testing.assert_array_equal(self.paths[2]['points'][z['parent_segment_index']], self.newpaths[4]['points'])
        payload = export_archive(self.out/'authored', protocol()['viewer_camera'], 4)
        unpack_archive(payload, self.out/'imported', {'chair': self.meta['original']['sha256']})
        for name in ('mesh.npz','region_2.npz','region_4.npz','selection_4.npz'):
            self.assertEqual(sha(self.out/'authored'/name), sha(self.out/'imported'/name))
        for i, mask in enumerate((0, 1, 1 << 31, -1)):
            bad = self.out/f'bad{i}';shutil.copytree(self.out/'authored',bad)
            data = dict(self.newpaths[4]);data['visibility_mask'] = np.full(len(data['points']),mask,np.int64)
            np.savez_compressed(bad/'region_4.npz', **data)
            with self.assertRaisesRegex(ValueError,'visibility masks'):load_asset(bad)
        # A support mask cannot claim background or an unrelated absent label.
        bad = self.out/'badshape';shutil.copytree(self.out/'authored',bad)
        data = dict(self.newpaths[4]);data['visibility_mask'] = data['visibility_mask'][:1]
        np.savez_compressed(bad/'region_4.npz', **data)
        with self.assertRaisesRegex(ValueError,'visibility masks'):load_asset(bad)

    def test_split_cannot_leave_enabled_source_cross_layer_empty(self):
        edit(self.out/'authored', self.out/'cross', 4, {'cross_enabled': True})
        m,s,j = load_asset(self.out/'cross');paths=s[4];layers=layer_ids(paths)
        selected=np.unique(paths['face'][layers==1])
        self.assertTrue((~np.isin(paths['face'][layers==0],selected)).any())
        with self.assertRaisesRegex(ValueError,'without.*cross'):
            author_face_selection(self.out/'cross',self.out/'invalid_split',selected,4,'All cross faces',{})
        self.assertFalse((self.out/'invalid_split').exists())

    def test_valid_signed_import_masks_render_like_unsigned(self):
        bad=self.out/'signed';shutil.copytree(self.out/'authored',bad)
        data=dict(self.newpaths[4]);data['visibility_mask']=data['visibility_mask'].astype(np.int64)
        np.savez_compressed(bad/'region_4.npz',**data)
        m,s,j=load_asset(bad)
        c=orbit_camera(29,28,4.9,192)
        expected=render(self.newmesh,self.newpaths,self.newmeta['styles'],c)
        actual=render(m,s,j['styles'],c)
        np.testing.assert_array_equal(expected['image'],actual['image'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
