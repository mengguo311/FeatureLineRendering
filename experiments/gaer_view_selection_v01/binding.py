"""Reuse VERIFIED absolute-path APIs/binaries; never execute old runtime import."""
import importlib.util, sys, types
from stage_runtime import OLD,ART,atomic_json,digest,sha
NATIVE=__import__('pathlib').Path('/home/u00134/3dgs_line/object_neighborhood_edge_control_v1/out/object_neighborhood_edge_control_v1')
shim=types.ModuleType('runtime')
shim.NATIVE=NATIVE
shim.SOURCE=NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization'
shim.OUT=OLD/'out/gaer_attribution_buffer_v01'  # read-only binary binding
shim.ART=ART
shim.DATA_FREEZE=OLD/'artifacts/edge_control_lego_chair_v1/DATA_FREEZE.json'
shim.atomic_json=atomic_json; shim.digest=digest; shim.sha=sha

def read_api(name,path):
    saved=sys.modules.get('runtime'); sys.modules['runtime']=shim
    try:
        spec=importlib.util.spec_from_file_location(name,path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        return m
    finally:
        if saved is None: sys.modules.pop('runtime',None)
        else: sys.modules['runtime']=saved

native=read_api('gaer_verified_native_api',OLD/'experiments/gaer_attribution_buffer_v01/src/native.py')
scene_io=read_api('gaer_verified_scene_io',OLD/'experiments/gaer_attribution_buffer_v01/src/scene_io.py')
def backend(variant='patched'): return native.load_backend(variant)
