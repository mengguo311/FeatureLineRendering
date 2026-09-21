#!/usr/bin/env python3
"""Gate G0 only: native-buffer calibration and complete diagnostic artifacts."""
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.topk_layered_evidence import native_prefix,prefix_calibration,prefix_diagnostics


def save_calibration(output, scene, e, state, black, camera, metrics):
    d=prefix_diagnostics(e,8);native_alpha=1-state['final_T']
    arrays=dict(e,**d,stock_white=state['stock_rgb'],stock_black=black,native_alpha=native_alpha,K=np.asarray(camera['native_K']),w2c=np.asarray(camera['w2c']))
    for k in [4,8,16]:
        arrays[f'A{k}']=e['w'][...,:k].sum(-1)
        arrays[f'missing{k}']=native_alpha-arrays[f'A{k}']
        arrays[f'truncated_rgb{k}']=(e['w'][...,:k,None]*e['rgb'][...,:k,:]).sum(-2)+(1-arrays[f'A{k}'])[...,None]
    with (output/f'{scene}_g0.npz').open('xb') as f:np.savez_compressed(f,**arrays)
    (output/f'{scene}_g0.json').write_text(json.dumps(metrics,sort_keys=True,indent=2,allow_nan=False)+'\n')
    gray=lambda x:np.repeat(np.clip(x,0,1)[...,None],3,axis=-1)
    # Fixed physical display: z/8, variance/.1, entropy/log(8). No per-scene stretch.
    color=lambda x:cv2.applyColorMap(np.round(np.clip(x,0,1)*255).astype('u1'),cv2.COLORMAP_VIRIDIS)[...,::-1]/255.
    identity=np.maximum(e['ids'][...,0],0).astype('u8');idrgb=np.stack([((identity*factor+17)%251)/250 for factor in [37,73,109]],axis=-1);idrgb[~d['valid']]=1
    ratio=arrays['A8']/np.maximum(native_alpha,1e-12)
    panels=[('Stock CUDA RGB',state['stock_rgb']),('Native alpha [0,1]',gray(native_alpha)),
        ('First-8 alpha [0,1]',gray(arrays['A8'])),('Missing alpha [0,1]',color(arrays['missing8'])),
        ('First-8 RGB + background',arrays['truncated_rgb8']),('Front depth / 8',color(d['z_front']/8)),
        ('Median depth / 8',color(d['z_50']/8)),('Mean depth / 8',color(d['z_mean']/8)),
        ('Variance / .1 (display clipped)',color(d['z_var']/.1)),('Entropy / log(8)',color(d['H_id']/np.log(8))),
        ('First contributor ID (hash color)',idrgb),('First-8 / native alpha',color(ratio)),
        ('First-4 alpha [0,1]',gray(arrays['A4'])),('First-16 alpha [0,1]',gray(arrays['A16'])),
        ('First-16 missing alpha',color(arrays['missing16'])),('G0 ROI: native alpha >= .5',gray(native_alpha>=.5))]
    tiles=[]
    for title,rgb in panels:
        tile=np.full((436,400,3),255,'u1')
        im=np.round(np.clip(rgb,0,1)*255).astype('u1')
        tile[36:]=cv2.resize(im[...,::-1],(400,400),interpolation=cv2.INTER_AREA)
        cv2.putText(tile,title,(5,23),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1,cv2.LINE_AA)
        tiles.append(tile)
    sheet=np.vstack([np.hstack(tiles[i:i+4]) for i in range(0,16,4)])
    if not cv2.imwrite(str(output/f'{scene}_g0.png'),sheet,[cv2.IMWRITE_PNG_COMPRESSION,6]):raise RuntimeError('PNG encode failed')


def calibrate(asset,camera,library):
    from src.foundation import native_render,project_jacobian
    from src.multiscene_probe import NativeLayers
    from src.corrected_sampling import stock_reference
    h,w=camera['native_height'],camera['native_width'];K=camera['native_K'];w2c=camera['w2c']
    state=native_render(asset,K,w2c,h,w,1.)
    black=native_render(asset,K,w2c,h,w,0.)['stock_rgb']
    e=native_prefix(state,h,w,16,library);metrics=prefix_calibration(e,state,black)
    old=NativeLayers(state,h,w);valid=e['ids']>=0
    idx=old.offsets[:-1].reshape(h,w,1)+np.arange(16)[None,None,:]
    counts=np.diff(old.offsets).reshape(h,w)
    same_counts=bool(np.array_equal(counts,e['count']))
    depth_error=float(np.max(np.abs(old.depth[idx[valid]]-e['z'][valid]),initial=0))
    weight_error=float(np.max(np.abs(old.weight[idx[valid]]-e['w'][valid]),initial=0))
    metrics['errors'].update(existing_depth=depth_error,existing_weight=weight_error)
    metrics['checks']['existing_native_prefix']=same_counts and max(depth_error,weight_error)<=2e-6
    uv,z,_=project_jacobian(asset['mu'],K,w2c);active=state['radii']>0
    projection_error=float(np.max(np.abs(uv[active]-state['means2D'][active]),initial=0))
    depth_error=float(np.max(np.abs(z[active]-state['depths'][active]),initial=0))
    metrics['errors'].update(projection_pixels=projection_error,camera_depth=depth_error)
    metrics['checks']['full_intrinsics']=projection_error<=1e-4 and depth_error<=1e-5
    if h==800 and w==800 and 'FoVx' in camera:
        reference=stock_reference(asset,w2c,camera['FoVx'],camera['FoVy'],1.)
        err=float(np.max(np.abs(reference-state['stock_rgb'])))
        metrics['errors']['stock_top_level']=err
        metrics['checks']['stock_top_level']=err<=1/255
    metrics['passed']=all(metrics['checks'].values());metrics['failed']=[k for k,v in metrics['checks'].items() if not v]
    return e,state,black,metrics


def gate_summary(rows):
    complete=set(rows)=={'lego','chair','drums','ficus'}
    passed=complete and all(r['passed'] for r in rows.values())
    return dict(G0='PASS' if passed else 'INVALID',G1='NOT_RUN',G2='NOT_RUN',G3='NOT_RUN',verdict='G0_PASS' if passed else 'ENGINEERING_NOT_READY',scientific_failure=False,complete=complete,scenes=rows,earliest_failure=None if passed else 'G0',execution_audit='PENDING_EXTERNAL_VERIFICATION')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_inputs(directory):
    if sha(directory/'PROTOCOL.md')!=(directory/'PROTOCOL.sha256').read_text().strip():raise ValueError('protocol hash mismatch')
    if f"INPUTS.json SHA256: `{sha(directory/'INPUTS.json')}`" not in (directory/'PROTOCOL.md').read_text():raise ValueError('input hash mismatch')
    return json.loads((directory/'INPUTS.json').read_text())


def main():
    import argparse,ctypes,gc
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    protocol=ROOT/'artifacts/topk_layered_probe';cfg=frozen_inputs(protocol)
    library=ROOT/'out/topk_layered_probe/setup/topk_native.so'
    from src.foundation import restrict_filesystem,load_asset,STOCK_SITE,freeze_json
    import torch
    # Load runtime/code only before confinement. No asset arrays or photos here.
    from src.multiscene_probe import NativeLayers
    from src.corrected_sampling import stock_reference
    upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    import gaussian_renderer,diff_gaussian_rasterization
    torch.cuda.init();torch.set_num_threads(1)
    for binary in [library,ROOT/'out/multiscene_foundation/setup/layers.so']:ctypes.CDLL(str(binary))
    sources=[Path(__file__).resolve(),*sorted((ROOT/'src').glob('*.py')),library,ROOT/'src/topk_native.cpp',ROOT/'src/multiscene_layers.cpp',ROOT/'out/multiscene_foundation/setup/layers.so']
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
    code_roots=[upstream/k for k in ['gaussian_renderer','utils','scene']]
    inputs=[Path(cfg['scenes'][s]['checkpoint']['path']) for s in ['lego','chair','drums','ficus']]
    readonly=[*inputs,*sources,*code_roots,*[r.resolve() for r in runtime if r.exists()]]
    policy=dict(readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],source_hashes={str(x):sha(x) for x in sources},upstream_source_hashes={str(x):sha(x) for r in code_roots for x in r.rglob('*.py')},bootstrap_files=[str(protocol/n) for n in ['PROTOCOL.md','PROTOCOL.sha256','INPUTS.json']],protocol_sha256=sha(protocol/'PROTOCOL.md'),photographs=[],stage='G0',scene_views={s:[1] for s in cfg['scenes']})
    freeze_json(output/'allowlist.json',policy);restrict_filesystem(readonly,[output,'/dev'])
    rows={}
    for scene in ['lego','chair','drums','ficus']:
        checkpoint=cfg['scenes'][scene]['checkpoint'];camera=cfg['scenes'][scene]['cameras']['1']
        if sha(checkpoint['path'])!=checkpoint['sha256']:raise ValueError('checkpoint hash mismatch')
        asset=load_asset(checkpoint['path']);e,state,black,metrics=calibrate(asset,camera,library)
        metrics.update(scene=scene,view=1,checkpoint_sha256=checkpoint['sha256'],gaussian_count=len(asset['mu']))
        save_calibration(output,scene,e,state,black,camera,metrics)
        rows[scene]=metrics
        print(json.dumps(dict(scene=scene,passed=metrics['passed'],failed=metrics['failed'],coverage=metrics['coverage']),sort_keys=True),flush=True)
        del asset,e,state,black;gc.collect();torch.cuda.empty_cache()
    (output/'GATES.json').write_text(json.dumps(gate_summary(rows),sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
