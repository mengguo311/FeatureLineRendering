"""Test-first curved-duplicate competition; bounded real fitting only."""
from common import *
import common,copy,unittest
from core import Engine,Carrier
from pipeline import state_of,restore
from test_unit3 import equal
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031')
UNIT=ROOT/'units/unit_010'
def variant_class():
    try:from local_tangent import LocalTangentEngine;return LocalTangentEngine
    except ModuleNotFoundError:return Engine

def curved_duplicates(cls=Engine):
    theta=np.linspace(-.5,.5,18);q=np.c_[20*np.sin(theta),20*(1-np.cos(theta)),np.zeros(18)]
    x=np.tile(q,(3,1));t=np.tile(np.c_[np.cos(theta),np.sin(theta),np.zeros(18)],(3,1));n=len(x)
    r=dict(x=x.reshape(-1,2,3).mean(1),t=t[::2],endpoints=x.reshape(-1,2,3),kernel_rep=np.repeat(np.arange(n//2),2),member_rows=np.arange(n),member_offsets=np.arange(0,n+1,2),mid=np.arange(0,n,2))
    e=cls(dict(means=x,primitive_id=np.repeat(np.arange(3),18)),r,t,1.)
    for lo in (0,18,36):e.carriers[lo]=Carrier(lo,np.arange(lo//2,(lo+18)//2),np.arange(lo,lo+18),q.copy(),'polyline',True,True,(lo,))
    e.level=4;e.candidates=lambda:[(0.,0,18),(0.,0,36)]
    return e
class CurvedDuplicateContract(unittest.TestCase):
    def test_same_curved_alternatives_do_not_create_false_ambiguity(self):
        e=curved_duplicates(variant_class());e.pass_once(False)
        self.assertEqual(e.fit_count,2)
        self.assertEqual(len(e.events),1,'Coincident curved alternatives falsely blocked by whole-curve chord')
        self.assertEqual(e.stats['ambiguous'],0)
if __name__=='__main__':unittest.main()
