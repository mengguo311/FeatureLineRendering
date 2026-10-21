"""Optional historical caches must never become a fake replay pass."""
import runtime
import unittest
from pathlib import Path
import numpy as np
from build_proxy import source_cache_diagnostic


class SourceCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=runtime.OUTPUT_ROOT/'units/unit_003/source_model/frame_000.npz'
        with np.load(cls.path) as data:
            cls.real={k:data[k] for k in data.files}

    def test_absent_optional_cache_is_explicitly_unverified(self):
        result=source_cache_diagnostic(self.real,None)
        self.assertEqual(result['status'],'NOT_AVAILABLE')
        self.assertIsNone(result['all_arrays_exact'])

    def test_supplied_missing_cache_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            source_cache_diagnostic(self.real,self.path.with_name('missing_cache.npz'))

    def test_real_saved_source_replay_and_difference(self):
        result=source_cache_diagnostic(self.real,self.path)
        self.assertTrue(result['all_arrays_exact'])
        changed=dict(self.real,rgb=self.real['rgb'].copy())
        changed['rgb'][100,100,0]+=.1
        result=source_cache_diagnostic(changed,self.path)
        self.assertFalse(result['all_arrays_exact'])
        self.assertGreater(result['max_abs_errors']['rgb'],.09)


if __name__=='__main__':unittest.main(verbosity=2)
