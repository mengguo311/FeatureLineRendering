import runtime
import unittest,tempfile
from pathlib import Path
from stage_cache import cached_opacity,CheckpointPause
from path_control import match_nonlinear

class StageCacheTests(unittest.TestCase):
    def test_resume_matches_uninterrupted_matching_exactly(self):
        effect=lambda arm,x: (2 if arm=='a' else 5)*x*x
        expected=match_nonlinear(['a','b'],effect)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cache.json';interruptions=0
            for _ in range(10):
                try:
                    actual=match_nonlinear(['a','b'],cached_opacity(path,effect,4));break
                except CheckpointPause:interruptions+=1
            self.assertGreater(interruptions,0)
            self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
