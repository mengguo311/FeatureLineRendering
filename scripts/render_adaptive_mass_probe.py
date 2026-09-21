#!/usr/bin/env python3
"""Isolated adaptive native mass calibration, with conditional scientific gates."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.adaptive_mass import native_csr,csr_metrics


def prepare_native(asset,camera):
    from scripts.render_topk_layered_probe import calibrate as old_calibrate
    from src.multiscene_probe import NativeLayers
    _,state,black,baseline=old_calibrate(asset,camera,ROOT/'out/topk_layered_probe/setup/topk_native.so')
    baseline['checks'].pop('coverage_k8')
    old=NativeLayers(state,camera['native_height'],camera['native_width'])
    return state,black,baseline,old


def extract_calibrated(prepared,camera,tau,kmax,library):
    state,black,baseline,old=prepared
    h,w=camera['native_height'],camera['native_width']
    e=native_csr(state,h,w,tau,kmax,library);m,d=csr_metrics(e,state,black,tau,kmax)
    sizes=np.diff(e['offsets']);pix=np.repeat(np.arange(h*w),sizes)
    ranks=np.arange(len(e['ids']))-e['offsets'][pix]
    idx=old.offsets[pix]+ranks
    err=max(float(np.max(np.abs(old.depth[idx]-e['z']),initial=0)),float(np.max(np.abs(old.weight[idx]-e['w']),initial=0)))
    m['checks'].update({'baseline_'+k:v for k,v in baseline['checks'].items()})
    m['checks']['existing_native_prefix']=err<=2e-6 and np.array_equal(np.diff(old.offsets).reshape(h,w),e['count'])
    m['errors']['existing_native_prefix']=err
    m['baseline_errors']=baseline['errors']
    m['passed']=all(m['checks'].values());m['failed']=[k for k,v in m['checks'].items() if not v]
    return e,state,black,m,d


def calibrate(asset,camera,tau,kmax,library):
    return extract_calibrated(prepare_native(asset,camera),camera,tau,kmax,library)


def gate_summary(rows):
    complete=set(rows)=={'lego','chair','drums','ficus'} and all(set(v)=={f'{t}_{k}' for t in [90,95] for k in [32,64,128]} for v in rows.values())
    chosen=next((k for k in [32,64,128] if complete and all(v[f'90_{k}']['passed'] for v in rows.values())),None)
    return dict(G0='PASS' if chosen else 'INVALID',G1='NOT_RUN',G2='NOT_RUN',G3='NOT_RUN',chosen_kmax=chosen,
                verdict='G0_PASS' if chosen else 'ENGINEERING_NOT_READY',scientific_verdict='NOT_EVALUATED',
                complete=complete,scenes=rows,execution_audit='PENDING_EXTERNAL_VERIFICATION')


def color(x):
    return cv2.applyColorMap(np.round(np.clip(x,0,1)*255).astype('u1'),cv2.COLORMAP_VIRIDIS)[...,::-1]/255.


def gray(x):return np.repeat(np.clip(x,0,1)[...,None],3,axis=-1)


def tile(title,rgb):
    out=np.full((844,800,3),255,'u1')
    im=np.round(np.clip(rgb,0,1)*255).astype('u1')[...,::-1]
    out[44:]=cv2.resize(im,(800,800),interpolation=cv2.INTER_NEAREST)
    cv2.putText(out,title,(8,29),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,0),1,cv2.LINE_AA)
    return out


def write_sheet(path,rows):
    if not cv2.imwrite(str(path),np.vstack([np.hstack(row) for row in rows]),[cv2.IMWRITE_PNG_COMPRESSION,6]):raise RuntimeError('PNG encoding failed')


def save_config(output,scene,t,k,e,state,black,camera,metrics,d):
    shape=d['A'].shape;pix=np.repeat(np.arange(d['A'].size),np.diff(e['offsets']))
    rgb=np.stack([np.bincount(pix,weights=e['w'].astype('f8')*e['rgb'][:,c],minlength=d['A'].size).reshape(shape) for c in range(3)],axis=-1)
    truncated=rgb+(1-d['A'])[...,None];native=1-state['final_T'].astype('f8')
    arrays=dict(e,**d,stock_white=state['stock_rgb'],stock_black=black,native_alpha=native,
                camera_K=np.asarray(camera['native_K']),w2c=np.asarray(camera['w2c']),truncated_rgb=truncated,
                native_depths=state['depths'],native_point_list=state['point_list'],native_ranges=state['ranges'])
    stem=f'{scene}_{t}_{k}'
    with (output/(stem+'.npz')).open('xb') as f:np.savez_compressed(f,**arrays)
    (output/(stem+'.json')).write_text(json.dumps(metrics,sort_keys=True,indent=2,allow_nan=False)+'\n')
    tag=f'tau .{t} Kmax {k}'
    return [tile(tag+' alpha',gray(d['A'])),tile(tag+' missing alpha',color(d['missing'])),
            tile(tag+' capture/native',color(d['A']/np.maximum(native,1e-12))),
            tile(tag+' K(x) / 128',color(d['K']/128)),tile(tag+' truncated RGB',truncated)]


def save_sheets(output,scene,rows,state,d,e):
    write_sheet(output/f'{scene}_coverage.png',rows)
    valid=np.diff(e['offsets'])>0;ids=np.zeros(len(valid),'i8');ids[valid]=e['ids'][e['offsets'][:-1][valid]]
    identity=np.stack([((ids*f+17)%251)/250 for f in [37,73,109]],axis=-1).reshape((*d['A'].shape,3));identity.reshape(-1,3)[~valid]=1
    panels=[('Stock CUDA RGB',state['stock_rgb']),('Native alpha',gray(1-state['final_T'])),
            ('tau .95 Kmax128 front depth / 8',color(d['z_front']/8)),('Median depth / 8',color(d['z_50']/8)),
            ('Expected depth / 8',color(d['z_mean']/8)),('Depth variance / .1',color(d['z_var']/.1)),
            ('Entropy / log(128)',color(d['H_id']/np.log(128))),('First native ID hash color',identity),
            ('tau .95 Kmax128 alpha',gray(d['A'])),('tau .95 Kmax128 missing',color(d['missing'])),
            ('tau .95 Kmax128 target reached',gray(d['reached'])),('G0 ROI native alpha >= .5',gray(1-state['final_T']>=.5))]
    tiles=[tile(*p) for p in panels]
    write_sheet(output/f'{scene}_diagnostics.png',[tiles[i:i+4] for i in range(0,12,4)])


from scripts.render_topk_layered_probe import frozen_inputs,sha


def main():
    import argparse,ctypes,gc
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    protocol=ROOT/'artifacts/adaptive_mass_layered_probe';cfg=frozen_inputs(protocol)
    library=ROOT/'out/adaptive_mass_layered_probe/setup/adaptive_mass_native.so'
    from src.foundation import restrict_filesystem,load_asset,STOCK_SITE,freeze_json
    import torch
    # Load runtime/code only before confinement. No asset arrays or photos here.
    from src.multiscene_probe import NativeLayers
    from src.corrected_sampling import stock_reference
    from scripts.render_topk_layered_probe import calibrate as old_calibrate
    upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    import gaussian_renderer,diff_gaussian_rasterization
    torch.cuda.init();torch.set_num_threads(1)
    for binary in [library,ROOT/'out/multiscene_foundation/setup/layers.so',ROOT/'out/topk_layered_probe/setup/topk_native.so']:ctypes.CDLL(str(binary))
    sources=[Path(__file__).resolve(),ROOT/'scripts/render_topk_layered_probe.py',ROOT/'out/topk_layered_probe/setup/topk_native.so',ROOT/'src/adaptive_mass_native.cpp',*sorted((ROOT/'src').glob('*.py')),library,ROOT/'src/topk_native.cpp',ROOT/'src/multiscene_layers.cpp',ROOT/'out/multiscene_foundation/setup/layers.so']
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
        asset=load_asset(checkpoint['path']);prepared=prepare_native(asset,camera)
        rows[scene]={};panels=[]
        for t in [90,95]:
            for k in [32,64,128]:
                e,state,black,metrics,d=extract_calibrated(prepared,camera,t/100,k,library)
                metrics.update(scene=scene,view=1,checkpoint_sha256=checkpoint['sha256'],gaussian_count=len(asset['mu']))
                panels.append(save_config(output,scene,t,k,e,state,black,camera,metrics,d))
                rows[scene][f'{t}_{k}']=metrics
                print(json.dumps(dict(scene=scene,tau=t,kmax=k,passed=metrics['passed'],failed=metrics['failed'],coverage=metrics['coverage'],memory=metrics['memory']),sort_keys=True),flush=True)
                if t==95 and k==128:save_sheets(output,scene,panels,state,d,e)
                del e,d;gc.collect()
        del asset,prepared,state,black,panels;gc.collect();torch.cuda.empty_cache()
    (output/'GATES.json').write_text(json.dumps(gate_summary(rows),sort_keys=True,indent=2)+'\n')


if __name__=='__main__':main()
