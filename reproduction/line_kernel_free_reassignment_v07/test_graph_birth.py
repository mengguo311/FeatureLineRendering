"""Unit005 bounded first tests. No full assets or renders."""
from free_io import *
import unittest,tempfile
from unittest.mock import patch
import free_core as f
import merge_core as m
import graph_birth_core as g

class GraphBirthTests(unittest.TestCase):
 def data(self,n=63):
  x=np.c_[np.linspace(.1,12.9,n),np.full(n,.1),np.full(n,.1)]
  return dict(x=x,t=np.tile([1.,0,0],(n,1)),valid=np.ones(n,bool),half=np.full(n,.3))
 def test_modes_keep_crossing_and_opposite_directions_together(self):
  d=self.data(4);d['x'][:]=[.2,.2,.2];d['t']=np.array([[1.,0,0],[-1.,0,0],[0,1.,0],[0,-1.,0]])
  z=g.build_modes(d,np.full(4,-1));self.assertEqual(len(z['position']),2);self.assertEqual(z['offsets'].tolist(),[0,2,4]);self.assertEqual(z['members'].tolist(),[0,1,2,3])
 def test_complete_adjacency_no_nearest_k(self):
  d=self.data(42);d['x'][0]=[.8,.2,.2];d['x'][1:]=np.c_[np.full(41,1.8),np.linspace(.201,.24,41),np.full(41,.2)]
  z=dict(position=d['x'],tangent=d['t'],voxel=np.r_[0,np.arange(1,42)],representative=np.arange(42),has_unknown=np.ones(42,bool))
  a=g.build_graph(z);self.assertEqual(np.sum(a['source']==0),41)
 def test_complete_seed_bank_and_path(self):
  d=self.data();z=g.build_modes(d,np.full(len(d['x']),-1));a=g.build_graph(z);seeds,cov,meta=g.select_seeds(z,a);self.assertTrue(seeds)
  paths,receipts=g.propose(z,a,seeds);self.assertTrue(paths);self.assertGreaterEqual(len(paths[0]['modes']),6);self.assertEqual(len(set(z['voxel'][paths[0]['modes']])),len(paths[0]['modes']))
  self.assertEqual(cov['offsets'][-1],len(cov['voxel_ids']));self.assertTrue(meta['complete_coverage_bank'])
 def test_dijkstra_exact_equal_tie(self):
  a=dict(source=np.array([0,0,1,2]),target=np.array([1,2,3,3]),weight=np.ones(4),length=np.ones(4),state_count=4)
  dist,prev=g.shortest(a,0);self.assertEqual(prev[3],1);self.assertEqual(dist[3],2)
 def test_birth_accepts_unknown_and_rejects_duplicate_without_mutation(self):
  d=self.data();q=np.array([[.1,.1,.1],[12.9,.1,.1]]);a=f.assign(d['x'],d['t'],d['valid'],{});old={k:v.copy() for k,v in a.items()}
  r=g.trial(d,{},a,10,q);self.assertTrue(r['accepted'],r['reason']);self.assertLess(r['after']['total'],r['before']['total']);self.assertEqual(r['surviving_children'],[10])
  for k in a:np.testing.assert_array_equal(a[k],old[k])
  mm=r['models'];aa=r['assignment'];r2=g.trial(d,mm,aa,r['next_id'],mm[10]);self.assertFalse(r2['accepted']);self.assertEqual(r2['reason'],'birth_support_not_one_piece')
 def test_graph_guard_failure_not_silently_partial(self):
  def guard():raise TimeoutError('incomplete_graph')
  z=g.build_modes(self.data(),np.full(63,-1));self.assertRaisesRegex(TimeoutError,'incomplete_graph',g.build_graph,z,guard)
 def test_fit_failure_preserves_state_and_raw_failure_progress(self):
  d=self.data();a=f.assign(d['x'],d['t'],d['valid'],{});q=np.array([[.1,.1,.1],[12.9,.1,.1]])
  with patch.object(f,'geometry_ok',return_value=(False,'fixture')):r=g.trial(d,{},a,10,q)
  self.assertFalse(r['accepted']);self.assertEqual(r['next_id'],10)
  phases=[]
  with patch.object(f,'validate_support',side_effect=RuntimeError('after_raw')):
   with self.assertRaisesRegex(RuntimeError,'after_raw'):g.trial(d,{},a,10,q,progress=lambda ph,r:phases.append(ph))
  self.assertIn('raw',phases)
 def runner_fixture(self,p):
  from test_merge import MergeTests
  c=MergeTests().runner_fixture(p)
  with np.load(c['gaussians']) as z:asset={k:z[k] for k in z.files}
  asset['means']=np.c_[np.linspace(.1,20.9,63),np.full(63,.1),np.full(63,.1)];ap=p/'graph_asset.npz';np.savez(ap,**asset);c['gaussians']=str(ap);c['input_files'][str(ap)]=sha(ap)
  phases=[];d=load(c,lambda phase:phases.append(phase));self.assertTrue(phases);self.assertEqual(set(phases),{'readiness'})
  mm={4:np.c_[np.arange(7.),np.full(7,.6),np.full(7,.1)],8:np.c_[np.arange(14.,21.),np.full(7,.6),np.full(7,.1)]};a=f.assign(d['x'],d['t'],d['valid'],mm);st=p/'graph_previous';save_stage(st,d,mm,a,[],10,c['predecessor_config_sha256'],{});c['predecessor_stage']=str(st);return c
 def test_real_loader_runner_and_accepted_full_checkpoint(self):
  import graph_birth_runner as runner
  with tempfile.TemporaryDirectory() as td:
   c=self.runner_fixture(Path(td))
   with patch.object(runner,'deliver',return_value=dict(fixture_render_not_run=True)):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0);out=Path(c['unit_root']);mm,a,_=cold_stage(out/'scenes/fixture/stages/BIRTH_FINAL','fixture');_,old,_=cold_stage(c['predecessor_stage'],c['predecessor_config_sha256']);_,control,_=cold_stage(out/'scenes/fixture/stages/NO_BIRTH','fixture')
   for k in runner.FIELDS:np.testing.assert_array_equal(old[k],control[k])
   self.assertEqual(len(a['edge_id']),63);self.assertEqual(len(mm),1);self.assertTrue(np.all(a['edge_id']==10));self.assertTrue((out/'scenes/fixture/stages/BIRTH_001/CHECKPOINT.json').exists());self.assertTrue((out/'graph/CHECKPOINT.json').exists());self.assertTrue((out/'trials/TRIAL_000/PROGRESS_RAW_DELTA.npz').exists())
 def test_real_loader_guard_phase_exception_not_whole_loader_mock(self):
  import graph_birth_runner as runner
  phases=[]
  def guard(phase):phases.append(phase);raise TimeoutError('resource:'+phase)
  with self.assertRaisesRegex(TimeoutError,'resource:readiness'):runner.load({},guard)
  self.assertEqual(phases,['readiness'])
 def test_later_failure_keeps_control_and_no_incomplete_promotion(self):
  import graph_birth_runner as runner
  with tempfile.TemporaryDirectory() as td:
   c=self.runner_fixture(Path(td))
   with patch.object(runner.g,'propose',side_effect=TimeoutError('candidate_bank_incomplete')),patch.object(runner,'deliver',return_value={}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,0);out=Path(c['unit_root']);cold_stage(out/'scenes/fixture/stages/NO_BIRTH','fixture');self.assertFalse((out/'scenes/fixture/stages/BIRTH_FINAL').exists());self.assertFalse((out/'graph/CHECKPOINT.json').exists());r=json.loads((out/'RUN_RESULT.json').read_text());self.assertEqual(r['execution_state'],'partial');self.assertEqual(r['attempts_started'],0)
 def test_unsupported_gap_birth_rejected_no_member_clipping(self):
  d=self.data();d['x'][31:,0]+=5;aa=f.assign(d['x'],d['t'],d['valid'],{});q=np.array([[.1,.1,.1],[17.9,.1,.1]])
  r=g.trial(d,{},aa,10,q);self.assertFalse(r['accepted']);self.assertIn(r['reason'],['birth_support_not_one_piece','geometry:vertex_turn','geometry:window_turn'])
 def test_all_row_template_compatibility_and_energy_rejection(self):
  d=self.data();q=np.array([[.1,.1,.1],[12.9,.1,.1]]);mm={0:f.resample(q)+[0,.01,0]};a=f.assign(d['x'],d['t'],d['valid'],mm);old={k:v.copy() for k,v in a.items()}
  r=g.trial(d,mm,a,10,q);self.assertEqual(len(r['fit_rows']),63);self.assertFalse(r['accepted'])
  for k in old:np.testing.assert_array_equal(a[k],old[k])
 def test_complete_graph_matches_all_pairs_oriented_oracle(self):
  d=self.data(20);d['x']=np.c_[np.arange(20)*.8,np.sin(np.arange(20)*.03),np.full(20,.1)];d['t']=np.c_[np.ones(20),.0375*np.cos(np.arange(20)*.03),np.zeros(20)];d['t']/=np.linalg.norm(d['t'],axis=1)[:,None];z=g.build_modes(d,np.full(20,-1));graph=g.build_graph(z);expected={}
  for i in range(2*len(z['position'])):
   for j in range(2*len(z['position'])):
    if z['voxel'][i//2]==z['voxel'][j//2]:continue
    v=z['position'][j//2]-z['position'][i//2];length=np.linalg.norm(v)
    if length<=f.EPS or length>1.5+f.EPS:continue
    direction=v/length;ta=z['tangent'][i//2]*(1 if i%2==0 else -1);tb=z['tangent'][j//2]*(1 if j%2==0 else -1)
    aa=np.degrees(np.arccos(np.clip(ta@direction,-1,1)));bb=np.degrees(np.arccos(np.clip(tb@direction,-1,1)));cc=np.degrees(np.arccos(np.clip(ta@tb,-1,1)))
    if aa<=35+f.EPS and bb<=35+f.EPS and cc<=30+f.EPS:expected[i,j]=length*(1+(cc/30)**2+.25*(aa*aa+bb*bb)/35**2)
  got={(int(i),int(j)):float(w) for i,j,w in zip(graph['source'],graph['target'],graph['weight'])};self.assertEqual(set(expected),set(got))
  for k in expected:self.assertAlmostEqual(expected[k],got[k],places=12)
 def test_mode_members_all_rows_once_invalid_excluded(self):
  d=self.data();d['valid'][9]=False;z=g.build_modes(d,np.full(63,-1));np.testing.assert_array_equal(np.sort(z['members']),np.flatnonzero(d['valid']));self.assertEqual(len(np.unique(z['members'])),62)
 def test_coverage_selection_exact_greedy_and_voxel_dedup(self):
  d=self.data();z=g.build_modes(d,np.full(63,-1));a=g.build_graph(z);seeds,bank,meta=g.select_seeds(z,a);covered=set();remaining=list(map(int,bank['candidate_modes']));expected=[]
  covers={int(mid):set(bank['voxel_ids'][bank['offsets'][j]:bank['offsets'][j+1]]) for j,mid in enumerate(bank['candidate_modes'])}
  while remaining and len(expected)<64:
   mid=min(remaining,key=lambda i:(-len(covers[i]-covered),z['representative'][i]));gain=len(covers[mid]-covered)
   if not gain:break
   expected.append(mid);covered.update(covers[mid]);remaining.remove(mid)
  self.assertEqual(seeds,expected);self.assertEqual(meta['covered_unknown_voxels'],len(covered))
 def test_later_raw_failure_retains_real_control_checkpoint(self):
  import graph_birth_runner as runner
  with tempfile.TemporaryDirectory() as td:
   c=self.runner_fixture(Path(td))
   with patch.object(f,'validate_support',side_effect=RuntimeError('after_raw_science')),patch.object(runner,'deliver',return_value={}):rc=runner.run(c,'fixture')
   self.assertEqual(rc,1);out=Path(c['unit_root']);cold_stage(out/'scenes/fixture/stages/NO_BIRTH','fixture');self.assertTrue((out/'trials/TRIAL_000/PROGRESS_RAW_DELTA.npz').exists());self.assertFalse((out/'scenes/fixture/stages/BIRTH_001').exists())
 def test_birth_diagnostics_contributors_without_images(self):
  import graph_birth_runner as runner
  import graph_birth_delivery as delivery
  with tempfile.TemporaryDirectory() as td:
   c=self.runner_fixture(Path(td))
   with patch.object(runner,'deliver',return_value={}):self.assertEqual(runner.run(c,'fixture'),0)
   d=load(c,lambda phase:None);out=Path(c['unit_root']);mm,a,_=cold_stage(out/'scenes/fixture/stages/BIRTH_FINAL','fixture');old=np.full(63,-1);gg=delivery.groups(d,mm,a,old,lambda:None);delivery.enrich(c,d,mm,a,gg,'fixture',lambda:None)
   self.assertEqual(len(gg),1);self.assertTrue(gg[0]['new_graph_birth']);self.assertTrue(gg[0]['existing_model_contributions']);self.assertGreater(gg[0]['outward_largest_input_domain_proxy_p'],4.)
