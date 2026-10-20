"""Small development fixtures; --old invokes actual unchanged center renderer."""
import round013_common
import sys,unittest
import numpy as np
import core,mesh_attachment as adapter
import planar_fragments as new
import area_coverage as old
RED='--old' in sys.argv
if RED:sys.argv.remove('--old')
CAM={'R':np.eye(3),'t':np.zeros(3),'center':np.array([8.,8.]),'eye':np.zeros(3),'focal':8.,'size':16}
def mesh(extra=None,duplicate=False):
    v=[[-3,-3,4],[3,-3,4],[3,3,4],[-3,3,4]];f=[[0,1,2],[0,2,3]];parts=[1,1]
    if duplicate:f.append([0,2,1]);parts.append(1)
    if extra:
        x0,y0,x1,y1,z=extra;k=len(v);v.extend([[(x-8)*z/8,(y-8)*z/8,z] for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]);f.extend([[k,k+1,k+2],[k,k+2,k+3]]);parts.extend([1,1])
    return core.finalize_mesh(v,f,parts)
def run(m,p,owners=(0,1),sf=(0,),renderer=None):
    return adapter.render_validated(m,list(owners),list(sf),np.array(p,float),renderer or (old.render if RED else new.render),CAM)
def area(a):return a['coverage']*a['gate'] if RED else a['visible']
class FragmentTests(unittest.TestCase):
    def test_owner_edge_half_area(self):
        a=run(mesh(),[[-2,-3,4],[2,-3,4]])
        self.assertAlmostEqual(float(area(a).sum()),8.,places=10)
    def test_occluder_fraction(self):
        a=run(mesh((7.25,1,8.25,15,3)),[[-2,-2,4],[2,-2,4]])
        self.assertAlmostEqual(float(area(a).sum()),14.,places=10)
    def test_visible_and_hidden_nonempty(self):
        p=[[-2,-2,4],[2,-2,4]]
        self.assertAlmostEqual(float(area(run(mesh(),p)).sum()),16.)
        self.assertEqual(float(area(run(mesh((1,1,15,15,3)),p)).sum()),0.)
    @unittest.skipIf(RED,'new mechanism support and invariance checks')
    def test_shared_edge_and_duplicate_union(self):
        p=[[-2,-2,4],[2,2,4]];a=run(mesh(),p);b=run(mesh(duplicate=True),p,(0,1,2))
        np.testing.assert_array_equal(a['visible'],b['visible']);self.assertAlmostEqual(a['visible'].sum(),16*np.sqrt(2))
    @unittest.skipIf(RED,'new mechanism support and invariance checks')
    def test_nearer_samepart_and_farther(self):
        p=[[-2,-2,4],[2,-2,4]]
        self.assertEqual(area(run(mesh((1,1,15,15,3)),p)).sum(),0.)
        self.assertEqual(area(run(mesh((1,1,15,15,5)),p)).sum(),16.)
    @unittest.skipIf(RED,'new mechanism support and invariance checks')
    def test_ambiguous_depth_reject(self):
        for z in [4.,4.003]:
            with self.assertRaisesRegex(new.UnsupportedGeometry,'ambiguous_nonowner_depth'):run(mesh((1,1,15,15,z)),[[-2,-2,4],[2,-2,4]])
    @unittest.skipIf(RED,'new mechanism support and invariance checks')
    def test_tilt_reject(self):
        m=mesh((1,1,15,15,3));m['vertices'][4,2]+=.1;m['tri']=m['vertices'][m['faces']]
        with self.assertRaisesRegex(new.UnsupportedGeometry,'nonfrontoparallel_triangle'):run(m,[[-2,-2,4],[2,-2,4]])
    @unittest.skipIf(RED,'new mechanism support and invariance checks')
    def test_convex_difference_partition(self):
        p=np.array([[0.,0],[4,0],[4,4],[0,4]]);q=np.array([[2.,-1],[5,-1],[5,2],[2,2]])
        fragments=new.difference(p,q);self.assertAlmostEqual(sum(abs(new.signed_area(f)) for f in fragments),12.)
        for i,f in enumerate(fragments):
            for g in fragments[:i]:self.assertAlmostEqual(abs(new.signed_area(new.intersect(f,g))),0.)
if __name__=='__main__':unittest.main(verbosity=2)
