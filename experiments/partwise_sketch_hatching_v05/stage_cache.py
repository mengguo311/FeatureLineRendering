"""Engineering checkpoints for the frozen experiment; numerical recipe unchanged."""
import runtime
from runtime import js
import json
import numpy as np

class CheckpointPause(Exception):
    pass

def cached_opacity(path,effect,new_call_limit):
    cache=json.loads(path.read_text()) if path.exists() else {}
    calls=0
    def wrapped(arm,scale):
        nonlocal calls
        key=arm+':'+float(scale).hex()
        if key in cache:return cache[key]
        if calls>=new_call_limit:raise CheckpointPause()
        value=float(effect(arm,scale));cache[key]=value;calls+=1
        js(path,cache)
        print('checkpoint opacity',arm,scale,value,'new calls',calls,flush=True)
        return value
    return wrapped

def restored_view(folder,camera):
    from run_path_unit import read_npz
    f=read_npz(folder/'baseline.npz')
    return dict(camera=camera,frame={k:f[k] for k in ('rgb','alpha','median_camera_z','center_depth_proxy','expected_camera_z','contribution')},
        trace=read_npz(folder/'trace.npz'),path=read_npz(folder/'path_support.npz'),
        proxy_depth=f['proxy_depth'],regions=f['proxy_regions'],path_mask=f['path_mask'],
        check=dict(restored_from_persisted_arrays=True,needs_fresh_readback_audit=True))
