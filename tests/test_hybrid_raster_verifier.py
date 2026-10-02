"""Mutated synthetic artifacts must not pass the independent final verifier."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.verify_hybrid_raster_evidence_v2 import verify_arrays, verify_native
from src.hybrid_raster_evidence import compute_evidence, fit_normalization, raw_fields
from tests.test_hybrid_raster_evidence import synthetic_raw


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.raw = synthetic_raw()
        self.result = compute_evidence(self.raw, fit_normalization([raw_fields(self.raw)]))

    def verify(self, result):
        return verify_arrays(result['arrays'], result['provenance'], result['diagnostics'], (16, 20))

    def test_valid_arrays_then_corrupted_complement_are_distinguished(self):
        self.assertTrue(self.verify(self.result)['passed'])
        corrupt = copy.deepcopy(self.result)
        corrupt['arrays']['C'][5, 5] = 0
        with self.assertRaises(ValueError): self.verify(corrupt)

    def test_provenance_background_and_matched_ink_tampering_rejected(self):
        for which in ('provenance', 'background', 'matching'):
            with self.subTest(which=which):
                corrupt = copy.deepcopy(self.result)
                if which == 'provenance': corrupt['provenance']['arm_bits'][5, 5] ^= 1
                elif which == 'background': corrupt['arrays']['B'][0, 0] = .3
                else: corrupt['arrays']['B_matched'] *= .5
                with self.assertRaises(ValueError): self.verify(corrupt)

    def test_native_headers_ids_mass_and_nonfinite_weights(self):
        base = Path('out/hybrid_raster_evidence_v2/test_tmp'); base.mkdir(parents=True, exist_ok=True)
        raw = {k:v for k,v in self.raw.items() if isinstance(v, np.ndarray)}
        raw['radii'] = np.zeros(100, np.int32)
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            path = Path(tmp) / 'native.npz'
            np.savez_compressed(path, **raw)
            self.assertTrue(verify_native(path, (16, 20), 100)['passed'])
            for which in ('id', 'weight', 'nonfinite'):
                changed = {k:v.copy() for k,v in raw.items()}
                if which == 'id': changed['topk_id'][5, 5, 0] = 101
                elif which == 'weight': changed['topk_w'][5, 5] = [.6, .3, .1, .05]
                else: changed['topk_w'][5, 5, 0] = np.nan
                np.savez_compressed(path, **changed)
                with self.subTest(which=which), self.assertRaises(ValueError):
                    verify_native(path, (16, 20), 100)

    def test_native_geometry_nonfinite_requires_explicit_full_mode(self):
        base = Path('out/hybrid_raster_evidence_v2/test_tmp'); base.mkdir(parents=True, exist_ok=True)
        raw = {k:v for k,v in self.raw.items() if isinstance(v, np.ndarray)}
        raw['radii'] = np.zeros(100, np.int32); raw['depth'][5, 5] = np.nan
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            path = Path(tmp) / 'native.npz'; np.savez_compressed(path, **raw)
            report = verify_native(path, (16, 20), 100)
            self.assertFalse(report['all_native_finite_redecoded'])
            with self.assertRaises(ValueError): verify_native(path, (16, 20), 100, full_native=True)


if __name__ == '__main__': unittest.main()
