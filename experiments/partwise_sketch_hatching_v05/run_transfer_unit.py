"""Frozen fresh-camera source-Gaussian transfer, with original-row evidence."""
import runtime
from runtime import js,sha,now,output_guard,OUTPUT_ROOT
from pathlib import Path
import argparse,json,shutil,time,csv
import numpy as np
from PIL import Image
import base_model as base
from geometry import orbit_camera
from footprint import FootprintRenderer,footprint_inputs,resolve_footprint
from membership import load_binding,resolve,evaluated_tint_copy
from path_control import resolve_path,opacity_copy
from run_path_unit import load_scene,read_npz,capture,path_stats
from run_footprint_unit import ARMS
from validate_path_unit import audit_trace
from run_unit import arrays_hash,png,panel,metrics
from render import render as render_hatches
from transfer_audit import membership_projection,coverage_assessment,kernel_damage_bound

BINDING_FILES=('SOURCE_BINDING.npz','PATH_BINDING.npz','FOOTPRINT_BINDING.npz',
               'CANDIDATES.npz','EDIT_SELECTION.npz','BUDGET_MATCH.json')


def load(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text())
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for name,h in p['source_hashes'].items():assert sha(Path(__file__).with_name(name))==h,name
    for scene,s in p['scenes'].items():
        for name,h in s['frozen_binding_hashes'].items():assert sha(unit/'results'/scene/name)==h,(scene,name)
    return p


def freeze(unit):
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('frozen protocol exists')
    prev=OUTPUT_ROOT/'units/unit_003';old=json.loads((prev/'PROTOCOL.json').read_text())
    lock=json.loads((prev/'EVIDENCE_LOCK.json').read_text())
    errors=[name for name,v in lock['files'].items() if sha(prev/name)!=v['sha256']]
    assert not errors,errors
    js(unit/'PREVIOUS_SEAL_AUDIT.json',dict(utc=now(),members=len(lock['files']),mismatches=errors,lock_sha256=sha(prev/'EVIDENCE_LOCK.json')))
    # Audit available camera metadata from all prior v05 units, including media.
    seen=[]
    def visit(x):
        if isinstance(x,dict):
            if 'extrinsic' in x and np.asarray(x['extrinsic']).shape==(4,4):seen.append(np.asarray(x['extrinsic']))
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    camera_files=0
    for number in (1,2,3):
        for file in (OUTPUT_ROOT/f'units/unit_{number:03d}').rglob('*.json'):
            if 'source_snapshot' in file.parts or 'delivery_source' in file.parts:continue
            visit(json.loads(file.read_text()));camera_files+=1
    scenes={}
    for scene in ('chair','lego'):
        s=dict(old['scenes'][scene]);s['prior_build_cameras']=[c for c in s['cameras'] if c['split']=='build']
        dist=5.1 if scene=='chair' else 5.3
        cameras=[]
        for el in (12.,72.):
            for az in (31.,121.,211.,301.):
                c=orbit_camera(az,el,dist,384);c.update(split='evaluation',azimuth=az,elevation=el,distance=dist)
                assert all(not np.allclose(c['extrinsic'],e,rtol=0,atol=1e-10) for e in seen)
                cameras.append(c)
        s['cameras']=cameras
        s['camera_disclosure']='Exact extrinsics absent from audited prior v05 JSON cameras, including media. Prior scientific decisions used previous views. Historical v04 exposure and underlying source-GS training overlap unverified; no native/semantic blind-test claim.'
        out=unit/'results'/scene;out.mkdir(parents=True)
        s['frozen_binding_hashes']={}
        for name in BINDING_FILES:
            shutil.copyfile(prev/'results'/scene/name,out/name)
            s['frozen_binding_hashes'][name]=sha(out/name)
        scenes[scene]=s
    p=dict(unit='unit_004',frozen_utc=now(),prior_unit=str(prev),prior_protocol_sha256=sha(prev/'PROTOCOL.json'),
        prior_evidence_lock_sha256=sha(prev/'EVIDENCE_LOCK.json'),
        started_jst='2026-10-22T18:38:23.892849+09:00',unit_deadline_jst='2026-10-22T19:33:23.892849+09:00',
        question='Do frozen full-footprint original-ID controls retain both local effect and path coverage at fresh low/high elevations on Chair and Lego?',
        scenes=scenes,source_ID_universe=old['source_ID_universe'],sampling=old['sampling'],membership=old['membership'],region_id=4,
        diagnostic=dict(tint=old['diagnostic']['tint'],aa_band_pixels=2,arms=list(ARMS),
            locality_gate=old['diagnostic']['locality_gate'],minimum_nonzero_target_mean_L1=.0001),
        coverage_gate=dict(min_supported_anchors=8,min_edited_anchor_fraction=.5,min_retained_mass_fraction=.05,edit_mass_threshold=.01),
        evaluation_rule='Per view joint transfer requires unchanged locality AND new frozen coverage gate. Unsupported/empty target is unscorable, never pass. Every scheduled view reported. No selection, strength, mask, tolerance or threshold update after evaluation.',
        budget='Exact byte copy of unit003 EDIT_SELECTION and BUDGET_MATCH: all four arms matched actual full-image RGB L1 over four BUILD cameras. No fresh-view budget fitting. Raw RGB primary; clipped display also reported. Previous-path count differs; nearest/shuffle match specific count.',
        operation='Actual complete original-GS renders. Tint is an evaluated full-SH3 color override; original SH intact. A separate specific-arm COPY opacity*(1-.5*unscaled_strength) rerenders T; no comparative opacity claim.',
        membership_projection='Save original soft evidence histogram and abstention-aware histogram separately. Whole UNKNOWN rows contribute entirely to channel0 in latter; normalize by accepted source alpha, zero-alpha rays UNKNOWN. Same-proxy intent agreement is not semantic accuracy.',
        failure_diagnosis='Save ALL selected original IDs with fresh full-image inside/band/far/depth-compatible masses, color-L1 far-damage upper bounds, projected covariance, and source centers. Upper bound permits color cancellation; not exact pixel damage decomposition.',
        camera_novelty=dict(prior_JSON_files=camera_files,camera_records=len(seen),exact_extrinsics_disjoint=True),
        scientific_scope='UNCERTIFIED_CPU_MAPPING; finite CPU engineering transfer only. Proxy intent not independent semantics; no physical attachment/native/H1/H2/H3 proof.',
        resource_limits=dict(serial=True,cpu_affinity=2,numeric_threads=1,GPU=False,no_nested_models=True))
    snap=unit/'source_snapshot';shutil.copytree(Path(__file__).parent,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={f.name:sha(f) for f in snap.iterdir() if f.is_file()}
    js(unit/'PROTOCOL.json',p);js(unit/'PROTOCOL_LOCK.json',dict(utc=now(),sha256=sha(unit/'PROTOCOL.json')))
    print('FROZEN',sha(unit/'PROTOCOL.json'),p['camera_novelty'],flush=True)


def audit(unit,scene):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene
    n=len(a['means']);b,bmeta=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],n);m=p['membership']
    resolved=resolve(b['per_view_score'],m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in resolved.items():np.testing.assert_array_equal(v,b[k])
    pb=read_npz(out/'PATH_BINDING.npz');path=resolve_path(pb['per_view_total'],pb['per_view_accepted'],b)
    for k,v in path.items():np.testing.assert_array_equal(v,pb[k])
    q=read_npz(out/'FOOTPRINT_BINDING.npz');fp=resolve_footprint(q['per_view_mass'],pb)
    for k,v in fp.items():np.testing.assert_array_equal(v,q[k])
    sel=read_npz(out/'EDIT_SELECTION.npz');cand=read_npz(out/'CANDIDATES.npz')
    budget=json.loads((out/'BUDGET_MATCH.json').read_text())
    for arm in ARMS:np.testing.assert_array_equal(sel[arm],cand[arm]*budget['scales'][arm])
    np.testing.assert_array_equal(cand['specific'],q['strength'])
    assert (sel['specific'][b['unknown']]==0).all()
    prev=Path(p['prior_unit']);op=json.loads((prev/'PROTOCOL.json').read_text())
    checks={}
    for c in op['scenes'][scene]['cameras']:
        if c['split']!='evaluation':continue
        folder=prev/'results'/scene/c['view'];f=read_npz(folder/'baseline.npz');t=read_npz(folder/'trace.npz')
        check=audit_trace(a,c,t,f);row=json.loads((folder/'EVALUATION.json').read_text())
        intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4
        for arm in ARMS:
            edit=read_npz(folder/('tint_'+arm+'.npz'))
            mm=metrics(f['rgb'],edit['rgb'],intent,f['contribution'],p)
            assert mm==row['arms'][arm]
        check['prior_actual_all4_RGB_metrics_exact']=True;checks[c['view']]=check
    result=dict(utc=now(),source_count=n,M1_unknown=int(b['unknown'].sum()),M1_conflict=int(b['conflict'].sum()),
        M1_all_rows_recomputed=True,path_all_rows_recomputed=True,footprint_all_rows_recomputed=True,
        selection_and_budget_exact=True,unknown_never_promoted=True,prior_eval_actual_trace_checks=checks,
        original_array_hashes=arrays_hash(a),source_metadata=bmeta,
        selected_original_IDs=int((sel['specific']>0).sum()),
        criticism='Previous 6/6 locality used exposed evaluation cameras and no joint path coverage gate. Sparse M1 UNKNOWN and weak Lego path coverage remain; fresh transfer has not yet been evaluated.')
    js(out/'PRIOR_AUDIT.json',result);print('AUDITED',scene,n,'UNKNOWN',result['M1_unknown'],flush=True)


def project_intent(t,b,p):
    mp=membership_projection(t,b,len(t['xy']));mask=t['sample_eligible']&(t['proxy_region']>0)&(mp['mass']>=.5)
    known_mass=mp['mass'][mask].sum();labels=t['proxy_region'][mask]
    stats=dict(eligible_sample_count=int(mask.sum()),source_unknown_mass_fraction=float(mp['unknown_kernel_mass'][mask].sum()/max(known_mass,1e-30)))
    for name in ('soft_q','abstaining_q'):
        q=mp[name][mask];target=np.eye(6)[labels]
        stats[name]=dict(mean_unknown=float(q[:,0].mean()) if len(q) else None,
            same_proxy_argmax_agreement=float((q.argmax(1)==labels).mean()) if len(q) else None,
            same_proxy_Brier=float(((q-target)**2).sum(1).mean()) if len(q) else None)
    return mp,stats


def evaluate(unit,scene,index):
    start=time.monotonic();p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene)
    out=unit/'results'/scene;c=s['cameras'][index];folder=out/c['view'];folder.mkdir(exist_ok=False)
    sel=read_npz(out/'EDIT_SELECTION.npz');cand=read_npz(out/'CANDIDATES.npz')
    b,_=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],len(a['means']))
    r=FootprintRenderer(unit/'build');original=arrays_hash(a)
    d=capture(r,a,mesh,paths,c,p,s);t=d['trace'];ps=d['path'];old=d['frame']
    f,tr,fp=r.footprint(a,c,*footprint_inputs(dict(old,proxy_depth=d['proxy_depth'],path_mask=d['path_mask'])),xy=t['xy'],strength=sel['specific'])
    for k in old:
        if k!='contribution':np.testing.assert_array_equal(f[k],old[k])
    for k,v in tr.items():np.testing.assert_array_equal(v,t[k])
    check=audit_trace(a,c,t,f)
    if index==0:
        ref=r.baseline(a,c)
        for k,v in ref.items():np.testing.assert_array_equal(v,f[k])
        check['same_uninstrumented_CPU_exact']=True
    np.testing.assert_allclose(fp[:,1:4].sum(1),fp[:,0],rtol=1e-12,atol=1e-10)
    masserr=abs(fp[:,0].sum()-f['alpha'].sum(dtype=float));assert masserr<.001
    check.update(full_pixel_partition_exact=True,full_pixel_alpha_mass_error=masserr,trace_and_footprint_on_off_exact=True)
    np.savez_compressed(folder/'baseline.npz',**f,proxy_depth=d['proxy_depth'],proxy_regions=d['regions'],path_mask=d['path_mask'])
    np.savez_compressed(folder/'trace.npz',**t);np.savez_compressed(folder/'path_support.npz',**ps)
    np.savez_compressed(folder/'FOOTPRINT.npz',source_index=np.arange(len(a['means'])),mass=fp,camera_json=np.array(json.dumps(c)),source_sha256=np.array(s['source']['sha256']))
    mp,mstats=project_intent(t,b,p);np.savez_compressed(folder/'M1_PROJECTION.npz',**mp,xy=t['xy'],proxy_region=t['proxy_region'],sample_eligible=t['sample_eligible'])
    intent=np.where(d['regions']>0,1,0);intent[d['path_mask']]=4
    row=dict(camera=c,trace_check=check,M1_projection=mstats,path_support=path_stats(ps),arms={},coverage={},joint_transfer={},tint_reconstruction={},source_array_hashes=original)
    if p.get('unit')=='unit_005':
        reference,_=load_binding(Path(p['prior_unit'])/'results'/scene/'SOURCE_BINDING.npz',s['source']['sha256'],len(a['means']))
        refmp,refstats=project_intent(t,reference,p)
        np.savez_compressed(folder/'M1_PREVIOUS_PROJECTION.npz',**refmp,xy=t['xy'])
        row['M1_previous_projection']=refstats
    col=base.source_colors(a,c);sid=t['sample_index'];ids=t['source_index'];xx,yy=t['xy'].T;images={}
    for arm in ARMS:
        ef,_=r.render(evaluated_tint_copy(a,c,sel[arm],p['diagnostic']['tint']),c)
        for k in ('alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(f[k],ef[k])
        delta=np.zeros((len(t['xy']),3));np.add.at(delta,sid,t['weight'][:,None]*sel[arm][ids,None]*(np.asarray(p['diagnostic']['tint'])-col[ids]))
        err=float(np.abs(f['rgb'][yy,xx]+delta-ef['rgb'][yy,xx]).max());assert err<1e-6
        row['tint_reconstruction'][arm]=err
        row['arms'][arm]=metrics(f['rgb'],ef['rgb'],intent,f['contribution'],p)
        row['coverage'][arm]=coverage_assessment(ps,sel[arm],p['coverage_gate'])
        row['joint_transfer'][arm]=bool(row['arms'][arm]['intent_locality_gate'] and row['coverage'][arm]['coverage_gate'])
        np.savez_compressed(folder/('tint_'+arm+'.npz'),**ef);png(folder/('tint_'+arm+'.png'),ef['rgb']);images[arm]=ef['rgb']
    op_a=opacity_copy(a,cand['specific'],.5);op,ot=r.render(op_a,c,t['xy'])
    row['opacity_check']=audit_trace(op_a,c,dict(ot,xy=t['xy']),op)
    before=np.unique(sid*len(a['means'])+ids);after=np.unique(ot['sample_index']*len(a['means'])+ot['source_index'])
    row['opacity_check']['newly_accepted_pixel_ID_pairs']=len(np.setdiff1d(after,before))
    row['opacity_diagnostic']=metrics(f['rgb'],op['rgb'],intent,f['contribution'],p)
    np.savez_compressed(folder/'opacity_specific.npz',**op);np.savez_compressed(folder/'opacity_trace.npz',**ot,xy=t['xy']);png(folder/'opacity_specific.png',op['rgb'])
    bound=kernel_damage_bound(fp,col,sel['specific'],p['diagnostic']['tint']);selected=np.flatnonzero(sel['specific']>0)
    uv,z,cov=base.project_cov(a['means'],a['covariance'],c);evals=np.linalg.eigvalsh(cov[selected]);vals=np.linalg.eigvalsh(a['covariance'][selected])
    np.savez_compressed(folder/'SELECTED_KERNEL_DIAGNOSTICS.npz',source_index=selected,full_pixel_mass=fp[selected],
        far_RGB_L1_upper_bound=bound[selected],strength=sel['specific'][selected],source_center=a['means'][selected],
        projected_uv=uv[selected],center_camera_z=z[selected],projected_sigma_major=np.sqrt(evals[:,-1]),
        world_sigma=np.sqrt(vals),M1_membership=b['membership'][selected],M1_unknown=b['unknown'][selected])
    worst=selected[np.argsort(-bound[selected],kind='stable')[:10]]
    actualfar=row['arms']['specific']['far_other']['L1_sum']+row['arms']['specific']['far_background']['L1_sum']
    assert actualfar<=bound.sum()+.002
    row['failure_diagnosis']=dict(actual_far_RGB_L1=actualfar,triangle_bound_far_RGB_L1=float(bound.sum()),
        bound_is_not_exact_damage_attribution=True,all_selected_IDs_saved=len(selected),
        largest_bound_source_IDs=worst,largest_bound_values=bound[worst],
        selected_responsibility_far_fraction=float((fp[:,3]*sel['specific']).sum()/max((fp[:,0]*sel['specific']).sum(),1e-30)))
    hatch=render_hatches(mesh,strokes,meta['styles'],c,2,meta.get('display'))
    target=np.repeat(hatch['proxy'][:,:,None],3,2);target[d['regions']==4]=[1.,.72,.72];target[d['path_mask']]=[.95,.1,.15]
    support=f['rgb']*(1-f['contribution'][:,:,None])+np.asarray(p['diagnostic']['tint'])*f['contribution'][:,:,None]
    for name,im in [('source',f['rgb']),('authored_path_intent',target),('hatches_context',hatch['image']),('full_T_source_support',support)]:png(folder/(name+'.png'),im)
    panel(folder/'comparison.png',[f['rgb'],target,support,images['specific'],op['rgb'],hatch['image']],
        ['Original GS / full SH3','Authored region + fixed paths','Full-T original-ID support','Frozen source tint','Source opacity diagnostic','Saved 3D hatches'],
        scene+' '+c['view']+' | New v05 camera; frozen BUILD budget; CPU mapping only')
    panel(folder/'controls.png',[f['rgb']]+[images[k] for k in ARMS],
        ['Original GS']+p['diagnostic'].get('arm_labels',['Full-footprint selection','Previous path selection','Nearest path / same count','Shuffled source IDs']),
        'Matched actual BUILD source-RGB effect; no new-view matching; all failure views retained')
    differences=[]
    for arm in ARMS:
        value=np.clip(np.abs(images[arm]-f['rgb']).sum(2)/.3,0,1)
        differences.append(np.stack([np.ones_like(value),1-value,1-value],-1))
    panel(folder/'difference_diagnostics.png',differences,list(ARMS),'Actual RGB L1 / 0.3 difference heat; diagnostic, not source RGB')
    assert original==arrays_hash(a) and sha(s['source']['original_ply'])==s['source']['sha256']
    row.update(original_arrays_and_PLY_unchanged=True,seconds=time.monotonic()-start,finished_utc=now())
    js(folder/'EVALUATION.json',row)
    print('FRESH',scene,c['view'],{k:dict(effect=v['target_interior']['L1_mean'],far=v['far_non_target_fraction'],local=v['intent_locality_gate'],coverage=row['coverage'][k]['coverage_gate'],joint=row['joint_transfer'][k]) for k,v in row['arms'].items()},'seconds',row['seconds'],flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True)
    ap.add_argument('--stage',choices=['freeze','audit','evaluate'],required=True)
    ap.add_argument('--scene',choices=['chair','lego']);ap.add_argument('--index',type=int,default=0)
    args=ap.parse_args();unit=output_guard(args.unit)
    if args.stage=='freeze':freeze(unit)
    elif args.stage=='audit':audit(unit,args.scene)
    else:evaluate(unit,args.scene,args.index)


if __name__=='__main__':main()
