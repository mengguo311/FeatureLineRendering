"""Small post-output regressions; toy truth is used only in these tests."""
import unittest
from common import *
from core import Engine, Carrier, union_intervals

def fixture(paths):
    xs=[];ts=[];mids=[];ends=[];rows=[];off=[0];kr=[];count=[]
    for path in paths:
        path=np.asarray(path,float);tt=np.gradient(path,axis=0);tt/=np.linalg.norm(tt,axis=1)[:,None];offset=len(xs);xs.extend(path);ts.extend(tt)
        for start in range(0,len(path),4):
            rr=np.arange(offset+start,offset+min(start+4,len(path)));rid=len(mids);mids.append(rr[len(rr)//2]);ends.append([rr[0],rr[-1]]);rows.extend(rr);off.append(len(rows));kr.extend([rid]*len(rr));count.append(len(rr))
    x=np.asarray(xs);t=np.asarray(ts);mid=np.asarray(mids);ep=np.asarray(ends);a=dict(means=x,primitive_id=np.arange(len(x)),internal_piece_id=np.arange(len(x)),arc_t=np.arange(len(x),dtype=float));r=dict(x=x[mid],t=t[mid],endpoints=x[ep],mid=mid,member_rows=np.asarray(rows),member_offsets=np.asarray(off),kernel_rep=np.asarray(kr),count=np.asarray(count))
    return Engine(a,r,t,1.)

class GuardTests(unittest.TestCase):
    def test_duplicate_union_not_sum(self):
        x=np.arange(40)*.35;line=np.c_[x,np.zeros((40,2))];e=fixture([line,line]);reps=np.arange(len(e.rx));rows=np.arange(len(e.x));fit,why,_=e.fit(rows,reps,line)
        self.assertIsNotNone(fit,why);length=e.support(reps,fit[0])[1];one=e.support(reps[:10],fit[0])[1];self.assertAlmostEqual(length,one,places=7)
    def test_curved_and_s(self):
        tt=np.linspace(0,1,64);x=np.linspace(0,24,80)
        for path in (np.c_[20*np.cos(tt),20*np.sin(tt),np.zeros(64)],np.c_[x,1.5*np.sin(x/6),np.zeros(80)]):
            e=fixture([path]);fit,why,_=e.fit(np.arange(len(e.x)),np.arange(len(e.rx)),path)
            self.assertIsNotNone(fit,why);self.assertEqual(fit[1],'polyline')
    def test_parallel_and_depth(self):
        x=np.arange(40)*.35;line=np.c_[x,np.zeros((40,2))]
        for shift in ([0,.8,0],[0,0,2.]):
            e=fixture([line,line+shift]);a=Carrier(0,np.arange(10),np.arange(40),line[[0,-1]],'line',True,True,(0,));b=Carrier(40,np.arange(10,20),np.arange(40,80),(line+shift)[[0,-1]],'line',True,True,(40,));q,why,_,_=e.proposal(a,b,False);self.assertIsNone(q);self.assertEqual(why,'parallel')
    def test_t_and_gap(self):
        x=np.linspace(-10,10,64);h=np.c_[x,np.zeros((64,2))];v=np.c_[np.zeros(32),np.linspace(0,10,32),np.zeros(32)];e=fixture([h,v]);fit,_,_=e.fit(np.arange(len(e.x)),np.arange(len(e.rx)),np.vstack([h,v]));self.assertIsNone(fit)
        a=Carrier(0,np.arange(2),np.arange(8),np.array([[0.,0,0],[2.,0,0]]),'line',True,False,());b=Carrier(8,np.arange(2,4),np.arange(8,16),np.array([[5.,0,0],[8.,0,0]]),'line',True,False,());q,why,_,_=e.proposal(a,b,False);self.assertIsNone(q);self.assertEqual(why,'endpoint_gap')
    def test_real_vertical_red_green(self):
        a=np.load(OUT/'scan24/L0/MEMBERSHIP.npz');b=np.load(OUT/'scan24/L1/MEMBERSHIP.npz');changed=np.flatnonzero((a['edge_id']<0)&(b['edge_id']>=0));self.assertGreater(len(changed),0);row=int(changed[0]);target=int(b['edge_id'][row]);rows=np.flatnonzero(b['edge_id']==target)
        with self.assertRaises(AssertionError):self.assertTrue(np.all(a['edge_id'][rows]>=0),'RED: inherited baseline strands selected real support')
        self.assertTrue(np.all(b['edge_id'][rows]==target));self.assertTrue(np.all(b['edge_id'][a['edge_id']>=0]>=0))
        js(OUT/'REAL_RED_GREEN_FIXTURE.json',dict(kernel_rows=rows.tolist(),baseline_ids=a['edge_id'][rows].tolist(),new_id=target,RED='baseline does not assign all selected support',GREEN='all selected support is pooled; physical identity unverified',truth='geometric membership regression, not real physical labels'))

if __name__=='__main__':unittest.main(verbosity=2)
