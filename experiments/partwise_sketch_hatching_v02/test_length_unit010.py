"""Necessary length/provenance contracts; image quality is a separate gate."""
import copy
import unittest
from unittest.mock import patch

from length_cli import (UNIT, MESH_SHA256, bound_file, destination, generate,
    generator_hashes, length_value, load_asset, make_recipe, np, read_recipe,
    revision, selected_domain, sha, validate_recipe, walker)


def arc_world(mesh, stroke):
    points = np.einsum('ij,ijk->ik', stroke['bary'], mesh['tri'][stroke['faces']])
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


class BaseLengthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = UNIT / 'inputs/asset.json'
        cls.manifest, cls.files, cls.mesh, cls.old, cls.cfg = load_asset(cls.source)
        cls.noop_recipe = make_recipe(cls.manifest, cls.files, cls.mesh, cls.old,
                                     cls.cfg, .18, cls.source)
        cls.recipe = make_recipe(cls.manifest, cls.files, cls.mesh, cls.old,
                                cls.cfg, .12, cls.source)
        cls.noop = generate(cls.mesh, cls.noop_recipe)
        with patch.object(walker, 'generate_strokes',
                          side_effect=AssertionError('must not generate all seeds')):
            with patch.object(walker, 'walk', wraps=walker.walk) as integration:
                cls.short = generate(cls.mesh, cls.recipe)
                cls.walk_calls = integration.call_args_list

    def test_original_length_exactly_recovers_selected_base_paths(self):
        original = {s['id']: s for s in self.old if s['part'] == 3}
        self.assertEqual(sha(self.files['mesh']), MESH_SHA256)
        self.assertEqual(revision(self.noop), revision(list(original.values())))
        for stroke in self.noop:
            prior = original[stroke['id']]
            np.testing.assert_array_equal(stroke['faces'], prior['faces'])
            np.testing.assert_array_equal(stroke['bary'], prior['bary'])
            self.assertEqual(stroke['ink'], prior['ink'])

    def test_only_selected_150_paths_are_integrated(self):
        selected = set(self.recipe['selected_seed_indices'])
        self.assertEqual(len(self.short), 150)
        self.assertEqual(len(self.walk_calls), 300)
        self.assertEqual({int(s['id'].split('seed')[1].split(':')[0])
                          for s in self.short}, selected)
        self.assertEqual({call.args[3] for call in self.walk_calls}, {3})
        self.assertEqual({call.args[5] for call in self.walk_calls}, {0, 1})
        self.assertEqual({call.args[7] for call in self.walk_calls}, {.06})

    def test_shorter_paths_keep_ids_inks_seed_and_valid_base_anchors(self):
        original = {s['id']: s for s in self.old if s['part'] == 3}
        self.assertEqual(set(original), {s['id'] for s in self.short})
        shorter_count = 0
        for stroke in self.short:
            prior = original[stroke['id']]
            self.assertEqual(stroke['ink'], prior['ink'])
            self.assertTrue(np.all(self.mesh['parts'][stroke['faces']] == 3))
            self.assertTrue(np.isfinite(stroke['bary']).all())
            self.assertGreaterEqual(float(stroke['bary'].min()), -1e-12)
            np.testing.assert_allclose(stroke['bary'].sum(axis=1), 1., atol=1e-12, rtol=0)
            self.assertTrue(np.any((stroke['faces'] == stroke['seed_face'])
                & np.all(stroke['bary'] == stroke['seed_bary'], axis=1)))
            new_arc, old_arc = arc_world(self.mesh, stroke), arc_world(self.mesh, prior)
            self.assertLessEqual(new_arc, .12+1e-9)
            self.assertLessEqual(new_arc, old_arc+1e-9)
            shorter_count += int(new_arc < old_arc-1e-8)
        self.assertGreater(shorter_count, 0)

    def test_nonfinite_boolean_and_out_of_domain_lengths_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, False,
                      0., .0599, .2401):
            with self.subTest(value=value), self.assertRaises(ValueError):
                length_value(value)
        for value in (.06, .12, .18, .24):
            self.assertEqual(length_value(value), value)

    def test_bad_dependency_or_seed_domain_rejected_before_walking(self):
        bad_hash = copy.deepcopy(self.recipe)
        bad_hash['generator_sha256']['legacy/core.py'] = '0'*64
        bad_pair = copy.deepcopy(self.recipe)
        bad_pair['selected_stroke_inks'].pop(next(iter(bad_pair['selected_stroke_inks'])))
        duplicate_seed = copy.deepcopy(self.recipe)
        duplicate_seed['selected_seed_indices'][0] = duplicate_seed['selected_seed_indices'][1]
        for recipe in (bad_hash, bad_pair, duplicate_seed):
            with patch.object(walker, 'walk', side_effect=AssertionError('must not walk')):
                with self.assertRaises(ValueError):
                    generate(self.mesh, recipe)
        self.assertEqual(self.recipe['generator_sha256'], generator_hashes())

    def test_missing_duplicate_layer_and_corrupt_source_seed_rejected(self):
        base = next(stroke for stroke in self.old if stroke['part'] == 3)
        missing = [stroke for stroke in self.old if stroke['id'] != base['id']]
        duplicate = self.old + [copy.deepcopy(base)]
        for strokes in (missing, duplicate):
            with self.assertRaises(ValueError):
                selected_domain(strokes)
        corrupt = copy.deepcopy(self.old)
        target = next(stroke for stroke in corrupt if stroke['id'] == base['id'])
        target['bary'][:] = [1., 0., 0.]
        with self.assertRaises(ValueError):
            make_recipe(self.manifest, self.files, self.mesh, corrupt,
                        self.cfg, .12, self.source)

    def test_cold_recipe_has_no_target_path_or_stale_manifest_binding(self):
        stale = copy.deepcopy(self.manifest)
        stale['recipe'] = {'path': 'absent_ancestor_recipe.json', 'sha256': '0'*64}
        stale['path_lineage'] = {'obsolete': True}
        recipe = make_recipe(stale, self.files, self.mesh, self.old,
                             self.cfg, .12, self.source)
        for field in ('recipe', 'path_lineage', 'mesh', 'strokes', 'config'):
            self.assertNotIn(field, recipe['baseline_manifest'])
        self.assertNotIn('faces', recipe)
        self.assertNotIn('bary', recipe)
        self.assertEqual(recipe['selected_stroke_inks'], self.recipe['selected_stroke_inks'])
        self.assertEqual(validate_recipe(recipe), recipe['selected_seed_indices'])

    def test_authority_and_input_digest_controls(self):
        for path in (UNIT, UNIT / 'inputs', UNIT.parent / 'unit_009/new_length_output'):
            with self.subTest(path=path), self.assertRaises((ValueError, FileExistsError)):
                destination(path)
        with self.assertRaises(FileNotFoundError):
            read_recipe(UNIT / 'nonexistent_recipe.json')
        with self.assertRaises(ValueError):
            bound_file(UNIT, {'path': str(self.files['mesh']), 'sha256': '0'*64})


if __name__ == '__main__':
    unittest.main(verbosity=2)
