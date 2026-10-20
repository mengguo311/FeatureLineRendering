"""Development controls, disjoint geometry from frozen acceptance fixtures."""
import round008_common
import argparse
import copy
import unittest
import numpy as np
import mesh_attachment as a

BACKEND = 'new'


def fixture():
    return ({'vertices': np.array([[-1,0,0],[1,0,0],[0,-1,-.5],[0,1,.25]],float),
             'faces': np.array([[0,1,2],[0,1,3]])},
            [0,1], [0,1], np.array([[0,-.5,-.25],[0,0,0],[0,.5,.125]]))


def invoke(mesh, owners, segments, path, callback):
    if BACKEND == 'unguarded':
        return callback(mesh, owners, path)
    return a.render_validated(mesh, owners, segments, path, callback)


class Tests(unittest.TestCase):
    def reject(self, data, code):
        calls=[]
        with self.assertRaises(a.AttachmentError) as caught:
            invoke(*data, lambda *x: calls.append(x))
        self.assertEqual(caught.exception.code,code)
        self.assertEqual(calls,[])

    def test_original_references_unchanged(self):
        m,o,s,p=fixture();before=p.tobytes();seen=[]
        result=invoke(m,o,s,p,lambda *x:seen.append(x) or 'rendered')
        self.assertEqual(result,'rendered');self.assertIs(seen[0][0],m)
        self.assertIs(seen[0][1],o);self.assertIs(seen[0][2],p)
        self.assertEqual(before,p.tobytes())

    def test_vertical_rotation(self):
        m,o,s,p=fixture();r=np.array([[0,0,1],[0,1,0],[-1,0,0]])
        m['vertices']=m['vertices']@r.T;p=p@r.T
        self.assertEqual(invoke(m,o,s,p,lambda *x:42),42)

    def test_straight_chord_rejected(self):
        m,o,s,p=fixture();self.reject((m,o,[0],p[[0,2]]),'off_plane')

    def test_outside_finite_triangle(self):
        m,o,s,p=fixture();p[0]=[2,-.5,-.25]
        self.reject((m,o,s,p),'outside_triangle')

    def test_wrong_ownership(self):
        m,o,s,p=fixture();self.reject((m,[0],s,p),'segment_not_owned')

    def test_float_id_not_silently_truncated(self):
        m,o,s,p=fixture();self.reject((m,o,[0,1.5],p),'segment_face_id')

    def test_duplicate_coordinates_are_not_adjacency(self):
        m,o,s,p=fixture();m['vertices']=np.vstack([m['vertices'],m['vertices'][:2]])
        m['faces'][1]=[4,5,3];self.reject((m,o,s,p),'disconnected_transition')

    def test_finite_shared_edge_waypoint(self):
        m,o,s,p=fixture();p[1]=[1.1,0,0]
        self.reject((m,o,s,p),'waypoint_not_on_shared_edge')

    def test_nonfinite(self):
        m,o,s,p=fixture();p[0,0]=np.nan
        self.reject((m,o,s,p),'path_nonfinite')

    def test_degenerate(self):
        m,o,s,p=fixture();m['vertices'][2]=[0,0,0]
        self.reject((m,o,s,p),'degenerate_triangle')

    def test_bad_cached_triangles(self):
        m,o,s,p=fixture();m['tri']=m['vertices'][m['faces']].copy();m['tri'][0,0,2]+=.1
        self.reject((m,o,s,p),'mesh_cache_mismatch')

    def test_failed_call_does_not_mutate(self):
        m,o,s,p=fixture();p[0,2]+=.1;before=copy.deepcopy((m,o,s,p))
        self.reject((m,o,s,p),'off_plane')
        np.testing.assert_array_equal(p,before[3])
        np.testing.assert_array_equal(m['vertices'],before[0]['vertices'])
        self.assertEqual(o,before[1]);self.assertEqual(s,before[2])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--backend',choices=['new','unguarded'],default='new')
    args=parser.parse_args();BACKEND=args.backend
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    raise SystemExit(0 if result.wasSuccessful() else 1)
