"""Small bounded regressions; never executes a complete asset."""
from common import *
from core import Engine,Carrier
import unittest,tempfile,sys,copy
from pipeline import merge_then_export

def fixture(kind='straight', cls=Engine, carrier_cls=Carrier):
    xx=np.r_[np.linspace(0,4,6),np.linspace(4.5,8.5,6)];x=np.c_[xx,np.zeros((12,2))];t=np.tile([1.,0,0],(12,1))
    if kind=='duplicate':x[6:]=x[:6]+[0,.1,0]
    if kind=='parallel':x[6:]=x[:6]+[0,.8,0]
    if kind=='gap':x[6:,0]+=2
    if kind in ('curve','gentle_curve','S'):
        x[:,1]=.9*np.sin(x[:,0]/(3 if kind in ('curve','gentle_curve') else 1.5));dy=.9/(3 if kind in ('curve','gentle_curve') else 1.5)*np.cos(x[:,0]/(3 if kind in ('curve','gentle_curve') else 1.5));t=np.c_[np.ones(12),dy,np.zeros(12)];t/=np.linalg.norm(t,axis=1)[:,None]
    if kind=='curve':
        theta=np.linspace(0,np.pi/2,12);x=np.c_[9*np.sin(theta),9*(1-np.cos(theta)),np.zeros(12)];t=np.c_[np.cos(theta),np.sin(theta),np.zeros(12)]
    if kind in ('T','X'):x[6:]=np.c_[np.full(6,2.),np.linspace(0 if kind=='T' else -2,4 if kind=='T' else 2,6),np.zeros(6)];t[6:]=[0,1,0]
    if kind=='tie':
        x=np.vstack([x,x[6:]+[0,.3,0],x[6:]-[0,.3,0]]);t=np.tile([1.,0,0],(len(x),1))
    n=len(x);ep=x.reshape(-1,2,3);r=dict(x=ep.mean(1),t=t[::2],endpoints=ep,kernel_rep=np.repeat(np.arange(n//2),2),member_rows=np.arange(n),member_offsets=np.arange(0,n+1,2),mid=np.arange(0,n,2))
    e=cls(dict(means=x,primitive_id=np.repeat(np.arange(n//6),6)),r,t,1.)
    for lo in range(0,n,6):e.carriers[lo]=carrier_cls(lo,np.arange(lo//2,(lo+6)//2),np.arange(lo,lo+6),x[lo:lo+6].copy(),'line',True,True,(lo,))
    e.level=2;return e

class CheckpointContract(unittest.TestCase):
    def test_committed_merge_survives_later_failure(self):
        e=fixture()
        with tempfile.TemporaryDirectory(dir=os.environ['V05_TEST_DIR']) as td:
            out=Path(td)
            def expensive():
                self.assertEqual(len(e.events),1)
                raise RuntimeError('INJECTED_EXPENSIVE_STAGE_FAILURE')
            with self.assertRaisesRegex(RuntimeError,'INJECTED'):merge_then_export(e,out,expensive)
            self.assertTrue((out/'STATE.pkl').exists(),'Committed topology lost before expensive export failed')
            with open(out/'STATE.pkl','rb') as f:s=pickle.load(f)
            self.assertEqual(len(s['carriers']),1)
            np.testing.assert_array_equal(s['carriers'][0].rows,np.arange(12))
if __name__=='__main__':unittest.main()
