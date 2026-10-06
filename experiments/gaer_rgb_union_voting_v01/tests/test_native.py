"""CPU all-ray oracle, full-T feature checks, frozen native fullSH3 alignment."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import runtime
import numpy as np
import torch
from binding import backend,read_api,ops
from assignment import assign

class NativeTruth(unittest.TestCase):
    def test_ray_and_fullT_subset(self):
        runtime.guard('native_test_cpu_oracle');m=backend()
        f=read_api('vote_cpu_fixture',runtime.VIEW/'experiments/gaer_view_selection_v01/fixtures.py')
        model,s=f.cpu_ray_fixture(m);truth=f.cpu_weights(model,s)
        with torch.no_grad():r=m.GaussianRasterizer(s)(**model,attribution=True,K=8)
        mass,alpha=ops.feature_mass(m,s,model)
        np.testing.assert_allclose(mass,truth.sum((0,1)),rtol=2e-5,atol=2e-6)
        np.testing.assert_allclose(alpha,truth.sum(2),atol=2e-6,rtol=0)
        actual=ops.render_features(m,s,model,np.array([0,2],np.int32))
        np.testing.assert_allclose(actual,truth[:,:,[0,2]].sum(2),atol=2e-6,rtol=0)
        line=np.zeros((9,9),bool);line[4,4]=True
        normal=np.zeros((9,9,2),np.float32);normal[...,0]=1
        a=assign(r.gaussian_ids.cpu().numpy(),r.gaussian_weights.cpu().numpy(),alpha,line,normal,np.ones((9,9)),12)
        self.assertEqual(a['counts'].sum(),1)
        winner=a['winner_map'][4,4];self.assertGreater(truth[4,4,winner],0)
        # Geometry/color texture do not change attribution coefficients.
        p,st,t=f.flat_fixture(m,False);q,_,_=f.flat_fixture(m,True)
        with torch.no_grad():
            ra=m.GaussianRasterizer(st)(**p,attribution=True,K=8)
            rb=m.GaussianRasterizer(st)(**q,attribution=True,K=8)
        self.assertTrue(torch.equal(ra.gaussian_ids,rb.gaussian_ids));self.assertTrue(torch.equal(ra.gaussian_weights,rb.gaussian_weights))
        self.assertEqual(t['interior_geometry_edges'],0)

if __name__=='__main__':unittest.main(verbosity=2)
