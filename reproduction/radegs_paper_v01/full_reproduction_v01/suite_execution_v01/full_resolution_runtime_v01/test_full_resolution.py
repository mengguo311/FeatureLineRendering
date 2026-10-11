"""CPU TDD: full-resolution table rows must map to actual camera/parser shape.

No GPU work; actual forward/backward and memory gate remain mandatory.
"""
import json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.append(str(Path(__file__).resolve().parents[3]/'stage2'))
from test_scope_runner import Scope
from test_runtime_scope import RuntimeScope
from safety import atomic_json
import suite_scope,pilot_runtime,gpu_stages

class FullResolution(RuntimeScope):
 def fullconfig(self):
  p=self.config(entry_id='DTU_scan37_full30k_TSDF',resolution_divisor=1);return p
 def test_full_table_entry_accepted(self):
  c=json.loads(self.fullconfig().read_text());self.assertEqual(suite_scope.validate_config_scope(c)['resolution_pixels'],[1554,1162])
 def test_full_training_arguments_accepted(self):
  p=self.fullconfig();pilot_runtime.validate_pilot_arguments(self.args(p,resolution=1))
 def test_resolution_entry_mismatch_rejected(self):
  c=json.loads(self.config(resolution_divisor=1).read_text())
  with self.assertRaises(ValueError):suite_scope.validate_config_scope(c)
 def test_full_manifest_dimensions_checked(self):
  c=json.loads(self.fullconfig().read_text());c['expected_scene']={'views':49,'initial_colmap_points':17,'image_resolution':[1554,1162]}
  model=SimpleNamespace(_xyz=list(range(17)))
  gpu_stages.validate_scene_manifest(c,[SimpleNamespace(image_width=1554,image_height=1162)]*49,model,True)
  with self.assertRaises(AssertionError):gpu_stages.validate_scene_manifest(c,[SimpleNamespace(image_width=777,image_height=581)]*49,model,True)
 def test_scene_loader_uses_configured_resolution(self):
  c=json.loads(self.fullconfig().read_text());captured=[]
  class ModelParams:
   def __init__(self,p):
    p.add_argument('-s',dest='source_path');p.add_argument('-m',dest='model_path');p.add_argument('-r',dest='resolution',type=int);p.add_argument('--use_decoupled_appearance',action='store_true')
   def extract(self,args):args.images='images';args.sh_degree=3;captured.append(args.resolution);return args
  class PipelineParams:
   def __init__(self,p):pass
   def extract(self,args):return object()
  class Model:
   def __init__(self,n):pass
   def create_from_pcd(self,*args):pass
   def compute_3D_filter(self,*args):pass
  modules={'arguments':SimpleNamespace(ModelParams=ModelParams,PipelineParams=PipelineParams),'scene':SimpleNamespace(GaussianModel=Model),'scene.dataset_readers':SimpleNamespace(sceneLoadTypeCallbacks={'Colmap':lambda *args:SimpleNamespace(train_cameras=[],point_cloud=None,nerf_normalization={'radius':1})}),'utils.camera_utils':SimpleNamespace(cameraList_from_camInfos=lambda *args:[])}
  with patch.dict(sys.modules,modules):gpu_stages.load_scene(c,Path(c['model']),False)
  self.assertEqual(captured,[1])
if __name__=='__main__':unittest.main(verbosity=2)
