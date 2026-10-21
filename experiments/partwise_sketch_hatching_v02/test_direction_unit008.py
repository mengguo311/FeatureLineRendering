"""Necessary recipe/identity/authority controls for target-only generation."""
from direction_cli import *
import unittest
from unittest.mock import patch

class DirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest,cls.files,cls.mesh,cls.old,cls.cfg=load_asset(UNIT/'inputs/asset.json')
        cls.recipe=dict(schema='shade_direction_recipe_v1',part=1,style='mixed',seed=1729,count=260,length_world=.32,step_world=.015,angle_deg=0.,generator_sha256=generator_hashes())
    def test_zero_recipe_recovers_original_shade(self):
        self.assertEqual(revision([s for s in self.old if s['part']==1]),revision(generate(self.mesh,self.recipe)))
    def test_changed_angle_valid_anchors_and_unchanged_ink_ids(self):
        recipe=copy.deepcopy(self.recipe);recipe['angle_deg']=15.;new=generate(self.mesh,recipe)
        original={s['id']:s for s in self.old if s['part']==1}
        self.assertNotEqual(revision(new),revision(list(original.values())))
        self.assertEqual(set(original),{s['id'] for s in new})
        for s in new:
            self.assertEqual(s['ink'],original[s['id']]['ink'])
            self.assertTrue(np.all(self.mesh['parts'][s['faces']]==1))
            self.assertTrue(np.isfinite(s['bary']).all())
            self.assertGreaterEqual(s['bary'].min(),-1e-12)
            np.testing.assert_allclose(s['bary'].sum(axis=1),1,atol=1e-12,rtol=0)
    def test_nonfinite_or_out_of_domain_angles_rejected(self):
        for v in (float('nan'),float('inf'),-46,46):
            with self.assertRaises(ValueError):angle_value(v)
    def test_generator_hash_mismatch_rejected_before_generation(self):
        recipe=copy.deepcopy(self.recipe);recipe['generator_sha256']['core.py']='0'*64
        with patch.object(walker,'generate_strokes',side_effect=AssertionError('must not generate')):
            with self.assertRaises(ValueError):generate(self.mesh,recipe)
    def test_historical_or_existing_output_rejected(self):
        for p in (UNIT.parent/'unit_007/new_output',UNIT,UNIT/'inputs'):
            with self.assertRaises((ValueError,FileExistsError)):destination(p)
    def test_missing_and_mismatched_recipe_dependency(self):
        with self.assertRaises(FileNotFoundError):read_recipe(UNIT/'does_not_exist.json')
        with self.assertRaises(ValueError):bound_file(UNIT,dict(path=str(self.files['mesh']),sha256='0'*64))

if __name__=='__main__':unittest.main(verbosity=2)
