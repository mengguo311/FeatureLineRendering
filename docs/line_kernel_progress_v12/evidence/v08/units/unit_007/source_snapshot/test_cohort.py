import runtime_io
import copy,json,unittest,tempfile
from pathlib import Path
import numpy as np
import cohort_core as cc
import test_overlap as fixture
import test_switch
from observation_core import ObservationOracle
from runtime_io import sha
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_006/tests')

class CohortTests(unittest.TestCase):
 def test_new_seed_is_added_without_new_version_or_old_seam_loss(self):
  d=fixture.data(isolated=True);st=fixture.state(d);st['curves'][0][3][1]=.02;before=copy.deepcopy(st)
  nxt,receipt=cc.augment(st,d,[{'carrier_id':1,'version':11,'model':'line'}],ObservationOracle(d['leaves'],d['ports']))
  self.assertEqual(set(nxt['chains']),{0,1})
  self.assertEqual(nxt['versions'][1],11);self.assertEqual(nxt['next_version'],st['next_version'])
  self.assertEqual(nxt['curves'][0],st['curves'][0]);self.assertEqual(nxt['used'],{0,1});self.assertEqual(st,before)
  self.assertEqual(receipt[0]['status'],'ready')

 def test_queue_exact_versions_used_contributions_and_ties(self):
  events=[];groups=[];versions={}
  for i,kind,support in [(1,'line',8.),(2,'line',8.),(3,'line',10.),(4,'polyline',5.),(5,'polyline',20.),(6,'polyline',30.)]:
   events.append(dict(operation='endpoint',output=[i,10+i]));versions[i]=10+i
   groups.append(dict(edge_id=i,version=10+i,model=kind,valid=True,supported_length_p=support,M4_contributions=[dict(kernels=12,mapped_supported_length_p=2.)]*2))
  versions[3]=99;groups[4]['M4_contributions'][0]=dict(kernels=11,mapped_supported_length_p=20.)
  selected,receipt=cc.select_cohort(events,groups,versions,{6},1)
  self.assertEqual([x['carrier_id'] for x in selected],[1,4])
  reasons={r['carrier_id']:r['reason'] for r in receipt['records']}
  self.assertEqual(reasons[2],'unselected_cohort_cap');self.assertEqual(reasons[3],'inactive_or_version_mismatch');self.assertEqual(reasons[5],'insufficient_M4_contributions');self.assertEqual(reasons[6],'starting_used_leaf')

 def test_selected_validation_failure_remains_protected_without_replacement(self):
  d=fixture.data(isolated=True);st=fixture.state(d);d['leaves'][1].valid=False
  nxt,receipt=cc.augment(st,d,[dict(carrier_id=1,version=11,model='line')],ObservationOracle(d['leaves'],d['ports']))
  self.assertEqual(set(nxt['chains']),{0,1});self.assertEqual(nxt['used'],{0,1});self.assertEqual(receipt[0]['status'],'NOT_RUN');self.assertIn((1,0),nxt['stopped']);self.assertNotIn(2,nxt['chains'])

 def test_new_seed_protection_removes_donor_and_invalidates_cached_library(self):
  import overlap_core as oc
  from frontier_core import endpoint_index
  import switch_core as sc
  d=fixture.data(False);st=fixture.state(d);sig=cc.frontier_signature(st,0)
  old=sc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']));self.assertTrue(any(z['common'] for z in old['records']))
  nxt,_=cc.augment(st,d,[dict(carrier_id=1,version=11,model='line')],ObservationOracle(d['leaves'],d['ports']))
  new=sc.candidates(d,nxt,0,1,oc.SegmentIndex(d['leaves']),endpoint_index(d['leaves']));self.assertFalse(any(z['common'] for z in new['records']));self.assertNotEqual(sig,cc.frontier_signature(nxt,0))

 def test_exact_cold_membership_at_augmentation_and_checkpoint_on_accept(self):
  from cohort_delivery import save_stage
  from runtime_io import verify_checkpoint
  import switch_core as sc
  import overlap_core as oc
  d=fixture.data(isolated=True);st=fixture.state(d)
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);f=r/'carrier';f.write_bytes(b'fixture');c=dict(membership='fixture',carriers=str(f),input_files={str(f):sha(f)})
   before,_=save_stage(r/'old',c,d,st,'old')
   nxt,_=cc.augment(st,d,[dict(carrier_id=1,version=11,model='line')],ObservationOracle(d['leaves'],d['ports']))
   after,_=save_stage(r/'initial',c,d,nxt,'new')
   self.assertEqual(after.keys(),before.keys())
   for k in before:np.testing.assert_array_equal(before[k],after[k])
   verify_checkpoint(r/'initial','new');self.assertEqual(nxt['next_version'],st['next_version'])
  d=fixture.data(False);st=fixture.state(d);lib=oc.candidates(d,st,0,1,oc.SegmentIndex(d['leaves']));z=next(v for v in lib['records'] if v['common'])
  # Actual transaction core must preserve original input when checkpoint fails.
  z.update(relation='overlap',donors=[z['donor']],donor_versions=[z['donor_version']],relay=[(z['donor'],z['reverse'])],total_gap=z['gap'])
  old=copy.deepcopy(st)
  def fail(_):raise OSError('cohort checkpoint fixture')
  with self.assertRaises(OSError):sc.commit(st,0,z,fail)
  self.assertEqual(st,old)

 def test_actual_prior_library_replay_and_no_post_selection_substitution(self):
  import overlap_core as oc,switch_core as sc
  from frontier_core import endpoint_index,choices
  from runtime_io import js
  d=fixture.data(isolated=True);st=fixture.state(d);idx=oc.SegmentIndex(d['leaves']);end=endpoint_index(d['leaves'])
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   paths=[]
   for side in (0,1):
    lib=sc.candidates(d,st,0,side,idx,end);path=Path(name)/f'{side}.json';js(path,dict(seed=0,side=side,version=st['versions'][0],shadow=choices(lib['records']),**lib));paths.append(str(path))
   receipt,context=cc.replay_visits(paths,d,st,idx,end,lambda:None)
   self.assertEqual(receipt['status'],'MATCHED');self.assertEqual(len(receipt['visits']),2)

 def test_diagnostic_selection_is_new_cohort_only_and_damage_explicit(self):
  from cohort_delivery import choose_visuals
  c={'fixed_seeds':[[0,1]]};selected=[dict(carrier_id=i,model='line' if i<5 else 'polyline') for i in range(1,9)]
  inc={'BASE':[dict(seed=i,support_outside_starting_seed_p=float(i)) for i in range(1,9)]}
  baseline=np.arange(9);end=baseline.copy();end[1]=-1
  saved={'NO_FURTHER_GROWTH':({'edge_id':baseline},[]),'BASE':({'edge_id':end},[]),'HISTORY':({'edge_id':baseline},[])}
  ids,receipt=choose_visuals(c,selected,inc,saved);self.assertEqual(ids,[0,1,2,3,4,6,7,8]);self.assertFalse(receipt['zero_damage_no_fabricated_damage_case'])

 def test_runner_phase_aware_loader_entrypoint(self):
  # Exercise the exact imported loader used by the new runner, not a replaced load function.
  import cohort_runner
  def guard(phase):self.assertEqual(phase,'readiness');raise TimeoutError('cohort phase propagation')
  with self.assertRaisesRegex(TimeoutError,'cohort phase propagation'):
   cohort_runner.load(dict(input_files={},helper_files={},source_files={}),guard)

if __name__=='__main__':
 import sys,test_loader_fixture
 fixture.ROOT=ROOT;test_switch.ROOT=ROOT;test_loader_fixture.ROOT=ROOT
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(CohortTests)
 if '--red' not in sys.argv:
  import test_cohort_runner
  test_cohort_runner.ROOT=ROOT
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(test_cohort_runner.RunnerFixture))
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(test_switch.SwitchTests))
  suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(fixture))
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
