"""Behavior checks on the actual saved Lego bucket, before delivery renders."""
import runtime
from runtime import OUTPUT_ROOT,sha
from pathlib import Path
import json, unittest
from unittest.mock import patch
import numpy as np
from demo import load_asset,edit
from refine_proxy import refine

UNIT=OUTPUT_ROOT/'units/unit_015'
P=json.loads((UNIT/'PROTOCOL.json').read_text())
ASSET=Path(P['asset'])

class LocalRefinement(unittest.TestCase):
    def test_01_region_ids_do_not_change_refinement(self):
        mesh,_,_=load_asset(ASSET);r=mesh['regions'].copy()
        config=dict(P['refinement'],pinned_regions=[1,2,3])
        a,_=refine(mesh['vertices'],mesh['faces'],r,config)
        r[r==4]=7
        b,_=refine(mesh['vertices'],mesh['faces'],r,config)
        np.testing.assert_array_equal(a,b,err_msg='A saved region ID is not a smoothing parameter')

    def test_02_saved_asset_preserves_other_regions_and_reanchors_target(self):
        from local_refinement import refine_asset
        out=UNIT/'test_work/refined'
        result=refine_asset(ASSET,out,4,P['refinement'])
        old,paths,meta=load_asset(ASSET)
        with patch('demo.generate_region',side_effect=AssertionError('cold load regenerated')):
            new,after,saved=load_asset(out)
        np.testing.assert_array_equal(old['faces'],new['faces'])
        np.testing.assert_array_equal(old['regions'],new['regions'])
        fixed=np.unique(old['faces'][old['regions']!=4])
        np.testing.assert_array_equal(old['vertices'][fixed],new['vertices'][fixed])
        displ=np.linalg.norm(new['vertices']-old['vertices'],axis=1)
        self.assertGreater(int((displ>1e-12).sum()),0)
        self.assertLessEqual(displ.max(),P['refinement']['max_displacement']+1e-12)
        self.assertFalse(np.array_equal(paths[4]['points'],after[4]['points']))
        for name in ['selection_4.npz']+[f'region_{r}.npz' for r in (1,2,3)]:
            self.assertEqual(sha(ASSET/name),sha(out/name))
        self.assertEqual(meta['styles'],saved['styles'])
        self.assertEqual(meta['region_history'],saved['region_history'])
        self.assertEqual(result['regenerated_layers'],[0,1])
        self.assertEqual(saved['geometry_history'][-1]['parent_mesh_sha256'],meta['mesh_sha256'])
        self.assertEqual(saved['geometry_history'][-1]['mesh_sha256'],saved['mesh_sha256'])
        self.assertTrue(result['oriented_area_guard_pass'])
        probe=UNIT/'test_work/style_probe';edit(out,probe,4,{'angle':50.})
        _,_,probe_meta=load_asset(probe)
        self.assertEqual(probe_meta['styles']['4']['angle'],50.)
        for r in (1,2,3):self.assertEqual(sha(out/f'region_{r}.npz'),sha(probe/f'region_{r}.npz'))

    def test_03_bad_region_and_unbounded_settings_do_not_create_output(self):
        from local_refinement import refine_asset
        out=UNIT/'test_work/rejected'
        for region,config in [(9,P['refinement']),(4,dict(P['refinement'],max_displacement=float('nan'))),
                              (4,dict(P['refinement'],positive_step=2)),(4,dict(P['refinement'],pinned_regions=[]))]:
            with self.assertRaises(ValueError):refine_asset(ASSET,out,region,config)
            self.assertFalse(out.exists())

    def test_04_disabled_cached_cross_is_reanchored_and_can_reopen(self):
        from local_refinement import refine_asset
        off=UNIT/'test_work/off';refined=UNIT/'test_work/off_refined';on=UNIT/'test_work/on_again'
        edit(ASSET,off,4,{'cross_enabled':False})
        result=refine_asset(off,refined,4,P['refinement'])
        self.assertEqual(result['regenerated_layers'],[0,1])
        _,paths,meta=load_asset(refined)
        self.assertFalse(meta['styles']['4']['cross_enabled'])
        self.assertEqual(set(np.unique(paths[4]['layer_id'])),{0,1})
        edit(refined,on,4,{'cross_enabled':True})
        self.assertEqual(sha(refined/'region_4.npz'),sha(on/'region_4.npz'))
        self.assertEqual(sha(UNIT/'assets/refined/region_4.npz'),sha(on/'region_4.npz'))

if __name__=='__main__':unittest.main(verbosity=2)
