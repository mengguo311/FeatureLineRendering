import json,random,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from official_runtime import OfficialRuntime,phase,finite_model,reconcile_log
from test_restart import FakeGaussian
import checkpointing as cp
class Tests(unittest.TestCase):
 def test_literal_C24_boundaries(self):
  self.assertEqual(phase(14999),(False,True));self.assertEqual(phase(15000),(True,True));self.assertEqual(phase(30000),(True,False))
 def test_nan_and_bad_gradient_rejected_but_opacity_endpoint_explicit(self):
  m=FakeGaussian();m._opacity.data[0]=float('inf');finite_model(m)
  m._scaling.data[0]=float('inf')
  with self.assertRaises(FloatingPointError):finite_model(m)
  m=FakeGaussian();m._opacity.data[0]=float('nan')
  with self.assertRaises(FloatingPointError):finite_model(m)
  m=FakeGaussian();m._xyz.grad=torch.tensor([float('nan'),0.],dtype=torch.double)
  with self.assertRaises(FloatingPointError):finite_model(m,gradients=True)
 def test_reconcile_retains_failed_tail_and_rejects_gaps(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'iteration_loss.jsonl';p.write_text(''.join(json.dumps({'iteration':i})+'\n' for i in range(1,5)))
   reconcile_log(p,2);self.assertEqual([json.loads(x)['iteration'] for x in p.read_text().splitlines()],[1,2]);self.assertEqual(len(list(Path(t).glob('iteration_loss.jsonl.uncommitted-*'))),1)
   p.write_text('{"iteration":1}\n{"iteration":3}\n')
   with self.assertRaises(ValueError):reconcile_log(p,3)
 def test_checkpoint_resume_no_rng_filter_or_adam_drift_and_stop(self):
  random.seed(7);np.random.seed(7);torch.manual_seed(7)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);cfg=p/'config.json';cfg.write_text(json.dumps({'model':str(p/'model'),'inputs':{'source':'test'}}));a=FakeGaussian();r=OfficialRuntime(cfg,cuda=False);r.restore(a,None,[])
   a.step();r.stop_requested=True
   with self.assertRaises(SystemExit) as e:r.completed_step(1,a,[],{'total':torch.tensor(1.)},None)
   self.assertEqual(e.exception.code,75);a.step();expected=(random.random(),np.random.rand(),torch.rand(()))
   b=FakeGaussian();s=OfficialRuntime(cfg,cuda=False);it,stack=s.restore(b,None,[]);self.assertEqual(it,1);b.step();self.assertEqual(expected,(random.random(),np.random.rand(),torch.rand(())))
   for k in cp.PARAMETERS+cp.BUFFERS:self.assertTrue(torch.equal(getattr(a,k),getattr(b,k)),k)
   for k,v in a.optimizer.state_dict()['state'].items():
    for n,x in v.items():self.assertTrue(torch.equal(x,b.optimizer.state_dict()['state'][k][n]))
   s.log.close()
if __name__=='__main__':unittest.main(verbosity=2)
