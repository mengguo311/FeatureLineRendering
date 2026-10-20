"""Frozen round_002 geometry regressions; identical assertions for old/new walkers."""
import argparse
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--backend", choices=("old", "new"), required=True)
args, remaining = parser.parse_known_args()
core = importlib.import_module("core" if args.backend == "old" else "core_walk_v2")
CFG = json.loads((Path(__file__).resolve().parents[2] /
                  "docs/partwise_sketch_hatching/round_001/PROTOCOL.json").read_text())


def crease(parts=(2, 2), degrees=120.):
    theta = np.deg2rad(degrees)
    return core.finalize_mesh(
        [[-1, 0, 0], [1, 0, 0], [0, 1, 0],
         [0, -np.cos(theta), -np.sin(theta)]],
        [[0, 1, 2], [1, 0, 3]], parts)


def path(mesh, faces, bary):
    return np.einsum("ni,nij->nj", np.array(bary), mesh["tri"][faces])


class WalkProgressTests(unittest.TestCase):
    def test_obtuse_crease_makes_full_geometric_progress(self):
        mesh = crease()
        faces, bary = core.walk(mesh, 0, np.array([.4, .4, .2]), 2,
                                "parallel", 0, 0., .6, .05, -1)
        xyz = path(mesh, faces, bary)
        # A developed straight path travels .2 to the hinge and .4 on the flap.
        np.testing.assert_allclose(xyz[-1], [0., .2, -np.sqrt(3)*.2], atol=1e-9)
        self.assertAlmostEqual(float(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum()), .6, places=9)
        transitions = np.array(faces)[np.r_[True, np.diff(faces) != 0]]
        np.testing.assert_array_equal(transitions, [0, 1])
        self.assertLess(len(faces), 20)

    def test_part_boundary_stops_at_exact_hinge(self):
        mesh = crease(parts=(2, 3))
        faces, bary = core.walk(mesh, 0, np.array([.4, .4, .2]), 2,
                                "parallel", 0, 0., .6, .05, -1)
        xyz = path(mesh, faces, bary)
        np.testing.assert_allclose(xyz[-1], [0, 0, 0], atol=1e-10)
        self.assertTrue(np.all(mesh["parts"][faces] == 2))
        self.assertAlmostEqual(np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum(), .2, places=9)

    def test_crease_geometry_unchanged_by_field_sign(self):
        mesh = crease()
        native_field = core.field
        outputs = []
        for polarity in (1, -1):
            def unoriented(*a):
                return polarity*native_field(*a)
            with patch.object(core, "field", side_effect=unoriented):
                f, b = core.walk(mesh, 0, np.array([.4, .4, .2]), 2,
                                 "parallel", 0, 0., .6, .05, -polarity)
            outputs.append(path(mesh, f, b))
        np.testing.assert_allclose(outputs[0], outputs[1], atol=1e-12)

    def test_frozen_lamp_worst_paths_have_no_short_edge_cycles(self):
        mesh = core.make_lamp(CFG["asset"])
        # Chosen only from the sealed round_001 PATH_AUDIT, before this repair.
        cases = (("mixed", 2, 21, 0), ("parallel", 3, 86, 0), ("cross", 1, 193, 1))
        for style, part, seed, layer in cases:
            rng = np.random.default_rng(np.random.SeedSequence([CFG["seed"], part]))
            candidates = np.flatnonzero(mesh["parts"] == part)
            prob = mesh["areas"][candidates]; prob = prob/prob.sum()
            for _ in range(seed+1):
                face = int(rng.choice(candidates, p=prob))
                q = rng.random(2); sq = np.sqrt(q[0])
                bary = np.array([1-sq, sq*(1-q[1]), sq*q[1]])
            for sign in (-1, 1):
                f, b = core.walk(mesh, face, bary, part, style, layer, 0.,
                                 CFG["strokes"]["length_by_part"][str(part)]/2,
                                 CFG["strokes"]["step_world"], sign)
                xyz = path(mesh, f, b)
                arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(xyz, axis=0), axis=1))]
                indices = np.flatnonzero(np.r_[True, np.diff(f) != 0])
                trans = np.asarray(f)[indices]
                bad = (trans[:-2] == trans[2:]) & ((arc[indices[2:]]-arc[indices[:-2]]) < 1e-6)
                self.assertEqual(int(bad.sum()), 0, (style, part, seed, layer, sign))
                self.assertLess(len(f), 200, (style, part, seed, layer, sign))
                self.assertTrue(np.all(mesh["parts"][f] == part))
                self.assertGreaterEqual(np.asarray(b).min(), -1e-10)
                np.testing.assert_allclose(np.sum(b, axis=1), 1., atol=1e-12)


if __name__ == "__main__":
    unittest.main(argv=["test_walk_progress.py"]+remaining, verbosity=2)
