"""Read verified native APIs under a side-effect-free shim; production untouched."""
import importlib.util,sys,types
from runtime import *
def read_api(name,path,shim):
 saved=sys.modules.get('runtime');sys.modules['runtime']=shim
 try:
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 finally:
  if saved is None:sys.modules.pop('runtime',None)
  else:sys.modules['runtime']=saved
shim=types.ModuleType('runtime');shim.NATIVE=NATIVE;shim.SOURCE=NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization';shim.OUT=ATTR/'out/gaer_attribution_buffer_v01';shim.ART=ART;shim.DATA_FREEZE=ATTR/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json';shim.sha=sha;shim.digest=digest;shim.atomic_json=atomic_json
native=read_api('capacity_verified_native',ATTR/'experiments/gaer_attribution_buffer_v01/src/native.py',shim)
scene_io=read_api('capacity_verified_scene',ATTR/'experiments/gaer_attribution_buffer_v01/src/scene_io.py',shim)
def backend():return native.load_backend('patched')
