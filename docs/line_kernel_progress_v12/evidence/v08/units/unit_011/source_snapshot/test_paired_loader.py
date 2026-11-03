"""Control schema and phase-aware real-loader interface fixtures."""
import runtime_io
import unittest,copy
import numpy as np
from paired_loader import validate_control_identity,load

def fixture():
 n=6;cp=np.c_[np.arange(4),np.zeros((4,2))];pieces=np.array([[0,1],[1,2],[2,3]]);piece=np.repeat(np.arange(3),2);idx=pieces[piece];basis=np.tile([[.75,.25],[.25,.75]],(3,1));pid=np.zeros(n,np.int32);arc=np.linspace(0,1,n)
 a=dict(means=(cp[idx]*basis[:,:,None]).sum(1),primitive_id=pid.copy(),internal_piece_id=piece.copy(),arc_t=arc.copy())
 c=dict(control=cp,piece_control_indices=pieces,parent_control_offsets=np.array([[0,4]]),control_index=idx,basis=basis,derivative_basis=np.tile([-1.,1.],(n,1)),primitive_id=pid,internal_piece_id=piece,arc_t=arc)
 return a,c,dict(controls=4,pieces=3,parents=1)
class SchemaTests(unittest.TestCase):
 def test_exact_basis_and_phase_callback(self):
  a,c,e=fixture();phases=[];r=validate_control_identity(a,c,phases.append,e);self.assertTrue(r['verified']);self.assertEqual(set(phases),{'readiness'})
 def test_each_identity_mismatch_blocks(self):
  for key in ('primitive_id','internal_piece_id','arc_t'):
   a,c,e=fixture();a[key][0]+=1
   with self.assertRaises(AssertionError):validate_control_identity(a,c,lambda phase:None,e)
 def test_piece_and_parent_ranges_block(self):
  for key in ('control_index','parent_control_offsets'):
   a,c,e=fixture();c[key][0,-1]=0
   with self.assertRaises(AssertionError):validate_control_identity(a,c,lambda phase:None,e)
 def test_center_or_nonfinite_basis_blocks(self):
  a,c,e=fixture();a['means'][0,0]+=1e-8
  with self.assertRaises(AssertionError):validate_control_identity(a,c,lambda phase:None,e)
  a,c,e=fixture();c['basis'][0,0]=np.nan
  with self.assertRaises(AssertionError):validate_control_identity(a,c,lambda phase:None,e)
 def test_real_loader_guard_propagates_before_asset_access(self):
  phases=[]
  def guard(phase):phases.append(phase);raise TimeoutError('phase_resource_stop')
  with self.assertRaisesRegex(TimeoutError,'phase_resource_stop'):load(dict(input_files={},helper_files={},source_files={}),guard)
  self.assertEqual(phases,['readiness'])
