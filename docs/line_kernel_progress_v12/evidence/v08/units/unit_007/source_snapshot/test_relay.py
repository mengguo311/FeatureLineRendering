import runtime_io
import unittest,copy,numpy as np
from port_paths import Leaf,PathOracle
from frontier_core import initial,endpoint_index,choices
from relay_core import relay_candidates,commit_relay

def data(branch=False):
 leaves={};means=[];row=0
 for i,(a,b,n) in enumerate([(0,4,6),(4.2,5.4,3),(5.6,6.8,3)]+([(5.6,6.8,3)] if branch else [])):
  q=np.array([[a,0,0],[b,0,0]],float);rr=np.arange(row,row+n);row+=n;means.extend(np.linspace(q[0],q[-1],n))
  leaves[i]=Leaf(i,0,rr,np.array([i]),q,True,True,np.array([[0,b-a]],float))
 return dict(leaves=leaves,asset={'means':np.array(means)},p=1.)
class RelayTests(unittest.TestCase):
 def test_two_small_leaves_jointly_qualify(self):
  d=data();a=initial([0],10);lib=relay_candidates(d,a,0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None)
  self.assertEqual(lib['status'],'COMPLETE');z=[x for x in lib['records'] if x['common']]
  self.assertEqual(len(z),1);self.assertEqual(z[0]['donors'],[1,2]);self.assertEqual(z[0]['outward_kernels'],6);self.assertAlmostEqual(z[0]['outward_support_p'],2.4);self.assertTrue(z[0]['history']['eligible'])
 def test_batch_commit_and_rollback(self):
  d=data();a=initial([0],10);lib=relay_candidates(d,a,0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None);z=next(x for x in lib['records'] if x['common']);before=repr(a)
  def fail(_):raise OSError('fixture disk failure')
  with self.assertRaises(OSError):commit_relay(a,0,z,fail)
  self.assertEqual(repr(a),before);b=commit_relay(a,0,z,lambda _:None);self.assertEqual(b['used'],{0,1,2});self.assertEqual(b['accepted'][0],1);self.assertEqual([x[0] for x in b['chains'][0]],[0,1,2])
 def test_branch_kept_before_history(self):
  d=data(True);lib=relay_candidates(d,initial([0],10),0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None)
  self.assertEqual(sum(x['common'] for x in lib['records']),2);self.assertEqual(choices(lib['records'])['reason'],'ambiguous_gap')
 def test_failed_short_prefix_is_not_pruned(self):
  d=data();oracle=PathOracle(d['leaves']);called=[]
  def reject_short(chain):
   called.append(len(chain))
   if len(chain)==2:return False,'fixture_short_failure',{}
   return oracle(chain)
  lib=relay_candidates(d,initial([0],10),0,1,endpoint_index(d['leaves']),reject_short,lambda:None)
  self.assertIn(3,called);self.assertTrue(any(x['common'] for x in lib['records']))
 def test_overflow_no_partial_promotion(self):
  d=data();lib=relay_candidates(d,initial([0],10),0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None,max_prefixes=1)
  self.assertEqual(lib['status'],'NOT_RUN_OVERSIZE');self.assertFalse(any(x['common'] for x in lib['records']));self.assertEqual(lib['prefixes_seen'],2)
 def test_failed_support_no_activation(self):
  d=data();d['leaves'].pop(2);lib=relay_candidates(d,initial([0],10),0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None)
  self.assertFalse(any(x['common'] for x in lib['records']));self.assertEqual(lib['status'],'COMPLETE')
 def test_reverse_frontier(self):
  d=data()
  for leaf in d['leaves'].values():leaf.q=-leaf.q
  d['asset']['means']=-d['asset']['means'];lib=relay_candidates(d,initial([0],10),0,1,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None)
  self.assertEqual([x['donors'] for x in lib['records'] if x['common']],[[1,2]])
 def test_left_port_batch_order(self):
  d=data();d['leaves'][0].q=d['leaves'][0].q[::-1].copy();a=initial([0],10)
  lib=relay_candidates(d,a,0,0,endpoint_index(d['leaves']),PathOracle(d['leaves']),lambda:None)
  z=next(x for x in lib['records'] if x['common']);b=commit_relay(a,0,z,lambda _:None)
  self.assertEqual(b['chains'][0],[(2,True),(1,True),(0,False)])
 def test_atomic_batch_cold_checkpoint(self):
  from pathlib import Path
  import tempfile
  from runtime_io import sha,verify_checkpoint
  from relay_delivery import save_stage
  root=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102/units/unit_003/tests')
  d=data();a=initial([0],10);oracle=PathOracle(d['leaves'])
  d['membership']=dict(line_kernel_id=np.arange(12),edge_id=np.repeat([0,1,2],[6,3,3]),primitive_id=np.repeat([0,1,2],[6,3,3]),reason_code=np.zeros(12,np.uint8),provisional=np.ones(12,bool))
  d['owner']=d['membership']['edge_id'].copy();d['membership']['auxiliary_carrier_id']=np.tile([2,9],(12,1))
  lib=relay_candidates(d,a,0,1,endpoint_index(d['leaves']),oracle,lambda:None);z=next(x for x in lib['records'] if x['common'])
  with tempfile.TemporaryDirectory(dir=root) as name:
   r=Path(name);carrier=r/'fixture_reference';carrier.write_bytes(b'bounded fixture');c=dict(membership='fixture',carriers=str(carrier),input_files={str(carrier):sha(carrier)})
   saved={}
   def save(trial):saved['cold'],saved['groups']=save_stage(r/'accepted',c,d,trial,oracle,'fixture')
   b=commit_relay(a,0,z,save);verify_checkpoint(r/'accepted','fixture')
   self.assertEqual(saved['cold']['line_kernel_id'].tolist(),list(range(12)));self.assertEqual(saved['cold']['edge_id'].tolist(),[0]*12)
   self.assertEqual(saved['cold']['previous_edge_id'].tolist(),d['membership']['edge_id'].tolist());self.assertEqual(len(b['events']),1)
   self.assertEqual(b['events'][0]['donors'],[1,2]);self.assertEqual(a['used'],{0})
   np.testing.assert_array_equal(saved['cold']['auxiliary_carrier_id'],d['membership']['auxiliary_carrier_id'])
   self.assertEqual(saved['cold']['auxiliary_composite_id'].tolist(),[[9,-1]]*12)
if __name__=='__main__':unittest.main(verbosity=2)
