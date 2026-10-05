import unittest
import json
from data_access import frames,training_view
from runtime import EXP

class IsolationTests(unittest.TestCase):
    def test_controller_refuses_test_and_path(self):
        for group in ('test','path'):
            with self.assertRaises(PermissionError):frames(group)
            with self.assertRaises(PermissionError):training_view('panels_high',{'id':group+'_000'},group)
    def test_prefrozen_partitions_distinct(self):
        splits=json.loads((EXP/'data/manifests/cameras.json').read_text())['splits']
        self.assertEqual([len(splits[k]) for k in ('train','val','test','path')],[24,6,12,36])
        keys={k:{json.dumps(f['transform_matrix']) for f in v} for k,v in splits.items()}
        for a in keys:
            for b in keys:
                if a!=b:self.assertFalse(keys[a]&keys[b])
        arc=[f['theta_deg'] for f in splits['test'][6:]]
        self.assertEqual(arc,[22.,24.,26.,28.,30.,32.])
