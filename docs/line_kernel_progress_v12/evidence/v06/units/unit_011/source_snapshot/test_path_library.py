from runtime_io import *
import unittest,sys
from port_paths import Edge,joint

LEGACY='--legacy' in sys.argv
if LEGACY:sys.argv.remove('--legacy')
class PathLibraryTests(unittest.TestCase):
 def test_failed_short_path_must_not_cut_feasible_extension(self):
  edges=[Edge(0,1,1,2,0,1.),Edge(1,2,1,3,0,2.1)]
  oracle=lambda chain:(len(chain)==3,'short_path_model_failure',{})
  if LEGACY:
   selected,receipt=joint(edges,oracle,seconds=5)
   self.assertEqual(selected,[0,1],'A failed fitted subpath is not a valid superset cut')
  else:
   from path_library import enumerate_paths,select_greedy,select_joint
   hs=enumerate_paths(edges,128)
   hs=[dict(h,metrics={}) for h in hs if oracle(h['chain'])[0]]
   self.assertEqual(len(hs),1);self.assertEqual(hs[0]['edge_ids'],[0,1])
   self.assertEqual(select_greedy(hs),[hs[0]['hid']]);self.assertEqual(select_joint(hs,5)[0],[hs[0]['hid']])
 def test_all_paths_ports_cycles_reversal_and_overflow(self):
  from path_library import enumerate_paths,PathOverflow
  es=[Edge(0,1,1,2,0,1.),Edge(1,2,1,3,0,1.)]
  hs=enumerate_paths(es,128);self.assertEqual(len(hs),3)
  self.assertEqual(len({tuple(h['model_key']) for h in hs}),3)
  self.assertEqual(enumerate_paths(list(reversed(es)),128),hs)
  with self.assertRaises(PathOverflow):enumerate_paths(es,2)
  self.assertEqual(len(enumerate_paths([es[0],Edge(1,2,0,3,0,1.)],128)),2)
 def test_shared_bank_greedy_trap(self):
  from path_library import select_greedy,select_joint
  hs=[dict(hid=i,anchor=min(leaves),model_key=[i],leaves=leaves,benefit=b) for i,(leaves,b) in enumerate([([1,2],3.),([1,3],2.),([2,4],2.)])]
  self.assertEqual(select_greedy(hs),[0]);self.assertEqual(select_joint(hs,5)[0],[1,2])
 def test_common_model_fit_and_real_centers_finite_guard(self):
  from test_runner_fixture import RunnerFixture
  from path_library import common_model,fit_engine
  from types import SimpleNamespace
  d=RunnerFixture().data();engine=fit_engine(Path(__file__).parent/'pinned_v05_fit_core.py',d)
  ok,why,met,model=common_model(d,[(1,False),(2,False),(3,False)],engine)
  self.assertTrue(ok,why);self.assertEqual(engine.fit_count,1);self.assertAlmostEqual(met['supported_length_p'],6)
  fake=SimpleNamespace(fit=lambda *a:((np.array([[.1,0,0],[6.1,0,0]]),'line'),'accepted',{}))
  self.assertEqual(common_model(d,[(1,False),(2,False),(3,False)],fake)[1],'finite_domain')
  fake=SimpleNamespace(fit=lambda *a:((np.array([[0.,0,0],[6.2,0,0]]),'line'),'accepted',{}))
  d['leaves'][1].q=np.array([[0.,0,0],[1.8,0,0],[.2,0,0],[2.,0,0]])
  self.assertEqual(common_model(d,[(1,False),(2,False),(3,False)],fake)[1],'nonmonotone')
 def test_common_branch_at_original_knots(self):
  from path_library import branch_at
  x=[];t=[]
  for deg in (-25,0,25):
   v=np.array([np.cos(np.deg2rad(deg)),np.sin(np.deg2rad(deg)),0.])
   for rad in (.5,1.5,2.6):x.append(rad*v);t.append(v)
  d=dict(p=1.,representatives=dict(x=np.array(x),t=np.array(t)))
  self.assertTrue(branch_at(d,np.arange(9),np.array([[0.,0,0]]),lambda:None))

if __name__=='__main__':
 if LEGACY:
  r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([PathLibraryTests('test_failed_short_path_must_not_cut_feasible_extension')]))
  raise SystemExit(0 if r.wasSuccessful() else 1)
 unittest.main(verbosity=2)
