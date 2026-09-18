#!/usr/bin/env python3
"""Confined stock qualification for one frozen scene/posterior/stage."""
import argparse
import ctypes
import hashlib
from pathlib import Path
import sys
import cv2
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import (verified_json,freeze_json,restrict_filesystem,load_asset,STOCK_SITE)
from src.multiscene_qualification import measure_quality,qualify_parent
from src.multiscene_training import sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--scene',required=True,choices=['lego','chair','drums','ficus'])
    parser.add_argument('--seed',required=True,type=int,choices=[1729,2718])
    parser.add_argument('--stage',required=True,choices=['quality','controlled'])
    args=parser.parse_args();root=args.root.resolve()
    cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
    directory=root/'training'/args.scene/f'seed_{args.seed}'
    complete=verified_json(directory/'completion.json',(directory/'completion.json.sha256').read_text().strip())
    if not complete['complete']:raise RuntimeError('no completed full-training posterior')
    if args.stage=='controlled' and args.seed!=cfg['perturbations']['parent_seed']:
        raise ValueError('wrong registered parent')
    output=(directory/'quality') if args.stage=='quality' else (root/'controlled'/args.scene)
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    cameras=[cfg['scenes'][args.scene]['cameras'][f'{split}_{i:03d}']
        for split in (['train','val'] if args.stage=='quality' else ['train']) for i in cfg['splits']['TRAIN']]
    photo_paths=[v['path'] for v in cameras] if args.stage=='quality' else []
    sys.path.insert(0,str(STOCK_SITE));import diff_gaussian_rasterization
    replay=ROOT/'out/point_feature_foundation/setup/composite.so';ctypes.CDLL(str(replay))
    torch.cuda.init()
    sources=[ROOT/'src'/name for name in ['__init__.py','foundation.py','common.py',
        'multiscene.py','multiscene_qualification.py','multiscene_training.py']]+[Path(__file__).resolve(),replay]
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
    readonly=[complete['path'],*photo_paths,*[str(p) for p in sources],*[str(p.resolve()) for p in runtime if p.exists()]]
    allowlist=dict(stage=args.stage,scene=args.scene,seed=args.seed,readonly=readonly,
        writable=[str(output),'/dev'],photo_inputs=photo_paths,
        source_hashes={str(p):sha256(p) for p in sources},config_sha256=sha256(root/'config.json'))
    # Grant a newly-created output root; measurement functions themselves create
    # their exclusive artifact subtree, so replay cannot overwrite an old run.
    output.mkdir()
    freeze_json(output/'allowlist.json',allowlist)
    restrict_filesystem(readonly,[output,'/dev'])
    if sha256(complete['path'])!=complete['sha256']:raise ValueError('posterior hash changed')
    asset=load_asset(complete['path'])
    if args.stage=='quality':
        report=measure_quality(asset,cameras,cfg,output/'measurements')
    else:
        report=qualify_parent(asset,cameras,cfg,output/'measurements')
    freeze_json(output/'stage_complete.json',dict(stage=args.stage,scene=args.scene,seed=args.seed,
        asset_sha256=complete['sha256'],report_sha256=sha256(output/'measurements'/('quality.json' if args.stage=='quality' else 'qualification.json'))))
    print('completed',args.stage,args.scene,args.seed,flush=True)


if __name__=='__main__':main()
