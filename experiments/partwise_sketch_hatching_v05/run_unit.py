"""Chair authored region/path -> ORIGINAL source IDs -> actual CPU-GS control."""
import runtime
from runtime import js,sha,now,output_guard,json_default
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
from geometry import mesh_data,ray_surface,project
import base_model as base
from link_renderer import Renderer,validate_trace
from membership import accumulate,resolve,save_binding,load_binding,evaluated_tint_copy
from render import render as render_hatches

def png(path,x):
    Image.fromarray(np.uint8(np.clip(x,0,1)*255+.5)).save(path)

def panel(path,images,labels,footer=''):
    w=images[0].shape[1];h=images[0].shape[0]
    canvas=Image.new('RGB',(w*len(images),h+56),'white');draw=ImageDraw.Draw(canvas)
    for i,(im,label) in enumerate(zip(images,labels)):
        if im.ndim==2:im=np.repeat(im[:,:,None],3,2)
        canvas.paste(Image.fromarray(np.uint8(np.clip(im,0,1)*255+.5)),(i*w,24))
        draw.text((i*w+7,5),label,fill='black')
    draw.text((7,h+32),footer,fill='black');canvas.save(path)

def arrays_hash(a):
    import hashlib
    return {k:hashlib.sha256(np.ascontiguousarray(a[k]).tobytes()).hexdigest() for k in ('means','covariance','opacity','SH','precision')}

def samples(mesh,paths,c,p):
    z,face,region,_=ray_surface(mesh,c,1)
    stride=p['sampling']['grid_stride'];off=p['sampling']['grid_offset']
    y,x=np.mgrid[off:c['height']:stride,off:c['width']:stride]
    grid=np.column_stack([x.ravel(),y.ravel()])
    seg=np.unique(np.linspace(0,len(paths['points'])-1,min(p['sampling']['path_segments'],len(paths['points'])),dtype=int))
    xyz=paths['points'][seg].mean(1);bary=paths['bary'][seg].mean(1)
    uv,zz=project(xyz,c);xy=np.floor(uv+.5).astype(int)
    inside=(zz>.2)&(xy[:,0]>=0)&(xy[:,0]<c['width'])&(xy[:,1]>=0)&(xy[:,1]<c['height'])
    union=np.unique(np.concatenate([grid,xy[inside]]),axis=0)
    lookup={tuple(v):i for i,v in enumerate(union)}
    grid_sid=np.array([lookup[tuple(v)] for v in grid]);path_sid=np.full(len(seg),-1,np.int64)
    path_sid[inside]=[lookup[tuple(v)] for v in xy[inside]]
    weights=np.zeros(len(union));weights[grid_sid]=p['sampling']['grid_weight']
    visible=np.zeros(len(seg),bool)
    idx=np.flatnonzero(inside);xx,yy=xy[idx].T
    visible[idx]=(region[yy,xx]==p['region_id'])&np.isfinite(z[yy,xx])&(np.abs(z[yy,xx]-zz[idx])<=p['membership']['path_proxy_z_tolerance'])
    path=dict(segment_index=seg,stroke_id=paths['stroke_id'][seg],face=paths['face'][seg],bary=bary,
              world=xyz,projected_uv=uv,xy=xy,camera_z=zz,sample_index=path_sid,in_frame=inside,proxy_visible=visible,
              region_id=np.full(len(seg),p['region_id'],np.int32))
    return union,weights,grid_sid,path,z,face,region

def path_support(path,trace,proxy_z,sample_ok,p):
    order=np.argsort(trace['sample_index'],kind='stable');sorted_sid=trace['sample_index'][order]
    source=[];weights=[];depth=[];eligible=[];offset=[0];retained=[];total=[];state=[]
    for k,s in enumerate(path['sample_index']):
        if s<0:idx=np.empty(0,int)
        else:idx=order[np.searchsorted(sorted_sid,s,'left'):np.searchsorted(sorted_sid,s,'right')]
        w=trace['weight'][idx];d=trace['depth'][idx]
        good=np.zeros(len(idx),bool)
        if s>=0 and path['proxy_visible'][k] and sample_ok[s]:
            good=np.isfinite(d)&(np.abs(d-proxy_z[s])<=p['membership']['contributor_proxy_z_tolerance'])
        source.extend(trace['source_index'][idx]);weights.extend(w);depth.extend(d);eligible.extend(good)
        offset.append(len(source));retained.append(w[good].sum());total.append(w.sum())
        state.append('out_of_frame' if s<0 else 'proxy_occluded' if not path['proxy_visible'][k] else 'source_depth_unknown' if not sample_ok[s] else 'supported' if w[good].sum()>.01 else 'low_support')
    total=np.asarray(total);retained=np.asarray(retained)
    return dict(**path,offsets=np.asarray(offset),source_index=np.asarray(source,np.int64),weight=np.asarray(weights),
        contributor_depth=np.asarray(depth),eligible=np.asarray(eligible,bool),retained_mass=retained,total_mass=total,
        rejected_mass=total-retained,retained_fraction=np.divide(retained,total,out=np.zeros_like(total),where=total>0),
        state=np.asarray(state),unknown=np.asarray(state)!='supported')

def delta_budget(a,c,trace,grid_sid,strength,tint,ns):
    col=base.source_colors(a,c);ids=trace['source_index'];s=trace['sample_index']
    d=(np.asarray(tint)-col[ids])*trace['weight'][:,None]*strength[ids,None]
    out=np.zeros((ns,3));np.add.at(out,s,d)
    return float(np.abs(out[grid_sid]).sum())

def metrics(orig,edit,regions,contribution,p):
    d=np.abs(edit-orig).sum(2);dc=np.abs(np.clip(edit,0,1)-np.clip(orig,0,1)).sum(2)
    target=regions==p['region_id'];band=p['diagnostic']['aa_band_pixels']
    inner=ndimage.binary_erosion(target,iterations=band)
    near=ndimage.binary_dilation(target,iterations=band)
    boundary=near&~inner;other=(regions>0)&~near;bg=(regions==0)&~near
    out=dict(total_L1=float(d.sum()),clipped_total_L1=float(dc.sum()),changed_pixels=int((dc>1/255).sum()),
             target_pixels=int(target.sum()),target_contribution_mean=float(contribution[target].mean()) if target.any() else None)
    for name,m in [('target_interior',inner),('boundary',boundary),('far_other',other),('far_background',bg)]:
        out[name]=dict(pixels=int(m.sum()),L1_sum=float(d[m].sum()),L1_mean=float(d[m].mean()) if m.any() else None,
                       clipped_L1_mean=float(dc[m].mean()) if m.any() else None,changed_fraction=float((dc[m]>1/255).mean()) if m.any() else None)
    out['far_non_target_fraction']=float(d[other|bg].sum()/max(d.sum(),1e-30))
    gate=p['diagnostic']['locality_gate']
    mean=out['target_interior']['L1_mean']
    out['intent_locality_gate']=bool(mean is not None and mean>=gate['target_mean_L1_min'] and out['far_non_target_fraction']<=gate['far_non_target_fraction_max'])
    return out

def run(unit):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text());lock=json.loads((unit/'PROTOCOL_LOCK.json').read_text())
    assert sha(unit/'PROTOCOL.json')==lock['sha256']
    # The frozen source snapshot is runnable and all science source bytes are checked.
    for name,h in p['source_hashes'].items():assert sha(Path(__file__).parent/name)==h,name
    asset=Path(p['asset'])
    for name,h in p['asset_hashes'].items():assert sha(asset/name)==h,name
    out=unit/'results';out.mkdir(exist_ok=False)
    start=time.monotonic();r=Renderer(unit/'build');a=base.load_source(p['source']['original_ply'],p['source']['sha256'])
    n=len(a['means']);assert n==p['source_count'];a['source_index']=np.arange(n,dtype=np.int64)
    original_arrays=arrays_hash(a)
    with np.load(asset/'mesh.npz') as z:mesh=mesh_data(z['vertices'],z['faces'],z['face_regions'])
    strokes={}
    for rid in range(1,6):
        with np.load(asset/f'region_{rid}.npz') as z:strokes[rid]={k:z[k] for k in z.files}
    paths=strokes[p['region_id']];meta=json.loads((asset/'asset.json').read_text())
    recon=np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']])
    assert np.max(np.abs(recon-paths['points']))<1e-9
    js(out/'MODEL_IMPORT.json',dict(audit=a['audit'],source_sha256=sha(p['source']['original_ply']),array_hashes=original_arrays,
        source_index='original PLY row',proxy_faces=len(mesh['faces']),target_faces=int((mesh['regions']==4).sum()),
        target_segments=len(paths['points']),target_stroke_ids=len(np.unique(paths['stroke_id'])),loaded_utc=now()))
    # Historical same-camera CPU reference. Expected depth discrepancies stay visible.
    cc=p['calibration']['camera'];t=time.monotonic();cal=r.baseline(a,cc)
    assert sha(p['calibration']['cache'])==p['calibration']['cache_sha256']
    with np.load(p['calibration']['cache']) as cache:
        errs={k:dict(max_abs=float(np.max(np.abs(v-cache[k]))),mean_abs=float(np.mean(np.abs(v-cache[k])))) for k,v in cal.items()}
    js(out/'CALIBRATION.json',dict(errors=errs,scope=p['calibration']['scope'],native_per_ID='NOT_AVAILABLE',
        verdict='UNCERTIFIED_CPU_MAPPING',seconds=time.monotonic()-t))
    png(out/'historical_camera_current_source.png',cal['rgb']);del cal
    print('calibration',errs,flush=True)
    build_data=[];scores=[];trace_checks={};depth_checks={}
    for c in [x for x in p['cameras'] if x['split']=='build']:
        t=time.monotonic();folder=out/c['view'];folder.mkdir()
        xy,sw,grid,path,pz,pface,regions=samples(mesh,paths,c,p)
        f,tr=r.render(a,c,xy,max_events=p['sampling']['max_events_per_view'])
        off,_=r.render(a,c);ref=r.baseline(a,c)
        equality={k:bool(np.array_equal(f[k],ref[k]) and np.array_equal(f[k],off[k])) for k in ref}
        assert all(equality.values()),equality
        trace_checks[c['view']]=dict(validate_trace(a,c,xy,f,tr),exact_on_off_and_original=equality)
        xx,yy=xy.T;sample_z=pz[yy,xx];reg=regions[yy,xx]
        sample_ok=np.isfinite(sample_z)&(f['alpha'][yy,xx]>=p['membership']['sample_alpha_min'])
        sample_ok &= np.abs(sample_z-f['median_camera_z'][yy,xx])<=p['membership']['sample_proxy_source_z_tolerance']
        score,exp,diag=accumulate(n,tr,reg,sample_z,sample_ok,sw,p['membership']['contributor_proxy_z_tolerance'])
        scores.append(score);depth_checks[c['view']]=diag
        np.savez_compressed(folder/'trace.npz',**tr,xy=xy,grid_sample_index=grid,sampling_weight=sw,proxy_depth=sample_z,
            proxy_region=reg,sample_eligible=sample_ok,proxy_face=pface[yy,xx],camera_json=np.array(json.dumps(c)))
        ps=path_support(path,tr,sample_z,sample_ok,p);np.savez_compressed(folder/'path_support.npz',**ps)
        np.savez_compressed(folder/'frame.npz',**f,proxy_depth=pz,proxy_regions=regions)
        png(folder/'source.png',f['rgb'])
        build_data.append(dict(camera=c,trace=tr,xy=xy,grid=grid,frame=f,regions=regions,path=ps))
        print(c['view'],trace_checks[c['view']],diag,'paths',dict(zip(*np.unique(ps['state'],return_counts=True))),'seconds',time.monotonic()-t,flush=True)
    per_view=np.stack(scores);m=p['membership'];binding=resolve(per_view,m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    save_binding(out/'SOURCE_BINDING.npz',dict(binding,per_view_score=per_view),dict(source_sha256=p['source']['sha256'],source_count=n,
        protocol_sha256=lock['sha256'],asset_hashes=p['asset_hashes'],method='accepted alpha*T + proxy/source depth gates; 6-channel UNKNOWN/region evidence',
        build_cameras=[x['camera'] for x in build_data],region_names=meta['regions'],confidence_scope=p['scientific_scope']))
    loaded,_=load_binding(out/'SOURCE_BINDING.npz',p['source']['sha256'],n)
    assert all(np.array_equal(v,loaded[k]) for k,v in binding.items())
    proposed=np.where(binding['region_id']==4,binding['membership'][:,4],0.)
    # Simple spatial baseline: nearest proxy face centroid, no implicit surface claim.
    _,nearest=cKDTree(mesh['tri'].mean(1)).query(a['means'],workers=1)
    spatial=(mesh['regions'][nearest]==4).astype(float)
    shuffled=proposed.copy();rng=np.random.default_rng(1729)
    observed=np.flatnonzero(binding['exposure']>0);ordered=observed[np.argsort(binding['exposure'][observed],kind='stable')]
    for group in np.array_split(ordered,10):shuffled[group]=proposed[rng.permutation(group)]
    candidates=dict(linked=proposed,nearest_proxy=spatial,shuffled=shuffled)
    tint=p['diagnostic']['tint'];budgets={}
    for name,s in candidates.items():
        budgets[name]=sum(delta_budget(a,d['camera'],d['trace'],d['grid'],s,tint,len(d['xy'])) for d in build_data)
    common=.85*min(budgets.values());scales={name:common/b if b>0 else 0. for name,b in budgets.items()}
    strengths={name:s*scales[name] for name,s in candidates.items()}
    np.savez_compressed(out/'EDIT_SELECTION.npz',source_index=np.arange(n),**strengths,
        linked_unscaled=proposed,nearest_proxy_unscaled=spatial,shuffled_unscaled=shuffled,nearest_proxy_face=nearest,
        tint=np.asarray(tint),source_sha256=np.array(p['source']['sha256']))
    selected=np.flatnonzero(proposed>0)
    with (out/'SELECTED_SOURCE_IDS.csv').open('w') as f:
        f.write('source_index,q_region4,exposure,distinct_views,edit_strength\n')
        for i in selected:f.write(f'{i},{binding["membership"][i,4]:.12g},{binding["exposure"][i]:.12g},{binding["distinct_views"][i]},{strengths["linked"][i]:.12g}\n')
    js(out/'BUDGET_MATCH.json',dict(full_strength_build_sampled_L1=budgets,common_build_sampled_L1=common,scales=scales,
        selected_counts={k:int((v>0).sum()) for k,v in strengths.items()},method=p['diagnostic']['matching']))
    print('binding',dict(zip(*np.unique(binding['reason'],return_counts=True))),'selected',len(selected),'budgets',budgets,'scales',scales,flush=True)
    # Free raw build traces only after their persisted, validated budgets are used.
    del scores,per_view
    evaluation=[];all_panels=[]
    for ci,c in enumerate([x for x in p['cameras'] if x['split']=='evaluation']):
        t=time.monotonic();folder=out/c['view'];folder.mkdir()
        xy,sw,grid,path,pz,pface,regions=samples(mesh,paths,c,p)
        f,tr=r.render(a,c,xy,strength=proposed,max_events=p['sampling']['max_events_per_view'])
        trace_checks[c['view']]=validate_trace(a,c,xy,f,tr)
        xx,yy=xy.T;sample_z=pz[yy,xx]
        sample_ok=np.isfinite(sample_z)&(f['alpha'][yy,xx]>=m['sample_alpha_min'])&(np.abs(sample_z-f['median_camera_z'][yy,xx])<=m['sample_proxy_source_z_tolerance'])
        ps=path_support(path,tr,sample_z,sample_ok,p);np.savez_compressed(folder/'path_support.npz',**ps)
        np.savez_compressed(folder/'trace.npz',**tr,xy=xy,grid_sample_index=grid,proxy_depth=sample_z,proxy_region=regions[yy,xx],sample_eligible=sample_ok)
        np.savez_compressed(folder/'baseline.npz',**f,proxy_depth=pz,proxy_regions=regions)
        png(folder/'source.png',f['rgb']);png(folder/'full_T_contribution.png',f['contribution'])
        edits={};row=dict(camera=c,arms={})
        for name,s in strengths.items():
            changed=evaluated_tint_copy(a,c,s,tint);edit,_=r.render(changed,c)
            assert np.array_equal(edit['alpha'],f['alpha'])
            assert np.array_equal(edit['median_camera_z'],f['median_camera_z'])
            np.savez_compressed(folder/(name+'_edit.npz'),**edit)
            png(folder/(name+'_edit.png'),edit['rgb']);edits[name]=edit['rgb']
            row['arms'][name]=metrics(f['rgb'],edit['rgb'],regions,f['contribution'],p)
        hatch=render_hatches(mesh,strokes,meta['styles'],c,2,meta.get('display'))
        png(folder/'hatches_context.png',hatch['image'])
        target=np.repeat(hatch['proxy'][:,:,None],3,2);target[regions==4]=[.95,.2,.35]
        png(folder/'authored_target.png',target)
        # Full-T support is shown over the full original source object for context.
        heat=(1-f['contribution'][:,:,None])*f['rgb']+f['contribution'][:,:,None]*np.array([.02,.4,1.])
        panel(folder/'comparison.png',[f['rgb'],target,heat,edits['linked'],hatch['image']],
              ['Original GS / SH3','Authored proxy region 4','Full-T source support','Original GS linked tint','Saved 3D hatches'],
              c['view']+' | CPU mapping, not native-certified; support is not physical attachment')
        panel(folder/'controls.png',[f['rgb'],edits['linked'],edits['nearest_proxy'],edits['shuffled']],
              ['Original GS','Linked original IDs','Nearest-proxy control','Shuffled-ID control'],
              'Tint budgets matched on fixed BUILD pixel samples; evaluation effects reported separately')
        if ci==0:
            isolated=dict(a,opacity=a['opacity']*(proposed>0));sel,_=r.render(isolated,c)
            png(folder/'selected_only_recomputed_T.png',sel['rgb'])
            np.savez_compressed(folder/'selected_only_recomputed_T.npz',**sel)
        evaluation.append(row);all_panels.append(folder/'comparison.png')
        print('evaluation',c['view'],row['arms']['linked'],'seconds',time.monotonic()-t,flush=True)
    original_intact=original_arrays==arrays_hash(a) and sha(p['source']['original_ply'])==p['source']['sha256']
    assert original_intact
    summary=dict(finished_utc=now(),seconds=time.monotonic()-start,source_count=n,selected_original_ids=len(selected),
        supported_counts={str(k):int((binding['region_id']==k).sum()) for k in range(6)},
        reason_counts=dict(zip(*np.unique(binding['reason'],return_counts=True))),
        unknown_original_rows=int(binding['unknown'].sum()),observed_original_rows=int((binding['exposure']>0).sum()),
        trace_checks=trace_checks,depth_checks=depth_checks,budgets=dict(common=common,scales=scales),evaluation=evaluation,
        original_arrays_and_ply_unchanged=original_intact,save_load_exact=True,
        engineering_nonzero=bool(len(selected)>0 and all((x['arms']['linked']['target_interior']['L1_mean'] or 0)>p['engineering_gates']['minimum_nonzero_target_mean_L1'] for x in evaluation)),
        scientific_verdict='UNCERTIFIED_CPU_MAPPING',native_per_ID_validation=False,
        intent_locality_all_views=all(x['arms']['linked']['intent_locality_gate'] for x in evaluation))
    js(out/'SUMMARY.json',summary)
    ims=[Image.open(x).convert('RGB') for x in all_panels];contact=Image.new('RGB',(ims[0].width,sum(im.height for im in ims)),'white')
    offset=0
    for im in ims:contact.paste(im,(0,offset));offset+=im.height
    contact.save(out/'ALL_EVALUATION_VIEWS.png')
    print(json.dumps(dict(summary=str(out/'SUMMARY.json'),selected_original_ids=len(selected),engineering_nonzero=summary['engineering_nonzero'],seconds=summary['seconds']),default=json_default),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);run(p.parse_args().unit)
