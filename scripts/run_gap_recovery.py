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
from src import bridge_evidence as evidence
# Read-only reuse of audited full-K scaling and the pinned stock official RGB
# loader. No run_vrss CLI/checker is called and no old result is written.
from run_vrss import stock_rgb,scaled,rgb_white,label,orbit

OUT=ROOT/'out/gap_recovery'
BASE='9e643c2408954dffcfa8b298d5204e7314863a91'
RUN_NAME=None


def result_dir(scene):
    return OUT/(RUN_NAME or f'{scene}_dev')


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
        if p.name=='G1_AUDIT.json':raise RuntimeError('human evaluation labels forbidden in method')
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


def frozen_inputs(m):
    for record in m['pool'].values():
        if digest(record['path'])!=record['sha256']:raise RuntimeError('frozen pool changed')
    for path,h in m['core_source_sha256'].items():
        if digest(ROOT/path)!=h:raise RuntimeError('preregistered core changed: '+path)
    paths=load_paths(m['pool']['candidates.npz']['path'])
    meta=json.loads(Path(m['pool']['hypotheses.json']['path']).read_text())
    curves=load_paths(m['pool']['hypotheses.npz']['path'])
    proposals=[dict(row,points=p) for row,p in zip(meta['bridges'],curves)]
    assert len(curves)==len(meta['bridges'])
    return paths,proposals


def run_provenance():
    sources=['scripts/run_gap_recovery.py','scripts/run_vrss.py','src/stroke_bridge.py',
        'src/bridge_evidence.py','src/stroke_relations.py','src/common.py','src/render.py','src/visibility.py']
    return dict(commit=git('rev-parse','HEAD'),manifest_sha256=digest(OUT/'MANIFEST.json'),
                source_sha256={p:digest(ROOT/p) for p in sources})


def score_views(m,scene,cams,photos,paths,proposals,indices):
    g=common.load_gaussians(scene);keep=render.defloat_mask(g['mu'],g['opacity'])
    dense=drawing.densify(paths);rows=[[] for _ in proposals];cost=[];original=[]
    for index in indices:
        cam=scaled(cams[index],m['resolution']);gb=render.render_gbuffer(g,keep,cam)
        dt,tan=evidence.edge_field(rgb_white(photos[index],cam.W),m['evidence'])
        depth=gb['depth'].detach().cpu().numpy();alpha=gb['alpha'].detach().cpu().numpy()
        original.append(float(drawing.path_lengths(drawing.project_paths(dense,cam,gb['depth'])).sum()))
        cost.append(drawing.path_lengths(drawing.project_paths([b['points'] for b in proposals],cam,gb['depth'])))
        for b,out in zip(proposals,rows):
            out.append(dict(view=index,**evidence.view_score(b['points'],cam,depth,alpha,dt,tan,m['evidence'])))
        print('score TRAIN',index,'bridges',len(proposals),flush=True)
        del gb;torch.cuda.empty_cache()
    return rows,np.asarray(cost),np.asarray(original)


def fit(m,scene,cams,photos):
    dest=result_dir(scene);dest.mkdir(parents=True,exist_ok=True)
    if (dest/'frozen_bridges.json').exists():raise FileExistsError('selection already frozen')
    t=time.perf_counter();paths,proposals=frozen_inputs(m)
    rows,cost,original=score_views(m,scene,cams,photos,paths,proposals,m['fit_indices'])
    centers=[cams[i].center for i in m['fit_indices']]
    agg=[evidence.aggregate(r,centers,b['points'].mean(0),m['evidence']) for r,b in zip(rows,proposals)]
    object_scores=[b['object_score'] for b in proposals]
    full_scores=[s*a['image_score'] for s,a in zip(object_scores,agg)]
    length3d=sum(np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in paths)
    variants={};details=[]
    for name,scores in [('object_only',object_scores),('object_image',full_scores)]:
        ids,audit=bridge.choose(proposals,scores,cost,original,length3d,
            max_bridges=m['budget']['max_bridges'],fraction=m['budget']['max_added_visible_fraction'])
        variants[name]=dict(selected_ids=ids,selection_audit=audit,
            paths=[dict(bridge_id=i,endpoint_ids=proposals[i]['endpoint_ids'],points=proposals[i]['points'].tolist()) for i in ids],
            fit_added_visible_fractions=(np.asarray(audit['added_visible_lengths'])/np.maximum(original,1e-12)).tolist())
    for b,r,a in zip(proposals,rows,agg):
        details.append(dict(object={k:v for k,v in b.items() if k!='points'},views=r,aggregate=a))
    dump(dest/'fit_evidence.json',dict(provenance=run_provenance(),fit_indices=m['fit_indices'],bridges=details,
        original_visible_lengths=original.tolist(),original_length_3d=float(length3d),seconds=time.perf_counter()-t))
    dump(dest/'frozen_bridges.json',dict(provenance=run_provenance(),variants=variants,
        candidate_sha256=m['pool']['candidates.npz']['sha256'],evidence_sha256=digest(dest/'fit_evidence.json'),
        seconds=time.perf_counter()-t))
    print(json.dumps({k:dict(ids=v['selected_ids'],fit_added_visible_fractions=v['fit_added_visible_fractions']) for k,v in variants.items()},indent=2),flush=True)


def checked_selection(m,scene):
    p=result_dir(scene)/'frozen_bridges.json'
    relative=str(p.relative_to(ROOT))
    # Validation/final cameras stay sealed until exact selected paths are in Git.
    committed=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+relative])
    if hashlib.sha256(committed).hexdigest()!=digest(p):raise RuntimeError('selection not committed unchanged')
    selected=json.loads(p.read_text())
    if selected['provenance']['manifest_sha256']!=digest(OUT/'MANIFEST.json'):raise RuntimeError('selection manifest mismatch')
    if selected['candidate_sha256']!=m['pool']['candidates.npz']['sha256']:raise RuntimeError('selection pool mismatch')
    return selected


def validate(m,scene,cams,photos):
    dest=result_dir(scene);t=time.perf_counter();selected=checked_selection(m,scene)
    if (dest/'validation.json').exists():raise FileExistsError('validation already completed')
    paths,all_proposals=frozen_inputs(m)
    ids=sorted(set(i for v in selected['variants'].values() for i in v['selected_ids']))
    proposals=[all_proposals[i] for i in ids]
    if not proposals:
        dump(dest/'validation.json',dict(bridges=[],majority_pass=False,reason='no accepted bridges'));return
    rows,_,_=score_views(m,scene,cams,photos,paths,proposals,m['validation_indices'])
    detail=[]
    for b,r in zip(proposals,rows):
        q=sum(v['qualified'] for v in r);s=sum(v['passed'] for v in r)
        veto=any(v['reason']=='cross_depth_or_background' for v in r)
        detail.append(dict(bridge_id=b['bridge_id'],views=r,qualified_views=q,supported_views=s,
                           support_rate=s/max(q,1),passed=s>=2 and s/max(q,1)>=.6 and not veto))
    full=selected['variants']['object_image']['selected_ids']
    passed=sum(d['passed'] for d in detail if d['bridge_id'] in full)
    dump(dest/'validation.json',dict(provenance=run_provenance(),validation_indices=m['validation_indices'],
        selected_bridge_sha256=digest(dest/'frozen_bridges.json'),bridges=detail,
        full_accepted=len(full),full_validation_pass=passed,majority_pass=bool(full) and passed>len(full)/2,
        seconds=time.perf_counter()-t))
    print('validation full:',passed,'/',len(full),flush=True)


def render_result(m,scene,cams,photos):
    """Runtime: fixed 3D curves, GS geometry, camera only. No image evidence."""
    import imageio_ffmpeg
    dest=result_dir(scene);t=time.perf_counter();selected=checked_selection(m,scene)
    if (dest/'render_metrics.json').exists():raise FileExistsError('render already completed')
    paths,_=frozen_inputs(m);dense=drawing.densify(paths)
    variants=selected['variants'];ids=sorted(set(i for v in variants.values() for i in v['selected_ids']))
    lookup={p['bridge_id']:np.asarray(p['points']) for v in variants.values() for p in v['paths']}
    curves=[lookup[i] for i in ids]
    mask={name:np.asarray([i in v['selected_ids'] for i in ids]) for name,v in variants.items()}
    g=common.load_gaussians(scene);keep=render.defloat_mask(g['mu'],g['opacity'])
    trajectory=orbit(m,cams,g,keep);official,info=stock_rgb(dict(gs=m['inputs'][scene]['gs'],renderer=m['renderer']))
    dump(dest/'dev_cameras.json',dict(K=trajectory[0].K.tolist(),w2c=[c.w2c.tolist() for c in trajectory],
        source='new TRAIN7-derived synthetic DEV orbit; never used for selection'))
    names=['rgb_original_recovered','ablation_original_object_full','bridge_debug_all']
    writers={name:imageio_ffmpeg.write_frames(str(dest/f'{name}.mp4'),(1200,426),fps=m['dev_trajectory']['fps'],codec='libx264',quality=8,macro_block_size=1) for name in names}
    for writer in writers.values():writer.send(None)
    panels=[];ablations=[];debug_panels=[];thumbs=[];metrics=[]
    for frame,cam in enumerate(trajectory):
        gb=render.render_gbuffer(g,keep,cam)
        pp=drawing.project_paths(dense,cam,gb['depth'])
        bp=drawing.project_paths(curves,cam,gb['depth']) if curves else []
        base=drawing.draw_paths(pp,np.ones(len(paths),bool),(cam.H,cam.W),m['width_px'])
        base_length=float(drawing.path_lengths(pp).sum());bl=drawing.path_lengths(bp)
        rgb=(official(cam)[:,:,::-1]*255).astype(np.uint8);ims={};debug={};row={'frame':frame,'original_visible_length_px':base_length,'bridges_visible_length_px':dict(zip(map(str,ids),map(float,bl)))}
        for name in variants:
            ink=drawing.draw_paths(bp,mask[name],(cam.H,cam.W),m['width_px'])
            ims[name]=np.minimum(base,ink);debug[name]=base.copy()
            for i in np.flatnonzero(mask[name]):
                for run in bp[i]:
                    cv2.polylines(debug[name],[np.round(run*16).astype(np.int32)],False,(0,0,220),2,cv2.LINE_AA,4)
                    xy=np.round(run[len(run)//2]).astype(int)
                    cv2.putText(debug[name],str(ids[i]),tuple(xy),cv2.FONT_HERSHEY_SIMPLEX,.25,(160,0,0),1,cv2.LINE_AA)
            added=float(bl[mask[name]].sum())
            row[name]=dict(bridges=len(variants[name]['selected_ids']),added_visible_length_px=added,
                added_visible_length_fraction=added/max(base_length,1e-12),
                added_ink_area_px=float(((base[:,:,0].astype(float)-ims[name][:,:,0])/255.).sum()),
                original_ink_area_px=float((1-base[:,:,0]/255.).sum()))
        main=np.hstack([label(rgb,f'Official GS RGB | frame {frame:03d}'),label(base,'Original chains'),label(ims['object_image'],'Persistent bridges + image evidence')])
        ablation=np.hstack([label(base,'Original'),label(ims['object_only'],'Object-only bridges'),label(ims['object_image'],'Object + image evidence')])
        diagnostic=np.hstack([label(rgb,f'All bridges DIAGNOSTIC {frame:03d}'),label(debug['object_only'],'Object only / red = added'),label(debug['object_image'],'Object + image / red = added')])
        for name,im in zip(names,[main,ablation,diagnostic]):writers[name].send(np.ascontiguousarray(im[:,:,::-1]))
        if frame in (0,30,60,90):
            panels.append(main);ablations.append(ablation);debug_panels.append(diagnostic)
            cv2.imwrite(str(dest/f'frame_{frame:03d}.png'),main)
        thumbs.append(cv2.resize(main,(600,213),interpolation=cv2.INTER_AREA));metrics.append(row)
        if frame%10==0:print('render',frame,'/120',round(time.perf_counter()-t,1),'s',flush=True)
        del gb;torch.cuda.empty_cache()
    for writer in writers.values():writer.close()
    for name,items in [('fixed_quartiles',panels),('ablation_quartiles',ablations),('bridge_debug',debug_panels)]:
        cv2.imwrite(str(dest/f'{name}.png'),np.vstack(items))
    # Six pages contain EVERY frame at a readable 600px-wide triptych size.
    for page,start in enumerate(range(0,len(thumbs),20)):
        cv2.imwrite(str(dest/f'contact_sheet_{page:02d}.png'),np.vstack([np.hstack(thumbs[i:i+2]) for i in range(start,min(start+20,len(thumbs)),2)]))
    counts={}
    for name in names:
        cap=cv2.VideoCapture(str(dest/f'{name}.mp4'));count=0
        while True:
            ok,_=cap.read()
            if not ok:break
            count+=1
        cap.release();counts[name]=count
        if count!=len(trajectory):raise RuntimeError('incomplete video: '+name)
    summary={name:dict(n_bridges=len(v['selected_ids']),max_added_visible_fraction=max(r[name]['added_visible_length_fraction'] for r in metrics),
         mean_added_visible_fraction=float(np.mean([r[name]['added_visible_length_fraction'] for r in metrics])),
         mean_added_ink_area_px=float(np.mean([r[name]['added_ink_area_px'] for r in metrics]))) for name,v in variants.items()}
    dump(dest/'render_metrics.json',dict(provenance=run_provenance(),official_rgb=info,
        frozen_selection_sha256=digest(dest/'frozen_bridges.json'),frames=len(trajectory),decoded_frames=counts,
        videos={n:dict(sha256=digest(dest/f'{n}.mp4'),bytes=(dest/f'{n}.mp4').stat().st_size) for n in names},
        per_frame=metrics,summary=summary,seconds=time.perf_counter()-t))
    print(json.dumps(summary,indent=2),flush=True)


def main():
    global RUN_NAME
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['candidates','audit','fit','validate','render'])
    parser.add_argument('--scene',required=True,choices=['chair','lego','cadpartA'])
    parser.add_argument('--run-name',help='fresh result subdirectory for an exact frozen-pool rerun; fit/validate/render only')
    args=parser.parse_args()
    if git('branch','--show-current')!='gap-recovery':raise RuntimeError('wrong branch')
    later=args.stage in ('fit','validate','render')
    if args.run_name:
        if not later or not args.run_name.startswith(args.scene+'_') or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in args.run_name):
            raise ValueError('run-name must be a scene-prefixed simple directory for a result stage')
        RUN_NAME=args.run_name
    m=json.loads((OUT/('MANIFEST.json' if later else 'AUDIT_CONFIG.json')).read_text())
    if later and args.scene!=m['scene']:raise RuntimeError('scene is not preregistered')
    for k in ('extraction_indices','audit_indices','fit_indices','validation_indices'):
        if not set(m[k])<=set(view_split.TRAIN):raise RuntimeError('non-TRAIN indices')
    if set(m['validation_indices'])&set(m['extraction_indices']):raise RuntimeError('validation leaked to extraction')
    if set(m['validation_indices'])&(set(m['fit_indices'])|set(m['audit_indices'])):raise RuntimeError('validation leaked to selection/audit')
    for record in m['inputs'][args.scene].values():
        if digest(record['path'])!=record['sha256']:raise RuntimeError('source changed')
    np.random.seed(m['seed']);torch.manual_seed(m['seed']);torch.set_num_threads(4);cv2.setNumThreads(1)
    cams,photos=common.load_cameras(args.scene)
    allowed={'candidates':m['extraction_indices'],'audit':m['audit_indices'],'fit':m['fit_indices'],
             'validate':m['validation_indices'],'render':[]}[args.stage]
    dest=result_dir(args.scene) if later else OUT/'audit'/args.scene
    dest.mkdir(parents=True,exist_ok=True)
    log=dest/f'access_{args.stage}.json'
    if log.exists():raise FileExistsError(log)
    access=guard(m,args.scene,allowed)
    try:
        {'candidates':candidates,'audit':audit_scene,'fit':fit,'validate':validate,'render':render_result}[args.stage](m,args.scene,cams,photos)
    except Exception as exc:
        access['failure']=repr(exc);raise
    finally:dump(log,access)


if __name__=='__main__':main()
