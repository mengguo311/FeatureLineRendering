"""Execute frozen original-Gaussian path controls, serial CPU, two real scenes."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,time
from stage_cache import cached_opacity, CheckpointPause, restored_view
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
import base_model as base
from geometry import mesh_data
from link_renderer import Renderer,validate_trace
from membership import accumulate,resolve,save_binding,load_binding,evaluated_tint_copy
from path_control import aggregate_path,resolve_path,opacity_copy,match_nonlinear,path_mask
from run_unit import samples,path_support,delta_budget,metrics,arrays_hash,png,panel
from render import render as render_hatches

def read_npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def load_protocol(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text())
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for name,h in p['source_hashes'].items():assert sha(Path(__file__).parent/name)==h,name
    return p

def load_scene(p,scene):
    s=p['scenes'][scene];asset=Path(s['asset'])
    for name,h in s['asset_hashes'].items():assert sha(asset/name)==h,name
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);n=len(a['means'])
    assert n==s['source_count'];a['source_index']=np.arange(n,dtype=np.int64)
    mz=read_npz(asset/'mesh.npz');mesh=mesh_data(mz['vertices'],mz['faces'],mz['face_regions'])
    meta=json.loads((asset/'asset.json').read_text())
    strokes={int(k):read_npz(asset/f'region_{k}.npz') for k in meta['regions']}
    ix=np.asarray(s['selected_segment_indices']);paths={k:v[ix] for k,v in strokes[4].items()}
    np.testing.assert_allclose(np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),paths['points'],rtol=0,atol=1e-9)
    return s,a,mesh,meta,strokes,paths

def capture(r,a,mesh,paths,c,p,s):
    xy,sw,grid,path,pz,pface,regions=samples(mesh,paths,c,p)
    # Restore original saved-segment identity after bounded selection.
    path['segment_index']=np.asarray(s['selected_segment_indices'])[path['segment_index']]
    frame,trace=r.render(a,c,xy,max_events=p['sampling']['max_events_per_view'])
    check=validate_trace(a,c,xy,frame,trace)
    xx,yy=xy.T;sample_z=pz[yy,xx];m=p['membership']
    valid=np.isfinite(sample_z)&(frame['alpha'][yy,xx]>=m['sample_alpha_min'])
    valid &= np.abs(sample_z-frame['median_camera_z'][yy,xx])<=m['sample_proxy_source_z_tolerance']
    ps=path_support(path,trace,sample_z,valid,p)
    tr=dict(trace,xy=xy,grid_sample_index=grid,sampling_weight=sw,proxy_depth=sample_z,
            proxy_region=regions[yy,xx],sample_eligible=valid,proxy_face=pface[yy,xx])
    pm=path_mask(pz,regions,paths,c)
    return dict(camera=c,frame=frame,trace=tr,path=ps,proxy_depth=pz,regions=regions,path_mask=pm,check=check)

def save_view(folder,d):
    folder.mkdir()
    np.savez_compressed(folder/'trace.npz',**d['trace'])
    np.savez_compressed(folder/'path_support.npz',**d['path'])
    np.savez_compressed(folder/'baseline.npz',**d['frame'],proxy_depth=d['proxy_depth'],proxy_regions=d['regions'],path_mask=d['path_mask'])
    png(folder/'source.png',d['frame']['rgb'])

def path_stats(ps):
    visible=ps['proxy_visible']
    return dict(attempted=len(ps['state']),supported=int((~ps['unknown']).sum()),unknown=int(ps['unknown'].sum()),
        proxy_visible=int(visible.sum()),retained_mass=float(ps['retained_mass'].sum()),rejected_mass=float(ps['rejected_mass'].sum()),
        visible_retained_fraction=float(ps['retained_mass'][visible].sum()/max(ps['total_mass'][visible].sum(),1e-30)),
        states=dict(zip(*np.unique(ps['state'],return_counts=True))))

def run(unit,scene):
    unit=output_guard(unit);p=load_protocol(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene)
    out=unit/'results'/scene;out.mkdir(parents=True,exist_ok=True)
    r=Renderer(unit/'build');n=len(a['means']);start=time.monotonic();orig_hash=arrays_hash(a)
    m=p['membership'];build=[];scores=[];totals=[];accepted=[];checks={};pathchecks={};depthchecks={}
    js(out/'MODEL_IMPORT.json',dict(audit=a['audit'],source=s['source'],array_hashes=orig_hash,
        target_faces=int((mesh['regions']==4).sum()),sampled_segments=len(paths['points']),
        sampled_stroke_ids=np.unique(paths['stroke_id']),original_source_index='PLY row i'))
    for c in [c for c in s['cameras'] if c['split']=='build']:
        d=restored_view(out/c['view'],c) if (out/c['view']/'baseline.npz').exists() else capture(r,a,mesh,paths,c,p,s)
        off,_=r.render(a,c);ref=r.baseline(a,c)
        equality={k:bool(np.array_equal(d['frame'][k],off[k]) and np.array_equal(d['frame'][k],ref[k])) for k in ref}
        assert all(equality.values()),equality
        d['check']['trace_off_and_original_exact']=equality
        t=d['trace'];score,_,dc=accumulate(n,t,t['proxy_region'],t['proxy_depth'],t['sample_eligible'],t['sampling_weight'],m['contributor_proxy_z_tolerance'])
        total,accept=aggregate_path(n,d['path']);totals.append(total);accepted.append(accept);scores.append(score)
        checks[c['view']]=d['check'];depthchecks[c['view']]=dc;pathchecks[c['view']]=path_stats(d['path'])

        if not (out/c['view']).exists():save_view(out/c['view'],d)
        build.append(d)
        print(scene,'BUILD',c['view'],pathchecks[c['view']],flush=True)
    pv=np.stack(scores);binding=resolve(pv,m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    save_binding(out/'SOURCE_BINDING.npz',dict(binding,per_view_score=pv),dict(source_sha256=s['source']['sha256'],source_count=n,
        protocol_sha256=sha(unit/'PROTOCOL.json'),asset_hashes=s['asset_hashes'],build_cameras=[d['camera'] for d in build],
        region_names=meta['regions'],method='all accepted original-ID alpha*T, fixed proxy/source depth and UNKNOWN gates',confidence_scope=p['scientific_scope']))
    loaded,_=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    for k,v in binding.items():np.testing.assert_array_equal(v,loaded[k])
    same_chair=None
    if scene=='chair':
        prior,_=load_binding(Path(p['prior']['unit'])/'results/SOURCE_BINDING.npz',s['source']['sha256'],n)
        same_chair=all(np.array_equal(v,prior[k]) for k,v in binding.items());assert same_chair
    pb=resolve_path(np.stack(totals),np.stack(accepted),binding)
    np.savez_compressed(out/'PATH_BINDING.npz',**pb,source_sha256=np.array(s['source']['sha256']),
        protocol_sha256=np.array(sha(unit/'PROTOCOL.json')),selected_segment_indices=np.asarray(s['selected_segment_indices']),
        selected_stroke_ids=np.asarray(s['selected_stroke_ids']))
    proposed=pb['strength'];selected=np.flatnonzero(proposed>0)
    distance,nearest=cKDTree(paths['points'].mean(1)).query(a['means'],workers=1)
    nearest_strength=np.zeros(n);nearest_strength[np.argsort(distance,kind='stable')[:len(selected)]]=1.
    shuffled=proposed.copy();rng=np.random.default_rng(1729)
    observed=np.flatnonzero(binding['exposure']>0);ordered=observed[np.argsort(binding['exposure'][observed],kind='stable')]
    for group in np.array_split(ordered,10):shuffled[group]=proposed[rng.permutation(group)]
    candidates=dict(path_linked=proposed,nearest_path=nearest_strength,shuffled=shuffled)
    tint=p['diagnostic']['tint'];tbudgets={}
    for arm,st in candidates.items():
        tbudgets[arm]=sum(delta_budget(a,d['camera'],d['trace'],d['trace']['grid_sample_index'],st,tint,len(d['trace']['xy'])) for d in build)
    common=.85*min(tbudgets.values());tscales={k:common/v if v>0 else 0. for k,v in tbudgets.items()}
    tint_strength={k:v*tscales[k] for k,v in candidates.items()}
    for d in build:
        d['colors']=dict({k:v for k,v in a.items() if k!='SH'},colors=base.source_colors(a,d['camera']))
    def opacity_effect(arm,scale):
        effect=0.
        for d in build:
            changed=opacity_copy(d['colors'],candidates[arm],scale)
            f,_=r.render(changed,d['camera'])
            xy=d['trace']['xy'][d['trace']['grid_sample_index']];xx,yy=xy.T
            effect+=float(np.abs(f['rgb'][yy,xx]-d['frame']['rgb'][yy,xx]).sum(dtype=np.float64))
        return effect
    oscales,oreceipt=match_nonlinear(list(candidates),cached_opacity(out/'OPACITY_EFFECT_CACHE.json',opacity_effect,12))
    # Save a failed match honestly; don't replace thresholds or use EVAL fitting.
    js(out/'BUDGET_MATCH.json',dict(tint=dict(full_strength=tbudgets,target=common,scales=tscales,valid=common>0),opacity=oreceipt))
    opacity_strength={k:v*oscales[k] for k,v in candidates.items()}
    region_strength=np.where(binding['region_id']==4,binding['membership'][:,4],0.)*.85
    selections=dict(source_index=np.arange(n),source_sha256=np.array(s['source']['sha256']),tint=np.asarray(tint),
                    nearest_path_sample=nearest,nearest_path_distance=distance,region_strength=region_strength)
    for k,v in candidates.items():selections['unscaled_'+k]=v
    for k,v in tint_strength.items():selections['tint_'+k]=v
    for k,v in opacity_strength.items():selections['opacity_'+k]=v
    np.savez_compressed(out/'EDIT_SELECTION.npz',**selections)
    with (out/'SELECTED_SOURCE_IDS.csv').open('w') as f:
        f.write('source_index,path_accepted_mass,path_fraction,path_distinct_views,q_region4,tint_strength,opacity_attenuation\n')
        for i in selected:f.write(f'{i},{pb["accepted"][i]:.12g},{pb["fraction"][i]:.12g},{pb["distinct_views"][i]},{binding["membership"][i,4]:.12g},{tint_strength["path_linked"][i]:.12g},{opacity_strength["path_linked"][i]:.12g}\n')
    print(scene,'selected',len(selected),'opacity match',oreceipt['valid'],'time',time.monotonic()-start,flush=True)
    evaluations=[];panels=[]
    for ci,c in enumerate([c for c in s['cameras'] if c['split']=='evaluation']):
        folder=out/c['view']
        d=restored_view(folder,c) if (folder/'baseline.npz').exists() else capture(r,a,mesh,paths,c,p,s)
        if not folder.exists():save_view(folder,d)
        checks[c['view']]=d['check'];pathchecks[c['view']]=path_stats(d['path'])
        f=d['frame'];xy=d['trace']['xy'];regions=d['regions']
        full,ft=r.render(a,c,xy,strength=proposed)
        for k in f:np.testing.assert_array_equal(f[k],full[k] if k!='contribution' else np.zeros_like(f[k]))
        np.savez_compressed(folder/'full_T_contribution.npz',contribution=full['contribution'])
        intent=np.where(regions>0,1,0);intent[d['path_mask']]=4
        edits={};row=dict(camera=c,path_support=pathchecks[c['view']],arms={})
        for operation,strengths in [('tint',tint_strength),('opacity',opacity_strength)]:
            for arm,st in strengths.items():
                changed=evaluated_tint_copy(a,c,st,tint) if operation=='tint' else opacity_copy(a,st)
                key=operation+'_'+arm
                if (folder/(key+'.npz')).exists():
                    edited=read_npz(folder/(key+'.npz'))
                    trace=read_npz(folder/(key+'_trace.npz')) if operation=='opacity' else {}
                else:edited,trace=r.render(changed,c,xy if operation=='opacity' else None)
                edits[key]=edited['rgb']
                np.savez_compressed(folder/(key+'.npz'),**edited)
                png(folder/(key+'.png'),edited['rgb'])
                if operation=='opacity':
                    np.savez_compressed(folder/(key+'_trace.npz'),**dict(trace,xy=xy))
                    validate_trace(changed,c,xy,edited,trace)
                else:
                    np.testing.assert_array_equal(edited['alpha'],f['alpha'])
                    np.testing.assert_array_equal(edited['median_camera_z'],f['median_camera_z'])
                row['arms'][key]=dict(path_intent=metrics(f['rgb'],edited['rgb'],intent,full['contribution'],p),
                                     region_intent=metrics(f['rgb'],edited['rgb'],regions,full['contribution'],p),
                                     alpha_L1=float(np.abs(edited['alpha']-f['alpha']).sum()))
        region_edit,_=r.render(evaluated_tint_copy(a,c,region_strength,tint),c)
        np.savez_compressed(folder/'region_linked_tint.npz',**region_edit);png(folder/'region_linked_tint.png',region_edit['rgb'])
        row['region_linked']=metrics(f['rgb'],region_edit['rgb'],regions,full['contribution'],p)
        hatch=render_hatches(mesh,strokes,meta['styles'],c,2,meta.get('display'))
        png(folder/'hatches_context.png',hatch['image'])
        target=np.repeat(hatch['proxy'][:,:,None],3,2);target[regions==4]=[1.,.72,.72];target[d['path_mask']]=[.95,.1,.15]
        png(folder/'authored_path_intent.png',target)
        heat=(1-full['contribution'][:,:,None])*f['rgb']+full['contribution'][:,:,None]*np.asarray(tint)
        png(folder/'full_T_source_support.png',heat)
        panel(folder/'comparison.png',[f['rgb'],target,heat,edits['tint_path_linked'],edits['opacity_path_linked'],hatch['image']],
              ['Original GS / full SH3','Authored region + paths','Full-T original support','Path-linked source tint','Path-linked opacity edit','Saved 3D hatches'],
              scene+' '+c['view']+' | CPU mapping; original row IDs; not physical/native certification')
        for op in ('tint','opacity'):
            panel(folder/(op+'_controls.png'),[f['rgb']]+[edits[op+'_'+k] for k in candidates],
                  ['Original GS','Path-linked original IDs','Nearest-path / same count','Shuffled source IDs'],
                  'Actual BUILD RGB-L1 budgets matched per operation; EVAL effects remain independently measured')
        if ci==0:
            isolated,_=r.render(dict(a,opacity=a['opacity']*(proposed>0)),c)
            np.savez_compressed(folder/'selected_only_recomputed_T.npz',**isolated)
            png(folder/'selected_only_recomputed_T.png',isolated['rgb'])
        panels.append(folder/'comparison.png');evaluations.append(row)
        print(scene,'EVAL',c['view'],{k:dict(effect=v['path_intent']['target_interior']['L1_mean'],far=v['path_intent']['far_non_target_fraction']) for k,v in row['arms'].items()},flush=True)
    intact=arrays_hash(a)==orig_hash and sha(s['source']['original_ply'])==s['source']['sha256'];assert intact
    summary=dict(scene=scene,finished_utc=now(),seconds=time.monotonic()-start,source_count=n,
        source_binding_unknown=int(binding['unknown'].sum()),region4_supported=int((binding['region_id']==4).sum()),
        region_reasons=dict(zip(*np.unique(binding['reason'],return_counts=True))),
        path_selected_original_ids=len(selected),path_unknown_original_ids=int(pb['unknown'].sum()),
        path_reasons=dict(zip(*np.unique(pb['reason'],return_counts=True))),sampled_segments=len(paths['points']),
        sampled_stroke_ids=len(np.unique(paths['stroke_id'])),trace_checks=checks,path_checks=pathchecks,depth_checks=depthchecks,
        previous_chair_binding_exact=same_chair,source_arrays_and_PLY_unchanged=intact,
        tint_budget_valid=common>0,opacity_budget_valid=oreceipt['valid'],evaluation=evaluations,
        scientific_verdict=p['scientific_scope'])
    js(out/'SUMMARY.json',summary)
    ims=[Image.open(x).convert('RGB') for x in panels]
    contact=Image.new('RGB',(ims[0].width,sum(im.height for im in ims)),'white');offset=0
    for im in ims:contact.paste(im,(0,offset));offset+=im.height
    contact.save(out/'ALL_EVALUATION_VIEWS.png')
    print(json.dumps(dict(scene=scene,summary=str(out/'SUMMARY.json'),seconds=summary['seconds'],selected=len(selected))),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',type=Path,required=True);parser.add_argument('--scene',choices=['chair','lego'],required=True)
    args=parser.parse_args()
    try:run(args.unit,args.scene)
    except CheckpointPause:
        print(json.dumps(dict(checkpoint='budget cache saved; resume same command',scene=args.scene)),flush=True)
