"""Bounded CPU extraction from the actual frozen model, never a GT mesh."""
import runtime
from runtime import js, sha, now, output_guard
from pathlib import Path
import argparse
import json
import subprocess
import time
import numpy as np
from PIL import Image
import model_adapter as adapter
from geometry import depth_valid, backproject, region_ids

def save_image(path, a):
    Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(path)

def build(unit):
    unit=output_guard(unit); p=json.loads((unit/'PROTOCOL.json').read_text())
    out=unit/'proxy';out.mkdir(exist_ok=True)
    if (out/'mesh.npz').exists():
        raise FileExistsError('proxy already exists; do not overwrite a frozen run')
    builddir=unit/'build';builddir.mkdir(exist_ok=True)
    command=['g++','-O2','-shared','-fPIC',str(Path(__file__).with_name('source_ewa.cpp')),'-o',str(builddir/'libsource.so')]
    compiled=subprocess.run(command,capture_output=True,text=True,timeout=120)
    js(builddir/'COMPILE.json',dict(command=command,returncode=compiled.returncode,stdout=compiled.stdout,stderr=compiled.stderr))
    compiled.check_returncode();adapter.LIB_PATH=builddir/'libsource.so'
    start=time.monotonic();a=adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    js(out/'MODEL_IMPORT.json',dict(utc=now(),source_path=p['original']['original_ply'],source_sha256=p['original']['sha256'],
                                  audit=a['audit'],seconds=time.monotonic()-start,source_index='original PLY row, 0..N-1; proxy vertices have separate identity'))
    bounds=np.array([a['means'][a['opacity']>.5].min(0)-.06,a['means'][a['opacity']>.5].max(0)+.06])
    # Verify against a real source-only historical array using the same camera.
    c=p['static_cameras'][0]
    check=adapter.render_source(a,c)
    with np.load(p['input_cache_probe']) as cache:
        errors={k:float(np.max(np.abs(check[k]-cache[k]))) for k in check}
    js(out/'CACHE_REPLAY.json',dict(camera=c,cache=p['input_cache_probe'],max_abs_errors=errors,
                                   all_arrays_exact=all(x==0 for x in errors.values()),scope='agreement with prior CPU source-only renderer, not independent ground truth'))
    save_image(out/'source_train_r_32.png',check['rgb'])
    ref=Image.open(p['references']['train_r_32']).convert('RGBA')
    white=Image.new('RGBA',ref.size,'white');white.alpha_composite(ref);white.convert('RGB').save(out/'reference_train_r_32.png')
    rows=[]
    for i,c in enumerate(p['build_cameras']):
        t=time.monotonic();f=adapter.render_source(a,c)
        z=f['median_camera_z'];valid=depth_valid(z,f['alpha'],f['center_depth_proxy'])
        yy,xx=np.nonzero(valid);xyz=backproject(np.column_stack([xx,yy]),z[yy,xx],c)
        within=((xyz>=bounds[0])&(xyz<=bounds[1])).all(1)
        valid[yy[~within],xx[~within]]=False
        depth=np.where(valid,z,0.).astype(np.float32)
        np.savez_compressed(out/(c['view']+'.npz'),**f,qualified_depth=depth)
        row=dict(view=c['view'],alpha95_pixels=int((f['alpha']>=.95).sum()),qualified_pixels=int(valid.sum()),
                 accepted_fraction_of_alpha95=float(valid.sum()/max(1,(f['alpha']>=.95).sum())),seconds=time.monotonic()-t)
        rows.append(row);js(out/'BUILD_PROGRESS.json',rows);print(json.dumps(row),flush=True)
    from fuse_cpu import fuse
    fuse(unit)
    print(json.dumps(dict(proxy=str(out/'mesh.npz'),seconds=time.monotonic()-start)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);build(Path(p.parse_args().unit))
