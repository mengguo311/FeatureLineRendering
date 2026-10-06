"""Import verified APIs with a temporary new-stage runtime, no installs/builds."""
import importlib.util,sys,types
from pathlib import Path
from runtime import ATTR,FOUNDATION,VIEW,ART,atomic_json,digest,sha
NATIVE=Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
shim=types.ModuleType('runtime');shim.NATIVE=NATIVE
shim.SOURCE=NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization'
shim.OUT=ATTR/'out/gaer_attribution_buffer_v01';shim.ART=ART
shim.DATA_FREEZE=ATTR/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
shim.atomic_json=atomic_json;shim.digest=digest;shim.sha=sha
def read_api(name,path,override=None):
    saved=sys.modules.get('runtime');sys.modules['runtime']=override or shim
    try:
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    finally:
        if saved is None:sys.modules.pop('runtime',None)
        else:sys.modules['runtime']=saved
native=read_api('rgb_vote_native',ATTR/'experiments/gaer_attribution_buffer_v01/src/native.py')
scene_io=read_api('rgb_vote_scene',ATTR/'experiments/gaer_attribution_buffer_v01/src/scene_io.py')
boundary=read_api('rgb_vote_original_boundary',FOUNDATION/'experiments/image_space_edge_foundation_v1/src/boundary.py')
ops=read_api('rgb_vote_verified_ops',VIEW/'experiments/gaer_view_selection_v01/native_ops.py')
def backend(variant='patched'):return native.load_backend(variant)
