"""Frozen engineering regressions for the whole-lamp renderer interface.

These small rectangles isolate visibility and width contracts; they are not a
substitute for the separate whole-lamp evaluation.  Run this file with
``--backend old`` to apply identical assertions to the historical renderer.
The old adapter only maps the requested common width and selected IDs to its
API; it does not repair or alter rasterization.
"""

import argparse
from copy import deepcopy
import sys
import unittest

try:
    from . import common, renderer
except ImportError:
    import common
    import renderer

import numpy as np


BACKEND = "new"
VIEW = dict(azimuth=0.0, elevation=0.0, distance=4.5)
SIZE = 96


def fixture(occluder_part=None):
    """A rear plane at camera z=4, optionally occluded by a z=3.5 plane.

    Coordinates are prescribed in the output camera to make the assertions
    independent of a particular whole-lamp silhouette or stroke seed.
    """
    camera = common.core.camera(size=SIZE, focal=96.0, **VIEW)
    vertices, faces, parts = [], [], []

    def rectangle(x0, y0, x1, y1, depth, part):
        uv = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)
        offset = len(vertices)
        vertices.extend(common.core.backproject(uv, np.full(4, depth), camera))
        faces.extend([[offset, offset + 1, offset + 2], [offset, offset + 2, offset + 3]])
        parts.extend([part, part])

    rectangle(8, 8, 88, 88, 4.0, 1)
    if occluder_part is not None:
        rectangle(48, 16, 80, 80, 3.5, occluder_part)
    mesh = common.core.finalize_mesh(vertices, faces, parts)
    # Explicit face transition at the rear quad diagonal.  Both representations
    # of that shared point have identical world position.
    uv = np.array([[20., 48.], [48., 48.], [48., 48.], [72., 48.]])
    xyz = common.core.backproject(uv, np.full(4, 4.0), camera)
    owner_faces = np.array([1, 1, 0, 0], dtype=np.int32)
    bary = np.stack([common.core.barycentric(mesh, int(fi), x)
                     for fi, x in zip(owner_faces, xyz)])
    strokes = [dict(id="p1:fixture:layer0", part=1, faces=owner_faces,
                    bary=bary, ink=0.8, style="mixed", layer=0, angle=0.0)]
    cfg = {
        "renderer": {
            "resolution": [SIZE, SIZE], "supersample": 4, "focal_px": 96.0,
            "visibility_tolerance_world": 0.006,
            "contour_width_px": 0.8, "ring_width_px": 0.65,
        },
        "strokes": {"screen_width_px": 1.0},
        "widths_by_part": {"1": 1.0, "2": 1.0, "3": 1.0},
        "asset": {"profiles_ry": {}},
    }
    return mesh, strokes, cfg


def draw(mesh, strokes, cfg, width=1.0, selected_ids=None):
    cfg = deepcopy(cfg)
    cfg["widths_by_part"] = {str(p): float(width) for p in (1, 2, 3)}
    if BACKEND == "old":
        cfg["strokes"]["screen_width_px"] = float(width)
        if selected_ids is not None:
            selected = set(selected_ids)
            strokes = [s for s in strokes if s["id"] in selected]
        return common.core.render(mesh, strokes, cfg, structure=False, **VIEW)
    return renderer.render(mesh, strokes, cfg, structure=False,
                           selected_ids=selected_ids, **VIEW)


class RendererContracts(unittest.TestCase):
    def test_different_part_foreground_hides_full_width(self):
        mesh, strokes, cfg = fixture(occluder_part=2)
        output = draw(mesh, strokes, cfg, width=6.0)
        yy, xx = np.mgrid[:SIZE, :SIZE]
        # One pixel in from the true foreground edge excludes pixels whose
        # subpixel footprints legitimately straddle both visible surfaces.
        interior = (output["parts"] == 2) & (xx >= 49) & (xx <= 78) & (yy >= 18) & (yy <= 78)
        self.assertTrue(interior.any())
        self.assertGreater(float(output["hatch"][44:53, 22:44].sum()), 20.0,
                           "the visible rear segment must actually render")
        leakage = float(output["hatch"][interior].max())
        self.assertLessEqual(leakage, 1e-14,
                             f"rear ribbon leaked into foreground interior: max ink={leakage}")

    def test_same_part_foreground_still_requires_depth_visibility(self):
        mesh, strokes, cfg = fixture(occluder_part=1)
        output = draw(mesh, strokes, cfg, width=6.0)
        yy, xx = np.mgrid[:SIZE, :SIZE]
        interior = (xx >= 49) & (xx <= 78) & (yy >= 18) & (yy <= 78)
        self.assertTrue(np.all(output["depth"][interior] < 3.75),
                        "the interior must be on the nearer rectangle")
        leakage = float(output["hatch"][interior].max())
        self.assertLessEqual(leakage, 1e-14,
                             f"same-part occluder failed the depth gate: max ink={leakage}")

    def test_width_increase_adds_ink_without_moving_geometry(self):
        mesh, strokes, cfg = fixture()
        before = common.core.stroke_digest(strokes)
        narrow = draw(mesh, strokes, cfg, width=1.0)
        wide = draw(mesh, strokes, cfg, width=2.0)
        self.assertGreater(float(narrow["hatch"].sum()), 20.0)
        self.assertGreater(float(wide["hatch"].sum()), 1.5 * float(narrow["hatch"].sum()))
        self.assertEqual(before, common.core.stroke_digest(strokes))

    def test_fractional_width_changes_coverage(self):
        mesh, strokes, cfg = fixture()
        narrow = draw(mesh, strokes, cfg, width=0.75)["hatch"]
        wide = draw(mesh, strokes, cfg, width=1.25)["hatch"]
        self.assertTrue(np.isfinite(narrow).all() and np.isfinite(wide).all())
        self.assertGreater(float(narrow.sum()), 0.0)
        self.assertGreater(float(wide.sum()), 1.1 * float(narrow.sum()))
        self.assertFalse(np.array_equal(narrow, wide), "fractional widths must not be truncated to one integer")

    def test_no_edit_is_bitwise_deterministic_and_inputs_unchanged(self):
        mesh, strokes, cfg = fixture(occluder_part=2)
        digest = common.core.stroke_digest(strokes)
        cfg_before = deepcopy(cfg)
        first = draw(mesh, strokes, cfg, width=1.25)
        second = draw(mesh, strokes, cfg, width=1.25)
        for key in ("image", "hatch", "parts", "depth"):
            np.testing.assert_array_equal(first[key], second[key], err_msg=key)
        self.assertEqual(digest, common.core.stroke_digest(strokes))
        self.assertEqual(cfg, cfg_before)
        for key in ("image", "hatch"):
            self.assertEqual(first[key].shape, (SIZE, SIZE))
            self.assertTrue(np.isfinite(first[key]).all())
            self.assertGreaterEqual(float(first[key].min()), 0.0)
            self.assertLessEqual(float(first[key].max()), 1.0)

    def test_empty_id_selection_contains_no_hatch(self):
        mesh, strokes, cfg = fixture()
        output = draw(mesh, strokes, cfg, selected_ids=set())
        self.assertEqual(float(output["hatch"].sum()), 0.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--backend", choices=("new", "old"), default="new")
    options, remaining = parser.parse_known_args()
    BACKEND = options.backend
    unittest.main(argv=[sys.argv[0], *remaining], verbosity=2)
