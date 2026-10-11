import unittest
import numpy as np
from primitive import ordered_paths,split_path,fit_segment,associate,curve_eval,sample_graph,visibility_evidence

def segment(y=0,z=2,view=0,kind='surface',curve=False):
    t=np.linspace(0,1,17);x=(t-.5)*.16
    p=np.stack([x, y+(.04*np.sin(np.pi*t) if curve else np.zeros_like(t)),np.full_like(t,z)],1)
    s=fit_segment(p,.01);s.update(view=view,kind=kind,points=p,uv=np.stack([t*16,t*0],1),camera=None,source_ids=list(range(len(p))))
    return s
class Geometry(unittest.TestCase):
    def test_line_curve_complexity(self):
        self.assertEqual(segment()['type'],'line')
        self.assertEqual(segment(curve=True)['type'],'bezier')
        for s in [segment(),segment(curve=True)]:
            self.assertLess(np.max(np.linalg.norm(curve_eval(s['control'],s['type'],np.linspace(0,1,17))-s['points'],axis=1)),.01)
    def test_parallel_and_depth_layers(self):
        for a,b in [(segment(),segment(y=.02,view=1)),(segment(),segment(z=2.02,view=1))]:
            g,_=associate([a,b]);self.assertEqual(len(g),2)
    def test_no_transitive_chain(self):
        g,_=associate([segment(y=i*.009,view=i) for i in range(3)])
        self.assertEqual(len(g),2)
    def test_repeat_observations_and_new_capacity(self):
        reference=None
        for n in (3,12,47):
            g,_=associate([segment(view=i) for i in range(n)])
            self.assertEqual(len(g),1)
            a=sample_graph(g)
            if reference is None:reference=a
            else:
                for k in ['means','covariance','opacity']:np.testing.assert_allclose(a[k],reference[k],rtol=0,atol=1e-12)
        g,_=associate([segment(view=0),segment(y=.1,view=1)]);self.assertEqual(len(g),2)
    def test_missing_support_survives(self):
        g,_=associate([segment()]);self.assertEqual(len(g),1)
    def test_moving_silhouette_conflict(self):
        g,a=associate([segment(kind='silhouette'),segment(y=.008,view=1,kind='silhouette')])
        self.assertEqual(len(g),2)
    def test_hidden_unknown_no_negative(self):
        self.assertEqual(visibility_evidence(3,2,1,False),'hidden')
        self.assertEqual(visibility_evidence(2,2,.1,False),'unknown')
        self.assertEqual(visibility_evidence(2,2,1,False),'visible_offline')
        g,_=associate([segment()]);self.assertEqual(len(g),1)
    def test_T_X_corner_no_shortcut(self):
        for name in ('T','X'):
            m=np.zeros((17,17),bool);m[8,2:15]=1
            if name=='T':m[2:9,8]=1
            else:m[2:15,8]=1
            paths=ordered_paths(m)
            self.assertEqual(len(paths),3 if name=='T' else 4)
            self.assertTrue(all(any(np.array_equal(q,[8,8]) for q in p) for p in paths))
        p=np.array([[x,0] for x in range(9)]+[[8,y] for y in range(1,9)])
        out=split_path(p,np.ones(len(p))*2,.01,max_arc=30)
        self.assertGreaterEqual(len(out),2)
        self.assertTrue(all(not (q[:,0].ptp()>3 and q[:,1].ptp()>3) for q in out))
    def test_depth_jump_no_bridge(self):
        p=np.stack([np.arange(12),np.zeros(12)],1);z=np.r_[np.ones(6)*2,np.ones(6)*3]
        out=split_path(p,z,.01)
        self.assertTrue(all(not(q[:,0].min()<6 and q[:,0].max()>=6) for q in out))
    def test_perturbed_depth_and_spd(self):
        s=segment();s['points']=s['points'].copy();s['points'][:,2]+=.0005*np.sin(np.arange(17))
        f=fit_segment(s['points'],.01);self.assertEqual(f['type'],'line')
        f.update(view=0,kind='surface',source_ids=list(range(17)),uv=s['uv'],camera=None)
        g,_=associate([f]);a=sample_graph(g)
        self.assertTrue(np.isfinite(a['means']).all());self.assertTrue((np.linalg.eigvalsh(a['covariance'])>0).all())
    def test_reject_nonfinite(self):
        with self.assertRaises(ValueError):fit_segment(np.array([[0,0,np.nan],[0,1,2]]),.01)
    def test_partial_interval_does_not_shrink_coverage(self):
        a=segment();b=segment(view=1);b['control']=b['control'].copy();b['control'][:,0]+=.04;b['points']=b['points'].copy();b['points'][:,0]+=.04
        g,_=associate([a,b]);self.assertEqual(len(g),1)
        q=curve_eval(g[0]['control'],g[0]['type'],[0,1])
        self.assertLessEqual(q[:,0].min(),-.08+1e-10);self.assertGreaterEqual(q[:,0].max(),.12-1e-10)
    def test_duplicate_identical_same_view_not_extra_evidence(self):
        g,_=associate([segment(view=0) for _ in range(47)])
        self.assertEqual(len(g),1);self.assertEqual(len(g[0]['views']),1)
    def test_short_disjoint_intervals_are_not_overlap(self):
        a=segment();b=segment(view=1)
        for s in (a,b):s['control'][:,0]*=.04;s['points'][:,0]*=.04
        b['control'][:,0]+=.012;b['points'][:,0]+=.012
        g,_=associate([a,b]);self.assertEqual(len(g),2)
        self.assertTrue(all(np.isfinite(s['control']).all() for s in g))

if __name__=='__main__':unittest.main(verbosity=2)
