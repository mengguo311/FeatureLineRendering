import runtime_io
import unittest,copy
import numpy as np
import overlap_core as oc
import seam_core as sc
from geometry_base import arc,EPS

class SeamTests(unittest.TestCase):
 def test_short_overlap_has_extended_tangent_constrained_seam(self):
  a=np.array([[0.,0,0],[1,0,0],[2,0,0],[3,0,0],[4,0,0]])
  b=np.array([[3.85,.1,0],[5,.1,0],[6,.1,0],[7,.1,0],[8,.1,0]])
  q,m=sc.hermite_register(a,b,.15)
  self.assertEqual(m['status'],'ok')
  self.assertLessEqual(np.max(np.linalg.norm(np.diff(q[(q[:,0]>=2)&(q[:,0]<=6)],axis=0),axis=1)),.25+EPS)
  np.testing.assert_array_equal(q[:2],a[:2]);np.testing.assert_array_equal(q[-2:],b[-2:])
  self.assertAlmostEqual(m['local_start_a_p'],2.);self.assertAlmostEqual(m['local_end_b_p'],2.15)
  self.assertAlmostEqual(m['seam_p'],oc.project(oc.at(b,.15)[None,:],q)[0][0])
 def test_registration_failures_are_not_rescued(self):
  a=np.array([[0.,0,0],[4,0,0]])
  for b,s in [(np.array([[2.,1.1,0],[8,1.1,0]]),2.),(np.array([[8.,0,0],[2,0,0]]),4.)]:
   old,meta=oc.register(a,b,s);new,m=sc.hermite_register(a,b,s)
   self.assertIsNone(new);self.assertEqual(m['status'],meta['status'])
 def test_straight_no_duplicate_support_and_orientation(self):
  a=np.array([[0.,0,0],[2,0,0],[4,0,0]]);b=np.array([[2.,0,0],[4,0,0],[6,0,0],[8,0,0]])
  q,m=sc.hermite_register(a,b,2.)
  self.assertAlmostEqual(arc(q)[-1],8.);self.assertTrue(np.all(np.diff(q[:,0])>0))
  reflected,n=sc.hermite_register(-a,-b,2.)
  np.testing.assert_allclose(reflected,-q,atol=1e-14,rtol=0)

if __name__=='__main__':unittest.main(verbosity=2)

class IntegrationTests(unittest.TestCase):
 def test_real_hermite_library_support_and_rollback(self):
  import test_overlap as f
  import switch_core
  from frontier_core import endpoint_index,choices
  d=f.data(False);state=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves'])
  linear=sc.library(d,state,0,1,idx,ends,'LINEAR',lambda:None)
  hermite=sc.library(d,state,0,1,idx,ends,'HERMITE',lambda:None)
  self.assertEqual(linear['queries'],hermite['queries'])
  z=hermite['records'][choices(hermite['records'])['BASE']]
  self.assertEqual(z['registration']['representation'],'HERMITE');self.assertAlmostEqual(z['metrics']['supported_length_p'],8.)
  self.assertAlmostEqual(z['outward_support_p'],4.)
  before=copy.deepcopy(state)
  def fail(_):raise OSError('seam_fixture_save_failure')
  with self.assertRaises(OSError):switch_core.commit(state,0,z,fail)
  self.assertEqual(state,before)
  after=switch_core.commit(state,0,z,lambda _:None);self.assertEqual(after['used'],{0,1})
 def test_hermite_dispatch_keeps_whole_member_and_capacity_guards(self):
  import test_overlap as f
  from frontier_core import endpoint_index
  d=f.data(False);d['asset']['means'][13,1]=1.1
  lib=sc.library(d,f.state(d),0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']),'HERMITE',lambda:None)
  self.assertFalse(any(z['common'] for z in lib['records']));self.assertIn('whole_member_residual_tangent',[z['reason'] for z in lib['records']])
  d=f.data(False);lib=sc.library(d,f.state(d),0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']),'HERMITE',lambda:None,max_prefixes=1)
  self.assertEqual(lib['status'],'NOT_RUN_OVERSIZE');self.assertFalse(any(z['common'] for z in lib['records']))
 def test_local_boundary_tangents_and_sample_bound(self):
  a=np.array([[0.,0,0],[4,0,0]]);b=np.array([[3.85,.1,0],[8,.1,0]])
  q,m=sc.hermite_register(a,b,.15);p=np.array(m['bezier_controls_p'])
  np.testing.assert_allclose((p[1]-p[0])/np.linalg.norm(p[1]-p[0]),[1,0,0],atol=1e-14)
  np.testing.assert_allclose((p[3]-p[2])/np.linalg.norm(p[3]-p[2]),[1,0,0],atol=1e-14)
  self.assertLessEqual(m['local_sample_max_spacing_p'],.25+EPS);self.assertGreater(m['sample_segments'],1)
 def test_same_endpoint_policy_under_two_seams(self):
  import test_switch as f
  from frontier_core import endpoint_index
  d=f.data();st=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves'])
  libs=[sc.library(d,st,0,1,idx,ends,r,lambda:None) for r in ('LINEAR','HERMITE')]
  self.assertEqual([x for x in libs[0]['records'] if x['relation']=='endpoint_relay'],[x for x in libs[1]['records'] if x['relation']=='endpoint_relay'])
