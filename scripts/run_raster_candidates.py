#!/usr/bin/env python3
"""Four explicit stages: raster evidence -> ID anchors -> aggregation -> linelets.
All scientific artifacts are immutable. Final camera access requires committed pools.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import cv2,numpy as np,torch
from src import common,render,raster_state as rs,linelet,dt_pull,linelet_prune,strokes,view_split
from src import stroke_relations as draw
from src import id_anchor as anchor,candidate_fusion as fusion
from scipy.spatial import cKDTree
from run_vrss import stock_rgb,scaled,label
OUT=ROOT/'out/raster_state_candidates'


def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):
    if Path(path).exists():raise FileExistsError(path)
    Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def arrays(path,**values):
    if Path(path).exists():raise FileExistsError(path)
    np.savez_compressed(path,**values)
def provenance():
    files=['scripts/run_raster_candidates.py','src/raster_state.py','src/render.py','src/dt_pull.py','src/strokes.py','scripts/explore/syn/m1a_seeds.py']
    files += [p for p in ('src/id_anchor.py','src/candidate_fusion.py') if (ROOT/p).exists()]
    return dict(commit=git('rev-parse','HEAD'),manifest_sha256=sha(OUT/'MANIFEST.json'),sources={p:sha(ROOT/p) for p in files})
def stage_dir(scene,cheap=False):return OUT/(scene+'_transfer' if cheap else scene)
def indices(m,cheap):return m['secondary_cheap_indices'] if cheap else m['train_indices']
def paths_from(z):return [z['vertices'][a:b] for a,b in zip(z['offsets'][:-1],z['offsets'][1:])]
def save_paths(path,paths):arrays(path,vertices=np.concatenate(paths) if paths else np.empty((0,3)),offsets=np.r_[0,np.cumsum([len(p) for p in paths])].astype(int))
def geom(scene):
    g=common.load_gaussians(scene);return g,render.defloat_mask(g['mu'],g['opacity'])


def install_guard(m,scene,allowed):
    _,photos=common.load_cameras(scene);approved={str(Path(photos[i]).resolve()) for i in allowed};gs=m['inputs'][scene]['gs']['path']
    access=dict(rgb_reads=[],data_reads=[],allowed_indices=allowed)
    def check(name):
        if not isinstance(name,(str,bytes,os.PathLike)):return
        p=Path(os.fsdecode(name)).resolve();s=str(p)
        if any(t in s.lower() for t in ('mesh_oracle','gt_crease','/meshes/','/mesh/','/2dgs_','/dd3')) or p.suffix in ('.obj','.off','.stl'):raise RuntimeError('forbidden input '+s)
        if p.suffix=='.ply' and s!=gs:raise RuntimeError('unapproved geometry '+s)
        if '/data/full/' in s and p.suffix in ('.png','.jpg') and s not in approved:raise RuntimeError('non-TRAIN image '+s)
        if p.suffix in ('.npz','.npy') and not p.is_relative_to(OUT):raise RuntimeError('unapproved cache '+s)
        if '/cglib/' in s or p.is_relative_to(OUT):
            if s not in access['data_reads']:access['data_reads'].append(s)
    def audit(event,args):
        if event=='open' and not (isinstance(args[1],str) and any(c in args[1] for c in 'wax')):check(args[0])
    sys.addaudithook(audit);old=cv2.imread
    def imread(p,*a,**k):
        check(p)
        if '/data/full/' in str(p) and str(p) not in access['rgb_reads']:access['rgb_reads'].append(str(p))
        return old(str(p),*a,**k)
    cv2.imread=imread;return access


def heat(x,mask=None):
    mask=np.isfinite(x) if mask is None else mask&np.isfinite(x)
    hi=np.percentile(x[mask],99) if mask.any() else 1.
    val=np.clip(np.nan_to_num(x,nan=0,posinf=0)/max(float(hi),1e-12),0,1)
    return cv2.applyColorMap((255*val).astype('uint8'),cv2.COLORMAP_INFERNO)


def smoke(m,scene,cams,photos,dest,cheap):
    g,keep=geom(scene);cam=scaled(cams[m['train_indices'][0]],128);t=time.perf_counter()
    a=rs.numpy_state(rs.render_state(g,keep,cam));b=rs.numpy_state(rs.render_state(g,keep,cam))
    legacy=render.render_gbuffer(g,keep,cam,with_albedo=True)
    covered=a['alpha']>.5;d=legacy['depth'].cpu().numpy()
    official,info=stock_rgb(dict(gs=m['inputs'][scene]['gs'],renderer=m['renderer']))
    rgb=(official(cam)[:,:,::-1]*255).astype('uint8')
    assert np.isfinite(rgb).all() and a['n_frag']>0
    assert np.all(np.isin(a['topk_id'][a['topk_id']>=0],np.flatnonzero(keep)))
    record=dict(provenance=provenance(),n_frag=a['n_frag'],covered_pixels=int(covered.sum()),
        repeat_id_equal=bool(np.array_equal(a['topk_id'],b['topk_id'])),repeat_weight_max_difference=float(abs(a['topk_w']-b['topk_w']).max()),
        legacy_depth_median_abs_difference=float(np.median(abs(a['depth'][covered]-d[covered]))),
        official_rgb=info,seconds=time.perf_counter()-t)
    cv2.imwrite(str(dest/'smoke.png'),np.hstack([label(rgb,'Official RGB'),label((a['albedo'][:,:,::-1]*255).astype('uint8'),'SH0 disc'),label(heat(a['entropy']),'entropy')]))
    dump(dest/'smoke.json',record);print(record,flush=True)


def baseline(m,scene,cams,photos,dest,cheap):
    t=time.perf_counter();sys.path.insert(0,str(ROOT/'scripts/explore/syn'))
    from m1a_seeds import extract_seeds
    p,score,selected,X=extract_seeds(scene,'overall',keep_f=m['candidate_recipe']['seed_fraction'],train_indices=m['train_indices'])
    g,keep=geom(scene);L=linelet.init_linelets(p,X,g['scale'][keep])
    arrays(dest/'baseline_initial.npz',**L)
    dump(dest/'baseline.json',dict(provenance=provenance(),seeds=len(p),seed_indices=m['train_indices'],seconds=time.perf_counter()-t,
        initial_sha256=sha(dest/'baseline_initial.npz'),legacy_cache_used=False))
    print('baseline seeds',len(p),flush=True)


def step1(m,scene,cams,photos,dest,cheap):
    t=time.perf_counter();g,keep=geom(scene);official,info=stock_rgb(dict(gs=m['inputs'][scene]['gs'],renderer=m['renderer']))
    folder=dest/'step1';folder.mkdir(exist_ok=True);stats=[]
    for view in indices(m,cheap):
        cam=scaled(cams[view],m['resolution']);st=rs.numpy_state(rs.render_state(g,keep,cam,K=m['state']['k']))
        fields=rs.channel_fields(st,m['fields']);arrays(folder/f'state_{view:03d}.npz',**st)
        arrays(folder/f'fields_{view:03d}.npz',**{f'{name}_{k}':v for name,a in fields.items() for k,v in a.items()})
        cov=st['alpha']>=.5;sil=(cv2.dilate(cov.astype('uint8'),np.ones((5,5),np.uint8))-cv2.erode(cov.astype('uint8'),np.ones((5,5),np.uint8)))>0
        names=list(fields);counts={};overlap=[]
        for name,f in fields.items():
            mask=f['mask'];length=0.
            for dy,dx,w in [(0,1,1),(1,0,1),(1,1,2**.5),(1,-1,2**.5)]:
                if dx==-1:length+=w*np.sum(mask[:-1,1:]&mask[1:,:-1])
                else:length+=w*np.sum(mask[:mask.shape[0]-dy or None,:mask.shape[1]-dx or None]&mask[dy:,dx:])
            counts[name]=dict(mask_pixels=int(mask.sum()),nms_pixels=int(f['nms'].sum()),neighbor_graph_length_px=float(length),silhouette_fraction=float((mask&sil).sum()/max(mask.sum(),1)))
            overlap.append([float(np.sum(mask&fields[b]['mask'])/max(np.sum(mask|fields[b]['mask']),1)) for b in names])
        rgb=(official(cam)[:,:,::-1]*255).astype('uint8');tiles=[label(rgb,f'Official RGB TRAIN{view}')]
        for name in ['topk8','topk4','rgb','entropy','margin','variance','depth','normal','alpha','dispersion']:
            resp=heat(fields[name]['response'],st['coverage']);mask=np.full_like(resp,255);mask[fields[name]['mask']]=0
            tiles.append(label(resp,name+' response'));tiles.append(label(mask,name+' NMS / capped'))
        while len(tiles)%3:tiles.append(np.full_like(tiles[0],255))
        cv2.imwrite(str(folder/f'channels_{view:03d}.png'),np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]))
        stats.append(dict(view=view,n_frag=int(st['n_frag']),covered=int(cov.sum()),channels=counts,overlap_names=names,jaccard_matrix=overlap,
            k4_k8_jaccard=float(np.sum(fields['topk4']['mask']&fields['topk8']['mask'])/max(np.sum(fields['topk4']['mask']|fields['topk8']['mask']),1)),
            mean_topk_captured_mass=float(st['topk_mass'][cov].mean())))
        print('step1',scene,view,{k:v['mask_pixels'] for k,v in counts.items()},flush=True);torch.cuda.empty_cache()
    dump(dest/'step1.json',dict(provenance=provenance(),views=stats,official_rgb=info,seconds=time.perf_counter()-t))


def step2(m,scene,cams,photos,dest,cheap):
    if not (dest/'step1.json').exists():raise RuntimeError('Step1 required')
    t=time.perf_counter();g,keep=geom(scene);nn=cKDTree(g['mu'][keep]).query(g['mu'][keep],k=2)[0][:,1]
    spacing=float(np.median(nn[nn>1e-10]));folder=dest/'step2';folder.mkdir(exist_ok=True)
    allparts={'real':[],'shifted':[]};reports=[];names=m['fields']['arm_channels']['D'];file_hashes={}
    for v in indices(m,cheap):
        sp=dest/f'step1/state_{v:03d}.npz';fp=dest/f'step1/fields_{v:03d}.npz';file_hashes[str(v)]=dict(state=sha(sp),fields=sha(fp))
        state=dict(np.load(sp));fields=dict(np.load(fp));cam=scaled(cams[v],m['resolution'])
        base=(state['albedo'][:,:,::-1]*255).astype('uint8');base[~state['coverage']]=255
        evidence_im=base.copy();reproject=base.copy();errimage=np.zeros((cam.H,cam.W),np.float32)
        for mode in allparts:
            for source,name in enumerate(names):
                response=fields[name+'_response'];tangent=fields[name+'_tangent'];mask=fields[name+'_mask']
                if mode=='shifted':
                    dx,dy=m['null']['shift'];response=np.roll(response,(dy,dx),(0,1));tangent=np.roll(tangent,(dy,dx),(0,1))
                    eligible=np.roll(fields[name+'_nms'],(dy,dx),(0,1))&(state['alpha']>=.5)
                    mask=rs.exact_n(response,eligible,int(mask.sum()))
                y,x=np.nonzero(mask);pixels=np.c_[x,y].astype(float)
                r=anchor.anchor_samples(g,cam,pixels,tangent[y,x],state['topk_id'][y,x],state['topk_w'][y,x],state['depth_median'][y,x],m['anchor'],spacing)
                parts=dict(view=np.full(len(x),v),source=np.full(len(x),source),pixel=pixels,tangent=tangent[y,x],
                    strength=np.minimum(response[y,x]/m['fields']['min_response'][name],10.),
                    median_depth=state['depth_median'][y,x],original_ids=state['topk_id'][y,x],original_weights=state['topk_w'][y,x],**r)
                allparts[mode].append(parts)
                good=r['valid'];reasons={key:int(np.sum(r['reason']==key)) for key in np.unique(r['reason'])}
                reports.append(dict(view=v,mode=mode,channel=name,input_samples=len(x),accepted=int(good.sum()),reasons=reasons,
                    reprojection_median=float(np.median(r['reprojection_error'])) if len(x) else None,
                    accepted_reprojection_median=float(np.median(r['reprojection_error'][good])) if good.any() else None,
                    depth_relative_median=float(np.median(r['depth_relative_error'][good])) if good.any() else None,
                    backprojection_roundtrip_median=float(np.median(r['backprojection_error'])) if len(x) else None,
                    id_support_histogram={str(i):int(np.sum(((r['ids']>=0)&(r['weights']>0)).sum(1)[good]==i)) for i in range(1,9)}))
                if mode=='real':
                    evidence_im[y,x]=(0,0,220);errimage[y,x]=np.maximum(errimage[y,x],r['reprojection_error'])
                    xy=np.round(r['reprojection'][good]).astype(int)
                    xy=xy[(xy[:,0]>=0)&(xy[:,0]<cam.W)&(xy[:,1]>=0)&(xy[:,1]<cam.H)]
                    reproject[xy[:,1],xy[:,0]]=(0,170,0)
        cv2.imwrite(str(folder/f'anchor_{v:03d}.png'),np.hstack([label(evidence_im,f'TRAIN {v}: evidence pixels'),label(reproject,'ID-weighted centers reprojected'),label(heat(errimage),'raw reprojection error')]))
        print('step2',scene,v,flush=True)
    for mode,parts in allparts.items():arrays(folder/f'{mode}_observations.npz',**anchor.merge_observations(parts))
    dump(dest/'step2.json',dict(provenance=provenance(),spacing=spacing,views=reports,step1_inputs_sha256=file_hashes,
        arrays_sha256={k:sha(folder/f'{k}_observations.npz') for k in allparts},seconds=time.perf_counter()-t))


def step3(m,scene,cams,photos,dest,cheap):
    t=time.perf_counter();prior=json.loads((dest/'step2.json').read_text());g,keep=geom(scene);folder=dest/'step3';folder.mkdir(exist_ok=True)
    data={}
    for name in ['real','shifted']:
        p=dest/f'step2/{name}_observations.npz'
        if sha(p)!=prior['arrays_sha256'][name]:raise RuntimeError('observation checksum changed')
        z=dict(np.load(p));data[name]=anchor.subset(z,z['valid'])
    channel_names=m['fields']['arm_channels']['D'];allclusters={};reports={};matches={}
    for arm in ['B','C','D']:
        codes=[channel_names.index(n) for n in m['fields']['arm_channels'][arm]]
        obs=anchor.subset(data['real'],np.isin(data['real']['source'],codes))
        shifted=anchor.subset(data['shifted'],np.isin(data['shifted']['source'],codes))
        clusters,stats=fusion.group(obs,g,keep,cams,prior['spacing'],m['fusion']);allclusters[arm]=clusters;reports[arm]=stats
        real,n2=fusion.match_counts(obs,shifted,m['seed']);n1=fusion.shuffled_ids(real,len(g['mu']),m['seed'])
        for tag,o in [('real',real),('N1',n1),('N2',n2)]:
            cs,st=fusion.group(o,g,keep,cams,prior['spacing'],m['fusion']);matches[arm+'_'+tag]=st
            dump(folder/f'matched_{arm}_{tag}.json',dict(clusters=cs,statistics=st))
            if arm=='D' and tag!='real':allclusters[tag]=cs;reports[tag]=st
        print('step3',scene,arm,'full',stats['accepted'],'matched real/N1/N2',*[matches[arm+'_'+k]['accepted'] for k in ['real','N1','N2']],flush=True)
    for name,clusters in allclusters.items():
        dump(folder/f'clusters_{name}.json',dict(clusters=clusters,statistics=reports[name]))
        arrays(folder/f'linelets_{name}.npz',**fusion.linelets(clusters))
    # Existing TRAIN cameras only; single observations and every accepted cluster.
    panels=[]
    for v in m['audit_indices']:
        if v not in indices(m,cheap):continue
        cam=scaled(cams[v],m['resolution']);state=dict(np.load(dest/f'step1/state_{v:03d}.npz'))
        depth=torch.from_numpy(state['depth']);obs=data['real'];own=obs['view']==v
        uv,_=common.project(obs['anchor'][own],cam);im=np.full((400,400,3),255,np.uint8)
        for x,y in np.round(uv).astype(int):
            if 0<=x<400 and 0<=y<400:im[y,x]=0
        tiles=[label(im,f'TRAIN{v} single-view anchors')]
        for name in ['B','C','D','N1','N2']:
            L=fusion.linelets(allclusters[name]);pp=[np.stack([p-l*t,p+l*t]) for p,t,l in zip(L['p'],L['t'],L['l'])]
            proj=draw.project_paths(pp,cam,depth) if pp else []
            tiles.append(label(draw.draw_paths(proj,np.ones(len(pp),bool),(400,400)),f'{name} persistent clusters'))
        panels.append(np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])]))
    cv2.imwrite(str(folder/'aggregation_train.png'),np.vstack(panels))
    diagnosis={}
    for arm in ['B','C','D']:
        a=matches[arm+'_real']['accepted'];null=max(matches[arm+'_N1']['accepted'],matches[arm+'_N2']['accepted'])
        diagnosis[arm]=dict(matched_real_clusters=a,stronger_null_clusters=null,ratio_to_stronger_null=a/max(null,1),
            persistence_effect_pass=bool(a) and a>=m['null']['real_vs_null_persistence_ratio']*max(null,1),visual_semantic_value='not established by counts')
    dump(dest/'step3.json',dict(provenance=provenance(),arms=reports,matched=matches,null_comparison=diagnosis,
        input_sha256=sha(dest/'step2.json'),seconds=time.perf_counter()-t))


ARMS=['A','B','C','D','N1','N2']


def merged_pool(base,extra):
    """Preserve all original positions, tangents and lengths; rebuild only kNN."""
    p=np.vstack([base['p0'],extra['p']]);t=np.vstack([base['t'],extra['t']]);l=np.r_[base['l'],extra['l']]
    _,knn=cKDTree(p).query(p,k=min(9,len(p)))
    return dict(p0=p,p=p.copy(),t=t,l=l,knn=knn[:,1:].astype(int))


def as_segments(L):
    return [p+np.linspace(-l,l,7)[:,None]*t for p,t,l in zip(L['p'],L['t'],L['l'])]


def make_field(m,scene,cams,photos,dest,views):
    g,keep=geom(scene);cache=dest/'train_cache';cfg=m['downstream']
    dt=dt_pull.build_dt_cache(scene,photos,views,cfg_name=cfg['edge'],force=True,cache_dir=str(cache))
    depth,fg=dt_pull.build_geom_cache(scene,g,keep,cams,views,force=True,cache_dir=str(cache))
    return dt_pull.PullField(cams,views,dt,depth,fg)


def step4_smoke(m,scene,cams,photos,dest,cheap):
    t=time.perf_counter();folder=dest/'step4_smoke';folder.mkdir(exist_ok=True)
    base=dict(np.load(dest/'baseline_initial.npz'));base={k:v[:512] for k,v in base.items()}
    extra=dict(np.load(dest/'step3/linelets_D.npz'));extra={k:v[:128] for k,v in extra.items()}
    L=merged_pool(base,extra);field=make_field(m,scene,cams,photos,folder,m['train_indices'][:2])
    result=dt_pull.pull(field,L,steps=5,lr=m['downstream']['pull_lr'],delta_max=m['downstream']['delta_max'])
    assert all(np.isfinite(result[k]).all() for k in ['p','t','l','resid'])
    dump(dest/'step4_smoke.json',dict(provenance=provenance(),linelets=len(L['p']),steps=5,finite=True,seconds=time.perf_counter()-t))


def step4(m,scene,cams,photos,dest,cheap):
    if cheap:raise RuntimeError('cheap transfer stops at initial linelets; no downstream fit')
    if not json.loads((dest/'step4_smoke.json').read_text())['finite']:raise RuntimeError('smoke required')
    t=time.perf_counter();cfg=m['downstream'];folder=dest/'step4';folder.mkdir(exist_ok=True)
    basepath=dest/'baseline_initial.npz';meta=json.loads((dest/'baseline.json').read_text())
    if sha(basepath)!=meta['initial_sha256'] or meta['seed_indices']!=m['train_indices'] or meta['legacy_cache_used']:raise RuntimeError('baseline provenance')
    base=dict(np.load(basepath));pools={};inputs={};newcounts={}
    for arm in ARMS:
        p=dest/f'step3/linelets_{arm}.npz'
        extra=dict(np.load(p)) if arm!='A' else fusion.linelets([])
        pools[arm]=merged_pool(base,extra);newcounts[arm]=len(extra['p'])
        inputs[arm]=sha(p) if arm!='A' else sha(basepath)
        arrays(folder/f'raw_{arm}.npz',**pools[arm])
    # RAW coverage is examined before any pull/prune, at predeclared TRAIN views.
    for v in m['audit_indices']:
        cam=scaled(cams[v],m['resolution']);state=dict(np.load(dest/f'step1/state_{v:03d}.npz'));depth=torch.from_numpy(state['depth'])
        tiles=[];added=[]
        for arm in ARMS:
            segments=as_segments(pools[arm]);projected=draw.project_paths(segments,cam,depth)
            tiles.append(label(draw.draw_paths(projected,np.ones(len(segments),bool),(400,400)),f'{arm} raw TRAIN{v}'))
            select=np.arange(len(segments))>=len(base['p0'])
            added.append(label(draw.draw_paths(projected,select,(400,400)),f'{arm} newly generated only'))
        cv2.imwrite(str(folder/f'raw_{v:03d}.png'),np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])]))
        cv2.imwrite(str(folder/f'new_only_{v:03d}.png'),np.vstack([np.hstack(added[:3]),np.hstack(added[3:])]))
    field=make_field(m,scene,cams,photos,dest,m['train_indices']);reports={}
    for arm in ARMS:
        a=time.perf_counter();L=pools[arm]
        result=dt_pull.pull(field,L,steps=cfg['pull_steps'],lr=cfg['pull_lr'],delta_max=cfg['delta_max'])
        good,st=linelet_prune.consensus_prune(result['resid'],result['vis'],**cfg['prune'])
        chains,nms=strokes.chain_linelets_3d(result['p'][good],result['t'][good],result['l'][good],conf=st['inlier_ratio'][good],**cfg['chain'])
        paths=strokes.chain_vertices(chains,result['p'][good][nms]);origin=np.flatnonzero(good)[nms]
        path_sources=[origin[c].tolist() for c in chains];used=np.unique(np.concatenate([origin[c] for c in chains])) if chains else np.array([],int)
        arrays(folder/f'pulled_{arm}.npz',**result,good=good);save_paths(folder/f'paths_{arm}.npz',paths)
        reports[arm]=dict(raw_linelets=len(L['p']),new_linelets=newcounts[arm],pruned_linelets=int(good.sum()),
            new_after_prune=int(good[len(base['p0']):].sum()),after_nms=int(nms.sum()),final_chains=len(paths),
            new_in_chains=int(np.sum(used>=len(base['p0']))),chains_with_new=sum(any(x>=len(base['p0']) for x in c) for c in path_sources),
            path_source_indices=path_sources,path_sha256=sha(folder/f'paths_{arm}.npz'),
            raw_sha256=sha(folder/f'raw_{arm}.npz'),seconds=time.perf_counter()-a)
        dump(folder/f'arm_{arm}.json',reports[arm]);print('step4',arm,{k:v for k,v in reports[arm].items() if k!='path_source_indices'},flush=True)
        if reports[arm]['seconds']>m['limits']['each_arm_pull_seconds']:raise RuntimeError('per-arm time budget exceeded')
        torch.cuda.empty_cache()
    dump(dest/'step4.json',dict(provenance=provenance(),input_sha256=inputs,arms=reports,seconds=time.perf_counter()-t,
        warning='Added candidates also change common kNN smoothness/NMS/chaining; A paths need not remain identical within augmented arms.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['smoke','baseline','step1','step2','step3','step4_smoke','step4'])
    parser.add_argument('--scene',default='lego',choices=['lego','chair']);parser.add_argument('--cheap',action='store_true');a=parser.parse_args()
    if git('branch','--show-current')!='raster-state-candidates':raise RuntimeError('wrong branch')
    m=json.loads((OUT/'MANIFEST.json').read_text());dest=stage_dir(a.scene,a.cheap);dest.mkdir(parents=True,exist_ok=True)
    for record in m['inputs'][a.scene].values():
        if sha(record['path'])!=record['sha256']:raise RuntimeError('source changed')
    assert set(m['train_indices'])<=set(view_split.TRAIN)
    assert not set(m['train_indices'])&set(m['dev_validation_indices'])
    np.random.seed(m['seed']);torch.manual_seed(m['seed']);torch.set_num_threads(4);cv2.setNumThreads(1)
    cams,photos=common.load_cameras(a.scene);accessfile=dest/f'access_{a.stage}.json'
    if accessfile.exists():raise FileExistsError(accessfile)
    access=install_guard(m,a.scene,m['train_indices']);t=time.perf_counter()
    try:globals()[a.stage](m,a.scene,cams,photos,dest,a.cheap)
    except Exception as e:access['failure']=repr(e);raise
    finally:access['seconds']=time.perf_counter()-t;dump(accessfile,access)

if __name__=='__main__':main()
