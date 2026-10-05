import unittest
from pathlib import Path
import scene_binding as b
class SceneBinding(unittest.TestCase):
 def test_exact_scenes(self):
  self.assertEqual(b.SCENES,('lego','chair','ficus'))
  self.assertEqual(b.scene_id('tree'),'ficus')
  self.assertEqual(b.display('ficus'),'tree / Ficus (ficus)')
 def test_unknown_scene(self):
  for s in ('drums','mic','materials','tree2','../ficus'):
   with self.assertRaises(ValueError):b.scene_id(s)
 def test_output_containment(self):
  root=Path('/tmp/new');self.assertEqual(b.output_path(root,root/'out/representative_edge_gaussians_three_v1/x'),root/'out/representative_edge_gaussians_three_v1/x')
  for p in ('out/representative_edge_gaussians_v1/x','artifacts/representative_edge_gaussians_v1/code/x','out/representative_edge_gaussians_three_v1/../../old'):
   with self.assertRaises(ValueError):b.output_path(root,root/p)
 def test_budget_is_historical_rank_tiers(self):
  self.assertEqual(b.budget_counts(33551),[336,1007,3356])
  self.assertEqual(b.budget_counts(72130),[722,2164,7213])
if __name__=='__main__':unittest.main(verbosity=2)
