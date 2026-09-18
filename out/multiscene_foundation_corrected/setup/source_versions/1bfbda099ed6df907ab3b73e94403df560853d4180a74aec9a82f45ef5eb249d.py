#!/usr/bin/env python3
"""One confined stage, using only frozen final posteriors and canonical sampling."""
import argparse,ctypes,hashlib,json,sys,time
from pathlib import Path
import cv2,numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,restrict_filesystem,load_asset,STOCK_SITE
from src.corrected_qualification import measure_quality,qualify_parent
from src.corrected_sampling import stock_reference
from src.corrected_layers import AreaLayers

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True,choices=['lego','chair','drums','ficus']);p.add_argument('--seed',type=int,required=True,choices=[1729,2718]);p.add_argument('--stage',required=True,choices=['quality','controlled']);args=p.parse_args()
    root=ROOT/'out/multiscene_foundation_corrected'
    cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
    if sha(root/'PREREG.md')!=cfg['prereg_sha256']:raise ValueError('preregistration changed')
    posterior=cfg['frozen_posteriors'][f'{args.scene}_{args.seed}']
    if args.stage=='controlled' and args.seed!=1729:raise ValueError('wrong parent')
    output=root/(f'quality/{args.scene}/seed_{args.seed}' if args.stage=='quality' else f'controlled/{args.scene}')
    output.mkdir(parents=True,exist_ok=False)
    cameras=[cfg['scenes'][args.scene]['cameras'][f'{split}_{i:03d}'] for split in (['train','val'] if args.stage=='quality' else ['train']) for i in cfg['splits']['TRAIN']]
    photos=[c['path'] for c in cameras] if args.stage=='quality' else []
    upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    import gaussian_renderer,diff_gaussian_rasterization
    torch.cuda.init()
    binaries=[ROOT/'out/point_feature_foundation/setup/composite.so',ROOT/'out/multiscene_foundation/setup/layers.so',root/'setup/area_layers.so']
    for binary in binaries:ctypes.CDLL(str(binary))
    sources=[Path(__file__).resolve(),*list((ROOT/'src').glob('*.py')),*binaries]
    code_roots=[upstream/k for k in ['gaussian_renderer','utils','scene']]
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
    readonly=[posterior['path'],*photos,*sources,*code_roots,*[r.resolve() for r in runtime if r.exists()]]
    allow=dict(stage=args.stage,scene=args.scene,seed=args.seed,readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],photo_inputs=photos,source_hashes={str(x):sha(x) for x in sources},upstream_source_hashes={str(x):sha(x) for r in code_roots for x in r.rglob('*.py')},config_sha256=sha(root/'config.json'))
    freeze_json(output/'allowlist.json',allow)
    restrict_filesystem(readonly,[output,'/dev'])
    if sha(posterior['path'])!=posterior['sha256']:raise ValueError('frozen checkpoint changed')
    asset=load_asset(posterior['path']);start=time.monotonic()
    if args.stage=='quality':report=measure_quality(asset,cameras,cfg,output/'measurements');name='quality.json'
    else:report=qualify_parent(asset,cameras,cfg,output/'measurements',cfg['frozen_parents'][args.scene]);name='qualification.json'
    freeze_json(output/'stage_complete.json',dict(scene=args.scene,seed=args.seed,stage=args.stage,checkpoint_sha256=posterior['sha256'],report_sha256=sha(output/'measurements'/name),elapsed_seconds=time.monotonic()-start))

if __name__=='__main__':main()
