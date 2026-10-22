"""Real saved Chair checks for an existing algorithm on a newly frozen region."""
import runtime
from runtime import sha,js
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from unit019_run import U,protocol,hashes
from demo import load_asset,edit
from local_refinement import refine_asset

class ChairRefinement(unittest.TestCase):
    def test_01_real_candidate_locality_and_cold_saved_anchors(self):
        p=protocol();asset=Path(p['asset']);before,paths,meta=load_asset(asset)
        with patch('demo.generate_region',side_effect=AssertionError('cold load regenerated')):
            after,new,saved=load_asset(U/'assets/refined')
        np.testing.assert_array_equal(before['faces'],after['faces'])
        np.testing.assert_array_equal(before['regions'],after['regions'])
        fixed=np.unique(before['faces'][before['regions']!=2])
        np.testing.assert_array_equal(before['vertices'][fixed],after['vertices'][fixed])
        displacement=np.linalg.norm(after['vertices']-before['vertices'],axis=1)
        self.assertGreater(int((displacement>1e-12).sum()),0)
        self.assertLessEqual(displacement.max(),p['refinement']['max_displacement']+1e-12)
        self.assertFalse(np.array_equal(paths[2]['points'],new[2]['points']))
        for region in (1,3):self.assertEqual(sha(asset/f'region_{region}.npz'),sha(U/f'assets/refined/region_{region}.npz'))
        n0=np.cross(before['tri'][:,1]-before['tri'][:,0],before['tri'][:,2]-before['tri'][:,0])
        n1=np.cross(after['tri'][:,1]-after['tri'][:,0],after['tri'][:,2]-after['tri'][:,0])
        self.assertTrue((np.einsum('ij,ij->i',n0,n1)>0).all())
        self.assertTrue((np.linalg.norm(n1,axis=1)>=.2*np.linalg.norm(n0,axis=1)).all())
        self.assertEqual(meta['styles'],saved['styles'])
        self.assertEqual(hashes(asset),p['inputs'])
        probe,edited,edited_meta=load_asset(U/'assets/style_probe')
        self.assertEqual(edited_meta['styles']['2']['angle'],65.)
        np.testing.assert_array_equal(after['vertices'],probe['vertices'])
        for region in (1,3):self.assertEqual(sha(U/f'assets/refined/region_{region}.npz'),sha(U/f'assets/style_probe/region_{region}.npz'))
        js(U/'metrics/REAL_ASSET_TEST.json',dict(same_topology_and_labels=True,non_target_vertices_and_paths_exact=True,
            saved_anchors_load_without_regeneration=True,orientation_and_area_guards=True,displacement_max=float(displacement.max()),
            target_paths_changed=True,continued_local_angle_edit=True,source_inputs_unchanged=True))

    def test_02_rejected_region_or_unbounded_config_is_atomic(self):
        p=protocol();out=U/'test_work/rejected'
        for region,config in [(9,p['refinement']),(2,dict(p['refinement'],iterations=0)),
                              (2,dict(p['refinement'],max_displacement=float('nan'))),
                              (2,dict(p['refinement'],pinned_regions=[]))]:
            with self.assertRaises(ValueError):refine_asset(p['asset'],out,region,config)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main(verbosity=2)
