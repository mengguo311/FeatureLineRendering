#!/usr/bin/env python3
"""Execute the separately recorded nonconfirmatory resolution diagnosis."""
import argparse
from pathlib import Path
import sys
import cv2
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import verified_json,freeze_json,restrict_filesystem,load_asset,STOCK_SITE
from src.multiscene_diagnostic import resolution_diagnostic
from src.multiscene_training import sha256

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scene',required=True,choices=['lego','chair','drums','ficus'])
parser.add_argument('--seed',required=True,type=int,choices=[1729,2718]);args=parser.parse_args()
root=ROOT/'out/multiscene_foundation'
cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
directory=root/'training'/args.scene/f'seed_{args.seed}'
complete=verified_json(directory/'completion.json',(directory/'completion.json.sha256').read_text().strip())
assert complete['complete']
output=root/'diagnostics/resolution'/args.scene/f'seed_{args.seed}';output.mkdir(parents=True,exist_ok=False)
cameras=[cfg['scenes'][args.scene]['cameras'][f'{split}_{i:03d}'] for split in ['train','val'] for i in cfg['splits']['TRAIN']]
sys.path.insert(0,str(STOCK_SITE));import diff_gaussian_rasterization
torch.cuda.init()
sources=[ROOT/'src'/name for name in ['foundation.py','common.py','multiscene.py','multiscene_qualification.py',
    'multiscene_diagnostic.py','multiscene_training.py']]+[Path(__file__).resolve()]
runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
readonly=[complete['path'],*[v['path'] for v in cameras],*[str(p) for p in sources],*[str(p.resolve()) for p in runtime if p.exists()]]
freeze_json(output/'allowlist.json',dict(readonly=readonly,writable=[str(output),'/dev'],
    photo_inputs=[v['path'] for v in cameras],source_hashes={str(p):sha256(p) for p in sources},
    purpose='nonconfirmatory diagnosis; cannot override frozen gates'))
restrict_filesystem(readonly,[output,'/dev'])
if sha256(complete['path'])!=complete['sha256']:raise ValueError('posterior changed')
resolution_diagnostic(load_asset(complete['path']),cameras,output/'measurements')
