"""Bounded unit004 contracts; no original full assets or rendering."""
from free_io import *
import tempfile,unittest
from unittest.mock import patch
import free_core as f
import merge_core as m
import overlap_core as o

class OverlapTests(unittest.TestCase):
 def data(self):
  x=np.c_[np.linspace(0,12,61),np.zeros((61,2))]
  return dict(x=x,t=np.tile([1.,0,0],(61,1)),valid=np.ones(61,bool),half=np.full(61,.3))
 def models(self):return {4:np.c_[np.arange(9.),np.zeros((9,2))],8:np.c_[np.arange(4.,13.),np.zeros((9,2))]}
 def proposal(self,d,mm):
  cache={};tables=o.compatibility(d,mm,cache);ps,stats=o.enumerate_candidates(d,mm,tables);self.assertTrue(ps);return ps[0],tables
 def test_complete_compatibility_not_top_two_and_cost_ties(self):
  d=self.data();mm={i:np.array([[0.,0,0],[6,0,0],[12,0,0]]) for i in range(4)};cache={};tab=o.compatibility(d,mm,cache)
  self.assertEqual(len(tab),4)
  for z in tab.values():self.assertEqual(len(z['rows']),61);self.assertEqual(int(z['segment'][30]),0)
  ps,stats=o.enumerate_candidates(d,mm,tab);self.assertEqual(len(ps),6);self.assertEqual(len(stats['a']),6)
  self.assertTrue(np.all(f.assign(d['x'],d['t'],d['valid'],mm)['edge_id']==-1))
 def test_partial_overlap_no_backtracking_or_double_length(self):
  d=self.data();mm=self.models();p,t=self.proposal(d,mm);q,meta=o.template(mm,p,t)
  self.assertAlmostEqual(f.arc(q)[-1],12);self.assertTrue(np.all(np.diff(q[:,0])>0));self.assertEqual(meta['left_owner'],4);self.assertEqual(meta['right_owner'],8)
 def test_reverse_orientation_and_containment(self):
  d=self.data();mm=self.models();mm[8]=mm[8][::-1];p,t=self.proposal(d,mm);q,meta=o.template(mm,p,t);self.assertTrue(meta['reverse_b']);self.assertAlmostEqual(q[-1,0],12)
  mm={4:np.c_[np.arange(13.),np.zeros((13,2))],8:np.c_[np.arange(3.,10.),np.zeros((7,2))]};p,t=self.proposal(d,mm);q,meta=o.template(mm,p,t);self.assertEqual(meta['left_owner'],4);self.assertEqual(meta['right_owner'],4);np.testing.assert_allclose(q,mm[4])
 def test_shared_support_and_physical_distance_rejection(self):
  d=self.data();d['x'][:,1]=.6;mm={4:np.c_[np.arange(13.),np.zeros((13,2))],8:np.c_[np.arange(13.),np.full(13,1.2),np.zeros(13)]};p,t=self.proposal(d,mm)
  with self.assertRaisesRegex(o.TemplateError,'overlap_distance'):o.template(mm,p,t)
 def test_invalid_tangents_excluded_and_cache_versions(self):
  d=self.data();d['valid'][:10]=False;mm=self.models();cache={};t=o.compatibility(d,mm,cache);self.assertFalse(np.any(t[4]['rows']<10));v=m.version(mm[4]);mm[4]=mm[4]+[0,.1,0];o.compatibility(d,mm,cache);self.assertIn((4,v),cache);self.assertIn((4,m.version(mm[4])),cache)
 def test_real_trial_free_reassignment_and_rollback(self):
  d=self.data();mm=self.models();a=f.assign(d['x'],d['t'],d['valid'],mm);old={k:v.copy() for k,v in a.items()};p,t=self.proposal(d,mm);r=o.trial(d,mm,a,10,p,t)
  self.assertTrue(r['accepted'],r['reason']);self.assertLess(r['after']['total'],r['before']['total']);self.assertTrue(np.all(r['assignment']['edge_id']==10))
  for k in old:np.testing.assert_array_equal(a[k],old[k])
  with patch.object(f,'geometry_ok',return_value=(False,'fixture_geometry')):r=o.trial(d,mm,a,10,p,t)
  self.assertFalse(r['accepted']);self.assertIsNone(r['raw']);self.assertEqual(r['next_id'],10)
 def test_real_energy_rejection_and_raw_progress(self):
  d=self.data();mm=self.models();a=f.assign(d['x'],d['t'],d['valid'],mm);p,t=self.proposal(d,mm);phases=[]
  with patch.object(f,'validate_support',side_effect=RuntimeError('after_raw')):
   with self.assertRaisesRegex(RuntimeError,'after_raw'):o.trial(d,mm,a,10,p,t,progress=lambda ph,r:phases.append(ph))
  self.assertEqual(phases,['template','fitted','raw'])
 def test_complete_graph_guard_failure_propagates(self):
  def guard():raise TimeoutError('coverage_incomplete')
  self.assertRaisesRegex(TimeoutError,'coverage_incomplete',o.compatibility,self.data(),self.models(),{},guard)
 def test_real_loader_and_runner_preserve_exact_control(self):
  from test_merge import MergeTests
  import overlap_runner as runner
  with tempfile.TemporaryDirectory() as td:
   p=Path(td);c=MergeTests().runner_fixture(p)
   # Fixture predecessor has nonoverlapping endpoint leaves: valid zero-overlap result.
   with patch.object(runner,'deliver',return_value=dict(fixture_render_not_run=True)):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0);out=Path(c['unit_root']);mm,aa,_=cold_stage(out/'scenes/fixture/stages/NO_OVERLAP_MERGE','fixture');_,old,_=cold_stage(c['predecessor_stage'],c['predecessor_config_sha256'])
   for k in runner.FIELDS:np.testing.assert_array_equal(aa[k],old[k])
   self.assertTrue((out/'scenes/fixture/stages/OVERLAP_FINAL/CHECKPOINT.json').exists())
 def test_later_failure_preserves_real_control_checkpoint(self):
  from test_merge import MergeTests
  import overlap_runner as runner
  with tempfile.TemporaryDirectory() as td:
   c=MergeTests().runner_fixture(Path(td))
   with patch.object(runner.o,'compatibility',side_effect=RuntimeError('fixture_later_failure')),patch.object(runner,'deliver',return_value={}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,1);out=Path(c['unit_root']);cold_stage(out/'scenes/fixture/stages/NO_OVERLAP_MERGE','fixture');self.assertFalse((out/'scenes/fixture/stages/OVERLAP_FINAL').exists())

 def overlap_runner_fixture(self,p):
  from test_merge import MergeTests
  c=MergeTests().runner_fixture(p)
  with np.load(c['gaussians']) as z:asset={k:z[k] for k in z.files}
  asset['means']=np.c_[np.r_[np.linspace(0,20,62),50.],np.zeros((63,2))];ap=p/'overlap_asset.npz';np.savez(ap,**asset);c['gaussians']=str(ap);c['input_files'][str(ap)]=sha(ap)
  d=load(c,lambda phase:None);mm={4:np.c_[np.arange(13.),np.zeros((13,2))],8:np.c_[np.arange(8.,21.),np.zeros((13,2))]};a=f.assign(d['x'],d['t'],d['valid'],mm)
  st=p/'overlap_previous';save_stage(st,d,mm,a,[],10,c['predecessor_config_sha256'],{});c['predecessor_stage']=str(st);return c
 def test_real_overlap_runner_accept_checkpoint_and_shared_receipt(self):
  import overlap_runner as runner
  with tempfile.TemporaryDirectory() as td:
   c=self.overlap_runner_fixture(Path(td))
   with patch.object(runner,'deliver',return_value={'fixture_render_not_run':True}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0);out=Path(c['unit_root']);mm,a,_=cold_stage(out/'scenes/fixture/stages/OVERLAP_FINAL','fixture');self.assertEqual(len(mm),1);self.assertEqual(np.sum(a['edge_id']>=0),62)
   for name in ['SHARED_SUPPORT.npz','PARAMETERIZATION.json','PROGRESS_RAW_DELTA.npz','CHECKPOINT.json']:self.assertTrue((out/'trials/TRIAL_000'/name).exists(),name)
   self.assertTrue((out/'candidates/GEN_000/CHECKPOINT.json').exists());self.assertTrue((out/'scenes/fixture/stages/OVERLAP_001/CHECKPOINT.json').exists())
 def test_complete_relation_matches_direct_all_segment_cost(self):
  d=self.data();mm=self.models();mm[12]=np.array([[0.,.4,0],[6,.4,0],[12,.2,0]]);tab=o.compatibility(d,mm,{})
  for mid,q in mm.items():
   cost=m.row_cost(d['x'],d['t'],q);rr=np.flatnonzero(cost<1);np.testing.assert_array_equal(tab[mid]['rows'],rr);np.testing.assert_allclose(tab[mid]['cost'],cost[rr],rtol=0,atol=1e-14)
 def test_overlap_trial_energy_rejection_preserves_all_aux(self):
  with tempfile.TemporaryDirectory() as td:
   c=self.overlap_runner_fixture(Path(td));d=load(c,lambda phase:None);from merge_runner import restore
   mm,a,nxt=restore(c,d,lambda phase:None);p,t=self.proposal(d,mm);old={k:v.copy() for k,v in a.items()}
   with patch.object(f,'irls_update',side_effect=lambda x,q:q+[0,.5,0]):r=o.trial(d,mm,a,nxt,p,t)
   self.assertFalse(r['accepted']);self.assertEqual(r['reason'],'no_energy_decrease')
   for k in old:np.testing.assert_array_equal(a[k],old[k])
