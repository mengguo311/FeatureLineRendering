#!/usr/bin/env python3
"""Conditional G1 construction and complete control artifacts, TRAIN only."""
import gc,hashlib,json,sys
from pathlib import Path
import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.adaptive_mass import native_csr,csr_metrics
from src.adaptive_evidence import build_evidence,prefix_control,transform_control,finalize_channel,scalar_hessian
from src.density_ridge_lines import adaptive_kde
from src.foundation import native_render,project_jacobian
CONTROLS=['full','expected_depth','front_depth','median_depth','no_ids','uniform','shuffled_ids','shuffled_depths','density','rgb_canny','k4','k8','k16','tau95_128','tau90_32','tau90_64','tau95_32','tau95_64']
CHANNELS=['E_occ','E_layer','E_shape_ridge','E_shape_valley']


def write_json(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')


def save_npz(path,arrays):
    import zipfile
    # Stable ZIP timestamps and level1 deflate keep the exhaustive controls bounded.
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for key,value in arrays.items():
            with archive.open(key+'.npy','w',force_zip64=True) as member:
                np.lib.format.write_array(member,np.asarray(value),allow_pickle=False)


def fixed_prefix(state,h,w,k,library):
    # Absolute target 1 disables the mass stopping condition for fixed-k controls.
    e=native_csr(dict(state,final_T=np.zeros((h,w),'f4')),h,w,1.,k,library)
    e['native_final_T']=state['final_T'].copy()
    return e


def baseline_fields(full,kind,state,asset,camera):
    shape=full['diagnostics']['A'].shape;d=full['layers']['local_scale'];support=full['diagnostics']['A']>=.5
    sigma=np.full(shape,1.5);depth=full['diagnostics']['z_front']
    if kind in ['expected_depth','front_depth','median_depth']:
        key={'expected_depth':'z_mean','front_depth':'z_front','median_depth':'z_50'}[kind];depth=full['diagnostics'][key]
        gx=ndi.gaussian_filter(depth,1.5,order=(0,1),mode='nearest');gy=ndi.gaussian_filter(depth,1.5,order=(1,0),mode='nearest')
        response=np.hypot(gx,gy)/d;angle=(np.arctan2(gy,gx)+np.pi/2)%np.pi
    elif kind=='density':
        uv,z,_=project_jacobian(asset['mu'],camera['native_K'],camera['w2c']);keep=(z>0)&np.isfinite(uv).all(1)
        kde=adaptive_kde(uv[keep],np.ones(keep.sum()),shape)['density']
        response=np.zeros(shape);angle=np.zeros(shape)
        for s in [1.5,2.5,4.]:
            r,a=scalar_hessian(kde,s);win=r>response;response[win]=r[win];angle[win]=a[win];sigma[win]=s
    elif kind=='rgb_canny':
        rgb=np.round(np.clip(state['stock_rgb'],0,1)*255).astype('u1');gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
        blurred=cv2.GaussianBlur(gray,(0,0),1.2);response=cv2.Canny(blurred,50,120)/255.
        gy,gx=np.gradient(blurred.astype('f8'));angle=(np.arctan2(gy,gx)+np.pi/2)%np.pi
    else:raise ValueError(kind)
    field=dict(response=(response*support).astype('f4'),orientation=angle.astype('f4'),sigma=sigma.astype('f4'),depth=depth.astype('f4'),layer=np.zeros(shape,'i2'))
    return {channel:field for channel in CHANNELS}


def save_raw(output,stem,e,result,identity=True):
    arrays={f'events.{k}':e[k] for k in ['offsets','ids','z','w','stream_position']}
    arrays.update({f'layers.{k}':v for k,v in result['layers'].items()})
    arrays.update({f'diagnostics.{k}':v for k,v in result['diagnostics'].items()})
    arrays.update({f'{ch}.{k}':v for ch,f in result['channels'].items() for k,v in f.items()})
    arrays['BC']=result['pairs']['BC'] if identity else np.ones_like(result['pairs']['BC'])
    arrays['layer_BC']=result['pairs']['layer_BC'] if identity else np.ones_like(result['pairs']['layer_BC'])
    save_npz(output/'raw'/(stem+'.npz'),arrays)
    layer=result['layers'];sizes=np.diff(e['offsets']);pix=np.repeat(np.arange(len(sizes)),sizes)
    A=np.bincount(pix,weights=e['w'],minlength=len(sizes)).reshape(layer['local_scale'].shape)
    error=float(np.max(np.abs(layer['retained_mass'].sum(-1)+layer['overflow_mass']-A),initial=0))
    if error>1e-10:raise ValueError('layer mass conservation failed')
    write_json(output/'raw'/(stem+'.json'),dict(layer_mass_error=error,events=len(e['ids']),layers=len(layer['layer_mass']),
               overflow_alpha=float(layer['overflow_mass'].sum()),responses={ch:dict(positive=int((f['response']>0).sum()),maximum=float(f['response'].max(initial=0))) for ch,f in result['channels'].items()}))


def construct_view(output,scene,view,asset,camera,csr_library,evidence_library):
    (output/'raw').mkdir(exist_ok=True);(output/'native').mkdir(exist_ok=True)
    h,w=camera['native_height'],camera['native_width'];K=camera['native_K'];w2c=camera['w2c']
    state=native_render(asset,K,w2c,h,w,1.);black=native_render(asset,K,w2c,h,w,0.)['stock_rgb']
    native_alpha=1-state['final_T'].astype('f8');master=native_csr(state,h,w,.95,128,csr_library)
    fixed=fixed_prefix(state,h,w,16,csr_library)
    metrics,_=csr_metrics(master,state,black,.95,128)
    if not all(v for k,v in metrics['checks'].items() if k!='coverage'):raise ValueError('G1 native CSR semantics failed')
    source=dict(master,stock_white=state['stock_rgb'],stock_black=black,native_alpha=native_alpha,
                camera_K=np.asarray(K),w2c=np.asarray(w2c),native_depths=state['depths'],native_point_list=state['point_list'],native_ranges=state['ranges'])
    source.update({'fixed16.'+k:v for k,v in fixed.items()})
    save_npz(output/'native'/f'{scene}_{view}.npz',source);write_json(output/'native'/f'{scene}_{view}.json',metrics)
    primary=prefix_control(master,native_alpha,.90,128)
    full=build_evidence(primary,native_alpha,evidence_library)
    for kind in CONTROLS:
        e=primary;identity=True
        if kind=='full':result=full
        elif kind in ['expected_depth','front_depth','median_depth','density','rgb_canny']:
            result=dict(full,channels=baseline_fields(full,kind,state,asset,camera));identity=False
        elif kind=='no_ids':result=build_evidence(primary,native_alpha,evidence_library,False,geometry=full['geometry']);identity=False
        elif kind in ['uniform','shuffled_ids','shuffled_depths']:
            e=transform_control(primary,kind,20260921+view+(1000 if kind=='shuffled_depths' else 0))
            result=build_evidence(e,native_alpha,evidence_library,geometry=full['geometry'] if kind=='shuffled_ids' else None)
        elif kind.startswith('k'):
            e=prefix_control(fixed,native_alpha,None,int(kind[1:]));result=build_evidence(e,native_alpha,evidence_library)
        else:
            tau,cap=kind[3:].split('_');e=prefix_control(master,native_alpha,int(tau)/100,int(cap));result=build_evidence(e,native_alpha,evidence_library)
        stem=f'{scene}_{view}_{kind}';save_raw(output,stem,e,result,identity)
        print('G1 raw',stem,flush=True)
        if result is not full:del result
        gc.collect()
    del full,primary,master,fixed,state,black;gc.collect()


def ink_metrics(mask):
    labels,n=ndi.label(mask,np.ones((3,3)));ink=np.bincount(labels.ravel(),minlength=n+1);length=np.bincount(labels[skeletonize(mask)],minlength=n+1)
    long=length>=24;long[0]=False
    return dict(ink_pixels=int(mask.sum()),components=n,long_component_ink_fraction=float(ink[long].sum()/max(1,mask.sum())))


def matched_mask(response,mask,count):
    ids=np.flatnonzero(mask);order=np.argsort(-response.ravel()[ids],kind='stable');out=np.zeros(mask.size,bool);out[ids[order[:count]]]=True
    return out.reshape(mask.shape)


def finalize_run(output,records,library):
    (output/'final').mkdir(exist_ok=True);pooled={ch:[] for ch in CHANNELS}
    for scene,view in records:
        with np.load(output/'raw'/f'{scene}_{view}_full.npz') as f:
            for ch in CHANNELS:
                value=f[ch+'.response'];pooled[ch].append(value[value>0])
    norm={ch:float(np.percentile(np.concatenate(rows),99)) if any(len(r) for r in rows) else 1. for ch,rows in pooled.items()}
    write_json(output/'NORMALIZATION.json',norm)
    del pooled
    for scene,view in records:
        reference={}
        for kind in CONTROLS:
            stem=f'{scene}_{view}_{kind}';arrays={};metrics={}
            with np.load(output/'raw'/(stem+'.npz')) as f:
                BC=f['BC'];d=f['layers.local_scale']
                for ch in CHANNELS:
                    field={k:f[ch+'.'+k] for k in ['response','orientation','sigma','depth','layer']}
                    result=finalize_channel(field,BC,d,norm[ch],library)
                    if kind=='full':reference[ch]={k:v.copy() for k,v in result.items() if k in ['response','band_95_70']}
                    ref=reference[ch];count=min(int(ref['band_95_70'].sum()),int(result['band_95_70'].sum()))
                    result['matched_full']=matched_mask(ref['response'],ref['band_95_70'],count)
                    result['matched_control']=matched_mask(result['response'],result['band_95_70'],count)
                    arrays.update({ch+'.'+k:v for k,v in result.items()})
                    metrics[ch]={grid:ink_metrics(result['band_'+grid]) for grid in ['95_70','90_60']}
                    metrics[ch]['matched_ink']=count;metrics[ch]['thresholds']=result['thresholds'].tolist()
            save_npz(output/'final'/(stem+'.npz'),arrays);write_json(output/'final'/(stem+'.json'),metrics)
            print('G1 bands',stem,flush=True)


def make_sheets(output,records):
    from scripts.render_adaptive_mass_probe import tile,write_sheet
    (output/'figures').mkdir(exist_ok=True)
    scenes=list(dict.fromkeys(s for s,v in records))
    for scene in scenes:
        views=[v for s,v in records if s==scene];rgb={}
        for view in views:
            with np.load(output/'native'/f'{scene}_{view}.npz') as f:rgb[view]=f['stock_white']
        write_sheet(output/'figures'/f'{scene}_RGB.png',[[tile(f'{scene} TRAIN {v} official CUDA RGB',rgb[v]) for v in views]])
        for ch in CHANNELS:
            for group in range(3):
                rows=[]
                for control in CONTROLS[group*6:group*6+6]:
                    row=[]
                    for view in views:
                        with np.load(output/'final'/f'{scene}_{view}_{control}.npz') as f:
                            soft=np.exp(-np.maximum(f[ch+'.normalized_soft'].astype('f8'),0))
                            maps=[('soft',np.repeat(soft[...,None],3,axis=-1))]
                            for name in ['band_95_70','band_90_60']:
                                mask=f[ch+'.'+name].astype(bool);maps.append((name,np.where(mask[...,None],0,rgb[view])))
                            for name in ['matched_full','matched_control']:
                                mask=f[ch+'.'+name].astype(bool);maps.append((name,np.repeat((~mask)[...,None],3,axis=-1)))
                            row.extend(tile(f'{control} v{view} {name}',im) for name,im in maps)
                    rows.append(row)
                path=output/'figures'/f'{scene}_{ch}_group{group}.png';write_sheet(path,rows)
                print('G1 sheet',path.name,flush=True)


def main():
    import argparse,ctypes,torch
    from src.foundation import restrict_filesystem,load_asset,STOCK_SITE,freeze_json
    from scripts.render_topk_layered_probe import frozen_inputs,sha
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--g0',type=Path,default=ROOT/'out/adaptive_mass_layered_probe/run/GATES.json')
    args=parser.parse_args();art=ROOT/'artifacts/adaptive_mass_layered_probe';cfg=frozen_inputs(art)
    gates=json.loads(args.g0.read_text())
    if gates['G0']!='PASS' or gates['chosen_kmax']!=128:raise ValueError('adaptive G0 has not qualified Kmax128')
    detail=art/'G1_IMPLEMENTATION.md'
    if sha(detail)!=(art/'G1_IMPLEMENTATION.sha256').read_text().split()[0]:raise ValueError('G1 implementation freeze changed')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    library=ROOT/'out/adaptive_mass_layered_probe/setup/adaptive_evidence_native.so'
    csr=ROOT/'out/adaptive_mass_layered_probe/setup/adaptive_mass_native.so'
    upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    sys.path[:0]=[str(STOCK_SITE),str(upstream)]
    import diff_gaussian_rasterization
    from scripts.render_adaptive_mass_probe import tile,write_sheet
    torch.cuda.init();torch.set_num_threads(1)
    for binary in [library,csr]:ctypes.CDLL(str(binary))
    sources=[Path(__file__).resolve(),ROOT/'scripts/render_adaptive_mass_probe.py',ROOT/'scripts/render_topk_layered_probe.py',
             *sorted((ROOT/'src').glob('*.py')),ROOT/'src/adaptive_mass_native.cpp',ROOT/'src/adaptive_evidence_native.cpp',library,csr]
    runtime=[Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
    code_roots=[upstream/k for k in ['gaussian_renderer','utils','scene']]
    inputs=[Path(cfg['scenes'][s]['checkpoint']['path']) for s in ['lego','chair','drums','ficus']]
    readonly=[*inputs,*sources,*code_roots,*[r.resolve() for r in runtime if r.exists()]]
    policy=dict(readonly=[str(x) for x in readonly],writable=[str(output),'/dev'],source_hashes={str(x):sha(x) for x in sources},
                upstream_source_hashes={str(x):sha(x) for r in code_roots for x in r.rglob('*.py')},
                bootstrap_files=[str(art/n) for n in ['PROTOCOL.md','PROTOCOL.sha256','INPUTS.json','G1_IMPLEMENTATION.md','G1_IMPLEMENTATION.sha256']]+[str(args.g0.resolve())],
                protocol_sha256=sha(art/'PROTOCOL.md'),implementation_sha256=sha(detail),photographs=[],stage='G1',scene_views={s:[1,27,53,79] for s in cfg['scenes']})
    freeze_json(output/'allowlist.json',policy);restrict_filesystem(readonly,[output,'/dev'])
    records=[]
    for scene in ['lego','chair','drums','ficus']:
        checkpoint=cfg['scenes'][scene]['checkpoint']
        if sha(checkpoint['path'])!=checkpoint['sha256']:raise ValueError('checkpoint hash mismatch')
        asset=load_asset(checkpoint['path'])
        for view in [1,27,53,79]:
            construct_view(output,scene,view,asset,cfg['scenes'][scene]['cameras'][str(view)],csr,library)
            records.append((scene,view));torch.cuda.empty_cache()
        del asset;gc.collect()
    finalize_run(output,records,library)
    make_sheets(output,records)
    write_json(output/'GATES.json',dict(G0='PASS',chosen_kmax=128,G1='AWAITING_VISUAL_REVIEW',G2='NOT_RUN',G3='NOT_RUN',records=records,controls=CONTROLS,channels=CHANNELS))


if __name__=='__main__':main()
