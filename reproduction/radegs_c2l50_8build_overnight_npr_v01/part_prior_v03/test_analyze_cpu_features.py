import unittest
import numpy as np
from analyze_cpu_features import cluster_summary

class ClusterSummaryTests(unittest.TestCase):
    def test_counts_match_rows_and_quartiles(self):
        s=cluster_summary(np.array([0,1,1,2,2,2,0,1],dtype='u1'),np.arange(8,dtype='f4'))
        self.assertEqual(s['counts'],[2,3,3])
        self.assertEqual([sum(row) for row in s['z_quartile_by_cluster']],[2,3,3])
    def test_rejects_row_mismatch(self):
        with self.assertRaises(ValueError):
            cluster_summary(np.array([0]),np.array([1,2]))

if __name__=='__main__':
    unittest.main()
