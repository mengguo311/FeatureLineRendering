"""Deterministic-output and fixed-geometry checks, separate from scientific gates."""
import json,hashlib
from pathlib import Path
import numpy as np
import torch
from src.direct_curve import bezier


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_fixed_geometry(control,frames):
    expected=bezier(torch.tensor(control,dtype=torch.float64),257).numpy()
    return all(np.array_equal(expected,frame) for frame in frames)


def stable_json(value):
    if isinstance(value,dict):return {k:stable_json(v) for k,v in value.items() if k not in ['seconds','elapsed_seconds','fit_seconds']}
    if isinstance(value,list):return [stable_json(v) for v in value]
    return value


def compare_science(first,second):
    def inventory(root):return {str(p.relative_to(root)):p for p in root.rglob('*') if p.is_file() and p.suffix in ['.npz','.json','.png','.mp4'] and p.name!='allowlist.json'}
    a,b=inventory(first),inventory(second);checks={'inventory':set(a)==set(b) and bool(a)};hashes={};array_hashes={}
    for key in sorted(set(a)&set(b)):
        x,y=a[key],b[key];hashes[key]=[sha(x),sha(y)]
        if x.suffix=='.json':checks[key]=stable_json(json.loads(x.read_text()))==stable_json(json.loads(y.read_text()))
        else:checks[key]=hashes[key][0]==hashes[key][1]
        if x.suffix=='.npz':
            with np.load(x) as f:array_hashes[key]={k:dict(shape=list(f[k].shape),dtype=str(f[k].dtype),sha256=hashlib.sha256(np.ascontiguousarray(f[k]).tobytes()).hexdigest()) for k in f.files}
    return dict(passed=all(checks.values()),checks=checks,hashes=hashes,array_hashes=array_hashes,volatile_exclusions=['allowlist.json','JSON runtime fields seconds/elapsed_seconds/fit_seconds','sha256 sidecars whose JSON includes runtime fields'])


def decode_media(root,expected_frames=33):
    import cv2
    from src.multiscene_verify import verify_png
    pngs={};videos={}
    for p in sorted(root.rglob('*.png')):pngs[str(p.relative_to(root))]=verify_png(p)
    for p in sorted(root.rglob('*.mp4')):
        cap=cv2.VideoCapture(str(p));n=0;shape=None;ok=cap.isOpened()
        while True:
            good,frame=cap.read()
            if not good:break
            n+=1;shape=list(frame.shape)
        cap.release();videos[str(p.relative_to(root))]=dict(frames=n,shape=shape,passed=bool(ok and n==expected_frames))
    return dict(passed=all(v['passed'] for v in videos.values()),pngs=pngs,videos=videos)
