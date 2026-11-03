"""Bounded composition-change and same-source turning fixtures."""
import runtime_io
import unittest,copy
import numpy as np
from types import SimpleNamespace
import derivative_history_core as dh
import paired_history_core as ph

def fixture():
 x=np.r_[np.linspace(.1,.9,6),np.linspace(1.1,1.9,6)]
 xyz=np.c_[np.r_[x,x+2],np.zeros((24,2))]
 pid=np.array([0]*5+[1]+[0]+[1]*5+[2]+[3]*5+[2]+[3]*5)
 angles=np.where(pid%2,20.,-20.)*np.pi/180
 t=np.c_[np.cos(angles),np.sin(angles),np.zeros(24)]
 q=np.array([[0.,0,0],[2.,0,0]]);qb=q+[2,0,0]
 d=dict(p=1.,asset=dict(means=xyz,primitive_id=pid,arc_t=np.r_[x/2,x/2]),tangents=t,leaves={0:SimpleNamespace(rows=np.arange(12),q=q),1:SimpleNamespace(rows=np.arange(12,24),q=qb)})
 state=dict(chains={0:[(0,False)]},curves={0:q.tolist()},metrics={0:{'unsupported_connectors_p':[]}})
 z=dict(common=True,relation='overlap',donor=1,reverse=False,attachment_s_oriented_p=0.,gap=0.,relay=[(1,False)],history={'eligible':True})
 return d,state,z

class PairedTests(unittest.TestCase):
 def test_composition_shift_is_not_within_source_turn(self):
  d,s,z=fixture();obs=dh.observed_history(d,s,0,1,z)
  self.assertFalse(obs['eligible']);got=ph.paired_history(d,obs)
  self.assertTrue(got['eligible'])
  np.testing.assert_allclose(got['kS'],[0,0,0],atol=1e-14)
  np.testing.assert_allclose(got['t0'],obs['t0'],atol=0)
 def test_true_within_source_turn_is_retained(self):
  d,s,z=fixture();d['asset']['primitive_id'][:12]=0;d['asset']['primitive_id'][12:]=2
  d['tangents'][:6]=[1,0,0];d['tangents'][6:12]=[np.cos(.5),np.sin(.5),0];d['tangents'][12:]=d['tangents'][6]
  got=ph.paired_history(d,dh.observed_history(d,s,0,1,z));self.assertFalse(got['eligible']);self.assertEqual(got['reason'],'paired_history_reject')
 def test_parameter_reversal_is_valid(self):
  d,s,z=fixture();d['asset']['arc_t']=1-d['asset']['arc_t']
  self.assertTrue(ph.paired_history(d,dh.observed_history(d,s,0,1,z))['eligible'])
 def test_parameter_overlap_abstains_without_discarding_source(self):
  d,s,z=fixture();d['asset']['arc_t'][0]=.95
  got=ph.paired_history(d,dh.observed_history(d,s,0,1,z));self.assertFalse(got['eligible']);self.assertEqual(got['reason'],'paired_history_unknown')
 def test_no_pairs_and_insufficient_paired_rows(self):
  for mode in ('none','few'):
   d,s,z=fixture();d['asset']['primitive_id'][:6]=100
   if mode=='few':d['asset']['primitive_id'][0]=1
   got=ph.paired_history(d,dh.observed_history(d,s,0,1,z));self.assertFalse(got['eligible']);self.assertEqual(got['reason'],'paired_history_unknown')
 def test_shared_ambiguity_precedes_all_history(self):
  rec=[dict(common=True,gap=g,history={'eligible':True},observed_history={'eligible':True},paired_history={'eligible':True}) for g in (.2,.3)]
  out=ph.choices(rec);self.assertEqual(out['reason'],'ambiguous_gap');self.assertTrue(all(out[a] is None for a in ph.ARMS))
 def test_any_weak_paired_source_abstains(self):
  d,s,z=fixture();d['asset']['primitive_id'][:12]=[0]*4+[1]*2+[0]*4+[1]*2;d['tangents'][:]=[1,0,0]
  d['tangents'][[4,10]]=[0,1,0];d['tangents'][[5,11]]=[0,0,1]
  obs=dh.observed_history(d,s,0,1,z);got=ph.paired_history(d,obs)
  self.assertTrue(obs['source']['known']);self.assertFalse(got['eligible']);self.assertEqual(got['source']['reason'],'invalid_paired_source');self.assertEqual(got['source']['paired_ids'],[0,1])
 def test_real_library_two_paired_transactions_and_saved_rollback(self):
  import test_overlap as f,contact_core,switch_core,overlap_core as oc
  from frontier_core import endpoint_index
  d=f.data();d['asset']['arc_t']=d['asset']['means'][:,0]/20.;st=f.state(d);idx=oc.SegmentIndex(d['leaves']);ends=endpoint_index(d['leaves'])
  snapshots=[]
  for expected in [1,2]:
   lib=contact_core.library(d,st,0,1,idx,ends,'ARC',lambda:None);dh.annotate(d,st,0,1,lib);before=copy.deepcopy(lib)
   ph.annotate(d,st,0,1,lib);self.assertEqual(ph.remove_diagnostics(lib),before)
   choice=ph.choices(lib['records']);self.assertIsNotNone(choice['PAIRED_HISTORY']);z=lib['records'][choice['PAIRED_HISTORY']];self.assertEqual(z['donor'],expected)
   original=copy.deepcopy(st)
   def fail(trial):raise OSError('paired checkpoint rollback')
   with self.assertRaisesRegex(OSError,'paired checkpoint rollback'):switch_core.commit(st,0,z,fail)
   self.assertEqual(st,original)
   st=switch_core.commit(st,0,z,lambda trial:snapshots.append(copy.deepcopy(trial)))
  self.assertEqual(st['accepted'][0],2);self.assertEqual(len(snapshots),2);self.assertEqual(snapshots[0]['used'],{0,1});self.assertEqual(st['used'],{0,1,2})
if __name__=='__main__':unittest.main(verbosity=2)
