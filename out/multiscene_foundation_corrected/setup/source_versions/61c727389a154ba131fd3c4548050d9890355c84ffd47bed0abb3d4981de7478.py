#!/usr/bin/env python3
"""Complete controls after a logged import failure, preserving every original fit."""
import argparse,ctypes,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,restrict_filesystem,load_asset
from src.corrected_execution import finish_primary_controls
from src.corrected_probe import ImageEvidence
from src.corrected_layers import AreaLayers
from src.corrected_reporting import sha256,verify_probe_integrity

def main():
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);args=p.parse_args();root=ROOT/'out/multiscene_foundation_corrected'
    cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip());local=root/f'local/{args.scene}';output=local/'F'
    if (output/'frozen.json').exists():raise FileExistsError('F already frozen')
    prior_path=root/f'setup/local_{args.scene}_seed_1729_primary_exit.json';prior=json.loads(prior_path.read_text())
    if prior['exit_code']!=1:raise ValueError('completion requires preserved primary failure record')
    eligibility=json.loads((root/f'scenes/{args.scene}/eligibility.json').read_text());views=cfg['splits']['F']
    posterior=cfg['frozen_posteriors'][f'{args.scene}_1729'];parameter=Path(posterior['path']);policy=output/'control_completion';policy.mkdir(exist_ok=False)
    sources=[Path(__file__).resolve(),*list((ROOT/'src').glob('*.py'))]
    binaries=[ROOT/'out/multiscene_foundation/setup/layers.so',root/'setup/area_layers.so']
    for binary in binaries:ctypes.CDLL(str(binary))
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys')]
    readonly=[parameter,prior_path,local/'layers/seed_1729',*sources,*binaries,*[p.resolve() for p in runtime if p.exists()]]
    freeze_json(policy/'allowlist.json',dict(scene=args.scene,task='controls',asset='seed_1729',readonly=[str(p) for p in readonly],writable=[str(output),'/dev'],photo_inputs=[],source_hashes={str(p):sha256(p) for p in sources},config_sha256=sha256(root/'config.json'),purpose='Complete old PCA/random/F prediction controls; hash every original fit before and after. No original artifact may change.'))
    restrict_filesystem(readonly,[output,'/dev']);start=time.monotonic()
    if sha256(parameter)!=posterior['sha256']:raise ValueError('checkpoint changed')
    summaries=sorted(output.glob('*/summary.json'))
    if len(summaries)!=28:raise ValueError('not all primary inference arms completed')
    for path in summaries:verify_probe_integrity(path.parent)
    asset=load_asset(parameter);fields={i:dict(np.load(output/f'field_{i:03d}.npz')) for i in views}
    layers={i:AreaLayers.load(local/f'layers/seed_1729/view_{i:03d}.npz') for i in views}
    cameras={i:cfg['scenes'][args.scene]['cameras'][f'train_{i:03d}'] for i in views}
    report=finish_primary_controls(output,asset,ImageEvidence(cameras,fields,layers,eligibility['delta'],cfg),cfg)
    freeze_json(policy/'complete.json',dict(**report,elapsed_seconds=time.monotonic()-start,original_primary_exit=prior['exit_code']))
    frozen=dict(queries_sha256=sha256(output/'queries.json'),artifacts={str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},elapsed_seconds=time.monotonic()-start,asset='seed_1729',split='F',completion='Original 28 fits preserved; control import preload repaired after isolated regression test.')
    freeze_json(output/'frozen.json',frozen);print('F controls complete and frozen',args.scene,flush=True)

if __name__=='__main__':main()
