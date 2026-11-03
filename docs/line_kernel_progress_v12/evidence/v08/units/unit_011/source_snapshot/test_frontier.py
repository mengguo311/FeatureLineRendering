import runtime_io
import unittest,numpy as np
from frontier_core import history,choices,half_support,endpoint_index,candidates,initial,commit
from port_paths import Leaf,PathOracle
from frontier_loader import load
from unittest.mock import patch

def leaf(i,a,b):
 q=np.array([[a,0,0],[b,0,0]],float)
 return Leaf(i,0,np.arange(i*6,i*6+6),np.arange(i*3,i*3+3),q,True,True,np.array([[0,b-a]],float))
class Tests(unittest.TestCase):
 def test_loader_phase(self):
  class Stop(Exception):pass
  seen=[]
  def guard(phase):seen.append(phase);raise Stop()
  with patch('frontier_loader.verify') as v:
   with self.assertRaises(Stop):load(dict(input_files={},helper_files={},source_files={}),guard)
  self.assertEqual(seen,['readiness']);self.assertEqual(v.call_count,3)
 def test_history(self):
  q=np.array([[0,0,0],[3,0,0]],float);r=np.array([[3.2,0,0],[6,0,0]],float)
  self.assertTrue(history(q,r,.2)['eligible'])
  self.assertTrue(history(-q,-r,.2)['eligible'])
  self.assertFalse(history(q,np.array([[3.2,0,0],[3.2,3,0]]),.2)['eligible'])
  self.assertEqual(history(q[:1],r,.2)['reason'],'insufficient_history')
 def test_ambiguity_before_history(self):
  z=[dict(gap=.1,donor=1,port=0,common=True,history={'eligible':False}),dict(gap=.2,donor=2,port=0,common=True,history={'eligible':True})]
  self.assertEqual(choices(z)['reason'],'ambiguous_gap')
  z[1]['gap']=.4;self.assertEqual(choices(z)['HISTORY'],1);self.assertEqual(choices(z)['BASE'],0)
 def test_half_support(self):
  l=leaf(0,-2,2);self.assertAlmostEqual(half_support(l,np.zeros(3),np.array([1.,0,0])),2,places=7)
 def test_complete_and_repeated_both_ends(self):
  ls={0:leaf(0,0,4),1:leaf(1,4.2,8.2),2:leaf(2,-4.2,-.2),3:leaf(3,8.4,12.4)}
  means=np.vstack([np.linspace(x.q[0],x.q[-1],6) for x in ls.values()]);d=dict(leaves=ls,asset={'means':means},p=1.,next_version=10)
  a=initial([0],10);idx=endpoint_index(ls);oracle=PathOracle(ls)
  z=candidates(d,a,0,1,idx,oracle,lambda:None);ch=choices(z);self.assertEqual(z[ch['BASE']]['donor'],1)
  before=repr(a)
  def fail(x):raise OSError('disk')
  with self.assertRaises(OSError):commit(a,0,z[ch['BASE']],fail)
  self.assertEqual(repr(a),before)
  a=commit(a,0,z[ch['BASE']],lambda x:None)
  zz=candidates(d,a,0,1,idx,oracle,lambda:None);self.assertEqual(zz[choices(zz)['BASE']]['donor'],3)
  zz=candidates(d,a,0,0,idx,oracle,lambda:None);self.assertEqual(zz[choices(zz)['BASE']]['donor'],2)
  a=commit(a,0,zz[choices(zz)['BASE']],lambda x:None)
  self.assertEqual([v[0] for v in a['chains'][0]],[2,0,1])
 def test_radius_more_than_32_competitors(self):
  ls={0:leaf(0,0,4)}
  for i in range(1,41):ls[i]=leaf(i,4.2,8.2)
  means=np.vstack([np.linspace(x.q[0],x.q[-1],6) for x in ls.values()]);d=dict(leaves=ls,asset={'means':means},p=1.,next_version=10)
  z=candidates(d,initial([0],10),0,1,endpoint_index(ls),PathOracle(ls),lambda:None)
  self.assertEqual(sum(x['common'] for x in z),40)
  self.assertEqual(choices(z)['reason'],'ambiguous_gap')
 def test_gap_and_reversal(self):
  ls={0:leaf(0,0,4),1:leaf(1,6,10)}
  self.assertEqual(PathOracle(ls)([(0,False),(1,False)])[1],'endpoint_gap')
  self.assertFalse(PathOracle(ls)([(0,False),(1,True)])[0])
 def test_shared_oracle_rejection(self):
  a=leaf(0,0,4);b=leaf(1,4.1,8.1);b.q[1]=[4.1,4,0]
  self.assertFalse(PathOracle({0:a,1:b})([(0,False),(1,False)])[0])
if __name__=='__main__':unittest.main(verbosity=2)
