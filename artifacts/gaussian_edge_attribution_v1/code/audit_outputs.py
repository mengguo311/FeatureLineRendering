"""Independent source-F arithmetic and original alpha*T projection validation.

Import no production attribution/evidence module.  Evidence values themselves are
provided by the separately sealed implementation; this check independently
recomputes their lifting, complete-grid denominators and balancing from raw F.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from verify import atomic_json,sha256,verify_seal,validate_camera,reference_id_statistics,reference_projection

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/gaussian_edge_attribution_v1'
OUT=ROOT/'out/gaussian_edge_attribution_v1'
CLASSES=('color','geometry','outline','union')


def _compare(actual,expected,atol=2e-5,rtol=3e-6):
    a=np.asarray(actual,dtype=np.float64);b=np.asarray(expected,dtype=np.float64)
    return {'ok':bool(np.allclose(a,b,atol=atol,rtol=rtol)),'max_absolute_error':float(np.max(np.abs(a-b),initial=0)),
            'atol':atol,'rtol':rtol,'count':int(a.size)}


def audit_scene(scene,f_only=False):
    base=OUT/scene; assets=base/'assets'
    # This mandatory validation precedes even opening a C projection NPZ.
    asset_check=verify_seal(assets/'ASSET_SEAL.json')
    asset_files_before={p.name:sha256(p) for p in assets.iterdir() if p.is_file()}
    frozen_inputs=json.loads((ART/'INPUTS_FROZEN.json').read_text())
    inputs=frozen_inputs['scenes'][scene]
    score=dict(np.load(assets/'scores.npz',allow_pickle=False));selection=dict(np.load(assets/'selection.npz',allow_pickle=False))
    n=len(score['eligible']);rng=np.random.default_rng(1729)
    known=np.flatnonzero(score['eligible']);unknown=np.flatnonzero(score['unknown'])
    sample=np.concatenate([rng.choice(known,min(32,len(known)),replace=False),rng.choice(unknown,min(16,len(unknown)),replace=False)])
    checks={}; f_details={}; f_num=[]; f_den=[]; f_mass=[]
    checks['all_original_IDs_preserved']=np.array_equal(score['original_ids'],np.arange(n))
    checks['unknown_is_zero_F_cached_visibility']=np.array_equal(score['unknown'],score['raw_denominator']==0)
    checks['eligibility_matches_fixed_rule']=np.array_equal(score['eligible'],(score['raw_denominator']>=1.)&(score['support_view_count']>=2))
    eligible_ids=np.flatnonzero(score['eligible']);bins=np.full(n,-1,dtype=np.int32)
    for count in np.unique(score['support_view_count'][eligible_ids]):
        subset=eligible_ids[score['support_view_count'][eligible_ids]==count]
        order=subset[np.lexsort((subset,score['raw_denominator'][subset]))]
        bins[order]=int(count)*10+np.minimum(np.arange(len(order))*10//max(len(order),1),9)
    for key,ids in selection.items():
        ids=np.asarray(ids);checks['selection_valid/'+key]=bool(ids.dtype.kind in 'iu' and len(np.unique(ids))==len(ids) and np.all(ids>=0) and np.all(ids<n))
        arm,cls,pct=key.rsplit('_',2);pct=int(pct)
        if arm in ('baseline','enhanced'):
            order=eligible_ids[np.lexsort((eligible_ids,-score[arm+'_'+cls][eligible_ids]))]
            expected=order[:int(np.ceil(len(order)*pct/100))]
            checks['selection_fixed_ranking/'+key]=np.array_equal(ids,expected)
        elif arm=='random':
            selected=selection[f'enhanced_union_{pct:02d}']
            checks['random_count_and_visibility_strata/'+key]=len(ids)==len(selected) and np.array_equal(np.bincount(bins[ids],minlength=90),np.bincount(bins[selected],minlength=90))

    for frame in inputs['frames']:
        key=frame['key']
        if not key.startswith('F_'):continue
        verify_seal(base/'F'/key/'SEAL.json')
        if sha256(frame['raw_path'])!=frame['raw_sha256']:raise ValueError('F raw input hash changed')
        raw=dict(np.load(frame['raw_path'],allow_pickle=False))
        ev=dict(np.load(base/'F'/key/'evidence.npz',allow_pickle=False))
        stats=dict(np.load(base/'F'/key/'statistics.npz',allow_pickle=False))
        stats.update(json.loads((base/'F'/key/'statistics.json').read_text()))
        mass=float(np.asarray(raw['topk_w'],np.float64).sum())
        r_by_class={c:reference_id_statistics(raw['topk_id'],raw['topk_w'],ev[c],sample) for c in CLASSES}
        denom=r_by_class['union']['denominator'];num=np.stack([r_by_class[c]['numerator'] for c in CLASSES],axis=-1)
        detail={'denominator':_compare(stats['denominator'][sample],denom),'numerator':_compare(stats['numerator'][sample],num)}
        mass_key='raw_cached_mass' if 'raw_cached_mass' in stats else 'view_mass'
        if mass_key in stats:detail['view_mass']=_compare(stats[mass_key],mass,atol=.1)
        negative_key='soft_nonedge_mass' if 'soft_nonedge_mass' in stats else 'negative_numerator'
        if negative_key in stats:detail['soft_visible_nonevidence']=_compare(stats[negative_key][sample],denom[:,None]-num)
        if 'side_numerator' in stats:
            side=stats['side_numerator']; detail['side_bounded_by_whole_visibility']={'ok':bool(np.all(side>=-1e-6) and np.all(side<=stats['denominator'][:,None]+2e-5))}
        if 'positive_mass' in stats and 'nonedge_mass' in stats:
            detail['positive_plus_visible_nonevidence_equals_visibility']=_compare(stats['positive_mass'][sample]+stats['nonedge_mass'][sample],np.broadcast_to(denom[:,None],num.shape))
        for name,value in detail.items():checks[key+'/'+name]=value['ok']
        f_details[key]=detail;f_num.append(num);f_den.append(denom);f_mass.append(mass)
    f_num=np.asarray(f_num);f_den=np.asarray(f_den);f_mass=np.asarray(f_mass)
    balanced_num=(f_num/f_mass[:,None,None]).sum(axis=0);balanced_den=(f_den/f_mass[:,None]).sum(axis=0)
    balanced=np.divide(balanced_num,balanced_den[:,None],out=np.zeros_like(balanced_num),where=balanced_den[:,None]>0)
    aggregate={c:_compare(score['baseline_'+c][sample],balanced[:,j]) for j,c in enumerate(CLASSES)}
    for c,detail in aggregate.items():checks['aggregate/'+c]=detail['ok']
    if 'raw_denominator' in score:
        aggregate['raw_denominator']=_compare(score['raw_denominator'][sample],f_den.sum(axis=0));checks['aggregate/raw_denominator']=aggregate['raw_denominator']['ok']
    if f_only:
        result={'scene':scene,'ok':all(checks.values()),'checks':checks,'failed':[k for k,v in checks.items() if not v],
                'sample_original_ids':sample.tolist(),'sample_eligible_count':min(32,len(known)),'sample_unknown_count':min(16,len(unknown)),
                'F_source_recompute':f_details,'aggregate_recompute':aggregate,'asset_seal_sha256':asset_check['seal_sha256'],
                'scope':'Source F-only independent raw weight lifting; independent evidence extraction is not duplicated.'}
        atomic_json(base/'F_INDEPENDENT_VALIDATION.json',result)
        return result
    projection_details={};panels={};c_pixel_checks={};camera_hashes=[]
    baseline=score.get('projection_baseline_union',score['baseline_union']*score['eligible'])
    enhanced=score.get('projection_enhanced_union',score['enhanced_union']*score['eligible'])
    selected=np.zeros(n);selected[selection['enhanced_union_10']]=1.
    for frame in inputs['frames']:
        key=frame['key']; validate_camera(frame['camera']);camera_hashes.append(frame['camera_hash'])
        folder=base/'frames'/key
        sealed=verify_seal(folder/'SEAL.json')
        frame_seal=json.loads((folder/'SEAL.json').read_text())
        checks[key+'/asset_namespace']=frame_seal['context']['asset_seal_sha256']==asset_check['seal_sha256']
        checks[key+'/camera_identity']=frame_seal['context']['camera_hash']==frame['camera_hash']
        panel=base/'panels'/(key+'.jpg');class_panel=base/'classes_tiers'/(key+'.jpg')
        with Image.open(panel) as im: psize=im.size
        with Image.open(class_panel) as im: csize=im.size
        panels[key]={'panel_dimensions':psize,'classes_dimensions':csize,'panel_sha256':sha256(panel),'class_sha256':sha256(class_panel)}
        checks[key+'/full_frame_panel']=psize==(4000,936)
        projection=dict(np.load(folder/'projection.npz',allow_pickle=False))
        detail={'finite_all_arrays':all(np.isfinite(v).all() for v in projection.values() if np.asarray(v).dtype.kind in 'fiu'),
                'native800':all(np.asarray(projection[k]).shape==(800,800) for k in ('alpha','baseline_P','two_sided_P','selected_Q_10'))}
        for field in ('baseline_P','two_sided_P','selected_Q_10'):
            detail[field+'_bounded_by_original_alpha']=bool(np.all(projection[field]>=-1e-6) and np.all(projection[field]<=projection['alpha']+3e-5))
        projection_details[key]=detail
        for name,ok in detail.items():checks[key+'/'+name]=ok
        if key.startswith('C_'):
            if sha256(frame['raw_path'])!=frame['raw_sha256']:raise ValueError('C raw input hash changed')
            raw=dict(np.load(frame['raw_path'],allow_pickle=False));h,w=raw['alpha'].shape
            random_flat=rng.choice(h*w,min(512,h*w),replace=False)
            q=projection.get('top4_selected_Q_10',projection['selected_Q_10']).ravel()
            support_flat=np.argsort(q,kind='stable')[-128:]
            flat=np.unique(np.concatenate([random_flat,support_flat]));yy,xx=np.unravel_index(flat,(h,w))
            ids=raw['topk_id'][yy,xx];weights=raw['topk_w'][yy,xx]
            cd={}
            for name,field in (('baseline_P',baseline),('two_sided_P',enhanced),('selected_Q_10',selected)):
                expected=reference_projection(ids,weights,field);stored='top4_'+name if 'top4_'+name in projection else name
                cd[stored]=_compare(projection[stored][yy,xx],expected,atol=3e-6,rtol=1e-6)
                checks[key+'/'+stored+'_sample_recompute']=cd[stored]['ok']
                if stored!=name:
                    cd[name+'_full_at_least_top4']={'ok':bool(np.all(projection[name][yy,xx]+3e-5>=expected)),
                        'max_deficit':float(np.max(expected-projection[name][yy,xx],initial=0))}
                    checks[key+'/'+name+'_full_at_least_top4']=cd[name+'_full_at_least_top4']['ok']
            cd['sample_pixel_yx']=np.stack([yy,xx],axis=-1).tolist();cd['random_pixel_count']=len(random_flat);cd['strong_selected_pixel_count']=len(support_flat)
            c_pixel_checks[key]=cd
    # Duplicated endpoint cameras across C and arc are expected; only arc33 must differ.
    checks['pose_count_49']=len(panels)==49
    for control_path,record in frozen_inputs.get('root_git_control_snapshot',{}).items():
        checks['protected_root_git_unchanged/'+control_path]=sha256(control_path)==record['sha256'] and Path(control_path).stat().st_mtime_ns==record['mtime_ns']
    checks['arc_camera_count_33_distinct']=len({f['camera_hash'] for f in inputs['frames'] if f['key'].startswith('arc0_')})==33
    read_events=[json.loads(line) for line in (OUT/'READ_EVENTS.jsonl').read_text().splitlines()]
    eval_events=[e for e in read_events if e['scene']==scene and not e['key'].startswith('F_')]
    seal_created=json.loads((assets/'ASSET_SEAL.json').read_text())['created_utc']
    checks['every_C_arc_read_records_same_F_asset']=bool(eval_events) and all(e.get('asset_seal_sha256')==asset_check['seal_sha256'] for e in eval_events)
    checks['first_C_arc_read_after_F_seal']=bool(eval_events) and min(e['utc'] for e in eval_events)>seal_created
    asset_files_after={p.name:sha256(p) for p in assets.iterdir() if p.is_file()}
    checks['asset_hash_unchanged_after_C_audit']=asset_files_before==asset_files_after
    result={'scene':scene,'ok':all(checks.values()),'checks':checks,'failed':[k for k,v in checks.items() if not v],
            'gaussian_count':n,'sample_original_ids':sample.tolist(),'sample_eligible_count':min(32,len(known)),'sample_unknown_count':min(16,len(unknown)),
            'F_source_recompute':f_details,'aggregate_recompute':aggregate,'C_pixel_recompute':c_pixel_checks,
            'projection_checks':projection_details,'panels':panels,'asset_seal_sha256':asset_check['seal_sha256'],
            'asset_hashes_before':asset_files_before,'asset_hashes_after':asset_files_after,
            'asset_sealed_utc':seal_created,'first_C_arc_read_utc':min(e['utc'] for e in eval_events) if eval_events else None,
            'scope':'Independent CPU summation from source F raw weights and sealed evidence; independent C top4 arithmetic plus full>=top4 bounds. Evidence extraction and full CUDA traversal not independently reimplemented. No TEST or mesh read.',
            'actual_pose_count':len(panels),'requested_pose_count':49}
    atomic_json(base/'INDEPENDENT_VALIDATION.json',result)
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('scene',choices=('mic','materials'));ap.add_argument('--f-only',action='store_true');a=ap.parse_args()
    result=audit_scene(a.scene,f_only=a.f_only);print(json.dumps({k:result[k] for k in ('scene','ok','failed','actual_pose_count','requested_pose_count') if k in result},indent=2))
    if not result['ok']:raise SystemExit(1)
