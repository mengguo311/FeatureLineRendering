"""Behavior tests on the real Drums draft and frozen selection recipe."""
import runtime
from runtime import OUTPUT_ROOT, sha
from pathlib import Path
import json, tempfile, unittest
import numpy as np
from demo import load_asset, edit
from screen_selection import visible_faces
from selection_draft import SelectionDraft, replay_recipe
from region_tools import author_face_selection

UNIT=OUTPUT_ROOT/'units/unit_007'

class DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((UNIT/'PROTOCOL.json').read_text())
        cls.recipe=cls.p['selection'];cls.asset=Path(cls.p['source_asset'])
        cls.mesh,cls.paths,cls.meta=load_asset(cls.asset)

    def test_actual_multiview_union_subtract_undo_and_recipe(self):
        draft=SelectionDraft(self.mesh,self.meta['mesh_sha256'],3)
        expected=set();initial=None;added=removed=0
        for step in self.recipe['steps']:
            ids,_=visible_faces(self.mesh,step['camera'],step['rectangle'],3)
            before=set(expected)
            if step['operation']=='replace':expected=set(map(int,ids));initial=set(expected)
            elif step['operation']=='add':expected.update(map(int,ids));added+=len(expected-before)
            else:expected.difference_update(map(int,ids));removed+=len(before-expected)
            draft.apply(step['camera'],step['rectangle'],step['operation'])
            np.testing.assert_array_equal(draft.face_ids,sorted(expected))
        self.assertGreater(added,0);self.assertGreater(removed,0)
        self.assertGreater(len(expected-initial),0)
        final=draft.face_ids.copy();draft.undo()
        self.assertGreater(len(draft.face_ids),len(final))
        last=self.recipe['steps'][-1];draft.apply(last['camera'],last['rectangle'],last['operation'])
        np.testing.assert_array_equal(draft.face_ids,final)
        other=replay_recipe(self.mesh,self.meta['mesh_sha256'],self.recipe)
        np.testing.assert_array_equal(other.face_ids,final)
        bad=dict(self.recipe,mesh_sha256='wrong')
        with self.assertRaises(ValueError):replay_recipe(self.mesh,self.meta['mesh_sha256'],bad)
        with self.assertRaises(ValueError):draft.apply(last['camera'],last['rectangle'],'magic')
        np.testing.assert_array_equal(draft.face_ids,final)
        draft.clear();self.assertEqual(len(draft.face_ids),0)
        with self.assertRaises(ValueError):draft.undo()

    def test_commit_cold_edit_retains_unselected_real_paths(self):
        d=replay_recipe(self.mesh,self.meta['mesh_sha256'],self.recipe)
        root=UNIT/'test_work';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            a=Path(tmp)/'authored';b=Path(tmp)/'edited'
            author_face_selection(self.asset,a,d.face_ids,3,self.recipe['name'],d.provenance())
            mesh,paths,meta=load_asset(a)
            np.testing.assert_array_equal(mesh['vertices'],self.mesh['vertices'])
            np.testing.assert_array_equal(mesh['faces'],self.mesh['faces'])
            np.testing.assert_array_equal(np.flatnonzero(mesh['regions']==4),d.face_ids)
            keep=~np.isin(self.paths[3]['face'],d.face_ids)
            for k in self.paths[3]:np.testing.assert_array_equal(paths[3][k],self.paths[3][k][keep])
            for r in (1,2):self.assertEqual(sha(a/f'region_{r}.npz'),sha(self.asset/f'region_{r}.npz'))
            self.assertEqual(len(meta['region_history'][-1]['steps']),4)
            edit(a,b,4,dict(angle=35.));load_asset(b)
            for r in (1,2,3):self.assertEqual(sha(a/f'region_{r}.npz'),sha(b/f'region_{r}.npz'))
            self.assertNotEqual(sha(a/'region_4.npz'),sha(b/'region_4.npz'))

    def test_editor_navigation_retains_draft_without_mutating_asset(self):
        from viewer import Editor
        root=UNIT/'test_work';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            editor=Editor(self.asset,Path(tmp)/'session')
            original_hashes={p.name:sha(p) for p in self.asset.iterdir() if p.is_file()}
            editor.navigate(dict(revision=0,**self.p['viewer_camera']))
            step=self.recipe['steps'][0]
            preview=editor.preview_selection(dict(revision=editor.revision,source_region=3,
                mode='visible',rectangle=step['rectangle'],operation='add'))
            ids=editor.draft.face_ids.copy();old_token=preview['token'];old_revision=editor.revision
            editor.navigate(dict(revision=editor.revision,azimuth=337,elevation=55,distance=4.9))
            np.testing.assert_array_equal(editor.draft.face_ids,ids)
            self.assertEqual(editor.asset,self.asset)
            self.assertFalse(editor.history)
            self.assertEqual(editor.record['draft']['face_count'],len(ids))
            self.assertNotEqual(editor.record['draft']['token'],old_token)
            self.assertTrue((editor.output/'DRAFT.json').is_file())
            with self.assertRaises(ValueError):editor.author(dict(token=old_token,name='stale'))
            with self.assertRaises(ValueError):editor.navigate(dict(revision=old_revision,azimuth=20,elevation=55,distance=4.9))
            values=dict(region=3,**self.meta['styles']['3'],**editor.record['camera'])
            with self.assertRaises(ValueError):editor.apply(values)
            self.assertEqual(original_hashes,{p.name:sha(p) for p in self.asset.iterdir() if p.is_file()})
            editor.draft_action(dict(revision=editor.revision,action='undo'))
            self.assertEqual(editor.record['draft']['face_count'],0)
            self.assertIsNone(editor.record['draft']['token'])
            editor.draft_action(dict(revision=editor.revision,action='clear'))
            self.assertIsNone(editor.record['draft'])

if __name__=='__main__':unittest.main(verbosity=2)
