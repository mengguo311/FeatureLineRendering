import unittest,tempfile,pathlib,subprocess,sys,os
from test_matching import CFG
class Runner(unittest.TestCase):
 def test_stage_plan_enforces_photos_assets_and_freeze(self):
  import cc_runner
  p=cc_runner.stage_plan(CFG,'lego','primary','seed_1729')
  self.assertEqual(p['split'],'F');self.assertEqual(len(p['photos']),8)
  p=cc_runner.stage_plan(CFG,'chair','cross','seed_1729');self.assertEqual(p['split'],'C');self.assertTrue(p['requires_F_seal'])
  p=cc_runner.stage_plan(CFG,'chair','repeat','seed_2718');self.assertEqual(p['photos'],[]);self.assertTrue(p['requires_F_seal'])
  with self.assertRaises(ValueError):cc_runner.stage_plan(CFG,'lego','repeat','seed_2718')
  with self.assertRaises(ValueError):cc_runner.stage_plan(CFG,'drums','primary','seed_1729')
 def test_real_confinement_blocks_unapproved_and_preserves_inputs(self):
  import cc_runner
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td);good=root/'good';bad=root/'bad';out=root/'output';out.mkdir();good.write_text('yes');bad.write_text('no')
   code='''import sys,pathlib
from cc_runner import confine
root=pathlib.Path(sys.argv[1]);confine([root/'good'],root/'output')
assert (root/'good').read_text()=='yes'
for p,mode in [(root/'bad','r'),(root/'good','w')]:
 try:open(p,mode)
 except PermissionError:pass
 else:raise RuntimeError('confinement leak')
(root/'output'/'written').write_text('ok')
'''
   p=subprocess.run([sys.executable,'-c',code,td],capture_output=True,text=True);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual((out/'written').read_text(),'ok')
 def test_qualified_repeat_arm_manifest_is_complete(self):
  import cc_runner
  self.assertEqual(len(cc_runner.primary_arm_names(CFG)),26)
  self.assertIn('loo_001_gs',cc_runner.primary_arm_names(CFG))
if __name__=='__main__':unittest.main()
