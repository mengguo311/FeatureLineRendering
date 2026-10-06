import unittest,json
import numpy as np
import runtime as rt

class PipelineTests(unittest.TestCase):
 def test_native_only_no_target_overlay(self):
  from pipeline import native_output
  from adapter import backend,scene_io,NativeWeights
  import torch
  rt.guard('pipeline-native-test');record=json.loads((rt.ART/'INPUT_FREEZE.json').read_text())['scenes']['chair'];model=scene_io.load_model(record);module=backend();c=next(c for c in record['cameras'] if c['key']=='r_7');o=NativeWeights(module,scene_io.make_settings(module,c),model);s=torch.full((o.n,),.17,device='cuda')
  rgb,ink=native_output(o,s)
  expected=o.ink_rgb(s).cpu().numpy().transpose(1,2,0)
  np.testing.assert_array_equal(rgb,expected);np.testing.assert_array_equal(ink,1-expected[...,0])
  # Deliberately broad ink must survive outside a hypothetical narrow target.
  self.assertGreater(int((ink>.1).sum()),10000)
  rt.npz(rt.ART/'tests/NO_LINE_PLANE_NATIVE.npz',native_rgb=rgb,native_ink=ink,original_ids=np.arange(o.n,dtype=np.int32),strength=s.cpu().numpy())

if __name__=='__main__':unittest.main()
