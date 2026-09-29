#!/usr/bin/env python3
"""Isolated F-only fitting / sealed evaluation driver."""
import sys,json,hashlib,time,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from PIL import Image
from src.direct_curve import evidence,native_quantiles
from src.foundation import native_render


def permitted_photos(cfg,scene,stage):
    if stage not in ['fit','evaluate']:raise ValueError('forbidden stage')
    ids=cfg['F'] if stage=='fit' else cfg['F']+cfg['C']
    return [cfg['scenes'][scene]['cameras'][str(i)]['path'] for i in ids]


def prepare_view(asset,camera,view,photograph=None):
    state=native_render(asset,camera['native_K'],camera['w2c'],800,800,1.)
    replay=native_quantiles(state,800,800)
    errors=dict(rgb_max=float(np.max(abs(replay['rgb']-state['stock_rgb']))),alpha_max=float(np.max(abs(replay['alpha']-(1-state['final_T'])))),wrapper_max=float(np.max(abs(state['wrapper_rgb']-state['stock_rgb']))))
    if max(errors.values())>1/255:raise ValueError('ENGINEERING_INVALID native calibration '+str(errors))
    rgb=state['stock_rgb'].copy()
    if photograph is not None:
        rgba=np.asarray(Image.open(photograph).convert('RGBA'),np.float32)/255;rgb=rgba[:,:,:3]*rgba[:,:,3:]+1-rgba[:,:,3:]
    quant=np.nan_to_num(replay['quantiles']);alpha=1-state['final_T'];depth=quant[:,:,1]
    return dict(view=view,camera=camera,rgb=rgb,gs_rgb=state['stock_rgb'],maps=np.concatenate([alpha[:,:,None],quant],2),alpha=alpha,depth=depth,evidence=evidence(rgb,depth,alpha,np.nan_to_num(replay['front'])),calibration=errors)

from src.direct_curve import fit,proposals
from src.foundation import load_asset,freeze_json,restrict_filesystem,STOCK_SITE
from scripts.render_adaptive_g1 import save_npz


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_view(output,view):
    output.mkdir(parents=True,exist_ok=True)
    arrays={k:view[k] for k in ['rgb','gs_rgb','maps','alpha','depth']}
    arrays.update({arm+'.'+k:v for arm,e in view['evidence'].items() for k,v in e.items()})
    save_npz(output/f"{view['view']}.npz",arrays)
    freeze_json(output/f"{view['view']}.json",dict(view=view['view'],camera=view['camera'],calibration=view['calibration']))


def tensor_data(view,arm):
    e=view['evidence']['D' if arm=='D' else 'I']
    return dict(K=torch.tensor(view['camera']['native_K'],dtype=torch.float32),w2c=torch.tensor(view['camera']['w2c'],dtype=torch.float32),maps=torch.tensor(view['maps'].transpose(2,0,1)[None]),xy=torch.tensor(e['xy']),tangent=torch.tensor(e['tangent']),sides=torch.tensor(e['sides']) if arm!='D' else None,rgb=torch.tensor(view['rgb'].transpose(2,0,1)[None]) if arm!='D' else None,scale=1.)


def run_fit(cfg,scene,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);began=time.monotonic();s=cfg['scenes'][scene]
    asset=load_asset(s['checkpoint']['path']);views=[]
    for i in cfg['F']:
        cam=s['cameras'][str(i)];v=prepare_view(asset,cam,i,cam['path']);save_view(output/'native',v);views.append(v)
        print('PREPARED',scene,'F',i,flush=True)
    del asset;gc.collect();torch.cuda.empty_cache()
    prop=proposals(views,s['box']);save_npz(output/'proposals.npz',dict(starts=prop['starts']));freeze_json(output/'PROPOSALS.json',prop['provenance'])
    assets={};chosen={};rows={}
    for arm in ['D','I','L']:
        data=[tensor_data(v,arm) for v in views]
        for subset in ['full','loo93']:
            d=data if subset=='full' else [x for i,x in zip(cfg['F'],data) if i!=93]
            scores=[]
            for start in range(3):
                stem=f'{arm}_{subset}_{start}';print('FIT_BEGIN',scene,stem,flush=True)
                r=fit(prop['starts'][start],d,s['box'],arm)
                save_npz(output/(stem+'.npz'),{k:r[k] for k in ['control','active','gate']})
                freeze_json(output/(stem+'.json'),{k:r[k] for k in ['history','final','seconds']})
                arrays=output/(stem+'.npz');assets[stem]=sha(arrays);rows[stem]=r['final'];scores.append(r['final']['data']+r['final']['regularization'])
                print('FIT_DONE',scene,stem,'seconds',r['seconds'],flush=True)
            if subset=='full':chosen[arm]=f'{arm}_full_{int(np.argmin(scores))}'
        del data;gc.collect();torch.cuda.empty_cache()
    freeze_json(output/'SEAL.json',dict(scene=scene,assets=assets,chosen=chosen,width_native=1.5,opacity=1.,stable_ids=list(range(128)),topology='independent cubic spans',objective_components=rows,elapsed_seconds=time.monotonic()-began,proposal_sha256=sha(output/'proposals.npz')))
    print('SEALED',scene,flush=True)


def main():
    import argparse,ctypes
    ap=argparse.ArgumentParser();ap.add_argument('--scene',choices=['lego','chair','drums','ficus'],required=True);ap.add_argument('--stage',choices=['fit','evaluate'],required=True);ap.add_argument('--run',default='run');args=ap.parse_args()
    art=ROOT/'artifacts/direct_curve_global_fit_probe';cfg=json.loads((art/'INPUTS.json').read_text());frozen=json.loads((art/'FREEZE.json').read_text())
    assert sha(art/'PROTOCOL.md')==frozen['protocol_sha256'];assert sha(art/'INPUTS.json')==frozen['inputs_sha256']
    output=ROOT/'out/direct_curve_global_fit_probe'/args.run/args.scene/args.stage;output.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(STOCK_SITE));import diff_gaussian_rasterization
    torch.cuda.init();torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.optim.Adam([torch.zeros(1,requires_grad=True)]);ctypes.CDLL(str(ROOT/'out/direct_curve_global_fit_probe/setup/quantiles.so'))
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
    photos=permitted_photos(cfg,args.scene,args.stage);checkpoint=cfg['scenes'][args.scene]['checkpoint']
    readonly=[ROOT/'src',ROOT/'scripts',art,ROOT/'out/direct_curve_global_fit_probe/setup',*runtime,*map(Path,photos),Path(checkpoint['path'])]
    if args.stage=='evaluate':readonly.append(output.parent/'fit')
    writable=[output,Path('/dev'),Path('/tmp')]
    policy=dict(readonly=[str(p.resolve()) for p in readonly if p.exists()],writable=[str(p.resolve()) for p in writable],photographs=photos,source_hashes={str(p):sha(p) for pat in ['src/direct_curve*','scripts/*direct_curve*.py'] for p in ROOT.glob(pat) if p.is_file()},stage=args.stage,scene=args.scene)
    freeze_json(output/'allowlist.json',policy);restrict_filesystem(policy['readonly'],policy['writable'])
    assert sha(checkpoint['path'])==checkpoint['sha256']
    for i in (cfg['F'] if args.stage=='fit' else cfg['F']+cfg['C']):
        c=cfg['scenes'][args.scene]['cameras'][str(i)];assert sha(c['path'])==c['sha256']
    if args.stage=='fit':run_fit(cfg,args.scene,output)
    else:
        from scripts.evaluate_direct_curve_probe import run_evaluation
        run_evaluation(cfg,args.scene,output.parent/'fit',output)


if __name__=='__main__':main()
