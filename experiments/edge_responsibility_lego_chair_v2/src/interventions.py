"""Matched kernel groups, full model +/- probes and independent response tests."""
import time
import numpy as np
import torch
from runtime import ROOT,ART,OUT,guard,event,atomic_json,sha
from adapter import make_camera,render,alpha,support,numpy_image,perturb,effective_colors,contribution
from evidence import signed_map,sample_band,profile_vector
from scoring import match_random
from evaluation import intervention_metrics,features,rank_correlation,paired_bootstrap
from media import scene_view,save_png

def flat_mask(ref,shape):
    mask=np.zeros(shape,np.float32)
    for f in ref['flat']:
        x0,y0,x1,y1=f['roi'];mask[y0:y1,x0:x1]=1
    return mask

def probe(m,camera,ids,param,delta,direction,b0,a0,ref,s,band,flat):
    p0=profile_vector(b0,s,False);records={};profiles={};rendered={}
    for label,amount in [('plus',delta),('minus',-delta),('half_plus',delta/2),('half_minus',-delta/2)]:
        changed_model=perturb(m,ids,param,amount,direction)
        with torch.no_grad():
            im=numpy_image(render(changed_model,camera))
            aa=a0 if param=='dc' else alpha(changed_model,camera).cpu().numpy()
        pp=profile_vector(im,s,False)
        metrics=intervention_metrics(b0,im,a0,aa,ref,s,band,flat,p0,pp)
        metrics['alpha_edge_rms']=float(np.sqrt(((aa-a0)**2*band).sum()/max(band.sum(),1)))
        metrics['alpha_outside_rms']=float(np.sqrt(((aa-a0)**2*(1-band)).sum()/max((1-band).sum(),1)))
        records[label]=metrics;profiles[label]=(pp-p0).tolist();rendered[label]=im
    fd=(np.array(profiles['plus'])-np.array(profiles['minus']))/(2*delta)
    hfd=(np.array(profiles['half_plus'])-np.array(profiles['half_minus']))/delta
    stability=float(np.linalg.norm(fd-hfd)/max(np.linalg.norm(hfd),1e-5))
    return dict(param=param,delta=delta,half_delta=delta/2,direction=list(direction),metrics=records,
                native_profile_deltas=profiles,stability_relative_error=stability,
                finite_probe_whole_model=True,not_subset_render=True),rendered

def build_groups(scene,m,data,score,cfg):
    with np.load(ROOT/score['aggregate_path']) as z:ag={k:z[k] for k in z.files}
    groups=[];train=[v for v in data['views'] if v['entry']['role']=='edit-train'][:4]
    for vi,v in enumerate(train):
        key=v['entry']['key'];guard(f'{scene}/groups/{key}');c=make_camera(v['entry']['camera'])
        with np.load(ROOT/v['maps_path']) as z:maps={k:z[k] for k in z.files}
        with np.load(ROOT/score['cache'][key]['baseline_path']) as z:own=z['own'].astype(float)
        samples=v['reference']['samples']
        selected_samples=([s for s in samples if s['class_name']=='outline'][:2]+[s for s in samples if s['class_name']=='clear_color_transition'][:1])[:cfg['groups_per_view']]
        flats=v['reference']['flat'][:1]
        for s0 in selected_samples+flats:
            s=dict(s0)
            if s['class_name']=='flat_negative':
                pp=profile_vector(maps['rgb'],s,False);s.update(u=[1,0,0],c_star=((pp[-8:].mean(0)+pp[:8].mean(0))/2).tolist())
                dw=support(m,c,[signed_map(s,maps['aa'].shape)])[:,0]
                col=effective_colors(m,c).detach().cpu().numpy();terms=dw*((col-np.array(s['c_star']))@np.array(s['u']))
            else:
                with np.load(ROOT/score['cache'][key]['sample_cache'][s['id']]) as z:dw=z['dw'];terms=z['terms']
            band=sample_band(s,maps['aa'].shape,4);narrow=support(m,c,[band])[:,0].astype(float)
            pool=np.flatnonzero((narrow>.001)&(own>.001));k=min(cfg['group_budget'],len(pool))
            if k==0:continue
            arrays={'old_relative':ag['old_trusted_arc'],'absolute':narrow,'signed':terms}
            chosen={name:np.sort(pool[np.argsort(-a[pool],kind='stable')[:k]]) for name,a in arrays.items()}
            random,matching=match_random(chosen['signed'],own,ag['area'],ag['vis'],cfg['seed']+len(groups))
            chosen['matched_random']=random
            for method,ids in chosen.items():
                g=dict(id=f'{scene}_{vi}_{len(groups):03d}_{method}',view_key=key,view_index=vi,sample=s,method=method,
                       rows=ids.tolist(),count=len(ids),model_sha256=data['model_sha256'],target_class=s['class_name'],
                       signed_edge_attribution=float(terms[ids].sum()),absolute_signed_attribution=float(np.abs(terms[ids]).sum()),
                       positive_attribution=float(terms[ids][terms[ids]>0].sum()),negative_attribution=float(terms[ids][terms[ids]<0].sum()),
                       cancellation=1-abs(float(terms[ids].sum()))/max(float(np.abs(terms[ids]).sum()),1e-20),
                       full_visible_mass=float(own[ids].sum()),target_visible_mass=float(narrow[ids].sum()),
                       projected_area_proxy_sum=float(ag['area'][ids].sum()),random_matching=matching,
                       construction_group_semantics='shared reference sample UID support; both sides considered, no object or depth identity assumed',
                       ranking_positive_signed_only=method=='signed',equal_kernel_count_reference=True)
                groups.append(g)
    atomic_json(ART/f'{scene}_GROUP_INPUT_FREEZE.json',dict(scene=scene,groups=groups,configuration=cfg,
                independent_probe_not_yet_evaluated=True,source_score_sha256=sha(ART/'results'/f'{scene}_scores.json')))
    return groups

def training(scene,m,data,score,groups,calibration,cfg):
    lookup={v['entry']['key']:v for v in data['views']};rows=[];t=time.perf_counter()
    for g in groups:
        guard(f'{scene}/construction/{g["id"]}');v=lookup[g['view_key']];c=make_camera(v['entry']['camera']);s=g['sample']
        with np.load(ROOT/v['maps_path']) as z:maps={k:z[k] for k in z.files}
        with np.load(ROOT/score['cache'][g['view_key']]['baseline_path']) as z:b0=z['rgb'].astype(float);a0=z['alpha']
        band=sample_band(s,a0.shape,4);flat=flat_mask(v['reference'],a0.shape)
        probes={}
        for param in ['dc','scale']:
            dr=cfg['construction_'+param+'_direction'];delta=cfg['construction_'+param+'_delta']
            probes[param],_=probe(m,c,g['rows'],param,delta,dr,b0,a0,maps['rgb'],s,band,flat)
        # Three pre-fixed axis probes predict an independent anisotropic scale direction.
        basis=[]
        for axis in range(3):
            dr=np.eye(3)[axis];delta=cfg['construction_scale_delta']
            with torch.no_grad():
                p=numpy_image(render(perturb(m,g['rows'],'scale',delta,dr),c));q=numpy_image(render(perturb(m,g['rows'],'scale',-delta,dr),c))
            basis.append(((profile_vector(p,s,False)-profile_vector(q,s,False))/(2*delta)).tolist())
        action=max(probes[p]['metrics']['plus']['edge_rms'] for p in probes)
        outside=max(probes[p]['metrics']['plus']['outside_rms'] for p in probes)
        flatcost=max(probes[p]['metrics']['plus']['flat_rms'] for p in probes)
        stability=max(probes[p]['stability_relative_error'] for p in probes)
        platform=max(probes[p]['metrics']['plus']['platform_rms'] for p in probes)
        noholes=all(probes[p]['metrics'][sign]['new_coverage_holes']==0 for p in probes for sign in ['plus','minus'])
        alphaaction=probes['scale']['metrics']['plus']['alpha_edge_rms']
        action=max(action,alphaaction) if s['class_name']=='outline' else action
        accept=s['class_name']!='flat_negative' and action>=calibration['absolute_action_minimum'] and outside<=cfg['outside_rms_budget'] and flatcost<=cfg['flat_rms_budget'] and stability<=cfg['stability_relative_tolerance'] and platform<=action*.5 and noholes
        reason='ACCEPT_DIAGNOSTIC_CANDIDATE' if accept else ('no_visible_edge' if s['class_name']=='flat_negative' else 'insufficient_absolute_action' if action<calibration['absolute_action_minimum'] else 'unstable_response' if stability>cfg['stability_relative_tolerance'] else 'outside_or_platform_cost')
        rows.append(dict(**g,construction_probes=probes,scale_axis_profile_derivatives=basis,
                      construction_action=action,construction_outside_cost=outside,construction_flat_cost=flatcost,
                      construction_platform_cost=platform,construction_stability=stability,
                      construction_response_score=max(0,action-outside-flatcost-platform),construction_accepted=accept,reject_reason=reason))
        event(f'{scene}/construction/{g["id"]}','COMPLETE',accepted=accept,reason=reason)
    bysample={}
    for r in rows:bysample.setdefault(r['sample']['id'],[]).append(r)
    choices=[]
    for sid,candidates in bysample.items():
        best=max(candidates,key=lambda r:(r['construction_response_score'],r['id']))
        choices.append(dict(sample_id=sid,selected_group=best['id'],selected_original_method=best['method'],
                      response_score=best['construction_response_score'],accepted=best['construction_accepted'],
                      kernel_count=best['count'],search_candidates=len(candidates),search_not_free=True))
    record=dict(scene=scene,groups=rows,response_choices=choices,seconds=time.perf_counter()-t,
                search_candidate_groups=len(rows),native_render_cost_per_group='8 +/-half color/scale RGB + 4 scale alpha + 6 axis RGB',
                group_input_freeze_sha256=sha(ART/f'{scene}_GROUP_INPUT_FREEZE.json'),
                independent_probe_not_yet_evaluated=True)
    atomic_json(ART/f'{scene}_RESPONSE_SELECTION_FREEZE.json',record)
    return record

def independent(scene,m,data,score,construction,cfg):
    lookup={v['entry']['key']:v for v in data['views']};held=[v for v in data['views'] if v['entry']['role']=='edit-holdout']
    allrows=[];start=time.perf_counter()
    for g in construction['groups']:
        guard(f'{scene}/independent/{g["id"]}');v=lookup[g['view_key']];c=make_camera(v['entry']['camera']);s=g['sample'];ids=g['rows']
        with np.load(ROOT/v['maps_path']) as z:maps={k:z[k] for k in z.files}
        with np.load(ROOT/score['cache'][g['view_key']]['baseline_path']) as z:b0=z['rgb'].astype(float);a0=z['alpha']
        band=sample_band(s,a0.shape,4);flat=flat_mask(v['reference'],a0.shape);results={};predict={}
        for param in ['dc','scale']:
            dr=cfg['independent_'+param+'_direction'];delta=cfg['independent_'+param+'_delta']
            results[param],_=probe(m,c,ids,param,delta,dr,b0,a0,maps['rgb'],s,band,flat)
            if param=='dc':
                with torch.no_grad():
                    raw=effective_colors(m,c,True);feat=torch.zeros_like(raw)
                    feat[ids]=torch.as_tensor(dr,device='cuda')*(raw[ids]>0)
                    dimage=numpy_image(render(m,c,feat,(0,0,0)))
                pred=profile_vector(dimage,s,False)*delta
                method='full-model color adjoint / native SH-clamp derivative; same analytical predictor available to every selector'
            else:
                pred=delta*np.einsum('a,apc->pc',np.array(dr),np.array(g['scale_axis_profile_derivatives']))
                method='three pre-fixed .01 axis central differences; independent anisotropic direction .006'
            actual=np.array(results[param]['native_profile_deltas']['plus'])
            rel=float(np.linalg.norm(pred-actual)/max(np.linalg.norm(actual),cfg['prediction_absolute_floor']))
            absolute=float(np.sqrt(np.mean((pred-actual)**2)))
            u=np.array(s.get('u') or [1,0,0]);ep=lambda p:float((p[-10:].mean(0)-p[:10].mean(0))@u)
            predict[param]=dict(predicted_native_profile_delta=pred.tolist(),actual_native_profile_delta=actual.tolist(),
                    predicted_signed_delta=ep(pred),actual_signed_delta=ep(actual),relative_l2_error=rel,rms_error=absolute,
                    direction_correct=bool(np.sign(ep(pred))==np.sign(ep(actual))) if abs(ep(actual))>cfg['prediction_absolute_floor'] else None,
                    above_absolute_action_floor=results[param]['metrics']['plus']['edge_rms']>=cfg['minimum_action_floor'],
                    predictor=method,predictor_pass=rel<cfg['prediction_relative_tolerance'] or absolute<cfg['prediction_absolute_floor'])
        # A second camera tests the same original-row 3D operation. No overlap->object assumption.
        h=held[g['view_index']%len(held)];hc=make_camera(h['entry']['camera'])
        with np.load(ROOT/h['maps_path']) as z:hm={k:z[k] for k in z.files}
        with torch.no_grad():
            hb=numpy_image(render(m,hc));ha=alpha(m,hc).cpu().numpy()
            hp=numpy_image(render(perturb(m,ids,'scale',cfg['independent_scale_delta'],cfg['independent_scale_direction']),hc))
            hap=alpha(perturb(m,ids,'scale',cfg['independent_scale_delta'],cfg['independent_scale_direction']),hc).cpu().numpy()
            cm=contribution(m,hc,ids).cpu().numpy()
        hd=hp-hb;out=1-hm['band4']
        cross=dict(view=h['entry']['key'],role='exploratory GS-seen edit-holdout',selected_visible_mass=float(cm.sum()),
              outside_rms=float(np.sqrt((hd**2*out[...,None]).sum()/max(out.sum()*3,1))),
              target_rms=float(np.sqrt((hd**2*hm['band4'][...,None]).sum()/max(hm['band4'].sum()*3,1))),
              new_coverage_holes=int(((ha>.95)&(hap<.5)).sum()),outline_binary_changed_pixels=int(((ha>=.5)!=(hap>=.5)).sum()),
              same_3D_UID_operation=True,same_object_or_boundary_correspondence_certified=False,
              no_manual_or_score_derived_boundary_truth=True)
        consistency=cross['outside_rms']<=cfg['outside_rms_budget'] and cross['new_coverage_holes']==0
        stable=all(results[p]['stability_relative_error']<=cfg['stability_relative_tolerance'] for p in results)
        local=all(results[p]['metrics'][sign]['outside_rms']<=cfg['outside_rms_budget'] and results[p]['metrics'][sign]['flat_rms']<=cfg['flat_rms_budget'] and results[p]['metrics'][sign]['new_coverage_holes']==0 for p in results for sign in ['plus','minus'])
        allrows.append(dict(**g,independent_probes=results,prediction=predict,view_consistency=cross,
                           independent_locality_pass=local,independent_stability_pass=stable,cross_view_cost_pass=consistency,
                           diagnostic_validated=g['construction_accepted'] and local and stable and consistency and all(predict[p]['predictor_pass'] for p in predict)))
        event(f'{scene}/independent/{g["id"]}','COMPLETE',local=local,stable=stable)
    selected={r['sample_id']:r['selected_group'] for r in construction['response_choices']};summary={};paired=[]
    targets={r['sample']['id'] for r in allrows if r['target_class']!='flat_negative'}
    for method in ['old_relative','absolute','signed','matched_random','bounded_response']:
        rs=[r for r in allrows if r['target_class']!='flat_negative' and (r['method']==method if method!='bounded_response' else r['id']==selected[r['sample']['id']])]
        quality=[]
        for r in rs:
            act=max(r['independent_probes'][p]['metrics']['plus']['edge_rms'] for p in ['dc','scale'])
            cost=max(r['independent_probes'][p]['metrics']['plus']['outside_rms']+r['independent_probes'][p]['metrics']['plus']['flat_rms']+r['independent_probes'][p]['metrics']['plus']['platform_rms'] for p in ['dc','scale'])
            quality.append(max(0,act-cost))
        summary[method]=dict(groups=len(rs),mean_independent_quality=float(np.mean(quality)) if quality else 0,
                independent_locality_pass_rate=float(np.mean([r['independent_locality_pass'] for r in rs])) if rs else 0,
                mean_prediction_relative_error=float(np.mean([r['prediction'][p]['relative_l2_error'] for r in rs for p in ['dc','scale']])) if rs else None,
                accepted_groups=sum(r['diagnostic_validated'] for r in rs),per_group_quality=quality,
                kernel_count_per_group=cfg['group_budget'],search_candidates=4 if method=='bounded_response' else 1)
    for sid in sorted(targets):
        rows=[r for r in allrows if r['sample']['id']==sid];best=next(r for r in rows if r['id']==selected[sid])
        def quality(r):
            return max(0,max(r['independent_probes'][p]['metrics']['plus']['edge_rms'] for p in ['dc','scale'])-max(r['independent_probes'][p]['metrics']['plus']['outside_rms']+r['independent_probes'][p]['metrics']['plus']['flat_rms']+r['independent_probes'][p]['metrics']['plus']['platform_rms'] for p in ['dc','scale']))
        competitors=[quality(r) for r in rows if r['method'] in ['absolute','matched_random']]
        paired.append(quality(best)-max(competitors))
    ci=paired_bootstrap(paired,cfg['seed'])
    advantage=ci['n']>=8 and ci['ci95'][0]>0
    # Predictive advantage also requires score order to track unseen intervention quality.
    response_rs=[r for r in allrows if r['target_class']!='flat_negative']
    corr=rank_correlation([r['construction_response_score'] for r in response_rs],[max(r['independent_probes'][p]['metrics']['plus']['edge_rms'] for p in ['dc','scale']) for r in response_rs])
    result=dict(scene=scene,groups=allrows,methods=summary,paired_response_vs_best_simple_null=ci,
                construction_score_independent_response_spearman=corr,
                gate2_numeric_advantage_pass=advantage and corr is not None and corr>.3,
                prediction_test_independent_of_ranking_probe=True,response_selection_freeze_sha256=sha(ART/f'{scene}_RESPONSE_SELECTION_FREEZE.json'),
                human_visual_GO='PENDING',semantic_internal_certification='UNCERTIFIED',
                gate3_pass=False,gate3_reason='independent human visual GO and cross-view boundary interpretation pending; costs alone do not certify locality',
                accepted_rows=sorted({row for r in allrows if r['id']==selected[r['sample']['id']] and r['diagnostic_validated'] for row in r['rows']}),
                validation_seconds=time.perf_counter()-start,formal_advantage_claim=False)
    return result

def deliver_media(scene,m,data,score,validation,cfg):
    with np.load(ROOT/score['aggregate_path']) as z:ag={k:z[k] for k in z.files}
    ids=np.asarray(validation['accepted_rows'],int)
    sets={'old_broad':ag['ids_old_broad'],'signed':ag['ids_signed'],'accepted_diagnostic':ids}
    files=[];train=[v for v in data['views'] if v['entry']['role']=='edit-train'][:4]
    atomic_json(ART/'selection_ids'/scene/'accepted_diagnostic.json',dict(model_sha256=data['model_sha256'],original_rows=ids.tolist(),count=len(ids),
                  scientific_gates_pass=False,scope='local diagnostic acceptance; human GO pending'))
    for v in train:
        guard(f'{scene}/media/{v["entry"]["key"]}');c=make_camera(v['entry']['camera'])
        with np.load(ROOT/score['cache'][v['entry']['key']]['baseline_path']) as z:b0=z['rgb'].astype(float)
        with torch.no_grad():
            plus=numpy_image(render(perturb(m,ids,'dc',cfg['independent_dc_delta'],cfg['independent_dc_direction']),c))
            minus=numpy_image(render(perturb(m,ids,'dc',-cfg['independent_dc_delta'],cfg['independent_dc_direction']),c))
        files.append(scene_view(scene,v,m,c,b0,sets,plus,minus,cfg['display_diff_gain'],data['model_sha256']))
    if cfg['render_new_arc33']:
        panels=[]
        for v in data['arc']:
            guard(f'{scene}/arc/{v["key"]}');c=make_camera(v['camera'])
            from adapter import subset
            with torch.no_grad():
                b=numpy_image(render(m,c));s=numpy_image(render(subset(m,ids),c)) if len(ids) else np.ones_like(b)
                cm=contribution(m,c,ids).cpu().numpy()
            p=ART/'media'/scene/'arc33';p.mkdir(parents=True,exist_ok=True)
            save_png(p/f'{v["key"]}_baseline.png',b);save_png(p/f'{v["key"]}_selected_subset.png',s);save_png(p/f'{v["key"]}_selected_contribution.png',cm)
            panels.append((v['key']+' selected subset',s))
        from media import panel_sheet
        panel_sheet(panels,ART/'media'/scene/'arc33_selected_sheet.png',columns=6,size=192)
        atomic_json(ART/'media'/scene/'arc33_SOURCE.json',dict(model_sha256=data['model_sha256'],selected_original_rows=ids.tolist(),count=len(ids),views=data['arc'],
                    role='new native renders of prior visualization cameras, no target image supervision; subset unoccluded diagnostic'))
    return dict(scene=scene,views=len(files),sheets=files,selected_count=len(ids),arc_frames=len(data['arc']) if cfg['render_new_arc33'] else 0,
                native_subset_actual_removal=True,sealed_files=[str(p.relative_to(ROOT)) for p in (ART/'media'/scene).rglob('*') if p.is_file()])
