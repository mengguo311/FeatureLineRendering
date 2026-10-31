"""Pre-implementation endpoint coverage contract on a dense, finite fixture."""
from common import *
import common,unittest,copy
from core import Carrier
from budget_engine import BudgetEngine

def implementation():
    try:
        from endpoint_engine import EndpointEngine
        return EndpointEngine
    except ModuleNotFoundError:
        return BudgetEngine

def dense(cls=BudgetEngine):
    paths=[np.c_[np.linspace(0,4,6),np.zeros((6,2))],
           np.c_[np.linspace(4.5,8.5,6),np.zeros((6,2))]]
    paths += [paths[0]+[0,(-1 if k%2 else 1)*(k//2+1)*.001,0] for k in range(18)]
    x=np.concatenate(paths);n=len(x);t=np.tile([1.,0,0],(n,1));ep=x.reshape(-1,2,3)
    r=dict(x=ep.mean(1),t=t[::2],endpoints=ep,kernel_rep=np.repeat(np.arange(n//2),2),member_rows=np.arange(n),member_offsets=np.arange(0,n+1,2),mid=np.arange(0,n,2))
    e=cls(dict(means=x,primitive_id=np.repeat(np.arange(n//6),6)),r,t,1.)
    for lo in range(0,n,6):e.carriers[lo]=Carrier(lo,np.arange(lo//2,(lo+6)//2),np.arange(lo,lo+6),x[lo:lo+6].copy(),'line',True,True,(lo,))
    e.level=4
    return e

class EndpointCoverage(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_dense_duplicates_hide_feasible_endpoint_pair(self):
        old=dense();prefix=old.candidates()
        self.assertNotIn((0,6),[(i,j) for _,i,j in prefix])
        q,op,_,_=old.proposal(old.carriers[0],old.carriers[6],False)
        self.assertEqual(op,'endpoint');self.assertIsNotNone(q)
        fitted,why,_=old.fit(np.arange(12),np.arange(6),q)
        self.assertIsNotNone(fitted,why)
        new=dense(implementation());actual=new.candidates()
        self.assertEqual(actual[:len(prefix)],prefix)
        self.assertIn((0,6),[(i,j) for _,i,j in actual[len(prefix):]],'Feasible endpoint continuation remains hidden behind duplicate candidates')

if __name__=='__main__':unittest.main()
