"""Bounded shade-placement contracts; actual rendered quality is separate."""
import copy
import unittest
from collections import Counter
from unittest.mock import patch

from spacing_cli import (UNIT, MESH_SHA256, PLACEMENT, band_candidates,
    bound_file, destination, face_bands, generate, generator_hashes, load_asset,
    make_recipe, np, read_recipe, revision, select_band, sha, validate_recipe,
    walker)


def independent_bands(mesh):
    """Classify the four named surfaces from geometry, without face_bands."""
    out = np.full(len(mesh['faces']), -1, np.int32)
    for face in np.flatnonzero(mesh['parts'] == 1):
        tri = mesh['tri'][face]
        ys = tri[:, 1]
        if float(ys.max()-ys.min()) < 1e-10:
            out[face] = 1 if float(ys.mean()) > 2. else 3
        else:
            radius = np.hypot(tri[:, 0], tri[:, 2]).mean()
            outer_at_y = .85-(.33/.95)*(ys.mean()-1.4)
            out[face] = 0 if radius > outer_at_y-.0175 else 2
    return out


def replay_original(mesh):
    """Independent replay of the original area sampler, before redistribution."""
    rng = np.random.default_rng(np.random.SeedSequence([1729, 1]))
    faces = np.flatnonzero(mesh['parts'] == 1)
    probability = mesh['areas'][faces]/mesh['areas'][faces].sum()
    bands = independent_bands(mesh)
    result = {}
    for index in range(260):
        face = int(rng.choice(faces, p=probability))
        q = rng.random(2)
        root = np.sqrt(q[0])
        result[f'p1:seed{index:04d}:layer0'] = dict(face=face,
            bary=np.array([1-root, root*(1-q[1]), root*q[1]]),
            band=int(bands[face]))
    return result


class ShadeSpacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = UNIT/'inputs/asset.json'
        cls.manifest, cls.files, cls.mesh, cls.old, cls.cfg = load_asset(cls.source)
        cls.prior_revision = revision(cls.old)
        cls.recipe = make_recipe(cls.manifest, cls.files, cls.mesh, cls.old,
                                 cls.cfg, cls.source)
        with patch.object(walker, 'generate_strokes',
                          side_effect=AssertionError('must not regenerate all parts')):
            with patch.object(walker, 'walk', wraps=walker.walk) as integration:
                cls.edited = generate(cls.mesh, cls.recipe)
                cls.calls = integration.call_args_list
        cls.repeated = generate(cls.mesh, cls.recipe)
        cls.original = replay_original(cls.mesh)
        cls.bands = independent_bands(cls.mesh)

    def test_named_mesh_and_independent_original_seed_band_identity(self):
        self.assertEqual(sha(self.files['mesh']), MESH_SHA256)
        np.testing.assert_array_equal(face_bands(self.mesh), self.bands)
        self.assertEqual(Counter(self.bands[self.bands >= 0]),
                         {0:192, 1:192, 2:192, 3:192})
        prior = {s['id']:s for s in self.old if s['part'] == 1}
        actual = {r['id']:r['band'] for r in self.recipe['original_seed_identity']}
        self.assertEqual(actual, {sid:r['band'] for sid,r in self.original.items()})
        for sid, seed in self.original.items():
            stroke = prior[sid]
            self.assertTrue(np.any((stroke['faces'] == seed['face'])
                & np.all(np.abs(stroke['bary']-seed['bary']) <= 1e-12, axis=1)))

    def test_repeated_generation_and_per_band_counts_are_deterministic(self):
        self.assertEqual(len(self.edited), 260)
        self.assertEqual(revision(self.edited), revision(self.repeated))
        expected = Counter(seed['band'] for seed in self.original.values())
        self.assertEqual(Counter(s['seed_band'] for s in self.edited), expected)
        self.assertNotEqual(revision(self.edited),
                            revision([s for s in self.old if s['part'] == 1]))
        for a,b in zip(self.edited, self.repeated):
            self.assertEqual(a['id'], b['id'])
            self.assertEqual(a['seed_metadata']['candidate_index'],
                             b['seed_metadata']['candidate_index'])
            np.testing.assert_array_equal(a['seed_bary'], b['seed_bary'])
            np.testing.assert_array_equal(a['faces'], b['faces'])
            np.testing.assert_array_equal(a['bary'], b['bary'])

    def test_only_260_shade_paths_walk_frozen_direction_length_and_step(self):
        self.assertEqual(len(self.calls), 520)
        self.assertEqual({c.args[3] for c in self.calls}, {1})
        self.assertEqual({c.args[4] for c in self.calls}, {'mixed'})
        self.assertEqual({c.args[5] for c in self.calls}, {0})
        self.assertEqual({c.args[6] for c in self.calls}, {0.})
        self.assertEqual({c.args[7] for c in self.calls}, {.16})
        self.assertEqual({c.args[8] for c in self.calls}, {.015})
        self.assertEqual(Counter(c.args[9] for c in self.calls), {-1:260, 1:260})

    def test_inks_ids_input_paths_and_reported_anchor_bands_are_preserved(self):
        prior = {s['id']:s for s in self.old if s['part'] == 1}
        self.assertEqual(set(prior), {s['id'] for s in self.edited})
        self.assertEqual(revision(self.old), self.prior_revision)
        self.assertEqual(self.recipe['lineage']['non_target_revision'],
                         revision([s for s in self.old if s['part'] != 1]))
        for stroke in self.edited:
            self.assertEqual(stroke['ink'], prior[stroke['id']]['ink'])
            self.assertEqual(stroke['seed_band'], self.original[stroke['id']]['band'])
            self.assertEqual(int(self.bands[stroke['seed_face']]), stroke['seed_band'])
            self.assertEqual(stroke['path_bands'],
                             sorted(set(map(int,self.bands[stroke['faces']]))))
            self.assertTrue(np.all(self.mesh['parts'][stroke['faces']] == 1))
            self.assertTrue(np.isfinite(stroke['bary']).all())
            self.assertGreaterEqual(float(stroke['bary'].min()), -1e-12)
            np.testing.assert_allclose(stroke['bary'].sum(axis=1), 1., atol=1e-12, rtol=0)
            self.assertTrue(np.any((stroke['faces'] == stroke['seed_face'])
                & np.all(stroke['bary'] == stroke['seed_bary'], axis=1)))
            points = np.einsum('ni,nij->nj',stroke['bary'],self.mesh['tri'][stroke['faces']])
            self.assertLessEqual(float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()),
                                 .32+1e-9)

    def test_periodic_selection_and_lowest_index_ties(self):
        faces = np.arange(4,dtype=np.int32)
        barys = np.tile([.2,.3,.5],(4,1))
        with patch('spacing_cli.band_candidates',return_value=(faces,barys,
                np.array([0.,0.,np.pi,np.pi]),np.full(4,.5))):
            chosen = select_band(self.mesh,0,2)
        self.assertEqual([s['candidate_index'] for s in chosen],[0,2])
        with patch('spacing_cli.band_candidates',return_value=(faces[:3],barys[:3],
                np.array([.01,2*np.pi-.01,np.pi]),np.full(3,.5))):
            chosen = select_band(self.mesh,0,2)
        indices = {s['candidate_index'] for s in chosen}
        self.assertIn(2,indices)
        self.assertEqual(len(indices & {0,1}),1)
        with patch('spacing_cli.band_candidates',side_effect=AssertionError('empty band')):
            self.assertEqual(select_band(self.mesh,0,0),[])

    def test_bad_hash_recipe_and_band_domain_rejected_before_walking(self):
        invalid = []
        for key,value in [('schema','wrong'),('part',3),('count',259),('seed',1730),
                          ('length_world',.31),('step_world',.02),('angle_deg',1.),
                          ('numpy_version','incorrect')]:
            bad = copy.deepcopy(self.recipe); bad[key] = value; invalid.append(bad)
        bad = copy.deepcopy(self.recipe)
        bad['generator_sha256']['legacy/core.py'] = '0'*64; invalid.append(bad)
        bad = copy.deepcopy(self.recipe)
        bad['placement']['candidate_multiplier'] = 32; invalid.append(bad)
        bad = copy.deepcopy(self.recipe)
        bad['original_seed_identity'][0]['id'] = bad['original_seed_identity'][1]['id']
        invalid.append(bad)
        for value in (float('nan'), True, 1.01):
            bad = copy.deepcopy(self.recipe);bad['original_seed_identity'][0]['ink'] = value
            invalid.append(bad)
        bad = copy.deepcopy(self.recipe)
        bad['original_seed_identity'][0]['band'] = (bad['original_seed_identity'][0]['band']+1)%4
        invalid.append(bad)
        with patch.object(walker,'walk',side_effect=AssertionError('must reject before walk')):
            for index,recipe in enumerate(invalid):
                with self.subTest(case=index), self.assertRaises(ValueError):
                    generate(self.mesh,recipe)
        self.assertEqual(self.recipe['generator_sha256'],generator_hashes())

    def test_bad_source_seed_and_non_434_domain_rejected(self):
        with self.assertRaises(ValueError):
            make_recipe(self.manifest,self.files,self.mesh,self.old[:-1],self.cfg,self.source)
        corrupt = copy.deepcopy(self.old)
        target = next(s for s in corrupt if s['part'] == 1)
        target['bary'][:] = [1.,0.,0.]
        with self.assertRaises(ValueError):
            make_recipe(self.manifest,self.files,self.mesh,corrupt,self.cfg,self.source)
        changed_cfg = copy.deepcopy(self.cfg)
        changed_cfg['strokes']['length_by_part']['1'] = .30
        with self.assertRaises(ValueError):
            make_recipe(self.manifest,self.files,self.mesh,self.old,changed_cfg,self.source)

    def test_cold_recipe_contains_no_target_path_and_authority_is_bounded(self):
        stale = copy.deepcopy(self.manifest)
        stale['recipe'] = {'path':'old_recipe.json','sha256':'0'*64}
        stale['path_lineage'] = {'obsolete':True}
        recipe = make_recipe(stale,self.files,self.mesh,self.old,self.cfg,self.source)
        for key in ('recipe','path_lineage','mesh','strokes','config'):
            self.assertNotIn(key,recipe['baseline_manifest'])
        self.assertEqual({frozenset(row) for row in recipe['original_seed_identity']},
                         {frozenset(('id','band','ink'))})
        for key in ('faces','bary','seed_face','seed_bary','target_paths'):
            self.assertNotIn(key,recipe)
        validate_recipe(recipe)
        for path in (UNIT,UNIT/'inputs',UNIT.parent/'unit_010/new_output'):
            with self.subTest(path=path),self.assertRaises((ValueError,FileExistsError)):
                destination(path)
        with self.assertRaises(FileNotFoundError):
            read_recipe(UNIT/'absent_recipe.json')
        with self.assertRaises(ValueError):
            bound_file(UNIT,dict(path=str(self.files['mesh']),sha256='0'*64))


if __name__ == '__main__':
    unittest.main(verbosity=2)
