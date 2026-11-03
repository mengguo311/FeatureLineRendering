import unittest
from unittest.mock import patch
import numpy as np
import seam_repair_core as r
import overlap_core as oc
from geometry_base import arc,project
class RepairTests(unittest.TestCase):
 def fixture(self):
  a=np.array([[-4.,0,0],[-2.,0,0],[0.,0,0],[2.,0,0]])
  b=np.array([[0.,0,0],[2.,0,0],[4.,1,0],[7.,2.5,0]])
  return a,b,2.
 def test_member_informed_fit_beats_fixed_handles(self):
  a,b,s=self.fixture();target,_=r.geometry(a,b,s,[.46,.21]);x=(target[:-1]+target[1:])/2;t=np.diff(target,axis=0);t/=np.linalg.norm(t,axis=1)[:,None]
  fixed,_=r.geometry(a,b,s,[1/3,1/3]);before=np.mean(project(x,fixed)[1]**2)
  q,rec=r.fit(a,b,s,x,t,np.arange(len(x)),r.Budget())
  self.assertTrue(rec['success']);self.assertGreater(rec['actual_residual_evaluations'],0);self.assertLess(np.mean(project(x,q)[1]**2),before*.9)
 def test_bounds_and_fixed_outer_knots(self):
  a,b,s=self.fixture();q,m=r.geometry(a,b,s,[1/6,1/2]);np.testing.assert_array_equal(q[:2],a[:2]);np.testing.assert_array_equal(q[-1],b[-1]);self.assertLessEqual(m['sample_segments'],128)
  for h in ([0,.3],[.3,.51]):
   with self.assertRaises(ValueError):r.geometry(a,b,s,h)
 def test_reversal_and_spacing(self):
  a,b,s=self.fixture();q,m=r.geometry(a,b,s,[.4,.2]);lo=m['local_start_a_p'];hi=m['local_end_b_p'];br=b[::-1];ar=a[::-1]
  # Reverse the same fixed boundary geometry, not the unrelated attachment rule.
  c=np.asarray(m['bezier_controls_p']);np.testing.assert_allclose(c[1]-c[0],.4*m['chord_p']*oc.tangent_at(a,np.asarray(lo)))
  np.testing.assert_allclose(c[3]-c[2],.2*m['chord_p']*oc.tangent_at(b,np.asarray(hi)))
  ss=arc(q);local=q[(ss>=m['seam_begin_q_p']-1e-8)&(ss<=m['seam_end_q_p']+1e-8)];self.assertLessEqual(np.max(np.linalg.norm(np.diff(local,axis=0),axis=1)),.250001)
 def test_fixed_region_error_is_not_hidden_and_all_rows_fit(self):
  import test_overlap as f
  import contact_core
  from frontier_core import endpoint_index
  d=f.data(False);st=f.state(d);d['asset']['means'][13,1]=1.1
  lib=contact_core.library(d,st,0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']),'ARC',lambda:None)
  z=next(z for z in lib['records'] if z['reason']=='whole_member_residual_tangent');budget=r.Budget();out=r.repair_record(d,st,0,1,z,budget,lambda:None)
  self.assertEqual(budget.calls,1);self.assertFalse(out['common']);self.assertEqual(out['repair']['member_rows'],list(range(30)))
  self.assertEqual(len(out['original_rejection']['witness']['rows']),30);self.assertGreater(out['original_rejection']['witness']['distance_p'][13],1.)
  self.assertEqual(st['used'],{0});self.assertNotIn('repair',z)
 def test_noneligible_records_are_unchanged(self):
  for reason in ['common_candidate','kernel_outside_finite_domain','vertex_turn','overlap_distance']:
   z=dict(relation='overlap',reason=reason,registration={'status':'ok'},common=reason=='common_candidate')
   self.assertIs(r.repair_record({}, {},0,1,z,r.Budget(),lambda:None),z)
  z=dict(relation='endpoint_relay',reason='whole_member_residual_tangent');self.assertIs(r.repair_record({}, {},0,1,z,r.Budget(),lambda:None),z)
 def test_failed_convergence_and_exact_solver_contract(self):
  from types import SimpleNamespace
  a,b,s=self.fixture();x=np.array([[0.,0,0],[3.,.2,0]]);t=np.tile([1.,0,0],(2,1))
  def failed(fun,x0,**kw):
   self.assertEqual(kw['method'],'trf');self.assertEqual(kw['max_nfev'],64);self.assertEqual(kw['diff_step'],1e-4);self.assertEqual(kw['jac'],'2-point')
   residual=fun(x0);self.assertEqual(len(residual),6)
   return SimpleNamespace(success=False,status=0,message='fixture no convergence',x=x0,cost=float(residual@residual/2),nfev=1)
  with patch.object(r,'least_squares',side_effect=failed):q,rec=r.fit(a,b,s,x,t,np.arange(2),r.Budget())
  self.assertIsNone(q);self.assertFalse(rec['success']);self.assertEqual(rec['reason'],'optimizer_not_converged')
 def test_eval_limit_and_total_budget_are_enforced(self):
  a,b,s=self.fixture();x=np.array([[0.,0,0],[3.,.2,0]]);t=np.tile([1.,0,0],(2,1))
  def too_many(fun,x0,**kw):
   for _ in range(257):fun(x0)
  budget=r.Budget()
  with patch.object(r,'least_squares',side_effect=too_many):q,rec=r.fit(a,b,s,x,t,np.arange(2),budget)
  self.assertIsNone(q);self.assertEqual(rec['actual_residual_evaluations'],256)
  budget=r.Budget();budget.seconds=200.
  with self.assertRaisesRegex(TimeoutError,'total_optimizer_budget'):r.fit(a,b,s,x,t,np.arange(2),budget)
 def test_reflected_geometry_and_single_call_cache(self):
  a,b,s=self.fixture();q,m=r.geometry(a,b,s,[.4,.2]);qr,_=r.geometry(-a,-b,s,[.4,.2]);np.testing.assert_allclose(qr,-q)
  x=(q[:-1]+q[1:])/2;t=np.diff(q,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];budget=r.Budget();rows=np.arange(len(x))
  first=r.fit(a,b,s,x,t,rows,budget);second=r.fit(a,b,s,x,t,rows,budget);self.assertEqual(budget.calls,1);np.testing.assert_array_equal(first[0],second[0])
 def test_incomplete_optimizer_revokes_entire_frontier(self):
  import test_overlap as f
  from frontier_core import endpoint_index
  d=f.data(False);st=f.state(d);d['asset']['means'][13,1]=1.1;budget=r.Budget();budget.seconds=200.
  c={'switch':{'max_combined_prefixes':256,'max_endpoint_donors':3}}
  lib=r.library(d,st,0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']),'REPAIR',lambda:None,c,budget)
  self.assertEqual(lib['status'],'NOT_RUN_INCOMPLETE_REPAIR');self.assertFalse(lib['complete_competition']);self.assertFalse(any(z['common'] for z in lib['records']))
  z=next(z for z in lib['records'] if z.get('repair',{}).get('incomplete'));self.assertEqual(len(z['original_rejection']['witness']['rows']),30)
 def test_valid_library_never_fits_or_changes_any_original_record(self):
  import test_overlap as f
  from frontier_core import endpoint_index
  d=f.data(False);d['asset']['arc_t']=np.linspace(0,1,len(d['owner']));st=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves']);c={'switch':{'max_combined_prefixes':256,'max_endpoint_donors':3}};budget=r.Budget()
  fixed=r.library(d,st,0,1,idx,ends,'FIXED',lambda:None,c,budget);repaired=r.library(d,st,0,1,idx,ends,'REPAIR',lambda:None,c,budget)
  self.assertEqual(fixed,repaired);self.assertEqual(budget.calls,0)
