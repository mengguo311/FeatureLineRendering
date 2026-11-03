import runtime_io
import unittest,copy,tempfile
import numpy as np
import whole_core as w
class WholeTests(unittest.TestCase):
 def test_entire_old_segment_can_move_and_original_rows_stay_fixed(self):
  q=np.c_[np.arange(7.),np.zeros((7,2))];x=np.c_[np.linspace(0,6,80),np.full(80,.3),np.zeros(80)];before=x.copy()
  fitted,_=w.fit(q,x,np.ones(7,bool));self.assertGreater(fitted[1,1],.1);np.testing.assert_array_equal(x,before)
 def test_local_fixed_knots_and_no_hard_old_angle_gate(self):
  q=np.c_[np.arange(7.),np.zeros((7,2))];x=q+[0,.3,0];mask=np.arange(7)>3;f,_=w.fit(q,x,mask);np.testing.assert_array_equal(f[~mask],q[~mask]);self.assertGreater(f[-2,1],.1)
 def test_exact_whole_segment_query_not_endpoint_query(self):
  objects={0:dict(q=np.array([[-5.,0,0],[5,0,0]]),available=True),1:dict(q=np.array([[0.,1,0],[0,3,0]]),available=True),2:dict(q=np.array([[0.,5,0],[0,6,0]]),available=True)}
  result=w.CompleteIndex(objects).query(objects[0]['q'],{0});self.assertEqual([z[0] for z in result],[1]);self.assertAlmostEqual(result[0][1],1.)
 def test_exact_segment_crossing_and_parallel(self):
  got=w.segment_distances(np.array([-2.,0,0]),np.array([2.,0,0]),np.array([[0.,-2,0],[-1,2,0],[4,0,0]]),np.array([[0.,2,0],[1,2,0],[6,0,0]]));np.testing.assert_allclose(got,[0,2,2])
 def test_best_donor_is_not_nearest_and_failed_nearest_continues(self):
  rec=[dict(donor=i,relation='endpoint',direction=0,distance_p=i,connectable=i!=0,metrics={'score':3-i}) for i in range(3)];self.assertEqual(w.best(rec),2)
 def test_reversal_registration_keeps_finite_union(self):
  a=np.array([[0.,0,0],[4,0,0]]);b=np.array([[7.,0,0],[2,0,0]]);p=w.proposals(a,b);z=next(z for z in p if z['relation']=='overlap' and z['direction']==1);self.assertEqual(z['reason'],'template');self.assertAlmostEqual(w.arc(z['template'])[-1],7.)
 def test_capacity_is_incomplete_not_no_connection(self):
  with self.assertRaises(w.Incomplete):w.proposals(np.array([[0.,0,0],[4,0,0]]),np.array([[2.,0,0],[300,0,0]]))
 def test_true_support_closure_and_false_proximity(self):
  angles=np.linspace(0,2*np.pi,65);q=np.c_[2*np.cos(angles),2*np.sin(angles),np.zeros(len(angles))];x=q[:-1];t=np.c_[-np.sin(angles[:-1]),np.cos(angles[:-1]),np.zeros(len(x))];d=dict(p=1.,asset=dict(means=x,covariance=np.tile(np.eye(3)*.25,(len(x),1,1))),tangents=t);rows=np.arange(len(x))
  closed,receipt=w.closure(d,rows,q);self.assertTrue(receipt['supported']);self.assertFalse(w.contact(closed,True,lambda:None)['reject']);self.assertTrue(w.contact(q,False,lambda:None)['reject'])
  d['tangents'][:]=0;self.assertFalse(w.closure(d,rows,q)[1]['supported'])
 def test_real_more_than_eight_merges_monotone_and_save_rollback(self):
  from whole_runner import grow
  d,objects=synthetic(11);saved=[]
  result,events,version,status,_=grow(d,dict(seed_ids=[0]),'WHOLE',objects,20,lambda:None,lambda objs,ev,v,e:saved.append(set(objs[0]['rows'])),lambda *args:None)
  self.assertGreater(len(events),8);self.assertEqual(status['status'],'completed');self.assertTrue(all(a<=b for a,b in zip(saved,saved[1:])));self.assertEqual(len(result[0]['rows']),sum(len(o['rows']) for o in objects.values()))
  lib=w.library(d,objects,0,'WHOLE',w.CompleteIndex(objects));rec=lib['records'][lib['selected']];before=copy.deepcopy(objects)
  def fail(*args):raise RuntimeError('save failed')
  with self.assertRaisesRegex(RuntimeError,'save failed'):w.commit(objects,0,rec,20,fail)
  for gid in objects:np.testing.assert_array_equal(objects[gid]['rows'],before[gid]['rows']);np.testing.assert_array_equal(objects[gid]['q'],before[gid]['q'])

def synthetic(count=3):
 from port_paths import Leaf
 leaves={};objects={};xx=[];owner=[];rep=[];rt=[];n=0
 for gid in range(count):
  q=np.array([[2.2*gid,0,0],[2.2*gid+2,0,0]]);x=np.c_[np.linspace(2.2*gid,2.2*gid+2,12),np.zeros((12,2))];rr=np.arange(n,n+12);n+=12;xx.extend(x);owner.extend([gid]*12);reps=np.array([gid]);rep.append(x[6]);rt.append([1.,0,0]);leaves[gid]=w.Leaf(gid,10+gid,rr,reps,q,True,True,np.array([[0.,2.]]));objects[gid]=dict(id=gid,q=q,rows=rr,leaves=[gid],version=10+gid,available=True,seed_origins=[0] if gid==0 else [])
 d=dict(p=1.,asset=dict(means=np.array(xx),covariance=np.tile(np.eye(3)*.04,(n,1,1)),opacity=np.ones(n),primitive_id=np.array(owner)),tangents=np.tile([1.,0,0],(n,1)),leaves=leaves,representatives=dict(x=np.array(rep),t=np.array(rt)))
 return d,objects
