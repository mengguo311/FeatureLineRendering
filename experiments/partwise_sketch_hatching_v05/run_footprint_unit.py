"""Bounded serial stages for full-footprint source-GS linkage diagnostics."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,time
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image
import base_model as base
from footprint import FootprintRenderer,footprint_inputs,resolve_footprint
from membership import accumulate,resolve,load_binding,evaluated_tint_copy
from path_control import aggregate_path,resolve_path,opacity_copy
from run_path_unit import load_scene,read_npz
from validate_path_unit import audit_trace
from run_unit import arrays_hash,png,panel,metrics

ARMS=('specific','previous_path','nearest_path','shuffled')

def load(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text())
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for name,h in p['source_hashes'].items():assert sha(Path(__file__).with_name(name))==h,name
    return p

def freeze(unit):
    prev=runtime.OUTPUT_ROOT/'units/unit_002'
    lock=json.loads((prev/'EVIDENCE_LOCK.json').read_text())
    bad=[k for k,v in lock['files'].items() if sha(prev/k)!=v['sha256']]
    assert not bad,bad
    js(unit/'PREVIOUS_SEAL_AUDIT.json',dict(utc=now(),members=len(lock['files']),mismatches=bad,lock_sha256=sha(prev/'EVIDENCE_LOCK.json')))
    p=json.loads((prev/'PROTOCOL.json').read_text())
    p.update(unit='unit_003',frozen_utc=now(),prior_unit=str(prev),prior_protocol_sha256=sha(prev/'PROTOCOL.json'),
        question='Does excluding original kernels with full-image BUILD responsibility outside frozen path capsules improve actual source tint locality at equal visible effect?',
        camera_disclosure='All six evaluation cameras were already exposed in unit002. Fixed regression/generalization checks, not blind or independent semantic evaluation.',
        footprint=dict(channels=['total','inside_capsule','outside_capsule_AA_band','far','depth_consistent_inside'],
            pixels='ALL accepted full-image pixels at unchanged CPU acceptance site; no sample scaling, no topK',
            selection='Keep prior path strength only if total far/total <=.02 AND worst view far/total <=.05 for view total>=.02, accepted_inside>=.02 in >=2 views with per-view >=.002, accepted_inside/inside>=.7. Otherwise abstain; never promote prior UNKNOWN.',
            depth='same sample alpha>=.5, abs(proxy-source median)<=.08, contributor abs(depth-proxy)<=.06',
            mask='same frozen 3px visible capsules; fixed 2px dilation AA band',
            controls='previous_path is unchanged unscaled unit002 selection; nearest_path matches proposed count by center-to-segment-midpoint distance; shuffled proposed strengths within ten prior BUILD exposure bins seed1729',
            budget='Primary tint: .85 * minimum actual full-image BUILD RGB L1 at unit strength across four arms; linear scales fixed before evaluation; compare target effect, leakage and path coverage. A zero headroom is abstention, not success.',
            opacity='Secondary diagnostic only: proposed COPY opacity*(1-.5*unscaled_strength), real full-source rerender and new accepted trace. Not effect-matched, no comparative superiority claim.',
            superiority='Only descriptive two-scene exposed-camera comparison; all-view locality requires original target mean>=.02 AND far<=.02 in every view. No no-op success.'),
        scientific_scope='UNCERTIFIED_CPU_MAPPING. Full-footprint CPU responsibility and original-row edits; no native, semantic or physical certification.',
        resource_limits=dict(serial=True,cpu_affinity=2,numeric_threads=1,GPU=False,no_nested_models=True,unit_deadline_jst='2026-10-22T18:55:46+09:00'))
    p['diagnostic']['arms']=list(ARMS)
    src=Path(__file__).parent;snap=unit/'source_snapshot'
    shutil.copytree(src,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={f.name:sha(f) for f in snap.iterdir() if f.is_file()}
    js(unit/'PROTOCOL.json',p);js(unit/'PROTOCOL_LOCK.json',dict(sha256=sha(unit/'PROTOCOL.json'),utc=now()))
    print('FROZEN',sha(unit/'PROTOCOL.json'),flush=True)

def audit(unit,scene):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene)
    prior=Path(p['prior_unit'])/'results'/scene;n=len(a['means']);m=p['membership']
    binding,_=load_binding(prior/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    old=read_npz(prior/'PATH_BINDING.npz');scores=[];totals=[];accepted=[];checks={}
    for c in s['cameras']:
        f=read_npz(prior/c['view']/'baseline.npz');t=read_npz(prior/c['view']/'trace.npz')
        ps=read_npz(prior/c['view']/'path_support.npz')
        check=audit_trace(a,c,t,f)
        seg=ps['segment_index'];np.testing.assert_array_equal(seg,s['selected_segment_indices'])
        np.testing.assert_array_equal(ps['stroke_id'],strokes[4]['stroke_id'][seg])
        np.testing.assert_array_equal(ps['face'],strokes[4]['face'][seg])
        np.testing.assert_allclose(np.einsum('ni,nij->nj',ps['bary'],mesh['tri'][ps['face']]),ps['world'],rtol=0,atol=1e-9)
        # Check raw CSR against accepted source events, including rejected anchors.
        order=np.argsort(t['sample_index'],kind='stable');ss=t['sample_index'][order]
        for k,sid in enumerate(ps['sample_index']):
            ix=order[np.searchsorted(ss,sid,'left'):np.searchsorted(ss,sid,'right')] if sid>=0 else np.array([],int)
            lo,hi=ps['offsets'][k:k+2]
            np.testing.assert_array_equal(ps['source_index'][lo:hi],t['source_index'][ix])
            np.testing.assert_array_equal(ps['weight'][lo:hi],t['weight'][ix])
        check['raw_path_CSR_original_ID_anchor_identity']=True
        if c['split']=='build':
            score,_,_=accumulate(n,t,t['proxy_region'],t['proxy_depth'],t['sample_eligible'],t['sampling_weight'],m['contributor_proxy_z_tolerance'])
            scores.append(score);total,accept=aggregate_path(n,ps);totals.append(total);accepted.append(accept)
        checks[c['view']]=check
    b=resolve(np.stack(scores),m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in b.items():np.testing.assert_array_equal(v,binding[k])
    pb=resolve_path(np.stack(totals),np.stack(accepted),b)
    for k,v in pb.items():np.testing.assert_array_equal(v,old[k])
    out=unit/'results'/scene;out.mkdir(parents=True,exist_ok=True)
    for name in ('SOURCE_BINDING.npz','PATH_BINDING.npz'):
        shutil.copyfile(prior/name,out/name);assert sha(prior/name)==sha(out/name)
    js(out/'PRIOR_RAW_AUDIT.json',dict(utc=now(),checks=checks,M1_all_rows_exact=True,path_all_rows_exact=True,
       source_count=n,unknown=int(binding['unknown'].sum()),path_selected=int((pb['strength']>0).sum()),
       finding='Prior mapping is internally correct; anchor-only support does not bound off-path footprints.',source_array_hashes=arrays_hash(a)))
    print('AUDIT',scene,n,'UNKNOWN',int(binding['unknown'].sum()),flush=True)

def collect(unit,scene,index):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene)
    c=[v for v in s['cameras'] if v['split']=='build'][index]
    prior=Path(p['prior_unit'])/'results'/scene/c['view'];out=unit/'results'/scene/c['view'];out.mkdir(parents=True,exist_ok=True)
    old=read_npz(prior/'baseline.npz');t=read_npz(prior/'trace.npz');r=FootprintRenderer(unit/'build')
    f,tr,stats=r.footprint(a,c,*footprint_inputs(old),xy=t['xy'])
    check=audit_trace(a,c,dict(tr,xy=t['xy']),f)
    for k in ('rgb','alpha','median_camera_z','center_depth_proxy','expected_camera_z'):
        np.testing.assert_array_equal(f[k],old[k])
    for k,v in tr.items():np.testing.assert_array_equal(v,t[k])
    error=abs(float(stats[:,0].sum())-float(f['alpha'].sum(dtype=np.float64)))
    assert error<.001,error
    np.testing.assert_allclose(stats[:,1:4].sum(1),stats[:,0],rtol=1e-12,atol=1e-10)
    # An independent real-row partition check: mark exactly the traced pixels as
    # inside. Their per-ID C++ sums must equal a Python bincount of all events.
    if index==0:
        cat=np.full(f['alpha'].shape,2,np.int32);xx,yy=t['xy'].T;cat[yy,xx]=0
        ff,tt,grid_stats=r.footprint(a,c,cat,old['proxy_depth'],np.ones(cat.shape,bool),xy=t['xy'])
        expected=np.bincount(tr['source_index'],tr['weight'],minlength=len(a['means']))
        np.testing.assert_allclose(grid_stats[:,1],expected,rtol=0,atol=1e-12)
        check['all_original_rows_fixed_grid_footprint_equals_independent_event_sum']=True
        check['fixed_grid_per_ID_max_error']=float(np.max(np.abs(grid_stats[:,1]-expected)))
    np.savez_compressed(out/'FOOTPRINT.npz',source_index=np.arange(len(a['means'])),mass=stats,source_sha256=np.array(s['source']['sha256']),camera_json=np.array(json.dumps(c)))
    np.savez_compressed(out/'baseline.npz',**f,proxy_depth=old['proxy_depth'],proxy_regions=old['proxy_regions'],path_mask=old['path_mask'])
    png(out/'source.png',f['rgb'])
    check.update(full_pixel_mass_vs_alpha_sum_error=error,prior_all5_arrays_and_events_exact=True,footprint_channels_partition_total=True)
    js(out/'COLLECT_CHECK.json',check)
    print('COLLECT',scene,c['view'],'accepted full pixel mass',stats[:,0].sum(),flush=True)

def select(unit,scene):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene
    old=read_npz(out/'PATH_BINDING.npz');binding,_=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],len(a['means']))
    pv=np.stack([read_npz(out/c['view']/'FOOTPRINT.npz')['mass'] for c in s['cameras'] if c['split']=='build'])
    q=resolve_footprint(pv,old);count=int((q['strength']>0).sum())
    np.savez_compressed(out/'FOOTPRINT_BINDING.npz',**q,source_sha256=np.array(s['source']['sha256']),protocol_sha256=np.array(sha(unit/'PROTOCOL.json')))
    distance,nearest=cKDTree(paths['points'].mean(1)).query(a['means'],workers=1)
    spatial=np.zeros(len(distance));spatial[np.argsort(distance,kind='stable')[:count]]=1.
    shuffled=q['strength'].copy();rng=np.random.default_rng(1729)
    observed=np.flatnonzero(binding['exposure']>0);ordered=observed[np.argsort(binding['exposure'][observed],kind='stable')]
    for group in np.array_split(ordered,10):shuffled[group]=q['strength'][rng.permutation(group)]
    candidates=dict(specific=q['strength'],previous_path=old['strength'],nearest_path=spatial,shuffled=shuffled)
    np.savez_compressed(out/'CANDIDATES.npz',source_index=q['source_index'],source_sha256=np.array(s['source']['sha256']),nearest_distance=distance,**candidates)
    old_ids=old['strength']>0
    js(out/'SELECTION.json',dict(source_count=len(distance),counts={k:int((v>0).sum()) for k,v in candidates.items()},
        unknown=int(q['unknown'].sum()),reasons=dict(zip(*np.unique(q['reason'],return_counts=True))),
        old_selected_far_fraction_quantiles=np.quantile(q['far_fraction'][old_ids],[0,.25,.5,.75,.9,1]),
        old_selected_weighted_far_fraction=float((q['far']*old['strength']).sum()/max((q['total']*old['strength']).sum(),1e-30)),
        proposed_weighted_far_fraction=float((q['far']*q['strength']).sum()/max((q['total']*q['strength']).sum(),1e-30)),
        scope='BUILD complete-image alpha*T, including visible off-path responsibility; no native or physical ownership guarantee'))
    print('SELECT',scene,'old',int(old_ids.sum()),'specific',count,flush=True)

def budget(unit,scene,index):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene
    c=[v for v in s['cameras'] if v['split']=='build'][index];folder=out/c['view'];f=read_npz(folder/'baseline.npz')
    cand=read_npz(out/'CANDIDATES.npz');r=FootprintRenderer(unit/'build');values={};rgb=base.source_colors(a,c)
    for arm in ARMS:
        st=cand[arm];copy={k:v for k,v in a.items() if k!='SH'};copy['colors']=rgb*(1-st[:,None])+np.asarray(p['diagnostic']['tint'])*st[:,None]
        ef,_=r.render(copy,c)
        np.testing.assert_array_equal(ef['alpha'],f['alpha'])
        delta=ef['rgb'].astype(float)-f['rgb'].astype(float)
        values[arm]=float(np.abs(delta).sum())
        np.savez_compressed(folder/('budget_'+arm+'.npz'),delta=delta)
    js(folder/'BUDGET.json',dict(camera=c,full_image_L1=values))
    print('BUDGET',scene,c['view'],values,flush=True)

def match(unit,scene):
    p=load(unit);s=p['scenes'][scene];out=unit/'results'/scene;cand=read_npz(out/'CANDIDATES.npz')
    values={k:sum(json.loads((out/c['view']/'BUDGET.json').read_text())['full_image_L1'][k] for c in s['cameras'] if c['split']=='build') for k in ARMS}
    common=.85*min(values.values());scales={k:common/v if v>0 else 0. for k,v in values.items()}
    selection={k:cand[k]*scales[k] for k in ARMS}
    np.savez_compressed(out/'EDIT_SELECTION.npz',source_index=cand['source_index'],source_sha256=cand['source_sha256'],tint=np.asarray(p['diagnostic']['tint']),**selection)
    js(out/'BUDGET_MATCH.json',dict(full_image_unit_strength_L1=values,target=common,scales=scales,valid=common>1e-10,
        scope='Actual four BUILD full-source RGB renders per arm; linear tint matching, all evaluation strengths frozen',
        no_headroom_policy='zero budget is abstention, not local-control success'))
    print('MATCH',scene,common,scales,flush=True)

def coverage(ps,strength):
    weight=ps['weight']*ps['eligible']*strength[ps['source_index']]
    per=np.array([weight[lo:hi].sum() for lo,hi in zip(ps['offsets'][:-1],ps['offsets'][1:])])
    visible=ps['proxy_visible'];supported=ps['retained_mass']>.01
    return dict(attempted=len(per),proxy_visible=int(visible.sum()),original_supported=int((supported&~ps['unknown']).sum()),
        edited_mass_per_anchor=per,anchors_with_edit_mass_above_001=int((per>.01).sum()),
        weighted_retained_mass=float(per.sum()),retained_mass_before_selection=float(ps['retained_mass'].sum()),
        retained_fraction=float(per.sum()/max(ps['retained_mass'].sum(),1e-30)))

def evaluate(unit,scene,index):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene
    c=[v for v in s['cameras'] if v['split']=='evaluation'][index];prior=Path(p['prior_unit'])/'results'/scene/c['view']
    folder=out/c['view'];folder.mkdir(exist_ok=True)
    orig=arrays_hash(a);old=read_npz(prior/'baseline.npz');t=read_npz(prior/'trace.npz');ps=read_npz(prior/'path_support.npz')
    cand=read_npz(out/'CANDIDATES.npz');selection=read_npz(out/'EDIT_SELECTION.npz');r=FootprintRenderer(unit/'build')
    f,tr,fp=r.footprint(a,c,*footprint_inputs(old),xy=t['xy'],strength=selection['specific'])
    for k in ('rgb','alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(f[k],old[k])
    check=audit_trace(a,c,dict(tr,xy=t['xy']),f)
    np.savez_compressed(folder/'baseline.npz',**f,proxy_depth=old['proxy_depth'],proxy_regions=old['proxy_regions'],path_mask=old['path_mask'])
    np.savez_compressed(folder/'FOOTPRINT.npz',source_index=np.arange(len(a['means'])),mass=fp)
    np.savez_compressed(folder/'trace.npz',**tr,xy=t['xy'])
    shutil.copyfile(prior/'path_support.npz',folder/'path_support.npz')
    intent=np.where(old['proxy_regions']>0,1,0);intent[old['path_mask']]=4
    row=dict(camera=c,trace_check=check,arms={},coverage={},tint_reconstruction={},original_array_hashes=orig)
    images={};col=base.source_colors(a,c);sid=tr['sample_index'];ids=tr['source_index'];xx,yy=t['xy'].T
    for arm in ARMS:
        ef,_=r.render(evaluated_tint_copy(a,c,selection[arm],p['diagnostic']['tint']),c)
        for k in ('alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(ef[k],f[k])
        delta=np.zeros((len(t['xy']),3));np.add.at(delta,sid,tr['weight'][:,None]*selection[arm][ids,None]*(np.asarray(p['diagnostic']['tint'])-col[ids]))
        err=float(np.max(np.abs(f['rgb'][yy,xx]+delta-ef['rgb'][yy,xx])));assert err<1e-6
        row['tint_reconstruction'][arm]=err;row['arms'][arm]=metrics(f['rgb'],ef['rgb'],intent,f['contribution'],p)
        row['coverage'][arm]=coverage(ps,selection[arm]);images[arm]=ef['rgb']
        np.savez_compressed(folder/('tint_'+arm+'.npz'),**ef);png(folder/('tint_'+arm+'.png'),ef['rgb'])
    changed=opacity_copy(a,cand['specific'],.5);op,ot=r.render(changed,c,t['xy'])
    row['opacity_check']=audit_trace(changed,c,dict(ot,xy=t['xy']),op)
    row['opacity_diagnostic']=metrics(f['rgb'],op['rgb'],intent,f['contribution'],p)
    before=np.unique(sid*len(a['means'])+ids);after=np.unique(ot['sample_index']*len(a['means'])+ot['source_index'])
    row['opacity_check']['newly_accepted_pixel_ID_pairs']=len(np.setdiff1d(after,before))
    np.savez_compressed(folder/'opacity_specific.npz',**op);np.savez_compressed(folder/'opacity_trace.npz',**ot,xy=t['xy'])
    png(folder/'opacity_specific.png',op['rgb'])
    if index==0:
        isolated,_=r.render(dict(a,opacity=a['opacity']*(cand['specific']>0)),c)
        np.savez_compressed(folder/'selected_only_recomputed_T.npz',**isolated)
        png(folder/'selected_only_recomputed_T.png',isolated['rgb'])
    png(folder/'source.png',f['rgb'])
    for name in ('authored_path_intent.png','hatches_context.png'):shutil.copyfile(prior/name,folder/name)
    target=np.asarray(Image.open(folder/'authored_path_intent.png').convert('RGB'))/255
    hatch=np.asarray(Image.open(folder/'hatches_context.png').convert('RGB'))/255
    support=f['rgb']*(1-f['contribution'][:,:,None])+np.asarray(p['diagnostic']['tint'])*f['contribution'][:,:,None]
    png(folder/'full_T_source_support.png',support)
    panel(folder/'comparison.png',[f['rgb'],target,support,images['specific'],op['rgb'],hatch],
        ['Original GS / full SH3','Authored fixed path set','Full-T source support','Specific source tint','Source opacity x (1-.5s)','Saved 3D hatches'],
        scene+' '+c['view']+' | CPU mapping; fixed original PLY rows; no semantic/native certification')
    panel(folder/'controls.png',[f['rgb']]+[images[k] for k in ARMS],
        ['Original GS','Full-footprint selection','Previous path selection','Nearest path / same count','Shuffled source IDs'],
        'Equal actual full-image BUILD tint L1; evaluation unchanged; fixed 3px capsule / 2px AA band')
    row['source_arrays_and_PLY_unchanged']=arrays_hash(a)==orig and sha(s['source']['original_ply'])==s['source']['sha256']
    assert row['source_arrays_and_PLY_unchanged'];js(folder/'EVALUATION.json',row)
    print('EVAL',scene,c['view'],{k:(v['target_interior']['L1_mean'],v['far_non_target_fraction'],v['intent_locality_gate']) for k,v in row['arms'].items()},flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True)
    ap.add_argument('--stage',choices=['freeze','audit','collect','select','budget','match','evaluate'],required=True)
    ap.add_argument('--scene',choices=['chair','lego']);ap.add_argument('--index',type=int,default=0)
    args=ap.parse_args();unit=output_guard(args.unit)
    if args.stage=='freeze':freeze(unit)
    elif args.stage in ('audit','select','match'):globals()[args.stage](unit,args.scene)
    else:globals()[args.stage](unit,args.scene,args.index)

if __name__=='__main__':main()
