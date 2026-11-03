"""48-kernel end-to-end adapter fixture; stops before any renderer is obtained."""
import runtime_io
from runtime_io import *
import unittest,tempfile,pickle,types,sys,copy
from unittest.mock import patch
import test_overlap as fixture
from frontier_loader import Carrier
from observation_core import observations,ObservationOracle
from observation_bank import export_bank
from frontier_core import endpoint_index,choices
import overlap_core as oc
import switch_core as sc
from cohort_delivery import save_stage,statistics
import seam_repair_runner as contact_runner
import paired_history_core as old_history
import contact_core
import seam_core
from cohort_core import frontier_signature
ROOT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_011/tests')
class RunnerFixture(unittest.TestCase):
 def test_real_loader_three_arms_and_control_reproduction_before_render(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as name:
   r=Path(name);raw=fixture.data(isolated=True);n=len(raw['owner']);leaves=raw['leaves'];rows=np.arange(n);reps=raw['representatives'];member_chunks=[chunk for leaf in leaves.values() for chunk in np.array_split(leaf.rows,3)]
   member_offsets=np.r_[0,np.cumsum([len(z) for z in member_chunks])];reps.update(member_rows=np.concatenate(member_chunks),member_offsets=member_offsets,kernel_rep=np.repeat(np.arange(len(member_chunks)),np.diff(member_offsets)))
   npz=lambda p,**kw:nz(r/p,**kw)
   raw['asset']['primitive_id']=np.zeros(n,np.int32);raw['membership']['primitive_id']=np.zeros(n,np.int32);raw['asset']['internal_piece_id']=np.arange(n,dtype=np.int32);raw['asset']['arc_t']=np.linspace(0,1,n)
   controls=np.repeat(raw['asset']['means'],2,axis=0);controls[1::2,0]+=1.;indices=np.arange(2*n).reshape(n,2)
   npz('gaussians.npz',**raw['asset']);npz('membership.npz',**raw['membership']);npz('representatives.npz',**reps)
   npz('controls.npz',control=controls,control_index=indices,derivative_basis=np.tile([-1.,1],(n,1)),basis=np.tile([1.,0],(n,1)),piece_control_indices=indices,parent_control_offsets=np.array([[0,2*n]]),primitive_id=raw['asset']['primitive_id'],internal_piece_id=raw['asset']['internal_piece_id'],arc_t=raw['asset']['arc_t'])
   carriers={i:Carrier(i,v.reps,v.rows,v.q,'line',True,True,(i,),v.version) for i,v in leaves.items()}
   mod=types.ModuleType('core');mod.Carrier=Carrier;sys.modules['core']=mod;oldmodule=Carrier.__module__;Carrier.__module__='core'
   try:(r/'STATE.pkl').write_bytes(pickle.dumps(dict(carriers=carriers,aux={},next_version=20)))
   finally:Carrier.__module__=oldmodule;del sys.modules['core']
   def offsets(parts):return np.r_[0,np.cumsum([len(v) for v in parts])]
   qs=[v.q for v in leaves.values()];rr=[v.rows for v in leaves.values()];ss=[v.reps for v in leaves.values()];ivs=[v.intervals for v in leaves.values()]
   npz('carriers.npz',carrier_id=np.arange(4),version=np.arange(10,14),valid=np.ones(4,bool),baseline=np.ones(4,bool),kind=np.array(['line']*4),knots=np.concatenate(qs),knot_offsets=offsets(qs),rows=np.concatenate(rr),row_offsets=offsets(rr),seedlets=np.concatenate(ss),seed_offsets=offsets(ss),origins=np.arange(4),origin_offsets=np.arange(5),supported_intervals=np.concatenate(ivs),interval_offsets=offsets(ivs))
   js(r/'decision.json',dict(fixture=True));js(r/'old_config.json',dict(decision_path=str(r/'decision.json'),decision_sha256=sha(r/'decision.json')))
   js(r/'CHECKPOINT.json',dict(complete=True,stage='M5_STATE',config_binding=sha(r/'old_config.json'),decision_sha256=sha(r/'decision.json'),files={'STATE.pkl':sha(r/'STATE.pkl')}))
   c=dict(unit_root=str(r/'run'),unit=str(r/'run'),runtime_root=str(r),runtime=str(r),max_seconds=1800,absolute_deadline_jst='2026-11-02T07:38:00+09:00',input_files={},helper_files={},source_files={},decision_path=str(r/'decision.json'),decision_sha256=sha(r/'decision.json'),predecessor_checkpoint=str(r/'CHECKPOINT.json'),predecessor_config=str(r/'old_config.json'),state=str(r/'STATE.pkl'),kernel_count=n,carrier_count=4,knot_count=sum(len(q) for q in qs),next_version=20,p=1.,scene='fixture',expected_background_assigned=n,seeds=[[i,10+i] for i in range(4)],fixed_seeds=[[i,10+i] for i in range(4)],initial_assigned=n,initial_stage=str(r/'prior'),prior_config_sha256='prior',prior_observation_config_sha256='prior',prior_observation_bank=str(r/'bank'),observation_bank=str(r/'run/scenes/fixture/observation_bank'),cohort={'per_kind_cap':16},switch={'max_combined_prefixes':256,'max_endpoint_donors':3},max_attempts=64,max_accepts_per_seed=8,views=['a','b'],external_memberships={})
   for key in ['gaussians','membership','representatives','controls','carriers']:c[key]=str(r/(key+'.npz'));c['input_files'][c[key]]=sha(c[key])
   js(r/'lineage.json',dict(events=[dict(operation='endpoint',output=[i,10+i]) for i in range(4)]));js(r/'groups.json',dict(groups=[dict(edge_id=i,version=10+i,valid=True,model='line',supported_length_p=4.,M4_contributions=[dict(kernels=12,mapped_supported_length_p=2.)]*2) for i in range(4)]));c.update(lineage=str(r/'lineage.json'),groups=str(r/'groups.json'))
   d=observations(raw,lambda:None);export_bank(r/'bank',c,d,'prior');st=oc.initial_overlap(d,list(range(4)),ObservationOracle(d['leaves'],d['ports']));save_stage(r/'prior',c,d,st,'prior');c['initial_next_version']=st['next_version'];idx=oc.SegmentIndex(d['leaves']);end=endpoint_index(d['leaves']);paths=[]
   for sid in range(4):
    for side in (0,1):
     lib=contact_core.library(d,st,sid,side,idx,end,'ARC',lambda:None);old_history.annotate(d,st,sid,side,lib);path=r/'visits'/f'{sid}_{side}.json';js(path,dict(seed=sid,side=side,version=st['versions'][sid],signature=frontier_signature(st,sid),shadow=old_history.choices(lib['records']),**lib));paths.append(str(path))
   c['control_reproductions']={arm:{'stage':str(r/'prior'),'config_sha256':'prior'} for arm in ['BASE','OBS_HISTORY']};c['replay_libraries']=paths[:2];c['seed_count']=4;c['control_identity']={'expected':{'controls':2*n,'pieces':n,'parents':1}};js(r/'cameras.json',dict(fixture=[{'view':'a'},{'view':'b'}]));c['cameras']=str(r/'cameras.json');js(r/'config.json',c)
   # The real runner and real loader execute; only the unavailable render boundary is stopped.
   with patch.object(contact_runner,'renderer',side_effect=RuntimeError('fixture_stop_before_any_render')):
    with self.assertRaisesRegex(RuntimeError,'fixture_stop_before_any_render'):contact_runner.run(c,r/'config.json')
   result=json.loads((r/'run/RUN_RESULT.json').read_text());self.assertEqual(result['fit_calls'],0);self.assertEqual(result['actual_pngs'],[])
   
   for arm in contact_runner.ARMS:self.assertIn(arm+'_FINAL_MAPPING',result['completed'])
   self.assertIn('M5_REFERENCE_MAPPING',result['completed'])
   initial=dict(np.load(r/'prior/MEMBERSHIP.npz'))
   for arm in [a+'_FINAL' for a in contact_runner.ARMS]:
    stage=r/'run/scenes/fixture/stages'/arm;verify_checkpoint(stage,sha(r/'config.json'));mm=dict(np.load(stage/'MEMBERSHIP.npz'))
    for key in initial:np.testing.assert_array_equal(initial[key],mm[key])
   self.assertTrue(json.loads((r/'run/scenes/fixture/INITIAL_LIBRARY_FREEZE.json').read_text())['complete'])
   # Exercise incremental accounting on the saved miniature mappings without rendering.
   npz('m4.npz',carrier_id=raw['owner']);c['m4_membership']=str(r/'m4.npz')
   stage=r/'run/scenes/fixture/stages/FIXED_BASE_FINAL';state=sc.hydrate(json.loads((stage/'GROWTH_STATE.json').read_text()));groups=json.loads((stage/'GROUPS.json').read_text())['groups']
   result=statistics(stage,c,d,dict(np.load(stage/'MEMBERSHIP.npz')),groups,state,sc.reopen(st),lambda:None)
   self.assertTrue(all(z['support_outside_starting_seed_p']==0 for z in result))
