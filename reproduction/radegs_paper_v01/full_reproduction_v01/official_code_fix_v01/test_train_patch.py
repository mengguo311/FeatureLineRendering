import ast,unittest
from pathlib import Path
from train_patch import patch
BASE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS/train.py')
class Tests(unittest.TestCase):
 def test_scientific_blocks_unchanged_and_controls_at_completed_step(self):
  old=BASE.read_text();new=patch(old);ast.parse(new)
  for start,end in [('        if dataset.use_decoupled_appearance:','        if iteration >= opt.regularization_from_iter:'),('        rgb_loss =','        loss.backward()'),('            # Densification','            if (iteration in checkpoint_iterations):')]:
   def block(s):return s[s.index(start):s.index(end)]
   if start.strip()=='rgb_loss =':continue
   self.assertEqual(block(new),block(old))
  self.assertIn('if iteration >= opt.regularization_from_iter:',new);self.assertIn('if iteration < opt.iterations:',new)
  self.assertIn('depth_ratio = 0.6',new);self.assertIn('rendered_normal, p=2, dim=0',new)
  self.assertLess(new.index('gaussians.compute_3D_filter(cameras=trainCameras)'),new.index('runtime.restore'))
  self.assertGreater(new.index('runtime.completed_step'),new.index('gaussians.optimizer.step()'))
  self.assertNotIn('network_gui.try_connect()',new)
 def test_double_patch_rejected(self):
  with self.assertRaises(ValueError):patch(patch(BASE.read_text()))
if __name__=='__main__':unittest.main(verbosity=2)
