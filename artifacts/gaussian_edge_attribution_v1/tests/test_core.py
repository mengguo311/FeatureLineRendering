import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('edge_core', ROOT / 'code/core.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
CFG = json.loads((ROOT / 'code/config.json').read_text())


def raw(ids, weights, alpha=None, depths=None):
    ids = np.asarray(ids, np.int64)
    weights = np.asarray(weights, np.float32)
    if ids.ndim == 1:
        ids, weights = ids[None, None], weights[None, None]
    h, w, _ = ids.shape
    alpha = weights.sum(-1) if alpha is None else np.broadcast_to(alpha, (h, w)).copy()
    return dict(topk_id=ids, topk_w=weights, alpha=alpha,
                topk_depth=np.where(ids >= 0, 2., 0.).astype(np.float32) if depths is None else np.asarray(depths, np.float32),
                depth=np.full((h, w), 2., np.float32), median_depth=np.full((h, w), 2., np.float32),
                rgb=np.zeros((h, w, 3), np.float32))


def evidence(h, w, value):
    return {**{k: np.full((h, w), value, np.float32) for k in core.CLASSES},
            'orientation_x': np.ones((h, w, 3), np.float32),
            'orientation_y': np.zeros((h, w, 3), np.float32)}


class ContributionTests(unittest.TestCase):
    def test_blending_original_transmittance_and_background(self):
        r = raw([0, 1, -1, -1], [.3, .2, 0, 0], alpha=.8)
        p = core.project(r, scores=np.array([1., .5]), selected_ids=[1])
        self.assertAlmostEqual(float(p['attribute'][0, 0]), .4, places=6)
        self.assertAlmostEqual(float(p['conditional_attribute'][0, 0]), .5, places=6)
        self.assertAlmostEqual(float(p['selected_mass'][0, 0]), .2, places=6)
        self.assertAlmostEqual(float(p['omitted_mass'][0, 0]), .3, places=6)

    def test_more_than_four_and_empty_ids(self):
        r = raw([0, 1, 2, 3, 4, -1], [.3, .2, .1, .05, .02, 0], alpha=.7)
        p = core.project(r, scores=np.ones(5), selected_ids=[])
        self.assertAlmostEqual(float(p['attribute'][0, 0]), .67, places=6)
        self.assertEqual(float(p['selected_mass'][0, 0]), 0)
        empty = core.project(raw([-1]*4, [0]*4), scores=np.zeros(5), selected_ids=[])
        self.assertEqual(float(empty['conditional_attribute'][0, 0]), 0)

    def test_original_id_permutation(self):
        r = raw([0, 1, -1, -1], [.3, .2, 0, 0])
        a = core.project(r, scores=np.array([.2, .8]))['attribute']
        r['topk_id'][r['topk_id'] == 0] = 3
        r['topk_id'][r['topk_id'] == 1] = 0
        b = core.project(r, scores=np.array([.8, 0., 0., .2]))['attribute']
        np.testing.assert_allclose(a, b)

    def test_full_grid_denominator_and_size_bias(self):
        r = raw(np.array([[[0,1], [0,1]]]), np.array([[[.6,.2],[.6,.2]]]))
        e = evidence(1, 2, 0)
        for c in core.CLASSES:
            e[c][0, 0] = 1
        v = core.view_statistics(r, e, 3, CFG, with_side=False)
        a = core.aggregate_views([v, v], CFG)
        np.testing.assert_allclose(a['baseline_union'][:2], [.5,.5])
        self.assertAlmostEqual(v['denominator'][0], 1.2, places=6)
        self.assertEqual(a['support_view_count'][2], 0)
        self.assertTrue(a['unknown'][2])
        self.assertFalse(a['eligible'][1])
        np.testing.assert_allclose(v['positive_mass'][:, 3] + v['nonedge_mass'][:, 3], v['denominator'])

    def test_per_view_equal_mass_normalization(self):
        one = core.view_statistics(raw([0],[1.]), evidence(1,1,1), 1, CFG, with_side=False)
        many = core.view_statistics(raw(np.zeros((1,9,1),int), np.ones((1,9,1))), evidence(1,9,0), 1, CFG, with_side=False)
        a = core.aggregate_views([one,many], CFG)
        self.assertAlmostEqual(a['baseline_union'][0], .5)

    def test_overlap_coalesces_repeated_ids(self):
        result = core.contributor_overlap(np.array([[2,2,3]]), np.array([[.1,.2,.1]]), np.array([[2,3,-1]]), np.array([[.3,.1,0]]))
        np.testing.assert_allclose(result, [1.], atol=1e-6)

    def test_side_collision_bounded_and_front_only(self):
        ids = np.broadcast_to([0,1], (9,9,2)).copy()
        weights = np.broadcast_to([.5,.2], (9,9,2)).copy()
        r = raw(ids, weights, depths=np.broadcast_to([1.,2.],(9,9,2)))
        e = evidence(9,9,1)
        v = core.view_statistics(r,e,2,CFG)
        self.assertTrue(np.all(v['side_numerator'] <= v['denominator'][:,None]+1e-6))
        self.assertTrue(np.all(v['side_numerator'][1] == 0))

    def test_outline_deposition_foreground_not_background(self):
        r = raw(np.zeros((9,13,1),int), np.ones((9,13,1),np.float32)*.8)
        r['alpha'][:,:6] = .02
        r['topk_w'][:,:6] = .02
        e = evidence(9,13,0)
        e['outline'][:,6] = 1
        e['union'][:,6] = 1
        side, diag = core.side_evidence(r,e,CFG)
        self.assertTrue(np.all(side[:,:6,:,2] == 0))

    def test_deterministic_tier_and_matched_random(self):
        n=100
        a = dict(eligible=np.ones(n,bool), raw_denominator=np.arange(n)+1., support_view_count=np.ones(n,int)*3,
                 enhanced_union=np.ones(n))
        tiers=core.rank_tiers(a,CFG)
        np.testing.assert_array_equal(tiers['1'],[0])
        np.testing.assert_array_equal(tiers['3'],[0,1,2])
        x=core.visibility_matched_random(a,tiers['30'],1729,CFG)
        y=core.visibility_matched_random(a,tiers['30'],1729,CFG)
        np.testing.assert_array_equal(x,y)
        self.assertEqual(len(np.unique(x)),30)
        bins=core.visibility_bins(a,CFG)
        np.testing.assert_array_equal(np.bincount(bins[x]),np.bincount(bins[tiers['30']]))

    def test_corruption_rejected(self):
        r=raw([0,-1],[.2,.1],alpha=.5)
        with self.assertRaises(ValueError): core.validate_raw(r,1)
        r=raw([0],[.8],alpha=.5)
        with self.assertRaises(ValueError): core.validate_raw(r,1)
        r=raw([0],[.2]); r['rgb'][0,0,0]=np.nan
        with self.assertRaises(ValueError): core.validate_raw(r,1)

    def test_asset_seal_and_C_cannot_aggregate(self):
        a={'ids':np.arange(3),'scores':np.array([.1,.2,.3])}
        seal=core.asset_hash(a)
        core.verify_asset(a,seal)
        a['scores'][0]=.9
        with self.assertRaises(ValueError): core.verify_asset(a,seal)
        v=core.view_statistics(raw([0],[1]), evidence(1,1,1), 1, CFG,with_side=False)
        v['split']='C'
        with self.assertRaises(ValueError):core.aggregate_views([v],CFG)

    def test_evidence_independent_of_ids_and_normalization_sealed(self):
        r=raw(np.zeros((13,13,1),int),np.ones((13,13,1),np.float32))
        r['rgb'][:,7:]=1
        f=core.evidence_fields(r,CFG)
        norm=core.fit_normalization([f],CFG)
        e=core.compute_evidence(f,norm,CFG)
        r['topk_id'][:]=27
        f2=core.evidence_fields(r,CFG)
        e2=core.compute_evidence(f2,norm,CFG)
        np.testing.assert_array_equal(e['color'],e2['color'])
        self.assertGreater(e['color'].sum(),0)
        bad=dict(CFG);bad['gaussian_sigma']=2
        with self.assertRaises(ValueError):core.compute_evidence(f2,norm,bad)

    def test_null_shift_zero_fills_without_wrap(self):
        e=evidence(80,100,0)
        e['color'][0,0]=.75
        e['color'][79,99]=1
        e['union']=e['color'].copy()
        shifted=core.null_evidence(e,CFG)
        self.assertEqual(float(shifted['color'][37,53]),.75)
        self.assertEqual(float(shifted['color'].sum()),.75)
        self.assertTrue(np.all(shifted['color'][:37]==0))
        self.assertTrue(np.all(shifted['orientation_x'][:37]==0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
