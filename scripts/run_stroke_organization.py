#!/usr/bin/env python3
"""Frozen-Lego-D stroke organization; all writes confined to this experiment.

No mesh or held-out image is an input. Subcommands are separate reproducible stages.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree
from src import common, strokes, linelet_prune, stroke_relations as draw
from src.visibility import visible_mask
from run_vrss import scaled, label, stock_rgb, rgb_white
from src import stroke_graph as sg

OUT = ROOT / 'out/stroke_organization'
OLD = ROOT / 'out/raster_state_candidates/lego'
BASE = '3a10d3908173e35d359d41eec1469f5adaac4e56'
INPUT_HASH = '47ca8925cb86a98886f97aa3c88ef58f5c821cfdcfd656a3fb0a0ec19ca1d489'
TRAIN = [1,7,14,21,27,33,41,47,53,59,67,73,79,86,93,99]
ARMS = ['A','B','C','C-no-global','C-no-corner','N']

def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(p, value):
    p = Path(p)
    if p.exists(): raise FileExistsError(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def check_branch():
    if git('branch','--show-current') != 'stroke-organization':
        raise RuntimeError('STOP: wrong branch')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT,check=True)

def guard():
    """Block unapproved geometry, legacy caches and non-TRAIN photos at file access."""
    _, photos = common.load_cameras('lego')
    approved = {str(Path(photos[i]).resolve()) for i in TRAIN}
    access = dict(rgb_reads=[], data_reads=[], allowed_indices=TRAIN)
    allowed_old = ['step1/','step3/clusters_D.json','step4/pulled_D.npz',
                   'step4/paths_D.npz','step4/arm_D.json','baseline_initial.npz']
    def check(name):
        if not isinstance(name,(str,bytes,os.PathLike)): return
        p=Path(os.fsdecode(name)).resolve(); s=str(p)
        if any(t in s.lower() for t in ('mesh_oracle','gt_crease','/meshes/','/mesh/','/2dgs_','/dd3')) or p.suffix in ('.obj','.off','.stl'):
            raise RuntimeError('forbidden input '+s)
        if p.suffix == '.ply' and s != '/home/u00134/cglib/outputs/lego_static/point_cloud.ply':
            raise RuntimeError('unapproved geometry '+s)
        if '/data/full/' in s and p.suffix in ('.png','.jpg') and s not in approved:
            raise RuntimeError('non-TRAIN image '+s)
        if p.is_relative_to(OLD):
            rel=str(p.relative_to(OLD))
            if not any(rel == a or (a.endswith('/') and rel.startswith(a)) for a in allowed_old):
                raise RuntimeError('unapproved historical input '+s)
            if rel.startswith('step1/'):
                tail=p.stem.rsplit('_',1)[-1]
                if not tail.isdigit() or int(tail) not in TRAIN:
                    raise RuntimeError('unapproved TRAIN cache '+s)
        if p.suffix in ('.npz','.npy') and not (p.is_relative_to(OUT) or p.is_relative_to(OLD)):
            raise RuntimeError('unapproved cache '+s)
        if p.is_relative_to(OUT) or p.is_relative_to(OLD) or '/cglib/' in s:
            if s not in access['data_reads']: access['data_reads'].append(s)
    def audit(event,args):
        if event=='open' and not (isinstance(args[1],str) and any(c in args[1] for c in 'wax')):
            check(args[0])
    sys.addaudithook(audit); original=cv2.imread
    def imread(p,*a,**kw):
        check(p)
        if '/data/full/' in str(p) and str(p) not in access['rgb_reads']:access['rgb_reads'].append(str(p))
        return original(str(p),*a,**kw)
    cv2.imread=imread
    return access

def load_nodes():
    p = OLD/'step4/pulled_D.npz'
    if sha(p)!=INPUT_HASH: raise RuntimeError('frozen input hash mismatch')
    z=dict(np.load(p)); good=z['good']; original=np.flatnonzero(good)
    conf=linelet_prune.consensus_stats(z['resid'],z['vis'],tau_in=1.5)['inlier_ratio']
    chains,keep=strokes.chain_linelets_3d(z['p'][good],z['t'][good],z['l'][good],conf=conf[good],
        nms_radius_mult=1.,k=10,cos_tan=.6,cos_col=.5,gap_mult=4.,min_nodes=3)
    ids=original[keep]
    meta=json.loads((OLD/'step4/arm_D.json').read_text())
    if [ids[c].tolist() for c in chains] != meta['path_source_indices']:
        raise RuntimeError('baseline no longer reproduces frozen D')
    data={key:z[key][ids] for key in ['p','t','l']}
    data.update(ids=ids,conf=conf[ids],vis=z['vis'][:,ids],base_chains=chains,
                raw_count=len(z['p']),pruned_count=int(good.sum()))
    return data

def audit():
    start=time.perf_counter();d=load_nodes();cams,_=common.load_cameras('lego')
    folder=OUT/'audit';folder.mkdir(parents=True,exist_ok=True)
    p,t,l=d['p'],d['t'],d['l']; paths=[p[c] for c in d['base_chains']]
    segments=[np.stack([a-b*c,a+b*c]) for a,b,c in zip(p,t,l)]
    panels=[];per_view=[]
    for v in [1,27,53,79]:
        cam=scaled(cams[v],400);state=np.load(OLD/f'step1/state_{v:03d}.npz')
        depth=torch.from_numpy(state['depth'])
        rgb=cv2.imread(str(OLD/f'step1/channels_{v:03d}.png'))[26:426,:400]
        pp=draw.project_paths(draw.densify(paths),cam,depth)
        raw=draw.project_paths(segments,cam,depth)
        images=[rgb,draw.draw_paths(raw,np.ones(len(raw),bool),(400,400)),draw.draw_paths(pp,np.ones(len(pp),bool),(400,400))]
        row=np.hstack([label(im,title) for im,title in zip(images,[f'Official RGB TRAIN{v}',f'Frozen D / {len(p)} NMS nodes','A: existing chainer'])])
        panels.append(row);cv2.imwrite(str(folder/f'train_{v:03d}.png'),row)
        lengths=[float(np.linalg.norm(np.diff(run,axis=0),axis=1).sum()) for runs in pp for run in runs]
        per_view.append(dict(view=v,visible_fragments=len(lengths),short_fraction_lt12=float(np.mean(np.array(lengths)<12)),median_fragment_px=float(np.median(lengths))))
    cv2.imwrite(str(folder/'train_contact.png'),np.vstack(panels))
    lengths=np.array([np.linalg.norm(np.diff(x,axis=0),axis=1).sum() for x in paths])
    endpoints=np.concatenate([x[[0,-1]] for x in paths]);pairs=cKDTree(endpoints).query_pairs(4*np.median(l))
    source_counts={}; clusters=json.loads((OLD/'step3/clusters_D.json').read_text())['clusters']
    nbase=len(np.load(OLD/'baseline_initial.npz')['p']); used=set(np.concatenate([d['ids'][x] for x in d['base_chains']]).tolist())
    for source in range(6):
        original={nbase+j for j,c in enumerate(clusters) if source in c['source_tags']}
        source_counts[str(source)]=dict(raw=len(original),nms=len(original&set(d['ids'].tolist())),in_A_chains=len(original&used))
    dump(folder/'audit.json',dict(commit=git('rev-parse','HEAD'),input_sha256=INPUT_HASH,raw_nodes=d['raw_count'],pruned_nodes=d['pruned_count'],
        common_nms_nodes=len(p),baseline_paths=len(paths),baseline_used_nodes=len(used),potential_endpoint_pairs=len(pairs),
        path_length_quantiles=np.quantile(lengths,[0,.1,.5,.9,1]).tolist(),train_views=per_view,overlapping_source_survival=source_counts,seconds=time.perf_counter()-start))
    print(json.loads((folder/'audit.json').read_text()),flush=True)

def graph_stage(m):
    start=time.perf_counter();d=load_nodes();p,t,l=d['p'],d['t'],d['l'];cfg=m['graph']
    folder=OUT/'graph';folder.mkdir(exist_ok=True)
    graph=sg.geometry_graph(p,t,l,cfg);all_pairs=graph['pairs'];keep=graph['allowed']
    pairs=all_pairs[keep];n=len(p);g=common.load_gaussians('lego');tree=cKDTree(g['mu'])
    initial=np.load(OLD/'baseline_initial.npz');nbase=len(initial['p0'])
    distance,seed_ids=tree.query(initial['p0'],workers=1)
    if distance.max()>1e-7:raise RuntimeError('M1a seed IDs cannot be recovered exactly')
    cs=json.loads((OLD/'step3/clusters_D.json').read_text())['clusters']
    idsets=[];tags=[];source_weight=[];support_views=[];names=['topk','rgb','entropy','margin','variance','dispersion']
    for idx in d['ids']:
        if idx<nbase:
            idsets.append([int(seed_ids[idx])]);tags.append(['M1a']);source_weight.append(m['objective']['source_weights']['M1a'])
            support_views.append(np.asarray(TRAIN)[d['vis'][:,len(tags)-1]].tolist())
        else:
            c=cs[idx-nbase];idsets.append(c['ids']);tags.append([names[j] for j in c['source_tags']]);support_views.append(c['support_views'])
            # Average, never sum: many statistics tags do not manufacture confidence.
            source_weight.append(float(np.mean([m['objective']['source_weights'][names[j]] for j in c['source_tags']])))
    anchors=np.array([np.mean(g['mu'][ids],axis=0) for ids in idsets]);a,b=pairs.T
    shared=np.array([bool(set(idsets[i])&set(idsets[j])) for i,j in pairs])
    id_affinity=np.maximum(shared,np.exp(-np.linalg.norm(anchors[a]-anchors[b],axis=1)/(4*graph['unit'])))
    cams,photos=common.load_cameras('lego');evaluated=[];support=[];layers=[];length_px=[];node_support=[];node_eval=[];hashes={}
    for v in TRAIN:
        cam=scaled(cams[v],400);sp=OLD/f'step1/state_{v:03d}.npz';state=np.load(sp)
        field=sg.edge_field(rgb_white(photos[v],400))
        ev,su,layer,lp=sg.measure_view(p,pairs,cam,state['depth'],state['alpha'],field,cfg)
        nv,ns,*_=sg.visible_evidence(p,t,cam,state['depth'],state['alpha'],field,cfg)
        evaluated.append(ev);support.append(su);layers.append(layer);length_px.append(lp);node_support.append(ns);node_eval.append(nv)
        hashes[str(v)]=dict(state=sha(sp),rgb=sha(photos[v]))
        print('graph TRAIN',v,'evaluated',int(ev.sum()),'supported',int((ev&(su>=cfg['support_threshold'])).sum()),flush=True)
    ev=np.array(evaluated);su=np.array(support);layer=np.array(layers)
    physical=layer.sum(0)<cfg['layer_votes']
    nv=np.array(node_eval);ns=np.array(node_support)
    image_ok=(ev.sum(0)>=cfg['min_evaluated_views'])&((ev&(su>=cfg['support_threshold'])).sum(0)>=cfg['min_support_views'])
    full=physical&image_ok
    np.savez_compressed(folder/'graph.npz',p=p,t=t,l=l,original_ids=d['ids'],pairs=pairs,physical=physical,full=full,
        length=graph['length'][keep],gap=graph['gap'][keep],tube=graph['tube'][keep],continuation=graph['continuation'][keep],
        tangent_agreement=graph['tangent_agreement'][keep],corner=graph['corner'][keep],id_affinity=id_affinity,
        evaluated=ev,support=su,length_px=np.array(length_px),node_support=ns,node_evaluated=nv,
        source_weight=source_weight,unit=graph['unit'])
    dump(folder/'nodes.json',dict(original_ids=d['ids'].tolist(),gaussian_ids=idsets,sources=tags,views=support_views,
        M1a_id_recovery_max_error=float(distance.max()),M1a_id_mode='exact original p0 nearest PLY center; validated error <=1e-7'))
    comp,sz=sg.components(n,pairs[physical]);fc,fsz=sg.components(n,pairs[full])
    reasons={r:int(np.sum(graph['reason']==r)) for r in np.unique(graph['reason'])}
    counts=dict(nodes=n,potential_links=len(all_pairs),geometry_allowed=len(pairs),physical_allowed=int(physical.sum()),full_allowed=int(full.sum()),
        geometry_components=comp,full_components=fc,geometry_component_size_quantiles=np.quantile(sz,[.1,.5,.9,1]).tolist(),
        full_component_size_quantiles=np.quantile(fsz,[.1,.5,.9,1]).tolist(),geometry_reject_reasons=reasons,
        cross_depth_rejected=int((~physical).sum()),image_rejected=int((physical&~image_ok).sum()))
    # Node/link debug is a diagnostic overlay; primary renderings remain black/white.
    cam=scaled(cams[53],400);uv,_=common.project(p,cam)
    panels=[]
    for name,these,color in [('nodes',None,(50,50,50)),('allowed full',pairs[full],(0,150,0)),
                             ('image rejected',pairs[physical&~image_ok],(0,120,240)),
                             ('depth rejected',pairs[~physical],(0,0,200)),
                             ('geometric rejected',all_pairs[~keep],(180,0,180))]:
        im=np.full((400,400,3),255,np.uint8)
        if these is None:
            for x,y in np.round(uv).astype(int):
                if 0<=x<400 and 0<=y<400:im[y,x]=color
        else:
            for i,j in these:cv2.line(im,tuple(np.round(uv[i]).astype(int)),tuple(np.round(uv[j]).astype(int)),color,1,cv2.LINE_AA)
        panels.append(label(im,name+' (all depths)'))
    cv2.imwrite(str(folder/'graph_debug.png'),np.hstack(panels))
    regions=[];state=np.load(OLD/'step1/state_053.npz');depth=torch.from_numpy(state['depth']);vis,uv,_=visible_mask(p,cam,depth)
    auditim=cv2.imread(str(OUT/'audit/train_053.png'))
    rows=[]
    for r in m['regions']:
        x0,y0,x1,y1=r['box'];inside=vis&(uv[:,0]>=x0)&(uv[:,0]<x1)&(uv[:,1]>=y0)&(uv[:,1]<y1)
        intersect=[c for c in d['base_chains'] if inside[c].any()]
        regions.append(dict(**r,visible_nodes=int(inside.sum()),baseline_paths_touching=len(intersect),
                            full_links_inside=int((full&inside[a]&inside[b]).sum())))
        tiles=[]
        for col,title in enumerate(['Official RGB','frozen D nodes','A current chains']):
            crop=auditim[26+y0:26+y1,400*col+x0:400*col+x1]
            canv=np.full((180,360,3),255,np.uint8);ratio=min(360/crop.shape[1],180/crop.shape[0]);z=cv2.resize(crop,None,fx=ratio,fy=ratio,interpolation=cv2.INTER_NEAREST)
            canv[:z.shape[0],:z.shape[1]]=z;tiles.append(label(canv,r['id']+' '+title))
        rows.append(np.hstack(tiles))
    cv2.imwrite(str(folder/'premarked_regions.png'),np.vstack(rows))
    dump(folder/'audit.json',dict(**counts,regions=regions,input_hashes=hashes,graph_sha256=sha(folder/'graph.npz'),
        manifest_sha256=sha(OUT/'MANIFEST.json'),commit=git('rev-parse','HEAD'),seconds=time.perf_counter()-start))
    print(counts,flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['audit','graph'])
    args=parser.parse_args();check_branch();OUT.mkdir(exist_ok=True);access=guard()
    if args.stage=='audit':audit()
    else:graph_stage(json.loads((OUT/'MANIFEST.json').read_text()))
    dump(OUT/f'access_{args.stage}.json',access)

if __name__=='__main__':main()
