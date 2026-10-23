"""Expand BUILD observation diversity, then evaluate new original-GS controls."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT,output_guard
from pathlib import Path
import argparse,json,shutil,time
import numpy as np
from scipy.spatial import cKDTree
from geometry import orbit_camera
from membership import accumulate,resolve,save_binding,load_binding
from path_control import aggregate_path,resolve_path
from footprint import resolve_footprint
from expanded_binding import combine_evidence,transition_counts
from run_path_unit import load_scene,read_npz
from run_unit import arrays_hash,metrics
from validate_path_unit import audit_trace
import run_footprint_unit as footprint_run
import run_transfer_unit as transfer_run

ARMS=footprint_run.ARMS
FILES=transfer_run.BINDING_FILES


def load(unit):return transfer_run.load(unit)


def freeze(unit):
    if (unit/'PROTOCOL.json').exists():raise FileExistsError('protocol already frozen')
    prev=OUTPUT_ROOT/'units/unit_004';old=json.loads((prev/'PROTOCOL.json').read_text())
    audits={}
    for number in (2,3,4):
        root=OUTPUT_ROOT/f'units/unit_{number:03d}';lock=json.loads((root/'EVIDENCE_LOCK.json').read_text())
        errors=[name for name,v in lock['files'].items() if sha(root/name)!=v['sha256']]
        assert not errors,errors
        audits[str(number)]=dict(members=len(lock['files']),mismatches=errors,lock_sha256=sha(root/'EVIDENCE_LOCK.json'))
    js(unit/'PREVIOUS_SEAL_AUDIT.json',audits)
    seen=[]
    def visit(x):
        if isinstance(x,dict):
            if 'extrinsic' in x and np.asarray(x['extrinsic']).shape==(4,4):seen.append(np.asarray(x['extrinsic']))
            for v in x.values():visit(v)
        elif isinstance(x,list):
            for v in x:visit(v)
    for number in (1,2,3,4):
        for f in (OUTPUT_ROOT/f'units/unit_{number:03d}').rglob('*.json'):
            if 'source_snapshot' not in f.parts and 'delivery_source' not in f.parts:visit(json.loads(f.read_text()))
    scenes={};inputs={}
    for scene in ('chair','lego'):
        s=dict(old['scenes'][scene]);out=unit/'results'/scene;out.mkdir(parents=True)
        sources=[]
        for c in s['prior_build_cameras']:
            sources.append(dict(camera=c,trace=str(OUTPUT_ROOT/'units/unit_002/results'/scene/c['view']/'trace.npz'),
                path=str(OUTPUT_ROOT/'units/unit_002/results'/scene/c['view']/'path_support.npz'),
                baseline=str(OUTPUT_ROOT/'units/unit_003/results'/scene/c['view']/'baseline.npz'),
                footprint=str(OUTPUT_ROOT/'units/unit_003/results'/scene/c['view']/'FOOTPRINT.npz'),role='original_build'))
        for c in s['cameras']:
            root=prev/'results'/scene/c['view']
            sources.append(dict(camera=dict(c,split='build_from_exposed_unit004'),trace=str(root/'trace.npz'),
                path=str(root/'path_support.npz'),baseline=str(root/'baseline.npz'),footprint=str(root/'FOOTPRINT.npz'),role='exposed_unit004_build'))
        for item in sources:
            for key in ('trace','path','baseline','footprint'):inputs[item[key]]=sha(item[key])
        for name in FILES:
            path=prev/'results'/scene/name;inputs[str(path)]=sha(path)
        s['evidence_sources']=sources;s['budget_cameras']=s['prior_build_cameras']
        cameras=[];dist=5.1 if scene=='chair' else 5.3
        for el in (24.,60.):
            for az in (61.,241.):
                c=orbit_camera(az,el,dist,384);c.update(split='evaluation',azimuth=az,elevation=el,distance=dist)
                assert all(not np.allclose(c['extrinsic'],e,rtol=0,atol=1e-10) for e in seen)
                cameras.append(c)
        s['cameras']=cameras;s['frozen_binding_hashes']={}
        s['camera_disclosure']='Unit004 is explicitly exposed BUILD/DEV. Evaluation extrinsics absent from prior v05 JSON; historical v04 and source-GS training overlap unverified.'
        scenes[scene]=s
    p=dict(unit='unit_005',frozen_utc=now(),started_jst='2026-10-22T19:26:14.921289+09:00',
        unit_deadline_jst='2026-10-22T20:21:14.921289+09:00',prior_unit=str(prev),
        question='Does adding exposed low/high-elevation original-ID evidence reduce M1 UNKNOWN and improve fresh-camera local-control/coverage without changing any selection gate?',
        scenes=scenes,input_hashes=inputs,source_ID_universe=old['source_ID_universe'],
        sampling=old['sampling'],membership=old['membership'],region_id=4,diagnostic=old['diagnostic'],
        coverage_gate=old['coverage_gate'],scientific_scope=old['scientific_scope'],
        changed_variable='BUILD observation set: old four views plus all eight unit004 exposed views. Recompute M1, deduplicated path support, full-pixel footprints; exact existing thresholds unchanged.',
        controls='specific=new 12-view binding; previous_path=old 4-view FOOTPRINT binding (name retained for array compatibility); nearest_path=same new selected count by center-to-segment-midpoint distance; shuffled=new strengths in ten new M1 exposure bins, seed1729.',
        budget='All four arms matched to .85*minimum actual full-source raw RGB L1 across four original BUILD cameras. Old footprint is re-scaled to the same new effect budget. No matching on evaluation or post-evaluation tuning. Old arm count may differ; nearest/shuffle count matches new.',
        evaluation_rule=old['evaluation_rule'],operation=old['operation'],
        immutable_failure_policy='Unit004 8/16 joint result and historical negative evidence remain unchanged. Newly used unit004 views are never described as held out.',
        resource_limits=old['resource_limits'],camera_audit=dict(previous_camera_records=len(seen),exact_extrinsics_disjoint=True))
    p['diagnostic']=dict(p['diagnostic'],arm_labels=['Expanded BUILD binding','Old BUILD footprint','Nearest path / same count','Shuffled original IDs'])
    snap=unit/'source_snapshot';shutil.copytree(Path(__file__).parent,snap,ignore=shutil.ignore_patterns('__pycache__'))
    p['source_hashes']={f.name:sha(f) for f in snap.iterdir() if f.is_file()}
    js(unit/'PROTOCOL.json',p);js(unit/'PROTOCOL_LOCK.json',dict(sha256=sha(unit/'PROTOCOL.json'),utc=now()))
    print('FROZEN',sha(unit/'PROTOCOL.json'),flush=True)


def build(unit,scene):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene;n=len(a['means']);m=p['membership']
    prev=Path(p['prior_unit'])/'results'/scene
    old,old_meta=load_binding(prev/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    oldpath=read_npz(prev/'PATH_BINDING.npz');oldfp=read_npz(prev/'FOOTPRINT_BINDING.npz')
    blocks=[];totals=[];accepted=[];footprints=[];checks={}
    for item in s['evidence_sources']:
        c=item['camera']
        for key in ('trace','path','baseline','footprint'):assert sha(item[key])==p['input_hashes'][item[key]]
        t=read_npz(item['trace']);f=read_npz(item['baseline']);ps=read_npz(item['path']);fp=read_npz(item['footprint'])
        ck=audit_trace(a,c,t,f)
        np.testing.assert_array_equal(ps['segment_index'],s['selected_segment_indices'])
        for key in ('face','stroke_id'):np.testing.assert_array_equal(ps[key],strokes[4][key][ps['segment_index']])
        np.testing.assert_allclose(np.einsum('ni,nij->nj',ps['bary'],mesh['tri'][ps['face']]),ps['world'],rtol=0,atol=1e-9)
        order=np.argsort(t['sample_index'],kind='stable');ss=t['sample_index'][order]
        for j,sid in enumerate(ps['sample_index']):
            lo,hi=ps['offsets'][j:j+2];ix=order[np.searchsorted(ss,sid,'left'):np.searchsorted(ss,sid,'right')] if sid>=0 else np.array([],int)
            np.testing.assert_array_equal(ps['source_index'][lo:hi],t['source_index'][ix]);np.testing.assert_array_equal(ps['weight'][lo:hi],t['weight'][ix])
            eligible=np.zeros(len(ix),bool)
            if sid>=0 and ps['proxy_visible'][j] and t['sample_eligible'][sid]:eligible=np.isfinite(t['depth'][ix])&(np.abs(t['depth'][ix]-t['proxy_depth'][sid])<=m['contributor_proxy_z_tolerance'])
            np.testing.assert_array_equal(eligible,ps['eligible'][lo:hi])
        ck['all_unpruned_anchor_CSR_identity_depth_eligibility_exact']=True
        if item['role']=='exposed_unit004_build':
            folder=Path(item['baseline']).parent;row=json.loads((folder/'EVALUATION.json').read_text())
            intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4
            for arm in ARMS:
                edited=read_npz(folder/('tint_'+arm+'.npz'))
                assert metrics(f['rgb'],edited['rgb'],intent,f['contribution'],p)==row['arms'][arm]
            ck['previous_actual_four_arm_source_RGB_metrics_exact']=True
        score,_,diag=accumulate(n,t,t['proxy_region'],t['proxy_depth'],t['sample_eligible'],t['sampling_weight'],m['contributor_proxy_z_tolerance'])
        blocks.append(dict(camera_key=json.dumps(c['extrinsic']),source_sha256=s['source']['sha256'],source_index=fp['source_index'],score=score))
        total,acc=aggregate_path(n,ps);totals.append(total);accepted.append(acc);footprints.append(fp['mass'])
        np.testing.assert_allclose(fp['mass'][:,1:4].sum(1),fp['mass'][:,0],rtol=1e-12,atol=1e-10)
        assert abs(fp['mass'][:,0].sum()-f['alpha'].sum(dtype=float))<.001
        checks[c['view']]=dict(trace=ck,membership_mass=diag)
        if item['role']=='original_build':
            folder=out/c['view'];folder.mkdir();shutil.copyfile(item['baseline'],folder/'baseline.npz')
        print('AUDIT',scene,c['view'],ck['events'],flush=True)
    pv=combine_evidence(blocks,n,s['source']['sha256']);tp=np.stack(totals);ap=np.stack(accepted);fpv=np.stack(footprints)
    prior=resolve(pv[:4],m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in prior.items():np.testing.assert_array_equal(v,old[k])
    priorpath=resolve_path(tp[:4],ap[:4],old)
    for k,v in priorpath.items():np.testing.assert_array_equal(v,oldpath[k])
    priorfp=resolve_footprint(fpv[:4],oldpath)
    for k,v in priorfp.items():np.testing.assert_array_equal(v,oldfp[k])
    binding=resolve(pv,m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    save_binding(out/'SOURCE_BINDING.npz',dict(binding,per_view_score=pv),dict(source_sha256=s['source']['sha256'],source_count=n,
        protocol_sha256=sha(unit/'PROTOCOL.json'),asset_hashes=s['asset_hashes'],build_cameras=[x['camera'] for x in s['evidence_sources']],
        region_names=meta['regions'],method='unchanged original alpha*T + depth/UNKNOWN gates, expanded explicit views',confidence_scope=p['scientific_scope']))
    back,_=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    for k,v in binding.items():np.testing.assert_array_equal(v,back[k])
    pb=resolve_path(tp,ap,binding);q=resolve_footprint(fpv,pb)
    np.savez_compressed(out/'PATH_BINDING.npz',**pb,source_sha256=np.array(s['source']['sha256']))
    np.savez_compressed(out/'FOOTPRINT_BINDING.npz',**q,source_sha256=np.array(s['source']['sha256']))
    distance,_=cKDTree(paths['points'].mean(1)).query(a['means'],workers=1);count=int((q['strength']>0).sum())
    spatial=np.zeros(n);spatial[np.argsort(distance,kind='stable')[:count]]=1.
    shuffled=q['strength'].copy();rng=np.random.default_rng(1729)
    observed=np.flatnonzero(binding['exposure']>0);ordered=observed[np.argsort(binding['exposure'][observed],kind='stable')]
    for group in np.array_split(ordered,10):shuffled[group]=q['strength'][rng.permutation(group)]
    candidates=dict(specific=q['strength'],previous_path=oldfp['strength'],nearest_path=spatial,shuffled=shuffled)
    np.savez_compressed(out/'CANDIDATES.npz',source_index=np.arange(n),source_sha256=np.array(s['source']['sha256']),nearest_distance=distance,**candidates)
    assert (q['strength'][binding['unknown']]==0).all()
    transition=transition_counts(old,binding)
    np.savez_compressed(out/'M1_TRANSITIONS.npz',source_index=np.arange(n),old_unknown=old['unknown'],new_unknown=binding['unknown'],old_region=old['region_id'],new_region=binding['region_id'],old_exposure=old['exposure'],new_exposure=binding['exposure'])
    js(out/'BUILD_AUDIT.json',dict(utc=now(),checks=checks,previous_all_rows_reconstructed=True,save_load_exact=True,
        M1_transition=transition,new_region_counts={str(k):int((binding['region_id']==k).sum()) for k in range(6)},
        footprint_counts={k:int((v>0).sum()) for k,v in candidates.items()},
        new_footprint_reasons=dict(zip(*np.unique(q['reason'],return_counts=True))),original_array_hashes=arrays_hash(a)))
    print('EXPANDED',scene,transition,'selected',count,'old',int((oldfp['strength']>0).sum()),flush=True)


def budget(unit,scene,index):
    # Reuse validated actual-render matcher with a narrowly substituted camera list.
    real_load=footprint_run.load
    def protocol(u):
        p=load(u);p['scenes'][scene]=dict(p['scenes'][scene],cameras=p['scenes'][scene]['budget_cameras']);return p
    footprint_run.load=protocol
    try:footprint_run.budget(unit,scene,index)
    finally:footprint_run.load=real_load


def match(unit,scene):
    real_load=footprint_run.load
    def protocol(u):
        p=load(u);p['scenes'][scene]=dict(p['scenes'][scene],cameras=p['scenes'][scene]['budget_cameras']);return p
    footprint_run.load=protocol
    try:footprint_run.match(unit,scene)
    finally:footprint_run.load=real_load
    out=unit/'results'/scene
    js(out/'BINDING_LOCK.json',dict(utc=now(),files={name:sha(out/name) for name in FILES},scope='fixed before fresh evaluation'))


def evaluate(unit,scene,index):
    out=unit/'results'/scene
    for name,h in json.loads((out/'BINDING_LOCK.json').read_text())['files'].items():assert sha(out/name)==h
    transfer_run.evaluate(unit,scene,index)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);ap.add_argument('--stage',choices=['freeze','build','budget','match','evaluate'],required=True)
    ap.add_argument('--scene',choices=['chair','lego']);ap.add_argument('--index',type=int,default=0);args=ap.parse_args();unit=output_guard(args.unit)
    if args.stage=='freeze':freeze(unit)
    elif args.stage in ('build','match'):globals()[args.stage](unit,args.scene)
    else:globals()[args.stage](unit,args.scene,args.index)
