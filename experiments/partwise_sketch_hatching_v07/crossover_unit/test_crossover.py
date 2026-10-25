import runtime
import unittest
import numpy as np
from geometry import mesh_data
from hatching import generate_layers
from embedding import migrate
from test_embedding import fixture, EmbeddingTests
from crossover import cross_layouts

class CrossoverTests(unittest.TestCase):
    def test_two_independent_families_and_roundtrip(self):
        for shape in ('flat','fold','curve'):
            o,p,style,_=fixture(shape)
            v=o['vertices'].copy();v[:,0]*=1.03;v[:,2]+=.001*(v[:,0]+.12)
            c=mesh_data(v,o['faces'],o['regions'])
            pc,_=generate_layers(c,4,dict(style,length=.08))
            self.assertNotEqual(len(np.unique(p['stroke_id'])),len(np.unique(pc['stroke_id'])))
            paths,records=cross_layouts(p,pc,o,c,5_000_000_000_000,6_000_000_000_000)
            for label,original in [('OO',p),('CC',pc)]:
                for k in original:np.testing.assert_array_equal(paths[label][k],original[k])
            for label,original,source,target in [('OC',p,o,c),('CO',pc,c,o)]:
                q=paths[label]
                for k in original:
                    if k not in ('points','stroke_id'):np.testing.assert_array_equal(q[k],original[k])
                back,_=migrate(q,target,source,7_000_000_000_000)
                np.testing.assert_allclose(back['points'],original['points'],atol=1e-13,rtol=0)
                self.assertEqual(len(records[label]),len(np.unique(original['stroke_id'])))
                for r in records[label]:self.assertIn('immediate_saved_layout_id',r)
            self.assertFalse(set(paths['OC']['stroke_id'])&set(paths['CO']['stroke_id']))

if __name__=='__main__':unittest.main(verbosity=2)
