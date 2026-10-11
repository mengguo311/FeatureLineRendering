"""Render a packaged fixed asset without old inputs (no source-scene occlusion)."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='2'
import argparse,ctypes,importlib.util,json
from pathlib import Path
import numpy as np
from PIL import Image

def render(root,scene,frame):
    spec=importlib.util.spec_from_file_location('portable_core',root/'vendor/core.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    core._lib=ctypes.CDLL(str(root/'vendor/libewa.so'))
    core._lib.ewa.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*7+[ctypes.c_double,ctypes.c_void_p]
    core._lib.ewa.restype=None
    cameras=json.loads((root/'media_corrected'/scene/'ARC_CAMERAS.json').read_text())['cameras']
    a=dict(np.load(root/'results'/f'{scene}_full/optimized_gaussians.npz'))
    out=core.render(a,cameras[frame])
    return np.uint8(np.clip(out,0,1)*255+.5)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--scene',required=True);p.add_argument('--frame',type=int,default=16)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--verify-frame',type=Path)
    a=p.parse_args();out=render(a.root,a.scene,a.frame)
    if a.verify_frame:
        reference=np.asarray(Image.open(a.verify_frame).convert('RGB'))
        h,w=out.shape[:2];np.testing.assert_array_equal(out,reference[105:105+h,w:2*w])
        print('EXACT_PACKAGED_ASSET_RERENDER_PASS')
    a.output.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(out).save(a.output)
    print('INK_ONLY: original-scene occlusion unavailable')
