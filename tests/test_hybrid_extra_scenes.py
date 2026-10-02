import unittest
from hybrid_overlay_video import validate_scene

class ExpandedSceneTests(unittest.TestCase):
    def test_existing_and_new_scenes_are_supported(self):
        for scene in ('lego','chair','drums','ficus'):
            self.assertEqual(validate_scene(scene),scene)
    def test_unknown_scene_rejected(self):
        with self.assertRaises(ValueError):validate_scene('unknown')

if __name__=='__main__':unittest.main()
