"""Real baseline RED on new paper scene and cross-config GPU lock, no CUDA."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[5];BASE=ROOT/'reproduction/radegs_paper_v01/stage2'
sys.path.append(str(BASE))
from safety import atomic_json,sha256
import runner
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
PROTO=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/FULL_SUITE_PROTOCOL.json'
GPU='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
IDLE=[{'uuid':GPU,'memory_mib':0,'util_percent':0,'contexts':[]}]
class Child:
 pid=123456
 def poll(self):return None
class Scope(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.engines=[]
  if hasattr(runner,'GLOBAL_GPU_LOCK_DIR'):
   self.patch=patch.object(runner,'GLOBAL_GPU_LOCK_DIR',self.root/'locks');self.patch.start()
 def tearDown(self):
  for e in self.engines:e.close()
  if hasattr(self,'patch'):self.patch.stop()
  self.tmp.cleanup()
 def config(self,scene='scan37',name='one',**kw):
  d=self.root/name;d.mkdir();pre=d/'preflight.json';atomic_json(pre,{'passed':True})
  c={'scene':scene,'dataset':'DTU','entry_id':f'DTU_{scene}_half30k_TSDF','automatic_scene_limit':1,'engineering_ready':True,'resolution_divisor':2,'iterations':30000,'full_suite_protocol':str(PROTO),'full_suite_protocol_sha256':sha256(PROTO),'data':str(HDD/'data/prepared'/scene),'model':str(HDD/'models'/f'{scene}_suite_test'),'state_dir':str(d/'state'),'log_dir':str(d/'logs'),'inputs':{'source':'test'},'immutable_files':{},'preflight_report':str(pre),'stable_seconds':60,'poll_seconds':60,'reports':{},'runtime_env':{},'cwd':str(d),'stage_commands':{s:['fake',s] for s in runner.STAGES},'allowed_gpu_uuids':[GPU]}
  c.update(kw);f=d/'config.json';atomic_json(f,c);return f
 def make(self,path,spawn=None):
  e=runner.Runner(path,spawn=spawn or (lambda *a,**k:Child()),query=lambda:IDLE,space_check=lambda:True);self.engines.append(e);return e
 def test_real_paper_scan37_admitted(self):
  e=self.make(self.config());e.tick(IDLE,0);e.tick(IDLE,60);self.assertEqual(e.state['status'],'RUNNING')
 def test_nonpaper_scan1_rejected(self):
  with self.assertRaises(ValueError):self.make(self.config(scene='scan1'))
 def test_fake_dataset_and_underspecified20k_rejected(self):
  for i,kw in enumerate([{'dataset':'Objaverse'},{'iterations':20000},{'entry_id':'DTU_scan37_half20k_TSDF'},{'full_suite_protocol_sha256':'0'*64}]):
   with self.assertRaises(ValueError):self.make(self.config(name=str(i),**kw))
 def test_cross_config_lock_excludes_second_launch(self):
  calls=[];a=self.make(self.config(scene='scan24',name='a'));b=self.make(self.config(scene='scan24',name='b'),lambda *x,**k:calls.append(1) or Child());a.tick(IDLE,0);a.tick(IDLE,60);b.tick(IDLE,0);b.tick(IDLE,60);self.assertEqual(calls,[])
if __name__=='__main__':unittest.main(verbosity=2)
