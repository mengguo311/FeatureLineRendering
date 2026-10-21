"""Scene-specific region rules must survive extraction and asset loading."""
import runtime
import unittest
import numpy as np
from geometry import region_ids, mesh_data


class SceneRegions(unittest.TestCase):
    def test_lego_height_cuts_are_explicit_and_saved(self):
        centers=np.array([[0,0,-.3],[0,0,0.],[0,0,.3],[0,0,.6]])
        labels=region_ids(centers, [-.2,.45])
        np.testing.assert_array_equal(labels,[1,2,2,3])
        # The upper-middle sample differs from the legacy Chair rule.
        self.assertNotEqual(labels[2],region_ids(centers)[2])
        vertices=np.concatenate([p+np.array([[0,0,0],[.1,0,0],[0,.1,0]]) for p in centers])
        faces=np.arange(12).reshape(4,3)
        mesh=mesh_data(vertices,faces,labels)
        np.testing.assert_array_equal(mesh['regions'],labels)

    def test_bad_region_rules_rejected(self):
        for cuts in ([.4,-.2],[0,0],[np.nan,.4],[.2]):
            with self.assertRaises(ValueError):region_ids(np.zeros((1,3)),cuts)


if __name__=='__main__':unittest.main(verbosity=2)
