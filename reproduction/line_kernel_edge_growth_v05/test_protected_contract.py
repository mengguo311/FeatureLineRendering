"""Test-first real fitting counterexample to prefix loss under joint competition."""
from common import *
import common,unittest
from core import Carrier
from endpoint_engine import EndpointEngine

def implementation():
    try:
        from protected_engine import ProtectedEngine
        return ProtectedEngine
    except ModuleNotFoundError:return EndpointEngine

def competition_fixture(cls=EndpointEngine,ambiguous=False):
    specs=[(0,0),(4.5,.25),(4.5,0),(20,0),(24.5,.4 if ambiguous else 0)]
    if ambiguous:specs.append((24.5,-.4))
    x=np.concatenate([np.c_[np.linspace(start,start+4,6),np.full(6,y),np.zeros(6)] for start,y in specs]);n=len(x)
    t=np.tile([1.,0,0],(n,1));ep=x.reshape(-1,2,3)
    r=dict(x=ep.mean(1),t=t[::2],endpoints=ep,kernel_rep=np.repeat(np.arange(n//2),2),member_rows=np.arange(n),member_offsets=np.arange(0,n+1,2),mid=np.arange(0,n,2))
    class Routed(cls):
        def candidates(self):
            self.prefix_candidates=[(0.,0,6)]
            self.supplement_candidates=[(0.,0,12),(0.,18,24)]+([(0.,18,30)] if ambiguous else [])
            self.supplement_stats={};self.supplement_records=[];self.supplement_ports={}
            return self.prefix_candidates+self.supplement_candidates
    e=Routed(dict(means=x,primitive_id=np.repeat(np.arange(n//6),6)),r,t,1.)
    for lo in range(0,n,6):e.carriers[lo]=Carrier(lo,np.arange(lo//2,(lo+6)//2),np.arange(lo,lo+6),x[lo:lo+6].copy(),'line',True,True,(lo,))
    e.level=4;e.fit_limit=40000;return e

class ProtectionContract(unittest.TestCase):
    def setUp(self):common.CFG=None;common.END=None;common.START=None;common.PHASE='build_test'
    def test_prefix_accepted_merge_survives_better_supplement(self):
        old=competition_fixture();old.pass_once(False)
        oldpairs=[tuple(z[0] for z in ev['inputs']) for ev in old.events]
        self.assertNotIn((0,6),oldpairs);self.assertIn((0,12),oldpairs)
        e=competition_fixture(implementation());e.pass_once(False)
        pairs=[tuple(z[0] for z in ev['inputs']) for ev in e.events]
        self.assertIn((0,6),pairs,'Joint competition removed a verified prefix acceptance')
        self.assertNotIn((0,12),pairs);self.assertIn((18,24),pairs)
        self.assertEqual(e.fit_count,old.fit_count)
    def test_joint_ambiguity_survives_protection_filter(self):
        e=competition_fixture(implementation(),True);e.pass_once(False)
        pairs=[tuple(z[0] for z in ev['inputs']) for ev in e.events]
        self.assertNotIn((18,24),pairs);self.assertNotIn((18,30),pairs)
        self.assertIn((0,6),pairs)

if __name__=='__main__':unittest.main()
