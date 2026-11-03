"""Small deterministic feature tests; no scene asset or renderer execution."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import unittest
import numpy as np
from geometry_base import contact_bounded,segment_contact
from port_paths import Edge, greedy, joint, paths, complete_contexts, PathOracle, Leaf, endpoint_ports, parallel

def leaf(cid, q, n=6):
    q=np.asarray(q,float)
    return Leaf(cid,7,np.arange(cid*100,cid*100+n),np.array([cid*3+i for i in range(3)]),q,True,False,np.array([[0.,np.linalg.norm(np.diff(q,axis=0),axis=1).sum()]]))
def allow(chain): return True,'ok',{}
class Tests(unittest.TestCase):
    def test_joint_beats_port_greedy(self):
        edges=[Edge(0,1,0,2,0,.1),Edge(1,1,0,3,0,.8),Edge(2,2,0,4,0,.8)]
        g,_=greedy(edges,allow);j,r=joint(edges,allow,10)
        self.assertEqual(g,[0]);self.assertEqual(j,[1,2]);self.assertEqual(r['status'],'optimal')
    def test_three_leaves_share_identity_and_overlap_rows_not_ports(self):
        ls={1:leaf(1,[[0,0,0],[2,0,0]],60),2:leaf(2,[[2.1,0,0],[4.1,0,0]],90),3:leaf(3,[[4.2,0,0],[6.2,0,0]],6)}
        es=[Edge(0,1,1,2,0,.2),Edge(1,2,1,3,0,.2)]
        oracle=PathOracle(ls);g,_=greedy(es,oracle);j,_=joint(es,oracle,10)
        self.assertEqual(g,[0,1]);self.assertEqual(j,g)
        chain=paths(es,j)[0];self.assertEqual([x[0] for x in chain],[1,2,3])
        self.assertEqual(sum(len(ls[c].rows) for c,_ in chain),156)
    def test_cycle_is_cut(self):
        es=[Edge(0,1,1,2,0,.1),Edge(1,2,1,3,0,.1),Edge(2,3,1,1,0,.1)]
        j,r=joint(es,allow,10);self.assertEqual(len(j),2);self.assertTrue(r['cuts'])
    def test_whole_path_turn_rejects_pairwise_chain(self):
        qs=[];p=np.zeros(3)
        for a in (0,25,50,75):
            v=np.array([np.cos(np.deg2rad(a)),np.sin(np.deg2rad(a)),0.]);q=np.stack([p,p+2*v]);qs.append(q);p=q[-1]
        ls={i:leaf(i,q) for i,q in enumerate(qs)};o=PathOracle(ls)
        for i in range(3):self.assertTrue(o([(i,False),(i+1,False)])[0])
        self.assertEqual(o([(i,False) for i in range(4)])[1],'window_turn')
    def test_gap_is_not_supported(self):
        ls={1:leaf(1,[[0,0,0],[2,0,0]]),2:leaf(2,[[3.6,0,0],[5.6,0,0]])}
        self.assertEqual(PathOracle(ls)([(1,False),(2,False)])[1],'endpoint_gap')
    def test_complete_context_overflow_never_trims(self):
        records=[(i,i+1) for i in range(140)]
        cs=complete_contexts([('seed',[0])],records,128)
        self.assertEqual(len(cs[0]['carriers']),141);self.assertEqual(cs[0]['status'],'NOT_RUN_OVERSIZE')
    def test_intersecting_contexts_merge_and_close(self):
        cs=complete_contexts([('a',[1]),('b',[4])],[(1,2),(2,3),(3,4)],128)
        self.assertEqual(len(cs),1);self.assertEqual(cs[0]['carriers'],[1,2,3,4]);self.assertEqual(cs[0]['labels'],['a','b'])
    def test_memory_bounded_contact_matches_pinned_formula(self):
        rng=np.random.default_rng(5)
        for n in (3,8,16):
            for scale in (0.2,2.0):
                q=np.cumsum(rng.normal(size=(n,3))*scale,axis=0)
                self.assertEqual(contact_bounded(q),segment_contact(q))
    def test_parallel_and_three_arm_guards(self):
        a=leaf(1,[[0,0,0],[4,0,0]]);b=leaf(2,[[0,.6,0],[4,.6,0]])
        self.assertTrue(parallel(a,b))
        a=leaf(1,[[0,0,0],[8,0,0]],9);a.reps=np.arange(9)
        rx=[];rt=[]
        for deg in (-25,0,25):
            t=np.array([np.cos(np.deg2rad(deg)),np.sin(np.deg2rad(deg)),0.])
            for radius in (.5,1.5,2.6):rx.append(radius*t);rt.append(t)
        self.assertEqual(PathOracle({1:a},np.array(rx),np.array(rt))([(1,False)])[1],'branch')
    def test_timeout_never_promotes_unchecked_solution(self):
        selected,receipt=joint([Edge(0,1,1,2,0,.1)],allow,0)
        self.assertEqual(selected,[]);self.assertEqual(receipt['status'],'timeout')
    def test_joint_lazy_whole_path_cut(self):
        es=[Edge(0,1,1,2,0,.1),Edge(1,2,1,3,0,.1)]
        def reject_long(ch):return (len(ch)<3,'whole_path_test',{})
        j,r=joint(es,reject_long,10)
        self.assertEqual(len(j),1);self.assertEqual(r['cuts'][0]['reason'],'whole_path_test')
    def test_original_host_endpoint_ties(self):
        a=leaf(7,[[0,0,0],[1,0,0]]);b=leaf(3,[[0,1,0],[1,1,0]])
        self.assertEqual(endpoint_ports(a,b),(0,0))
if __name__=='__main__':unittest.main(verbosity=2)
