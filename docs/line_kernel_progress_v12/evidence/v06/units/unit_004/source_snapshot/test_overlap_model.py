"""Bounded tests written before the overlap implementation; no full assets."""
from runtime_io import *
from port_paths import Leaf
import unittest
from overlap_model import compatibility,build_bank,select_components,select_greedy,select_joint,group_guard
from overlap_delivery import membership_for

def fixture(n=4,length=6.,offsets=None):
    offsets=offsets or [0.]*n
    leaves={i:Leaf(i,100+i,np.arange(i*6,(i+1)*6),np.arange(i*3,(i+1)*3),np.array([[0.,offsets[i],0],[length,offsets[i],0]]),True,False,np.array([[0.,length]])) for i in range(n)}
    means=np.concatenate([np.linspace(x.q[0],x.q[-1],6) for x in leaves.values()]);mid=np.arange(0,n*6,2)
    pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
    return dict(leaves=leaves,p=1.,next_version=1000,asset=dict(means=means,primitive_id=np.repeat(np.arange(n),6),covariance=np.tile(np.eye(3),(n*6,1,1)),opacity=np.ones(n*6)),tangents=np.tile([1.,0,0],(n*6,1)),representatives=dict(x=means[mid],t=np.tile([1.,0,0],(n*3,1)),mid=mid,endpoints=np.repeat(np.array([[[0.,0,0],[length,0,0]]]),n*3,axis=0)),membership=dict(edge_id=np.array([0]*6+[-1]*(6*n-6)),line_kernel_id=np.arange(n*6),carrier_id=np.repeat(np.arange(n),6),reason_code=np.ones(n*6,np.int8),primitive_id=np.repeat(np.arange(n),6)),pairs=pairs,overlaps=[dict(record_id=k,a=a,b=b) for k,(a,b) in enumerate(pairs)],arrays=dict(carrier_id=np.arange(n),kind=np.array(['line']*n)),aux={})

class OverlapTests(unittest.TestCase):
    def test_four_observations_do_not_consume_ports(self):
        d=fixture();h,records=build_bank(d,dict(carriers=list(d['leaves'])),lambda:None)
        largest=max(h,key=lambda x:len(x['leaves']));self.assertEqual(len(largest['leaves']),4)
        self.assertAlmostEqual(largest['metrics']['supported_length_p'],6.)
        self.assertAlmostEqual(largest['metrics']['duplicate_observed_support_p'],18.)
    def test_global_set_packing_trap(self):
        hs=[dict(hid=0,anchor=0,leaves=[0,1],benefit=3.),dict(hid=1,anchor=0,leaves=[0,2],benefit=2.),dict(hid=2,anchor=1,leaves=[1,3],benefit=2.)]
        self.assertEqual(select_greedy(hs),[0]);chosen,r=select_joint(hs,5,lambda:None)
        self.assertEqual(chosen,[1,2]);self.assertEqual(r['status'],'optimal')
    def test_finite_domain_forbids_extrapolation(self):
        d=fixture(2);d['leaves'][1].q+=np.array([1.,0,0]);d['asset']['means'][6:]+=np.array([1.,0,0])
        ok,why,m=compatibility(d,0,1,lambda:None);self.assertFalse(ok);self.assertIn(why,['finite_domain','residual'])
    def test_parallel_not_identity(self):
        d=fixture(2,offsets=[0.,.6]);ok,why,m=group_guard(d,0,[0,1],lambda:None)
        self.assertFalse(ok);self.assertEqual(why,'parallel')
    def test_branch_with_original_three_arm_predicate(self):
        d=fixture(3);dirs=np.array([[1.,0,0],[-.5,.8660254,0],[-.5,-.8660254,0]])
        d['representatives']['x']=np.concatenate([np.array([.5,1.6,2.8])[:,None]*v for v in dirs]);d['representatives']['t']=np.repeat(dirs,3,axis=0)
        ok,why,m=group_guard(d,0,[0,1,2],lambda:None);self.assertFalse(ok);self.assertEqual(why,'branch')
    def test_unknown_activation_and_old_group_preserved(self):
        d=fixture(2,length=2.);hs,_=build_bank(d,dict(carriers=[0,1]),lambda:None)
        h=max(hs,key=lambda z:z['benefit']);m,gs,lin=membership_for(d,[h],hs)
        self.assertTrue(np.all(m['edge_id'][:6]==0));self.assertTrue(np.all(m['edge_id'][6:]<0))
        d=fixture(2,length=6.);hs,_=build_bank(d,dict(carriers=[0,1]),lambda:None);h=max(hs,key=lambda z:z['benefit']);m,gs,lin=membership_for(d,[h],hs)
        self.assertTrue(np.all(m['edge_id']==0));self.assertEqual(gs[0]['activated_unknown'],6)
    def test_complete_overflow_not_trimmed(self):
        d=fixture(4);c=dict(overlap_priority_ids=[0],decision_carrier_cap=3,max_components=8)
        cs,audit=select_components(c,d);self.assertEqual(cs[0]['carriers'],[0,1,2,3]);self.assertEqual(cs[0]['status'],'NOT_RUN_OVERSIZE')
        self.assertEqual(len(cs[0]['incident_record_ids']),6)

if __name__=='__main__':unittest.main(verbosity=2)
