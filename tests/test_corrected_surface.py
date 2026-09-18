import unittest
import numpy as np
from test_multiscene import CFG,asset_fixture

class SurfaceAuditTests(unittest.TestCase):
    def test_cell_grouping_blocks_clone_leakage_and_rejects_filaments(self):
        from src.corrected_surface import fit_neighborhood
        x,y=np.meshgrid(np.linspace(-.9,.9,16),np.linspace(-.9,.9,16));plane=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)]
        a=fit_neighborhood(plane,np.ones(len(plane)),np.zeros(3),.1,1.,CFG)
        b=fit_neighborhood(np.repeat(plane,2,axis=0),np.ones(len(plane)*2)*.5,np.zeros(3),.1,1.,CFG)
        self.assertEqual(a['occupied_cells'],b['occupied_cells']);self.assertEqual(a['fit_cell_ids'],b['fit_cell_ids'])
        self.assertLess(a['equal_cell']['plane_p90_h'],1e-10)
        self.assertGreater(a['equal_cell']['spread'],.8)
        line=np.c_[np.linspace(-1,1,100),np.zeros((100,2))]
        f=fit_neighborhood(line,np.ones(100),np.zeros(3),.02,1.,CFG)
        self.assertFalse(f['sheet_local'])

    def test_two_parallel_layers_are_never_crease_and_curved_sheet_has_quadratic(self):
        from src.corrected_surface import fit_neighborhood
        x,y=np.meshgrid(np.linspace(-.8,.8,16),np.linspace(-.8,.8,16));xy=np.c_[x.ravel(),y.ravel()]
        layers=np.vstack([np.c_[xy,np.full(len(xy),z)] for z in [-.3,.3]])
        r=fit_neighborhood(layers,np.ones(len(layers)),np.zeros(3),.05,1.,CFG)
        self.assertFalse(r['crease_local'])
        curve=np.c_[xy,.7*xy[:,0]**2]
        q=fit_neighborhood(curve,np.ones(len(curve)),np.zeros(3),.05,1.,CFG)
        self.assertLess(q['equal_cell']['quadratic_p90_h'],q['equal_cell']['plane_p90_h'])
        self.assertIn('normal_bootstrap_p90',q['equal_cell'])

    def test_native_contribution_weights_sum_to_replayed_mass(self):
        from src.corrected_surface import contribution_weights
        from src.foundation import native_render,replay_native
        a=asset_fixture();K=np.array([[70.,0,31.5],[0,60.,31.5],[0,0,1]])
        state=native_render(a,K,np.eye(4),64,64,1)
        weights=contribution_weights(state,64,64)
        replay=replay_native(state,64,64,np.ones(4,bool),np.zeros(4,bool),1)
        self.assertAlmostEqual(float(weights.sum()),float(replay['alpha'].sum(dtype=float)),places=4)
        self.assertTrue(np.all(weights>=0))
