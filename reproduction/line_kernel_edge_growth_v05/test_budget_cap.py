"""Pre-implementation contracts for both real fitting budget checks."""
from common import *
import common,unittest
from core import Carrier
from transfer import TransferEngine
from test_build import fixture

def implementation():
    try:from budget_engine import BudgetEngine;return BudgetEngine
    except ModuleNotFoundError:return TransferEngine

def two_pairs(cls=TransferEngine):
    base=fixture();x=np.vstack([base.x,base.x+[0,10,0]]);t=np.tile([1.,0,0],(24,1));ep=x.reshape(-1,2,3)
    r=dict(x=ep.mean(1),t=t[::2],endpoints=ep,kernel_rep=np.repeat(np.arange(12),2),member_rows=np.arange(24),member_offsets=np.arange(0,25,2),mid=np.arange(0,24,2))
    e=cls(dict(means=x,primitive_id=np.repeat(np.arange(4),6)),r,t,1.)
    for lo in range(0,24,6):e.carriers[lo]=Carrier(lo,np.arange(lo//2,(lo+6)//2),np.arange(lo,lo+6),x[lo:lo+6].copy(),'line',True,True,(lo,))
    e.level=4;e.candidates=lambda:[(0.,0,6),(0.,12,18)]
    return e

class BudgetContract(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None
    def test_small_budget_truncates_actual_acceptable_merge(self):
        low=two_pairs(implementation());low.fit_limit=1;low.control_fit_limit=1;low.pass_once(False)
        self.assertEqual(low.fit_count,1,'Configured pass budget ignored')
        self.assertEqual(len(low.events),1);self.assertEqual(low.stats['fit_cap'],1)
        high=two_pairs(implementation());high.fit_limit=2;high.control_fit_limit=1;high.pass_once(False)
        self.assertEqual(high.fit_count,2);self.assertEqual(len(high.events),2)
        self.assertEqual(len(high.carriers),2)
    def test_fit_accepts_above_historical_hard_limit(self):
        e=two_pairs(implementation());e.fit_limit=40000;e.fit_count=30000
        a,b=e.carriers[0],e.carriers[6];q,_,_,_=e.proposal(a,b,False)
        fit,why,metrics=e.fit(np.r_[a.rows,b.rows],np.r_[a.reps,b.reps],q)
        self.assertIsNotNone(fit,'fit() still uses the historical30000 cap')
        self.assertEqual(e.fit_count,30001)

if __name__=='__main__':unittest.main()
