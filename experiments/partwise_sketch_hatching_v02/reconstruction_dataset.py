"""RGB/camera-only loading contract, defaulting to the isolated train export.

This module neither loads nor exposes oracle geometry. Evaluation requires an
explicit purpose. It does not create SfM points, train or instantiate a GPU.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

CAMERA_FIELDS = {'id','split','azimuth_deg','elevation_deg','distance','width','height',
                 'focal_px','principal_point','R_w2c','t_w2c','eye_world','c2w_opengl',
                 'rgb_path','rgb_sha256'}
SPLIT_PATHS = {'train':'train/cameras.json','dev':'evaluation/dev/cameras.json',
               'test':'evaluation/test/cameras.json'}

def _inside(base, relative, suffix):
    p=Path(relative)
    if p.is_absolute() or '..' in p.parts or p.suffix != suffix:
        raise ValueError('invalid relative input path')
    resolved=(base/p).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError('input path escapes split')
    return resolved

def load_dataset(root, split='train', purpose='train', verify_hashes=True):
    root=Path(root).resolve()
    if split not in SPLIT_PATHS or purpose not in ('train','evaluate'):
        raise ValueError('unknown split or purpose')
    if purpose=='train' and split!='train':
        raise ValueError('held-out RGB is forbidden for training purpose')
    manifest=json.loads((root/'DATASET.json').read_text())
    if manifest['schema']!='lamp_rgb_camera_v1' or manifest['splits']!=SPLIT_PATHS:
        raise ValueError('unexpected dataset layout')
    cp=_inside(root,SPLIT_PATHS[split],'.json')
    data=json.loads(cp.read_text())
    if data['split']!=split: raise ValueError('split mismatch')
    frames=data['frames']
    if len(frames)!=manifest['counts'][split]:raise ValueError('frame count mismatch')
    result=[];ids=set();poses=set();paths=set()
    for f in frames:
        if set(f)!=CAMERA_FIELDS:raise ValueError('unexpected camera fields, including forbidden oracle data')
        if f['split']!=split or f['id'] in ids:raise ValueError('duplicate or wrong split ID')
        path=_inside(cp.parent,f['rgb_path'],'.png')
        if Path(f['rgb_path']).parts[0]!='rgb':raise ValueError('RGB must be within split/rgb')
        pose=(f['azimuth_deg'],f['elevation_deg'],f['distance'])
        if pose in poses or path in paths:raise ValueError('duplicate camera or file')
        ids.add(f['id']);poses.add(pose);paths.add(path)
        if verify_hashes and hashlib.sha256(path.read_bytes()).hexdigest()!=f['rgb_sha256']:
            raise ValueError('RGB hash mismatch')
        with Image.open(path) as im:
            im.load()
            if im.mode!='RGB' or im.size!=(f['width'],f['height']):raise ValueError('invalid RGB dimensions/mode')
            rgb=np.asarray(im).copy()
        R=np.asarray(f['R_w2c'],float);t=np.asarray(f['t_w2c'],float)
        if R.shape!=(3,3) or t.shape!=(3,) or not np.isfinite(R).all() or not np.isfinite(t).all():raise ValueError('invalid camera')
        if not np.allclose(R@R.T,np.eye(3),atol=1e-10,rtol=0) or not np.isclose(np.linalg.det(R),1,atol=1e-10,rtol=0):raise ValueError('camera rotation must be proper orthonormal')
        if not np.isfinite(f['focal_px']) or f['focal_px']<=0:raise ValueError('invalid focal length')
        center=np.asarray(f['principal_point'],float);eye=np.asarray(f['eye_world'],float)
        gl=np.asarray(f['c2w_opengl'],float)
        if center.shape!=(2,) or eye.shape!=(3,) or gl.shape!=(4,4) or not all(np.isfinite(x).all() for x in (center,eye,gl)):
            raise ValueError('nonfinite or malformed camera metadata')
        cv=np.eye(4);cv[:3,:3]=R.T;cv[:3,3]=-R.T@t
        if not np.allclose(eye,cv[:3,3],atol=1e-10,rtol=0) or not np.allclose(gl,cv@np.diag([1,-1,-1,1]),atol=1e-10,rtol=0):
            raise ValueError('inconsistent camera transforms')
        result.append({**f,'rgb':rgb})
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dataset');p.add_argument('--split',choices=list(SPLIT_PATHS),default='train')
    p.add_argument('--purpose',choices=['train','evaluate'],default='train')
    args=p.parse_args();samples=load_dataset(args.dataset,args.split,args.purpose)
    print(json.dumps({'split':args.split,'purpose':args.purpose,'loaded_rgb_frames':len(samples),'oracle_loaded':False}))
