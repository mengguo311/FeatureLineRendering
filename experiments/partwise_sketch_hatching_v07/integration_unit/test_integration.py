import runtime
import unittest
import numpy as np
from geometry import mesh_data
from fixture_embedding import fixture, EmbeddingTests
from base_walk import regenerate
from integration import transport_tangent, integrate_saved

class IntegrationTests(unittest.TestCase):
    def test_identity_saved_seeds_flat_fold_curve(self):
        for shape in ('flat','fold','curve'):
            m,p,_,_=fixture(shape); allowed=np.ones(len(m['faces']),bool)
            old,records=regenerate(m,p,allowed,id_offset=100_000_000_000)
            generated,pulled,new=integrate_saved(m,m,p,records,allowed,7_000_000_000_000)
            for k in ('points','bary','face','layer_id','visibility_mask','parent_stroke_id'):
                np.testing.assert_array_equal(generated[k],old[k])
                np.testing.assert_allclose(pulled[k],old[k],atol=1e-13,rtol=0)
            self.assertEqual(new[0]['minus_stop'],records[0]['minus_stop'])
            self.assertEqual(new[0]['plus_stop'],records[0]['plus_stop'])
            self.assertEqual(new[0]['requested_length'],records[0]['requested_length'])

    def test_known_affine_differential_and_fixed_material_seed(self):
        m,p,_,_=fixture('curve'); M=np.array([[1.2,.1,0],[0,.9,.03],[.05,0,1.1]])
        c=mesh_data(m['vertices']@M.T,m['faces'],m['regions'])
        _,r=regenerate(m,p,np.ones(len(m['faces']),bool))
        seed=r[0];face=seed['seed_face'];t=np.array(seed['initial_tangent'])
        expected=M@t;expected/=np.linalg.norm(expected)
        np.testing.assert_allclose(transport_tangent(m,c,face,t),expected,atol=1e-12)
        g,q,rr=integrate_saved(m,c,p,r,np.ones(len(m['faces']),bool),7_000_000_000_000)
        np.testing.assert_array_equal(rr[0]['seed_bary'],seed['seed_bary'])
        self.assertEqual(rr[0]['requested_length'],seed['requested_length'])
        for k in ('bary','face','stroke_id','layer_id','parent_stroke_id'):np.testing.assert_array_equal(g[k],q[k])
        np.testing.assert_allclose(q['points'],np.einsum('nij,njk->nik',q['bary'],m['tri'][q['face']]),atol=1e-13)
        for sid in np.unique(q['stroke_id']):
            x=q['points'][q['stroke_id']==sid];np.testing.assert_allclose(x[:-1,1],x[1:,0],atol=1e-12)

    def test_partition_boundary_and_topology_rejection(self):
        m,p,_,_=fixture('flat');_,r=regenerate(m,p,np.ones(len(m['faces']),bool))
        allowed=np.zeros(len(m['faces']),bool);allowed[r[0]['seed_face']]=True
        g,q,rr=integrate_saved(m,m,p,r,allowed,7_000_000_000_000)
        self.assertTrue(allowed[g['face']].all())
        self.assertIn('authored_region_boundary',(rr[0]['minus_stop'],rr[0]['plus_stop']))
        bad=dict(m,faces=m['faces'][::-1])
        with self.assertRaises(ValueError):integrate_saved(m,bad,p,r,allowed,7_000_000_000_000)

if __name__=='__main__':unittest.main(verbosity=2)
