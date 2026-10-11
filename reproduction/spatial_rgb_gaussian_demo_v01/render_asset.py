"""Portable CPU re-render of a fixed Gaussian asset; never detects new lines."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
import core
p=argparse.ArgumentParser();p.add_argument('--asset',required=True);p.add_argument('--cameras',required=True);p.add_argument('--view',default='0024');p.add_argument('--native-root',required=True,help='directory containing build/libewa.so');p.add_argument('--occlusion-npz');p.add_argument('--output',required=True);a=p.parse_args();core.TASK=Path(a.native_root)
cs=json.loads(Path(a.cameras).read_text());c=next(c for c in cs if c['view']==a.view);asset=dict(np.load(a.asset));z=alpha=None
if a.occlusion_npz:
 source=np.load(a.occlusion_npz);z=source['median_camera_z'][0];alpha=source['alpha'][0]
r=core.render(asset,c,z,alpha);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Image.fromarray(np.uint8(np.clip(r,0,1)*255+.5)).save(a.output)
print(json.dumps({'gaussians':len(asset['means']),'view':a.view,'uses_original_scene_occlusion':z is not None,'output':a.output}))
