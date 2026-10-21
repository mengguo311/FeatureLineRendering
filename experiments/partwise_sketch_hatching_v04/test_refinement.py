import runtime
import unittest
from pathlib import Path
import numpy as np
from refine_proxy import refine
from geometry import mesh_data

CONFIG = dict(iterations=8, positive_step=.5, negative_step=-.53,
              max_displacement=.012, pinned_regions=[1])


def normal_roughness(vertices, faces):
    tri = vertices[faces]
    normals = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-30)
    edges = {}
    for i, f in enumerate(faces):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges.setdefault(tuple(sorted((int(f[a]), int(f[b])))), []).append(i)
    pairs = np.array([v for v in edges.values() if len(v) == 2])
    return float(np.mean(1-np.einsum('ij,ij->i', normals[pairs[:, 0]], normals[pairs[:, 1]])))


class Refinement(unittest.TestCase):
    def test_real_chair_roughness_changes_with_bounded_pinned_geometry(self):
        path = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_001/proxy/mesh.npz')
        with np.load(path) as d:
            v, f, r = d['vertices'], d['faces'], d['face_regions']
        result, info = refine(v, f, r, CONFIG)
        self.assertLess(normal_roughness(result, f), normal_roughness(v, f)*.98,
                        'real noisy Chair must change; identity does not implement refinement')
        np.testing.assert_array_equal(result[np.unique(f[r == 1])], v[np.unique(f[r == 1])])
        self.assertLessEqual(np.linalg.norm(result-v, axis=1).max(), .01200000001)
        tri0, tri1 = v[f], result[f]
        n0 = np.cross(tri0[:, 1]-tri0[:, 0], tri0[:, 2]-tri0[:, 0])
        n1 = np.cross(tri1[:, 1]-tri1[:, 0], tri1[:, 2]-tri1[:, 0])
        self.assertTrue((np.einsum('ij,ij->i', n0, n1) > 0).all())
        self.assertTrue((np.linalg.norm(n1, axis=1) >= .2*np.linalg.norm(n0, axis=1)).all())
        self.assertGreater(info['pinned_vertices'], 0)

    def test_saved_face_labels_do_not_rethreshold_on_reload(self):
        v = np.array([[0, 0, .6], [1, 0, .6], [0, 1, .6]], float)
        m = mesh_data(v, np.array([[0, 1, 2]]), face_regions=np.array([2]))
        np.testing.assert_array_equal(m['regions'], [2])

    def test_open_disconnected_patches_never_weld_or_move_boundary(self):
        v = np.array([[0, 0, .5], [1, 0, .5], [0, 1, .5],
                      [0, 0, .501], [1, 0, .501], [0, 1, .501]], float)
        f = np.array([[0, 1, 2], [3, 4, 5]])
        result, info = refine(v, f, np.array([2, 2]), CONFIG)
        np.testing.assert_array_equal(result, v)


if __name__ == '__main__':
    unittest.main(verbosity=2)
