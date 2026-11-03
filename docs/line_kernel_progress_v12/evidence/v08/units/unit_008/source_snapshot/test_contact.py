import runtime_io
import unittest
import numpy as np
import contact_core as cc

class ContactTests(unittest.TestCase):
 def test_dense_gentle_arc_is_not_nonlocal_contact(self):
  t=np.linspace(0.,.2,11);q=np.c_[10*np.sin(t),10*(1-np.cos(t)),np.zeros(len(t))]
  self.assertTrue(cc.contact(q,'INDEX')['reject'])
  self.assertFalse(cc.contact(q,'ARC')['reject'])

 def test_same_and_adjacent_segment_domains(self):
  r=cc.contact(np.array([[0.,0,0],[2,0,0]]),'ARC')
  self.assertFalse(r['reject']);self.assertAlmostEqual(r['ARC']['witness']['distance_p'],1.)
  self.assertEqual(r['ARC']['witness']['segment_ids'],[0,0])
  r=cc.contact(np.array([[0.,0,0],[2,0,0],[0,0,0]]),'ARC')
  self.assertTrue(r['reject']);self.assertEqual(r['ARC']['witness']['segment_ids'],[0,1])
 def test_halfplane_boundary_and_empty_domain(self):
  z=np.zeros(3);x=np.array([2.,0,0]);y=np.array([0.,2,0])
  r=cc.pair_minimum(z,z,x,y,0.,0.,2.,2.,separation=1.)
  self.assertAlmostEqual(r[0],1.);self.assertAlmostEqual(r[3],0.);self.assertAlmostEqual(r[4],.5)
  r=cc.pair_minimum(z,z,x,y,0.,0.,2.,2.,separation=2.)
  self.assertAlmostEqual(r[0],4.)
  self.assertIsNone(cc.pair_minimum(z,z,x,y,0.,0.,2.,2.,separation=2.01))
 def test_parallel_hairpin_and_true_crossing(self):
  q=np.array([[0.,0,0],[3,0,0],[3,.2,0],[0,.2,0]])
  r=cc.contact(q);self.assertTrue(r['reject']);self.assertAlmostEqual(r['ARC']['witness']['distance_p'],.2)
  q=np.array([[-1.,-1,0],[1,1,0],[-1,1,0],[1,-1,0]])
  r=cc.contact(q);self.assertTrue(r['reject']);self.assertAlmostEqual(r['ARC']['witness']['distance_p'],0.)
  self.assertGreaterEqual(r['ARC']['witness']['arc_separation_p'],1.)
 def test_identical_piecewise_geometry_subdivision_invariance(self):
  for q in [np.array([[0.,0,0],[1,.03,0],[2,.1,0],[3,.21,0]]),np.array([[-1.,-1,0],[1,1,0],[-1,1,0],[1,-1,0]])]:
   fine=np.vstack([np.linspace(a,b,5)[:-1] for a,b in zip(q[:-1],q[1:])]+[q[-1:]])
   a=cc.contact(q);b=cc.contact(fine)
   self.assertEqual(a['reject'],b['reject']);self.assertAlmostEqual(a['ARC']['witness']['distance_p'],b['ARC']['witness']['distance_p'],places=12)
 def test_real_loader_phase_exception_propagates(self):
  from frontier_loader import load
  phases=[]
  def guard(phase):phases.append(phase);raise RuntimeError('phase_resource_fixture')
  with self.assertRaisesRegex(RuntimeError,'phase_resource_fixture'):load(dict(input_files={},helper_files={},source_files={}),guard)
  self.assertEqual(phases,['readiness'])
 def test_changed_contact_reaches_real_whole_member_validator(self):
  import test_overlap as f,overlap_core as oc
  from geometry_base import arc,project
  d=f.data(False);t=np.linspace(0.,.2,11);q=np.c_[10*np.sin(t),10*(1-np.cos(t)),np.zeros(len(t))]
  leaf=d['leaves'][0];leaf.q=q.copy();leaf.intervals=np.array([[0.,arc(q)[-1]]])
  points=np.array([oc.at(q,s) for s in np.linspace(0.,arc(q)[-1],len(leaf.rows))]);d['asset']['means'][leaf.rows]=points*d['p'];d['tangents'][leaf.rows]=project(points,q)[2]
  with cc.validation_policy('INDEX'):a=oc.validate(d,[(0,False)],q)
  with cc.validation_policy('ARC'):b=oc.validate(d,[(0,False)],q)
  self.assertEqual(a[1],'self_contact');self.assertTrue(b[0],b[1]);self.assertAlmostEqual(b[2]['supported_length_p'],arc(q)[-1])
  self.assertFalse(b[2]['contact_diagnostics']['ARC']['reject'])
  # Earlier geometric evidence is still authoritative in both policies.
  d['tangents'][leaf.rows[0]]=[0.,0,1.]
  with cc.validation_policy('ARC'):bad=oc.validate(d,[(0,False)],q)
  self.assertEqual(bad[1],'whole_member_residual_tangent');self.assertNotIn('contact_diagnostics',bad[2])
 def test_real_library_dispatch_early_reject_and_scoped_restore(self):
  import test_overlap as f,overlap_core as oc,switch_core
  from frontier_core import endpoint_index,choices
  d=f.data(False);st=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves']);old=(oc.validate,oc.contact_bounded)
  lib=cc.library(d,st,0,1,idx,ends,'ARC',lambda:None)
  z=lib['records'][choices(lib['records'])['BASE']]
  self.assertEqual(z['metrics']['contact_diagnostics']['policy'],'ARC');self.assertEqual((oc.validate,oc.contact_bounded),old)
  import copy
  before=copy.deepcopy(st)
  def fail(_):raise OSError('contact_checkpoint_failure')
  with self.assertRaises(OSError):switch_core.commit(st,0,z,fail)
  self.assertEqual(st,before)
  d['asset']['means'][13,1]=1.1
  lib=cc.library(d,st,0,1,idx,ends,'ARC',lambda:None)
  self.assertFalse(any(x['common'] for x in lib['records']))
  for x in lib['records']:
   if x['reason']=='whole_member_residual_tangent':self.assertNotIn('contact_diagnostics',x.get('validation',{}))
  def failguard():raise RuntimeError('contact_phase_stop')
  with self.assertRaisesRegex(RuntimeError,'contact_phase_stop'):cc.library(d,st,0,1,idx,ends,'ARC',failguard)
  self.assertEqual((oc.validate,oc.contact_bounded),old)

if __name__=='__main__':unittest.main(verbosity=2)
