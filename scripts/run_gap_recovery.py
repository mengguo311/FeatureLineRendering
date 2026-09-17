#!/usr/bin/env python3
"""Bounded, mesh-free persistent bridge experiment. Never uses TEST/VAL RGB.

Run with vfsdgs Python from repository root; each stage refuses completed output.
Audit precedes scene/bridge preregistration. Later stages require MANIFEST.json.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
import cv2
import numpy as np
import torch
from src import common,render,linelet,dt_pull,linelet_prune,strokes,view_split
from src import stroke_relations as drawing
from src import stroke_bridge as bridge
# Read-only reuse of audited full-K scaling and the pinned stock official RGB
# loader. No run_vrss CLI/checker is called and no old result is written.
from run_vrss import stock_rgb,scaled,rgb_white,label,orbit

OUT=ROOT/'out/gap_recovery'
BASE='9e643c2408954dffcfa8b298d5204e7314863a91'


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def dump(path,value):
    path=Path(path)
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def load_paths(path):
    z=np.load(path);p=z['vertices'];o=z['offsets']
    return [p[a:b] for a,b in zip(o[:-1],o[1:])]


def save_paths(path,paths):
    if Path(path).exists(): raise FileExistsError(path)
    np.savez_compressed(path,vertices=np.concatenate(paths) if paths else np.empty((0,3)),
                        offsets=np.r_[0,np.cumsum([len(p) for p in paths])].astype(int))


def guard(m,scene,allowed):
    """Defense-in-depth Python/native-imread access audit, not an OS sandbox."""
    _,photos=common.load_cameras(scene)
    approved={str(Path(photos[i]).resolve()) for i in allowed}
    gs=m['inputs'][scene]['gs']['path']
    reuse=ROOT/'out/vrss/chair_dev/candidates.npz'
    access={'rgb_reads':[],'data_reads':[],'allowed_rgb_indices':allowed}
    def check(name):
        if not isinstance(name,(str,bytes,os.PathLike)):return
        p=Path(os.fsdecode(name)).resolve();s=str(p);lo=s.lower()
        if any(x in lo for x in ('mesh_oracle','gt_crease','/meshes/','/mesh/','/2dgs_','/dd3')) or p.suffix.lower() in ('.obj','.off','.stl'):
            raise RuntimeError('forbidden method input: '+s)
        if p.suffix=='.ply' and s!=gs:raise RuntimeError('unapproved geometry: '+s)
        if '/data/full/' in s and p.suffix.lower() in ('.png','.jpg','.jpeg') and s not in approved:
            raise RuntimeError('unapproved RGB: '+s)
        if p.suffix in ('.npy','.npz') and not p.is_relative_to(OUT) and p!=reuse:
            raise RuntimeError('unapproved legacy cache: '+s)
        if '/cglib/' in s or p.is_relative_to(OUT) or p==reuse:
            if s not in access['data_reads']:access['data_reads'].append(s)
    def audit(event,args):
        if event=='open':
            mode=args[1]
            if isinstance(mode,str) and any(c in mode for c in 'wax'):return
            check(args[0])
    sys.addaudithook(audit)
    original=cv2.imread
    def imread(path,*args,**kwargs):
        check(path)
        if str(path) not in access['rgb_reads']:access['rgb_reads'].append(str(path))
        return original(str(path),*args,**kwargs)
    cv2.imread=imread
    return access


def candidates(m,scene,cams,photos):
    dest=OUT/'audit'/scene;dest.mkdir(parents=True,exist_ok=True)
    if (dest/'candidates.json').exists():raise FileExistsError(dest/'candidates.json')
    t=time.perf_counter();cfg=m['candidate_recipe'];views=m['extraction_indices']
    if scene=='chair':
        src=ROOT/'out/vrss/chair_dev/candidates.npz'
        meta=json.loads(src.with_suffix('.json').read_text())
        if digest(src)!=m['chair_reuse_sha256'] or meta['candidate_sha256']!=digest(src):
            raise RuntimeError('chair candidate checksum mismatch')
        if meta['provenance']['seed_indices']!=views or meta['provenance']['pull_indices']!=views or meta['legacy_cache_used']:
            raise RuntimeError('chair provenance invalid')
        for p,h in meta['provenance']['source_sha256'].items():
            if p not in ('scripts/run_vrss.py','src/stroke_relations.py','src/stroke_select.py') and digest(ROOT/p)!=h:
                raise RuntimeError('candidate-generating source changed: '+p)
        paths=load_paths(src);origin=str(src)
    else:
        sys.path.insert(0,str(ROOT/'scripts/explore/syn'))
        from m1a_seeds import extract_seeds
        p,_,_,X=extract_seeds(scene,'overall',keep_f=cfg['seed_fraction'],train_indices=views)
        g=common.load_gaussians(scene);keep=render.defloat_mask(g['mu'],g['opacity'])
        L=linelet.init_linelets(p,X,g['scale'][keep]);cache=dest/'train_cache'
        dt=dt_pull.build_dt_cache(scene,photos,views,cfg_name=cfg['edge'],force=True,cache_dir=str(cache))
        depth,fg=dt_pull.build_geom_cache(scene,g,keep,cams,views,force=True,cache_dir=str(cache))
        result=dt_pull.pull(dt_pull.PullField(cams,views,dt,depth,fg),L,
            steps=cfg['pull_steps'],lr=cfg['pull_lr'],delta_max=cfg['delta_max'])
        good,stats=linelet_prune.consensus_prune(result['resid'],result['vis'],**cfg['prune'])
        chains,nms=strokes.chain_linelets_3d(result['p'][good],result['t'][good],result['l'][good],
            conf=stats['inlier_ratio'][good],**cfg['chain'])
        paths=strokes.chain_vertices(chains,result['p'][good][nms]);origin='fresh canonical TRAIN-only same VRSS recipe'
    save_paths(dest/'candidates.npz',paths)
    dump(dest/'candidates.json',dict(scene=scene,paths=len(paths),vertices=sum(map(len,paths)),origin=origin,
        sha256=digest(dest/'candidates.npz'),seed_indices=views,pull_indices=views,mesh_free=True,vanilla_only=True,
        config_sha256=digest(OUT/'AUDIT_CONFIG.json'),commit=git('rev-parse','HEAD'),seconds=time.perf_counter()-t))
    print(scene,'candidate paths',len(paths),flush=True)


def audit_scene(m,scene,cams,photos):
    dest=OUT/'audit'/scene
    if (dest/'audit.json').exists():raise FileExistsError(dest/'audit.json')
    t=time.perf_counter();paths=load_paths(dest/'candidates.npz');dense=drawing.densify(paths)
    g=common.load_gaussians(scene);keep=render.defloat_mask(g['mu'],g['opacity'])
    proposals,pairlog,stats=bridge.propose(paths,g['mu'][keep],m['bridge'])
    save_paths(dest/'hypotheses.npz',[b['points'] for b in proposals])
    dump(dest/'hypotheses.json',dict(summary=stats,pairs=pairlog,
        bridges=[{k:v for k,v in b.items() if k!='points'} for b in proposals]))
    official,info=stock_rgb(dict(gs=m['inputs'][scene]['gs'],renderer=m['renderer']))
    panels=[];debug=[];projection_log=[]
    for index in m['audit_indices']:
        cam=scaled(cams[index],m['resolution']);gb=render.render_gbuffer(g,keep,cam)
        pp=drawing.project_paths(dense,cam,gb['depth'])
        im=drawing.draw_paths(pp,np.ones(len(paths),bool),(cam.H,cam.W),m['width_px'])
        rgb=(official(cam)[:,:,::-1]*255).astype(np.uint8)
        panels.append(np.hstack([label(rgb,f'{scene} official RGB TRAIN {index}'),label(im,'Original chains / no bridges')]))
        # All hypotheses are marked for audit only; these colored overlays are NOT
        # final method output and do not count as recovered gaps.
        marked=im.copy()
        for b in proposals:
            uv,z=common.project(b['points'],cam)
            from src.visibility import visible_mask
            vis,_,_=visible_mask(b['points'],cam,gb['depth'])
            if vis[[0,-1]].all() and (z>0).all() and np.all(uv>2) and np.all(uv<cam.W-3):
                middle=np.round(uv[len(uv)//2]).astype(int)
                cv2.circle(marked,tuple(middle),3,(0,0,220),1)
                cv2.putText(marked,str(b['bridge_id']),tuple(middle+[3,-3]),cv2.FONT_HERSHEY_SIMPLEX,.3,(150,0,0),1,cv2.LINE_AA)
                projection_log.append(dict(view=index,bridge_id=b['bridge_id'],uv=uv[[0,-1]].tolist(),
                    projected_gap_px=float(np.linalg.norm(np.diff(uv,axis=0),axis=1).sum()),visible_fraction=float(vis.mean())))
        debug.append(label(marked,f'TRAIN {index}: geometric hypotheses ONLY'))
        cv2.imwrite(str(dest/f'original_train_{index:03d}.png'),panels[-1])
        del gb;torch.cuda.empty_cache()
    cv2.imwrite(str(dest/'original_audit.png'),np.vstack(panels))
    cv2.imwrite(str(dest/'endpoint_audit.png'),np.vstack(debug))
    dump(dest/'audit.json',dict(scene=scene,official_rgb=info,summary=stats,projections=projection_log,
        audit_indices=m['audit_indices'],seconds=time.perf_counter()-t))
    print(scene,stats,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['candidates','audit'])
    parser.add_argument('--scene',required=True,choices=['chair','lego','cadpartA'])
    args=parser.parse_args()
    if git('branch','--show-current')!='gap-recovery':raise RuntimeError('wrong branch')
    m=json.loads((OUT/'AUDIT_CONFIG.json').read_text())
    for k in ('extraction_indices','audit_indices','fit_indices','validation_indices'):
        if not set(m[k])<=set(view_split.TRAIN):raise RuntimeError('non-TRAIN indices')
    if set(m['validation_indices'])&set(m['extraction_indices']):raise RuntimeError('validation leaked to extraction')
    for record in m['inputs'][args.scene].values():
        if digest(record['path'])!=record['sha256']:raise RuntimeError('source changed')
    np.random.seed(m['seed']);torch.manual_seed(m['seed']);torch.set_num_threads(4);cv2.setNumThreads(1)
    cams,photos=common.load_cameras(args.scene)
    allowed=m['extraction_indices'] if args.stage=='candidates' else m['audit_indices']
    dest=OUT/'audit'/args.scene;dest.mkdir(parents=True,exist_ok=True)
    log=dest/f'access_{args.stage}.json'
    if log.exists():raise FileExistsError(log)
    access=guard(m,args.scene,allowed)
    try:
        {'candidates':candidates,'audit':audit_scene}[args.stage](m,args.scene,cams,photos)
    except Exception as exc:
        access['failure']=repr(exc);raise
    finally:dump(log,access)


if __name__=='__main__':main()
