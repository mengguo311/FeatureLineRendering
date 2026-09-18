#!/usr/bin/env python3
"""Execute only the memo's prerequisite gates, before any local evidence result.

Invocation is tested end-to-end on a synthetic native-render fixture. Real runs
require all sixteen locked TRAIN cameras. No photographs are opened here.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import cv2
import torch
import plyfile
from src.foundation import (STOCK_SITE,freeze_json,verified_json,restrict_filesystem,
    load_asset,perturb_asset,native_render,replay_native,calibration_metrics,
    qualification_metrics,prerequisite_verdict,save_sheet)

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--config',type=Path,required=True)
parser.add_argument('--sha256',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
start=time.perf_counter(); started=datetime.now(timezone.utc).isoformat()
cfg=verified_json(args.config,args.sha256)
if cfg['scene']!='synthetic':
    if cfg['scene']!='lego': raise ValueError('Chair is gated by the completed Lego experiment')
    if [v['index'] for v in cfg['views']]!=[1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99]:
        raise ValueError('TRAIN views differ from frozen protocol')
    if (cfg['height'],cfg['width'])!=(400,400): raise ValueError('frozen resolution mismatch')
output=args.output.resolve(); output.mkdir(parents=True,exist_ok=False)
(output/'native').mkdir()
# Initialize runtime libraries before the irreversible kernel allowlist. No data
# asset, photograph, historical array, or annotation is read before restriction.
sys.path.insert(0,str(STOCK_SITE))
import diff_gaussian_rasterization
import ctypes
ctypes.CDLL(str(ROOT/'out/point_feature_foundation/setup/composite.so'))
torch.cuda.init()
runtime=[Path(sys.prefix),Path('/usr/lib'),Path('/lib'),Path('/lib64'),Path('/usr/local/cuda-12.6'),
         Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
runtime=[str(p.resolve()) for p in runtime if p.exists()]
sources=[ROOT/'src/__init__.py',ROOT/'src/foundation.py',ROOT/'src/foundation_composite.cpp',
         Path(__file__).resolve(),ROOT/'out/point_feature_foundation/setup/composite.so']
readonly=[str(args.config.resolve()),str(Path(cfg['asset_path']).resolve())]+[str(p) for p in sources]
allowlist=dict(readonly_files=readonly,runtime_readonly_roots=runtime,writable_roots=[str(output),'/dev'],
               photograph_inputs=[],scene=cfg['scene'],enforcement='Linux Landlock ABI >=3',
               input_metadata_read_before_restriction=[str(args.config.resolve())])
freeze_json(output/'allowlist.json',allowlist)
source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
restrict_filesystem(readonly+runtime,[output,'/dev'])
asset_bytes=Path(cfg['asset_path']).read_bytes()
if hashlib.sha256(asset_bytes).hexdigest()!=cfg['asset_sha256']: raise ValueError('GS hash mismatch')
del asset_bytes
asset=load_asset(cfg['asset_path']); n=len(asset['mu'])
clone,parents,selected=perturb_asset(asset,'clone')
split,parents_split,selected_split=perturb_asset(asset,'split')
assert np.array_equal(parents,parents_split) and np.array_equal(selected,selected_split)
low,high=np.quantile(asset['mu'].astype(np.float64),[.001,.999],axis=0)
margin=.1*np.linalg.norm(high-low); low-=margin; high+=margin
outside=np.any((asset['mu']<low)|(asset['mu']>high),axis=1)
np.savez_compressed(output/'native/intervention_parents.npz',parents=parents,selected=selected)
for name,a in [('original',asset),('clone',clone),('split',split)]:
    np.savez_compressed(output/f'native/{name}_parameters.npz',**a)
freeze_json(output/'frozen_interventions.json',dict(original_count=n,selected_count=int(selected.sum()),
    clone_count=len(clone['mu']),split_count=len(split['mu']),box=[low.tolist(),high.tolist()],
    original_outside_count=int(outside.sum()),parent_mask_sha256=hashlib.sha256(selected.tobytes()).hexdigest(),
    amplitude=.2,seed=20260918,created_utc=datetime.now(timezone.utc).isoformat()))
setup_seconds=time.perf_counter()-start
calibration=[]; coverage=[]; outside_ratios=[]; baseline={}; delta_samples=[]
cal_start=time.perf_counter()
for view in cfg['views']:
    i=view['index']; K=np.array(view['K']); w2c=np.array(view['w2c']); h,w=cfg['height'],cfg['width']
    white=native_render(asset,K,w2c,h,w,1.)
    black=native_render(asset,K,w2c,h,w,0.)
    replay=replay_native(white,h,w,selected.astype('u1'),outside.astype('u1'),1.)
    row=dict(view=i,**calibration_metrics(white,black['stock_rgb'],replay))
    calibration.append(row)
    roi=(1-white['final_T'])>=.5
    mass=float(replay['alpha'][roi].sum(dtype=np.float64))
    cov=float(replay['selected'][roi].sum(dtype=np.float64)/mass) if mass else 0.
    # Outside contributions use all pixels, to avoid hiding broad out-of-box splats.
    total=float(replay['alpha'].sum(dtype=np.float64))
    ext=float(replay['outside'].sum(dtype=np.float64)/total) if total else 1.
    coverage.append(cov); outside_ratios.append(ext)
    delta_samples.append(replay['depth_quantiles'][:,:,1][roi]/np.sqrt(K[0,0]*K[1,1]))
    np.savez_compressed(output/f'native/baseline_{i:03d}.npz',**white,stock_black=black['stock_rgb'],
        replay_rgb=replay['rgb'],replay_alpha=replay['alpha'],depth_quantiles=replay['depth_quantiles'],
        selected_mass=replay['selected'],outside_mass=replay['outside'],roi=roi)
    error=np.abs(white['stock_rgb']-replay['rgb'])
    alpha_error=np.abs((1-(white['stock_rgb']-black['stock_rgb']))-replay['alpha'][:,:,None])
    save_sheet(output/f'calibration_{i:03d}.png',[(f'TRAIN {i} stock RGB',white['stock_rgb']),
        ('native replay RGB',replay['rgb']),('absolute RGB error x255',error*255),
        ('absolute alpha error x255',alpha_error*255)])
    baseline[i]=(white['stock_rgb'],black['stock_rgb'],roi)
    print(json.dumps(dict(stage='calibration',**row)),flush=True)
calibration_seconds=time.perf_counter()-cal_start
qualification={'clone':[],'split':[]}; qualification_start=time.perf_counter()
# Scientific computations are only permitted following calibration of every view.
if all(r['passed'] for r in calibration):
    for view in cfg['views']:
        i=view['index']; K=np.array(view['K']); w2c=np.array(view['w2c']); h,w=cfg['height'],cfg['width']
        white,black,roi=baseline[i]
        for background,original,name in [(1.,white,'white'),(0.,black,'black')]:
            renders={}
            for mode,a in [('clone',clone),('split',split)]:
                rendered=native_render(a,K,w2c,h,w,background)
                rgb=rendered['stock_rgb']; renders[mode]=rgb
                row=dict(view=i,background=name,**qualification_metrics(original,rgb,roi))
                qualification[mode].append(row)
                np.savez_compressed(output/f'native/{mode}_{name}_{i:03d}.npz',rgb=rgb)
                print(json.dumps(dict(stage='qualification',mode=mode,**row)),flush=True)
            save_sheet(output/f'{name}_{i:03d}.png',[(f'TRAIN {i} original {name}',original),
                ('fixed clone',renders['clone']),('fixed split',renders['split']),
                ('clone abs error x10',np.abs(renders['clone']-original)*10),
                ('split abs error x10',np.abs(renders['split']-original)*10),
                ('frozen baseline ROI',np.repeat(roi[:,:,None],3,axis=2))])
            if time.perf_counter()-qualification_start>1800:
                raise TimeoutError('scientific prerequisite budget exhausted; no scientific failure verdict')
qualification_seconds=time.perf_counter()-qualification_start
unchanged=hashlib.sha256(Path(cfg['asset_path']).read_bytes()).hexdigest()==cfg['asset_sha256']
verdict=prerequisite_verdict(calibration,qualification,coverage,outside_ratios,0,unchanged)
values=np.concatenate(delta_samples)
delta=float(np.median(values)) if values.size else None
report=dict(**verdict,scene=cfg['scene'],started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),
    config_sha256=args.sha256,source_sha256=source_hashes,asset_sha256=cfg['asset_sha256'],
    native_renderer_kernel_commit='59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d',
    input_photo_reads=0,input_isolation='Landlock enforced; strace audit must be appended externally',
    original_count=n,selected_parent_count=int(selected.sum()),perturbed_count=len(parents),
    calibration=calibration,qualification=qualification,
    per_view=[dict(view=v['index'],coverage=c,outside_contribution=e,roi_pixels=int(baseline[v['index']][2].sum()))
              for v,c,e in zip(cfg['views'],coverage,outside_ratios)],
    box=[low.tolist(),high.tolist()],delta=delta,delta_foreground_rays=int(values.size),
    timing=dict(setup_seconds=setup_seconds,calibration_seconds=calibration_seconds,
                scientific_prerequisite_seconds=qualification_seconds,local_scientific_probe_seconds=0.,
                scientific_budget_seconds=1800),
    environment=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,opencv=cv2.__version__,
                     gpu=torch.cuda.get_device_name(0)),
    unreached=['local_image_probe','surface_sample_diagnostic','PCA_and_image_controls','F_C_repeatability',
               'DEV_annotations','glyphs','120_frame_video','independent_visual_review','Chair'])
freeze_json(output/'prerequisites.json',report)
print(json.dumps(dict(verdict=report['verdict'],may_run_local_probe=report['may_run_local_probe'],timing=report['timing'])),flush=True)
