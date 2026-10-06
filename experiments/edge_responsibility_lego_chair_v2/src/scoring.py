"""Evidence-only ablation first; fixed-evidence score comparison second."""
import json,time
from pathlib import Path
import numpy as np
import torch
from runtime import ROOT,ART,OUT,guard,event,sha,atomic_json
from adapter import render,alpha,support,numpy_image,make_camera,effective_colors,contribution
from evidence import signed_map,sample_band
from calibration import identity

def projected_area(m,camera):
    """Projected covariance ellipse proxy, including rotation and native .3 floor."""
    from utils.general_utils import build_rotation
    with torch.no_grad():
        xyz=m.get_xyz;w=camera.world_view_transform.T
        q=xyz@w[:3,:3].T+w[:3,3]
        r=build_rotation(m.get_rotation)*m.get_scaling[:,None,:]
        cam_r=w[:3,:3][None]@r
        fx=camera.image_width/(2*np.tan(camera.FoVx/2));fy=camera.image_height/(2*np.tan(camera.FoVy/2))
        z=q[:,2].clamp_min(.001);j=torch.zeros((len(xyz),2,3),device='cuda')
        j[:,0,0]=fx/z;j[:,0,2]=-fx*q[:,0]/z.square()
        j[:,1,1]=fy/z;j[:,1,2]=-fy*q[:,1]/z.square()
        r2=j@cam_r;cov=r2@r2.transpose(1,2)
        cov[:,0,0]+=.3;cov[:,1,1]+=.3
        area=np.pi*(cov[:,0,0]*cov[:,1,1]-cov[:,0,1].square()).clamp_min(0).sqrt()
    return area.cpu().numpy().astype(np.float64)

def match_random(ids,total,area,vis,seed):
    """Exact count with joint visibility/log visible-mass/projected-area strata."""
    ids=np.asarray(ids,int);rng=np.random.default_rng(seed)
    massbin=np.clip(np.floor(np.log2(total+1e-8)).astype(int),-16,16)
    areabin=np.clip(np.floor(np.log2(area+1e-8)).astype(int),-16,16)
    strata=(vis.astype(int)*33+(massbin+16))*33+(areabin+16)
    selected=[];fallback=0
    for st in np.unique(strata[ids]):
        k=int((strata[ids]==st).sum());pool=np.flatnonzero((strata==st)&(total>.001))
        if len(pool)<k:
            pool=np.flatnonzero(strata==st);fallback+=k
        selected.extend(rng.choice(pool,k,replace=False).tolist())
    random=np.sort(np.asarray(selected,int))
    return random,dict(exact_count=len(random)==len(ids),joint_strata_equal=bool(np.array_equal(np.sort(strata[random]),np.sort(strata[ids]))),
            fallback_rows=fallback,visible_mass_sum_selected=float(total[ids].sum()),visible_mass_sum_random=float(total[random].sum()),
            projected_area_sum_selected=float(area[ids].sum()),projected_area_sum_random=float(area[random].sum()),
            projected_area_is_covariance_proxy=True,random_can_overlap_selected=True)

def run(scene,m,data,cfg):
    n=len(m.get_xyz);total=np.zeros(n);vis=np.zeros(n,int)
    scores={k:np.zeros(n) for k in ['old_broad','old_trusted_arc','old_trusted_equal','absolute','signed','signed_absolute','negative']}
    masses={k:np.zeros(n) for k in ['broad','trusted_arc','trusted_equal','band2','band4']}
    cache={};identities=[];per=[];area=np.zeros(n);t=time.perf_counter()
    for v in data['views']:
        if v['entry']['role']!='edit-train':continue
        key=v['entry']['key'];guard(f'{scene}/score/{key}')
        with np.load(ROOT/v['maps_path']) as z:maps={k:z[k] for k in z.files}
        c=make_camera(v['entry']['camera'])
        with torch.no_grad():b0=numpy_image(render(m,c));a0=alpha(m,c).cpu().numpy()
        mass=support(m,c,[np.ones(a0.shape,np.float32),maps['broad'],maps['trusted']]).astype(np.float64)
        other=support(m,c,[maps['trusted_equal'],maps['band2'],maps['band4']]).astype(np.float64)
        own=mass[:,0];density=own/a0.size+1e-8
        total+=own;vis+=own>.001;area+=projected_area(m,c)/8
        scores['old_broad']+=mass[:,1]/density
        scores['old_trusted_arc']+=mass[:,2]/density
        scores['old_trusted_equal']+=other[:,0]/density
        masses['broad']+=mass[:,1];masses['trusted_arc']+=mass[:,2];masses['trusted_equal']+=other[:,0]
        masses['band2']+=other[:,1];masses['band4']+=other[:,2];scores['absolute']+=mass[:,2]
        samples=v['reference']['samples'];raw_colors=effective_colors(m,c).detach().cpu().numpy().astype(np.float64)
        sample_cache={}
        # Medium batches of three signed maps; N x 3 adjoint only, never N x H x W.
        for start in range(0,len(samples),3):
            batch=samples[start:start+3];sm=[signed_map(s,a0.shape) for s in batch]
            dweights=support(m,c,sm).astype(np.float64)
            from evaluation import centered_identity
            for j,s in enumerate(batch):
                u=np.asarray(s.get('u') or [1,0,0]);dtbg=float((sm[j]*(1-a0)).sum(dtype=np.float64))
                terms,bg,wi=centered_identity(dweights[:,j],raw_colors,dtbg,np.ones(3),u,np.array(s['c_star']))
                e=float((b0*sm[j][...,None]).sum((0,1))@u);summ=float(terms.sum()+bg);ab=float(np.abs(terms).sum())
                ids=np.argsort(-np.abs(terms),kind='stable')[:64]
                ident=dict(sample_id=s['id'],native_E=e,signed_sum=summ,background_term=bg,delta_T_bg=dtbg,
                     reconstruction_abs_residual=abs(e-summ),total_weight_identity_residual=wi,
                     primitive_signed_sum=float(terms.sum()),absolute_sum=ab,positive_sum=float(terms[terms>0].sum()),negative_sum=float(terms[terms<0].sum()),
                     cancellation=1-abs(float(terms.sum()))/max(ab,1e-20),c_star=s['c_star'],u=u.tolist(),
                     top_absolute_rows=ids.tolist(),top_rows_signed_terms=terms[ids].tolist(),
                     top_absolute_terms_are_not_accepted_as_good_edges=True)
                identities.append(ident)
                if s.get('allow_rgb_score',True):
                    scores['signed']+=terms/max(len(samples),1);scores['signed_absolute']+=np.abs(terms)/max(len(samples),1)
                    scores['negative']+=np.minimum(terms,0)/max(len(samples),1)
                sp=OUT/'score_cache'/scene/f'{key}_{start+j}.npz';sp.parent.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(sp,dw=dweights[:,j].astype(np.float32),terms=terms.astype(np.float32))
                sample_cache[s['id']]=str(sp.relative_to(ROOT))
        bp=OUT/'native_baselines'/scene/f'{key}.npz';bp.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(bp,rgb=b0.astype(np.float32),alpha=a0,own=own.astype(np.float32))
        from media import save_png
        save_png(ART/'media'/scene/key/'baseline_native.png',b0)
        cache[key]=dict(baseline_path=str(bp.relative_to(ROOT)),sample_cache=sample_cache)
        per.append(dict(view=key,broad_nonzero_fraction=v['reference']['metadata']['broad_nonzero_area_fraction'],
                  broad_weighted_mass=float(maps['broad'].sum()),trusted_weighted_mass=float(maps['trusted'].sum()),
                  trusted_nonzero_pixels=int((maps['trusted']>0).sum()),classes=v['reference']['metadata']['classes']))
        event(f'{scene}/score/{key}','COMPLETE',samples=len(samples))
    factor=np.sqrt(vis/8)/8
    for name in ['old_broad','old_trusted_arc','old_trusted_equal']:scores[name]*=factor
    k=min(cfg['rank_reference_cap'],int(np.ceil(n*cfg['rank_reference_fraction'])))
    sets={}
    for name in ['old_broad','old_trusted_arc','old_trusted_equal','absolute','signed']:
        score=scores[name].copy();score[total<.1]=-np.inf
        sets[name]=np.sort(np.argsort(-score,kind='stable')[:k])
    random,matched=match_random(sets['signed'],total,area,vis,cfg['seed']);sets['matched_random']=random
    metrics={}
    for name,ids in sets.items():
        metrics[name]=dict(count=len(ids),rank_reference_only=True,
                narrow2_recall=float(masses['band2'][ids].sum()/max(masses['band2'].sum(),1e-20)),
                narrow4_recall=float(masses['band4'][ids].sum()/max(masses['band4'].sum(),1e-20)),
                narrow2_selected_mass_concentration=float(masses['band2'][ids].sum()/max(total[ids].sum(),1e-20)),
                narrow4_selected_mass_concentration=float(masses['band4'][ids].sum()/max(total[ids].sum(),1e-20)),
                selected_visible_mass=float(total[ids].sum()),selected_positive_signed_sum=float(np.maximum(scores['signed'][ids],0).sum()),
                selected_negative_signed_sum=float(scores['negative'][ids].sum()))
    path=OUT/'score_cache'/scene/'aggregate.npz'
    np.savez_compressed(path,total=total,vis=vis,area=area,**scores,**{'mass_'+k:v for k,v in masses.items()},**{'ids_'+k:v for k,v in sets.items()})
    valid_identities=all(r['reconstruction_abs_residual']<cfg['identity_abs_tolerance'] and abs(r['total_weight_identity_residual'])<cfg['identity_weight_tolerance'] for r in identities)
    record=dict(scene=scene,model_sha256=data['model_sha256'],count=n,budget_reference=k,identity_pass=valid_identities,
          independent_truth='reference RGB/AA fixed before ranking; 2px and 4px evaluation independent of evidence normalization',
          sequence=['evidence only, segment equal retained: old_broad vs old_trusted_equal','weighting only: old_trusted_equal vs old_trusted_arc','fixed trusted_arc: old relative vs absolute vs signed vs matched random; bounded group response in interventions'],
          evidence_only_ablation={name:metrics[name] for name in ['old_broad','old_trusted_equal']},
          segment_equal_vs_arclength_ablation={name:metrics[name] for name in ['old_trusted_equal','old_trusted_arc']},
          fixed_evidence_ranking_reference={name:metrics[name] for name in ['old_trusted_arc','absolute','signed','matched_random']},
          signed_accounting=identities,per_train_view=per,random_matching=matched,cache=cache,
          aggregate_path=str(path.relative_to(ROOT)),aggregate_sha256=sha(path),selection_search_seconds=time.perf_counter()-t,
          outlines_in_main_evidence=True,not_causal_identification=True,
          signed_definition='sum of centered signed normal terms; positive ranking, negative terms/cancellation retained separately',
          empty_acceptance_supported=True,rank_reference_does_not_fill_acceptance=True)
    for name,ids in sets.items():
        atomic_json(ART/'selection_ids'/scene/f'{name}.json',dict(model_sha256=data['model_sha256'],original_rows=ids.tolist(),count=len(ids),reference_only=True))
    return record
