"""Small tests of new history evidence, with no asset science."""
import runtime_io
import unittest,copy
import numpy as np
from types import SimpleNamespace
import derivative_history_core as dc
from frontier_core import history

def fixture(angle=20.):
 x=np.array([.2,.5,.8,1.2,1.5,1.8]);a=np.c_[x,np.zeros((6,2))];b=a+[2.,0,0]
 t=np.tile([1.,0,0],(12,1));r=np.deg2rad(angle);t[6:]=[np.cos(r),np.sin(r),0]
 q=np.array([[0.,0,0],[2.,0,0]]);qb=q+[2,0,0]
 d=dict(p=1.,asset={'means':np.vstack([a,b])},tangents=t,leaves={0:SimpleNamespace(rows=np.arange(6),q=q),1:SimpleNamespace(rows=np.arange(6,12),q=qb)})
 state=dict(chains={0:[(0,False)]},curves={0:q.tolist()},metrics={0:{'unsupported_connectors_p':[]}})
 z=dict(common=True,relation='overlap',donor=1,reverse=False,attachment_s_oriented_p=0.,gap=0.,relay=[(1,False)],history=history(q,qb,0.))
 return d,state,z

class DerivativeTests(unittest.TestCase):
 def test_original_derivatives_can_reject_straight_auxiliary_history(self):
  d,s,z=fixture();self.assertTrue(z['history']['eligible']);got=dc.observed_history(d,s,0,1,z)
  self.assertFalse(got['eligible']);self.assertAlmostEqual(got['predicted_angle_deg'],20.)
 def test_axial_sign_and_original_rows(self):
  d,s,z=fixture(0);d['tangents'][::2]*=-1;got=dc.observed_history(d,s,0,1,z)
  self.assertTrue(got['eligible']);self.assertEqual(got['source']['bins'][0]['rows'],[3,4,5]);self.assertEqual(got['donor']['bins'][0]['rows'],[6,7,8])
 def test_missing_bin_no_secant_fallback(self):
  d,s,z=fixture(0);d['tangents'][0]=0;got=dc.observed_history(d,s,0,1,z)
  self.assertFalse(got['eligible']);self.assertEqual(got['reason'],'observed_history_unknown');self.assertEqual(got['source']['bins'][1]['count'],2)
 def test_exact_bin_boundary_and_dedup(self):
  q=np.array([[0.,0,0],[3.,0,0]]);x=np.c_[[0.,.3,.7,1.,1.5,2.,2.01],np.zeros((7,2))];d=dict(p=1.,asset={'means':x},tangents=np.tile([1.,0,0],(7,1)))
  r=dc.evidence(d,[0,0,1,2,3,4,5,6],q,False,0.,[])
  self.assertEqual(r['bins'][0]['rows'],[0,1,2]);self.assertEqual(r['bins'][1]['rows'],[3,4,5])
 def test_source_reversal(self):
  d,s,z=fixture(0);q=np.asarray(s['curves'][0])[::-1];r=dc.evidence(d,range(6),q,True,0.,[])
  self.assertEqual(r['bins'][0]['rows'],[0,1,2]);np.testing.assert_allclose(r['bins'][0]['axis'],[-1,0,0])
 def test_weak_axis_unknown(self):
  d,s,z=fixture(0);d['tangents'][0:3]=np.eye(3);got=dc.observed_history(d,s,0,1,z)
  self.assertFalse(got['eligible']);self.assertEqual(got['source']['bins'][1]['reason'],'weak_axis')
 def test_connector_strict_interior_and_finite_domain_exclusions(self):
  q=np.array([[0.,0,0],[4.,0,0]]);x=np.c_[[-.1,0.,.25,.5,1.,1.2,1.5,2.,4.1],np.zeros((9,2))];d=dict(p=1.,asset={'means':x},tangents=np.tile([1.,0,0],(9,1)))
  r=dc.evidence(d,range(9),q,False,0.,[[.25,1.]])
  self.assertEqual(r['exclusions']['finite_domain'],[0,8]);self.assertEqual(r['exclusions']['connector_interior'],[3]);self.assertIn(2,r['bins'][0]['rows']);self.assertIn(4,r['bins'][1]['rows'])
 def test_shared_ambiguity_precedes_observed_history(self):
  records=[dict(common=True,gap=.2,history={'eligible':False},observed_history={'eligible':False}),dict(common=True,gap=.3,history={'eligible':True},observed_history={'eligible':True})]
  got=dc.choices(records);self.assertEqual(got['reason'],'ambiguous_gap');self.assertTrue(all(got[k] is None for k in dc.ARMS))
 def test_commit_failure_preserves_state(self):
  import switch_core
  state=dict(chains={0:[(0,False)]},curves={0:[[0,0,0],[2,0,0]]},metrics={0:{}},ports={0:[]},used={0},versions={0:1},next_version=2,accepted={0:0},events=[])
  old=copy.deepcopy(state);z=dict(common=True,chain=[(0,False),(1,False)],q=[[0,0,0],[4,0,0]],metrics={'support_maps':[],'unsupported_connectors_p':[]},new_ports=[],donors=[1],donor_versions=[1],relation='endpoint_relay',relay=[(1,False)],gap=0.,total_gap=0.,history={},outward_support_p=2.,outward_rows=[6])
  def fail(st):raise RuntimeError('checkpoint failure')
  with self.assertRaisesRegex(RuntimeError,'checkpoint failure'):switch_core.commit(state,0,z,fail)
  self.assertEqual(state,old)
 def test_real_shared_library_and_repeated_observed_growth(self):
  import test_overlap as f,contact_core,switch_core
  import overlap_core as oc
  from frontier_core import endpoint_index
  d=f.data();st=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves'])
  for expected in [1,2]:
   lib=contact_core.library(d,st,0,1,idx,ends,'ARC',lambda:None);before=copy.deepcopy(lib)
   dc.annotate(d,st,0,1,lib);self.assertEqual(dc.remove_diagnostics(lib),before)
   choice=dc.choices(lib['records']);self.assertEqual(choice['BASE'],choice['SECANT_HISTORY']);self.assertEqual(choice['BASE'],choice['OBS_HISTORY'])
   z=lib['records'][choice['OBS_HISTORY']];self.assertEqual(z['donor'],expected)
   st=switch_core.commit(st,0,z,lambda _:None)
  self.assertEqual(st['accepted'][0],2);self.assertEqual(st['used'],{0,1,2})
 def test_reversed_overlap_donor_uses_full_oriented_domain(self):
  d,s,z=fixture(0);d['leaves'][1].q=d['leaves'][1].q[::-1];z['reverse']=True;z['relay']=[(1,True)]
  got=dc.observed_history(d,s,0,1,z);self.assertTrue(got['eligible']);self.assertEqual(got['donor']['bins'][0]['rows'],[6,7,8])
if __name__=='__main__':unittest.main(verbosity=2)
