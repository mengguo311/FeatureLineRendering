#!/usr/bin/env python3
"""Mesh-free VRSS entry. Each bounded stage writes only under out/vrss.

Examples (from repository root, vfsdgs Python, CUDA_VISIBLE_DEVICES=1):
  python scripts/run_vrss.py smoke
  python scripts/run_vrss.py candidates
  python scripts/run_vrss.py evidence
  python scripts/run_vrss.py select
  python scripts/run_vrss.py render

TEST and VAL RGB never enter these stages. No historical candidate cache is read.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
import torch
from src import common, render, linelet, dt_pull, linelet_prune, strokes, view_split
from src import stroke_relations as relations
from src.stroke_select import Objective, select

OUT = ROOT/'out/vrss'
DEV = OUT/'chair_dev'
EXT = ROOT.parent/'ext/gaussian-splatting'
SOURCES = ['scripts/run_vrss.py','scripts/explore/syn/m1a_seeds.py'] + ['src/'+x+'.py' for x in
    ('common','render','visibility','view_split','linelet','dt_pull','linelet_prune','strokes','stroke_relations','stroke_select')]


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def dump(path,value):
    path=Path(path)
    if path.exists():
        raise FileExistsError(f'refuse to overwrite completed artifact: {path}')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()


def provenance(m):
    return {'commit':git('rev-parse','HEAD'),'manifest_sha256':digest(OUT/'manifest.json'),
            'source_sha256':{p:digest(ROOT/p) for p in SOURCES},
            'gs_sha256':m['gs']['sha256'],'camera_sha256':m['cameras']['sha256'],
            'seed_indices':m['split']['seed_indices'],'pull_indices':m['split']['pull_indices'],
            'evidence_indices':m['split']['evidence_indices'],'vanilla_only':True,'mesh_free':True}


def checked_manifest():
    if git('branch','--show-current')!='vrss-experiment':
        raise RuntimeError('wrong branch; refusing all work')
    m=json.loads((OUT/'manifest.json').read_text())
    if git('rev-parse','visual-stroke-render')!=m['base_commit']:
        raise RuntimeError('protected local baseline changed')
    for key in ('gs','cameras'):
        if digest(m[key]['path'])!=m[key]['sha256']:
            raise RuntimeError(f'{key} input changed')
    allowed=set(view_split.TRAIN)
    for key in ('seed_indices','pull_indices','evidence_indices'):
        ids=m['split'][key]
        if not ids or len(ids)!=len(set(ids)) or not set(ids)<=allowed:
            raise ValueError(f'not clean TRAIN: {key}')
    if not all(m['split'][k]==m['split']['evidence_indices'] for k in ('seed_indices','pull_indices')):
        raise ValueError('cheap protocol requires identical extraction/evidence views')
    return m


def install_read_guard(m, paths):
    """Guard Python file IO and cv2.imread (which bypasses Python open audit).

    This is defense in depth plus an access log, not a sandbox claim for native
    extensions. The audited native renderer receives only the approved GS arrays.
    """
    approved={str(Path(paths[i]).resolve()) for i in m['split']['evidence_indices']}
    gs=str(Path(m['gs']['path']).resolve()); access={'rgb_reads':[], 'data_file_reads':[]}
    old_imread=cv2.imread
    def guard_name(name):
        if not isinstance(name,(str,bytes,os.PathLike)):
            return
        path=Path(os.fsdecode(name)).resolve(); s=str(path); low=s.lower()
        if any(token in low for token in ('mesh_oracle','gt_crease','/meshes/','/mesh/','/2dgs_','/dd3')) or path.suffix.lower() in ('.obj','.off','.stl'):
            raise RuntimeError(f'forbidden method input: {path}')
        if path.suffix.lower()=='.ply' and s!=gs:
            raise RuntimeError(f'unapproved geometry: {path}')
        if '/data/full/' in s and path.suffix.lower() in ('.png','.jpg','.jpeg') and s not in approved:
            raise RuntimeError(f'non-TRAIN RGB read: {path}')
        if path.suffix in ('.npy','.npz') and not path.is_relative_to(OUT):
            raise RuntimeError(f'unapproved legacy cache: {path}')
        if '/cglib/' in s or path.is_relative_to(OUT):
            if s not in access['data_file_reads']:
                access['data_file_reads'].append(s)
    def audit(event,args):
        if event=='open':
            mode=args[1]
            if isinstance(mode,str) and any(c in mode for c in 'wax'):
                return
            guard_name(args[0])
    sys.addaudithook(audit)
    def imread(path,*args,**kwargs):
        guard_name(path); absolute=str(Path(path).resolve())
        if absolute not in access['rgb_reads']:
            access['rgb_reads'].append(absolute)
        return old_imread(str(path),*args,**kwargs)
    cv2.imread=imread
    return access


def scaled(cam,resolution):
    sx,sy=resolution/cam.W,resolution/cam.H
    K=cam.K.copy();K[0]*=sx;K[1]*=sy
    return common.Camera(K,cam.w2c,resolution,resolution,cam.name)


def rgb_white(path, resolution):
    im=cv2.imread(str(path),cv2.IMREAD_UNCHANGED)
    if im is None: raise FileNotFoundError(path)
    if im.shape[2]==4:
        a=im[:,:,3:4]/255.;im=im[:,:,:3]*a+255*(1-a)
    return cv2.resize(im[:,:,:3].astype(np.uint8),(resolution,resolution),interpolation=cv2.INTER_AREA)


def smoke(m,cams,paths):
    c=scaled(cams[m['split']['evidence_indices'][0]],400)
    t=time.perf_counter()
    official=render.OfficialRGBRenderer(m['gs']['path'],EXT)
    im=official(c)
    g=common.load_gaussians(m['scene']); keep=render.defloat_mask(g['mu'],g['opacity'])
    gb=render.render_gbuffer(g,keep,c)
    assert np.isfinite(im).all() and float(im.std())>.05 and gb['alpha'].max()>.5
    import diff_gaussian_rasterization as dr
    photo=rgb_white(paths[m['split']['evidence_indices'][0]],400)[:,:,::-1]/255.
    cv2.imwrite(str(OUT/'entry_smoke.png'),(im[:,:,::-1]*255).astype(np.uint8))
    dump(OUT/'entry_smoke.json',{'status':'PASS','seconds':time.perf_counter()-t,
        'photo_psnr_diagnostic':float(-10*np.log10(np.mean((im-photo)**2))),
        'extension_binary':dr._C.__file__,'extension_binary_sha256':digest(dr._C.__file__),
        'provenance':provenance(m)})


def candidates(m,cams,paths):
    target=DEV/'candidates.npz'
    if target.exists(): raise FileExistsError(target)
    if not (OUT/'entry_smoke.json').exists(): raise RuntimeError('run cheap smoke first')
    sys.path.insert(0,str(ROOT/'scripts/explore/syn'))
    from m1a_seeds import extract_seeds
    t=time.perf_counter(); cfg=m['candidates']; views=m['split']['seed_indices']
    p,score,seed_keep,X=extract_seeds(m['scene'],'overall',keep_f=cfg['seed_fraction'],train_indices=views)
    g=common.load_gaussians(m['scene']); keep=render.defloat_mask(g['mu'],g['opacity'])
    L=linelet.init_linelets(p,X,g['scale'][keep])
    cache=DEV/'train_cache'
    dt=dt_pull.build_dt_cache(m['scene'],paths,views,cfg_name=cfg['edge'],force=True,cache_dir=str(cache))
    depth,fg=dt_pull.build_geom_cache(m['scene'],g,keep,cams,views,force=True,cache_dir=str(cache))
    field=dt_pull.PullField(cams,views,dt,depth,fg)
    result=dt_pull.pull(field,L,steps=cfg['pull_steps'],lr=cfg['pull_lr'],delta_max=cfg['delta_max'])
    good,stats=linelet_prune.consensus_prune(result['resid'],result['vis'],**cfg['prune'])
    chains,nms=strokes.chain_linelets_3d(result['p'][good],result['t'][good],result['l'][good],conf=stats['inlier_ratio'][good],**cfg['chain'])
    path_list=strokes.chain_vertices(chains,result['p'][good][nms])
    if not path_list: raise RuntimeError('NO-GO: zero frozen candidate paths')
    offsets=np.r_[0,np.cumsum([len(p) for p in path_list])]
    np.savez_compressed(target,vertices=np.concatenate(path_list),offsets=offsets)
    np.savez_compressed(DEV/'linelets_train.npz',p=result['p'],t=result['t'],l=result['l'],keep=good,resid=result['resid'],vis=result['vis'])
    report={'provenance':provenance(m),'candidate_sha256':digest(target),'paths':len(path_list),
        'vertices':int(offsets[-1]),'seeds':len(p),'pruned_linelets':int(good.sum()),'nms_linelets':int(nms.sum()),
        'seconds':time.perf_counter()-t,'legacy_cache_used':False,
        'train_rgb_sha256':{str(i):digest(paths[i]) for i in views}}
    dump(DEV/'candidates.json',report); print(json.dumps({k:v for k,v in report.items() if k!='provenance'},indent=2),flush=True)


def load_candidates(m):
    meta=json.loads((DEV/'candidates.json').read_text())
    if meta['provenance']['manifest_sha256']!=digest(OUT/'manifest.json') or meta['candidate_sha256']!=digest(DEV/'candidates.npz'):
        raise RuntimeError('candidate provenance mismatch')
    if meta['provenance']['seed_indices']!=m['split']['seed_indices'] or meta['legacy_cache_used']:
        raise RuntimeError('candidate TRAIN provenance invalid')
    # Any implementation change after freeze requires an explicit audit, not
    # silently reusing a differently generated pool.
    for source,expected in meta['provenance']['source_sha256'].items():
        if source not in ('scripts/run_vrss.py','src/stroke_relations.py','src/stroke_select.py') and digest(ROOT/source)!=expected:
            raise RuntimeError(f'candidate-generating source changed: {source}')
    z=np.load(DEV/'candidates.npz'); p=z['vertices']; offsets=z['offsets']
    return [p[a:b] for a,b in zip(offsets[:-1],offsets[1:])]


def evidence(m,cams,paths):
    if (DEV/'evidence.json').exists():raise FileExistsError('evidence already frozen')
    t=time.perf_counter(); candidate_paths=relations.densify(load_candidates(m))
    g=common.load_gaussians(m['scene']); keep=render.defloat_mask(g['mu'],g['opacity'])
    unary=[]; lengths=[]; entries=[]; overlaps=[]; stats=[]
    for vi,v in enumerate(m['split']['evidence_indices']):
        cam=scaled(cams[v],m['evidence']['resolution'])
        gb=render.render_gbuffer(g,keep,cam)
        projected=relations.project_paths(candidate_paths,cam,gb['depth'])
        gray=cv2.cvtColor(rgb_white(paths[v],cam.W),cv2.COLOR_BGR2GRAY)
        u,l,e,o,s=relations.view_evidence(gray,projected,m['evidence'],vi)
        unary.append(u);lengths.append(l);entries+=e;overlaps+=o;stats.append(dict(s,source_train_index=v))
        print(f'[evidence] {vi+1}/16 view={v} {s}',flush=True)
        del gb;torch.cuda.empty_cache()
    costs=np.mean(lengths,axis=0)/np.hypot(cam.H,cam.W)
    np.savez_compressed(DEV/'evidence.npz',unary=np.asarray(unary),lengths=np.asarray(lengths),costs=costs)
    dump(DEV/'evidence.json',{'provenance':provenance(m),'candidate_sha256':digest(DEV/'candidates.npz'),
        'array_sha256':digest(DEV/'evidence.npz'),'relations':entries,'overlap':overlaps,'views':stats,'seconds':time.perf_counter()-t})


def load_objective(m):
    meta=json.loads((DEV/'evidence.json').read_text())
    if meta['provenance']['manifest_sha256']!=digest(OUT/'manifest.json') or meta['candidate_sha256']!=digest(DEV/'candidates.npz') or meta['array_sha256']!=digest(DEV/'evidence.npz'):
        raise RuntimeError('evidence provenance mismatch')
    a=np.load(DEV/'evidence.npz');cfg=m['selection']
    obj=Objective(a['unary'],a['costs'],meta['relations'],[v['relations'] for v in meta['views']],meta['overlap'],alpha=cfg['alpha'],beta=cfg['beta'],tail_fraction=cfg['tail_fraction'])
    return obj,meta


def selection(m):
    load_candidates(m);obj,meta=load_objective(m);cfg=m['selection']; results={}
    for mode in 'ABCD':
        path=DEV/f'selection_{mode}.json'
        if path.exists(): raise FileExistsError(path)
        print(f'[selector] start {mode}, N={obj.N}, bundles={len(obj.bundles)}',flush=True)
        x,audit=select(obj,cfg['budget_fraction']*obj.costs.sum(),mode,
            **{key:cfg[key] for key in ('max_greedy_steps','max_swap_passes','swap_shortlist')})
        audit['budget_matched']=cfg['min_spent_fraction_of_pool']<=audit['spent_fraction_of_pool']<=cfg['budget_fraction']+1e-10
        audit['provenance']=provenance(m);audit['candidate_sha256']=digest(DEV/'candidates.npz');audit['evidence_sha256']=digest(DEV/'evidence.npz')
        dump(path,audit);results[mode]=audit
        print(f"[selector] {mode} paths={audit['n_selected']} length={audit['spent_fraction_of_pool']:.6f} q25={audit['q_common_worst25']:.6f} seconds={audit['seconds']:.2f}",flush=True)
    dump(DEV/'selection_summary.json',{k:{key:v[key] for key in ('n_selected','spent_fraction_of_pool','budget_matched','q_common_mean','q_common_worst25','seconds')} for k,v in results.items()})


def orbit(m,cams,g,keep):
    cfg=m['dev_trajectory'];reference=cams[cfg['reference_train_index']]
    target=np.median(g['mu'][keep],axis=0);offset=reference.center-target
    radius=np.linalg.norm(offset[:2]);phi0=np.arctan2(offset[1],offset[0]);out=[]
    K=scaled(reference,cfg['resolution']).K
    for j in range(cfg['frames']):
        phi=phi0+2*np.pi*j/cfg['frames'];C=target+np.array([radius*np.cos(phi),radius*np.sin(phi),offset[2]])
        forward=target-C;forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right)
        down=np.cross(forward,right);c2w=np.eye(4);c2w[:3,:3]=np.stack([right,down,forward],axis=1);c2w[:3,3]=C
        out.append(common.Camera(K,np.linalg.inv(c2w),cfg['resolution'],cfg['resolution'],f'dev_{j:03d}'))
    return out


def label(im,text):
    bar=np.full((26,im.shape[1],3),255,np.uint8)
    cv2.putText(bar,text,(6,18),cv2.FONT_HERSHEY_SIMPLEX,.46,(0,0,0),1,cv2.LINE_AA)
    return np.vstack([bar,im])


def render_video(m,cams):
    if (DEV/'render_metrics.json').exists():raise FileExistsError('render already completed')
    import imageio_ffmpeg
    t=time.perf_counter();paths=relations.densify(load_candidates(m))
    selected={};selection_hashes={}
    for mode in 'ABCD':
        path=DEV/f'selection_{mode}.json';data=json.loads(path.read_text())
        if data['candidate_sha256']!=digest(DEV/'candidates.npz') or data['provenance']['manifest_sha256']!=digest(OUT/'manifest.json'):
            raise RuntimeError('selection provenance mismatch')
        x=np.zeros(len(paths),bool);x[data['selected_ids']]=True;selected[mode]=x;selection_hashes[mode]=digest(path)
    g=common.load_gaussians(m['scene']);keep=render.defloat_mask(g['mu'],g['opacity'])
    trajectory=orbit(m,cams,g,keep);official=render.OfficialRGBRenderer(m['gs']['path'],EXT)
    dump(DEV/'dev_cameras.json',{'K':trajectory[0].K.tolist(),'w2c':[c.w2c.tolist() for c in trajectory],'source':'TRAIN-derived synthetic DEV orbit, no TEST cameras'})
    writers={name:imageio_ffmpeg.write_frames(str(DEV/f'{name}.mp4'),(1200,426),fps=m['dev_trajectory']['fps'],codec='libx264',quality=8,macro_block_size=1) for name in ('rgb_A_D','ablation_B_C_D')}
    for writer in writers.values():writer.send(None)
    fixed=[];ablations=[];thumbs=[];metrics={k:[] for k in 'ABCD'};frame_ids=[0,30,60,90]
    for j,cam in enumerate(trajectory):
        gb=render.render_gbuffer(g,keep,cam)
        projected=relations.project_paths(paths,cam,gb['depth'])
        rgb=(official(cam)[:,:,::-1]*255).astype(np.uint8)
        drawings={mode:relations.draw_paths(projected,x,(cam.H,cam.W),m['brush']['width_px']) for mode,x in selected.items()}
        main=np.hstack([label(rgb,f'Official GS RGB | frame {j:03d}'),label(drawings['A'],'A independent / average'),label(drawings['D'],'D full VRSS')])
        ablation=np.hstack([label(drawings[k],f'{k} '+{'B':'no relations','C':'no tail','D':'full VRSS'}[k]+f' | frame {j:03d}') for k in 'BCD'])
        writers['rgb_A_D'].send(np.ascontiguousarray(main[:,:,::-1]));writers['ablation_B_C_D'].send(np.ascontiguousarray(ablation[:,:,::-1]))
        if j in frame_ids:
            fixed.append(main);ablations.append(ablation)
            cv2.imwrite(str(DEV/f'frame_{j:03d}.png'),main)
        thumbs.append(cv2.resize(main,(360,128),interpolation=cv2.INTER_AREA))
        for mode,x in selected.items():
            metrics[mode].append(dict(frame=j,**relations.projected_metrics(projected,x,(cam.H,cam.W))))
        if j%10==0:print(f'[video] {j}/{len(trajectory)} elapsed={time.perf_counter()-t:.1f}s',flush=True)
        del gb;torch.cuda.empty_cache()
    for writer in writers.values():writer.close()
    cv2.imwrite(str(DEV/'fixed_quartiles.png'),np.vstack(fixed))
    cv2.imwrite(str(DEV/'ablation_quartiles.png'),np.vstack(ablations))
    cv2.imwrite(str(DEV/'complete_contact_sheet.png'),np.vstack([np.hstack(thumbs[i:i+4]) for i in range(0,len(thumbs),4)]))
    counts={}
    for name in writers:
        capture=cv2.VideoCapture(str(DEV/f'{name}.mp4'));count=0
        while True:
            ok,_=capture.read()
            if not ok:break
            count+=1
        capture.release();counts[name]=count
        if count!=len(trajectory):raise RuntimeError(f'incomplete video: {name} {count}')
    avg={mode:{key:float(np.mean([row[key] for row in rows])) for key in rows[0] if key!='frame'} for mode,rows in metrics.items()}
    dump(DEV/'render_metrics.json',{'provenance':provenance(m),'candidate_sha256':digest(DEV/'candidates.npz'),
        'selection_sha256':selection_hashes,'frames':len(trajectory),'decoded_frames':counts,'fixed_frames':frame_ids,
        'per_frame':metrics,'mean':avg,'seconds':time.perf_counter()-t,
        'q_scope':'q values in selection_*.json use TRAIN evidence only; no DEV image evidence queried at runtime',
        'videos':{name:{'sha256':digest(DEV/f'{name}.mp4'),'bytes':(DEV/f'{name}.mp4').stat().st_size} for name in writers}})
    print(json.dumps(avg,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('smoke','candidates','evidence','select','render'))
    args=parser.parse_args();m=checked_manifest();np.random.seed(m['seed']);torch.manual_seed(m['seed'])
    torch.set_num_threads(4);cv2.setNumThreads(1)
    cams,paths=common.load_cameras(m['scene']);access=install_read_guard(m,paths)
    DEV.mkdir(parents=True,exist_ok=True)
    functions={'smoke':lambda:smoke(m,cams,paths),'candidates':lambda:candidates(m,cams,paths),
        'evidence':lambda:evidence(m,cams,paths),'select':lambda:selection(m),'render':lambda:render_video(m,cams)}
    audit_path=DEV/f'access_{args.stage}.json'
    if audit_path.exists():raise FileExistsError(audit_path)
    try:
        functions[args.stage]()
    except Exception as exc:
        access['failure']=repr(exc)
        raise
    finally:
        dump(audit_path,access)

if __name__=='__main__':main()
