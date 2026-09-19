import unittest
import numpy as np
import cc_visibility as v

class VisibilityDiagnostic(unittest.TestCase):
    def test_strata_partition_without_excusing_all_in_frame_errors(self):
        class Layers:
            def query(self,uv,z,delta):
                return np.array([.9,.9,.5,.05,.9]),np.array([1,0,1,1,1],bool)
        sample=dict(uv=np.zeros((5,2)),inside=[1,1,1,1,0],joint=[1,0,1,0,0],projected_weights=[2,3,4,5,0])
        r=v.stratify(sample,np.ones(5),Layers(),.01)
        self.assertEqual(sum(x['samples'] for x in r['strata'].values()),5)
        self.assertEqual(r['strata']['hidden']['projected_length'],5)
        self.assertEqual(r['strata']['visible_supported']['joint_fraction'],1)
        self.assertEqual(r['strata']['visible_unsupported']['joint_fraction'],0)
        self.assertIsNone(r['strata']['out_of_frame']['joint_fraction'])
        self.assertEqual(r['all_in_frame']['joint_fraction'],6/14)
        self.assertEqual(r['classifications'],['visible_supported','visible_unsupported','uncertain','hidden','out_of_frame'])

    def test_empty_strata_are_unknown_not_success(self):
        class Layers:
            def query(self,*args):return np.array([]),np.array([],bool)
        r=v.stratify(dict(uv=np.empty((0,2)),inside=[],joint=[],projected_weights=[]),np.array([]),Layers(),.01)
        self.assertIsNone(r['all_in_frame']['joint_fraction'])
        self.assertEqual(sum(x['samples'] for x in r['strata'].values()),0)
