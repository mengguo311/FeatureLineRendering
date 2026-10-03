"""A matching working-tree hash must never stand in for the upstream Git pin."""
import unittest
from verify_acquisition import verify_source_bytes


class PinnedSourceTests(unittest.TestCase):
    def test_dirty_upstream_renderer_is_rejected_against_git_blob(self):
        pinned='rendered_image, radii = rasterizer()\n'
        dirty='rendered_image, radii, _depth, _alpha = rasterizer()\n'
        self.assertTrue(verify_source_bytes('gaussian_renderer/__init__.py',pinned,pinned))
        with self.assertRaises(ValueError):verify_source_bytes('gaussian_renderer/__init__.py',pinned,dirty)


if __name__=='__main__':unittest.main()
