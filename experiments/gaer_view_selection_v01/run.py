"""Eight independently scored native views, medium sparse batches, atomic unit seals."""
import argparse,gc,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from stage_runtime import ROOT,EXP,ART,OUT,OLD,atomic_json,digest,guard,sha
from binding import backend,scene_io
from freeze import make_freeze,check_protected
from calibrate import calibrate
from selection import silhouette,compare_sides,normalize_scores,select_ids,top_ids,matched_random,jaccard
from native_ops import feature_mass,render_features,render_subset,deletion
from validation import footprint_stats,causal_metrics
from media import save_rgb,sheet,heat,endpoint_overlay,crops,score_histogram

def timed_forward(module,s,model,K=None):
    opts=dict(attribution=True,K=K) if K else {}
    renderer=module.GaussianRasterizer(s)
    guard('native_forward_'+str(K));torch.cuda.reset_peak_memory_stats()
    base=torch.cuda.memory_allocated()
    with torch.no_grad():
        for _ in range(3):r=renderer(**model,**opts)
        times=[];wall=[]
        for _ in range(5):
            a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
            t=time.perf_counter();a.record();r=renderer(**model,**opts);b.record();torch.cuda.synchronize()
            times.append(a.elapsed_time(b));wall.append(1000*(time.perf_counter()-t))
    return r,dict(cuda_forward_ms=times,wall_forward_ms=wall,cuda_median_ms=float(np.median(times)),
        wall_median_ms=float(np.median(wall)),peak_allocated_bytes=torch.cuda.max_memory_allocated(),base_allocated_bytes=base,
        timing_scope='full native forward, 3 warmups/5 event+wall samples; excludes CPU copies, scores and image IO')

def project_centers(model,s):
    xyz=model['means3D'];hom=torch.cat([xyz,torch.ones((len(xyz),1),device='cuda')],1)@s.projmatrix
    ndc=hom[:,:2]/(hom[:,3:4]+1e-7)
    xy=((ndc+1)*torch.tensor([s.image_width,s.image_height],device='cuda')-1)/2
    return xy[:,[1,0]].cpu().numpy()

def quantiles(a):
    return dict(zip(('min','p25','median','p75','p95','p99','max'),map(float,np.percentile(a,[0,25,50,75,95,99,100])))) if len(a) else {}

def unit(name,record,camera,model,modules,freeze,cal):
    key=name+'_'+camera['key'];p=freeze['protocol'];guard(key);tstart=time.perf_counter()
    dst=OUT/'units'/key; seal=ART/'seals'/(key+'.json')
    config=dict(camera=camera,model_sha256=record['model_sha256'],protocol_sha256=freeze['protocol_sha256'],
        source_method_sha256=freeze['source_method_sha256'],calibration_sha256=sha(ART/'results/SYNTHETIC.json'))
    confsha=digest(config)
    if seal.exists():
        receipt=json.loads(seal.read_text())
        if receipt['config_sha256']!=confsha:raise RuntimeError('sealed configuration differs')
        for f,h in receipt['files'].items():
            if sha(ROOT/f)!=h:raise RuntimeError('sealed hash differs: '+f)
        print('SEALED_SKIP',key,flush=True);return json.loads((ART/'results'/(key+'.json')).read_text())
    if dst.exists():raise RuntimeError('unsealed final directory exists; preserve')
    tmp=dst.with_name(key+'.partial_'+str(time.time_ns()));tmp.mkdir()
    m=modules['patched'];s=scene_io.make_settings(m,camera);count=record['count'];timings={}
    baseline,timings['native_stock']=timed_forward(modules['actual'],scene_io.make_settings(modules['actual'],camera),model)
    rgb0=baseline[0].cpu().numpy();baseline_sha=__import__('hashlib').sha256(rgb0.tobytes()).hexdigest()
    del baseline
    on,timings['K8']=timed_forward(m,s,model,8)
    if not np.array_equal(rgb0,on.rgb.cpu().numpy()):raise AssertionError('baseline/debug RGB differs')
    rgbcheck=dict(actual_stock_vs_K8_bitwise_equal=True,baseline_float32_bytes_sha256=baseline_sha)
    oldunit=name+'_r_'+camera['key'].split('_')[1].zfill(3)
    oldrgb=OLD/'out/gaer_attribution_buffer_v01/views'/oldunit/'baseline_rgb.npy'
    if oldrgb.exists():
        rgbcheck['previous_canonical_bitwise_equal']=bool(np.array_equal(np.load(oldrgb),rgb0))
        if not rgbcheck['previous_canonical_bitwise_equal']:raise AssertionError('old canonical RGB differs')
    t=time.perf_counter()
    ids=on.gaussian_ids.cpu().numpy();weights=on.gaussian_weights.cpu().numpy()
    alpha=on.accumulated_alpha.cpu().numpy();full=on.all_contribution_sum.cpu().numpy()
    timings['K8_cpu_copy_ms']=1000*(time.perf_counter()-t)
    if ids.min()< -1 or ids.max()>=count:raise AssertionError('original ID range failed')
    if np.abs(full-alpha).max()>2e-6:raise AssertionError('accepted mass alpha mismatch')
    del on
    t=time.perf_counter();edge,points,normal,sdf=silhouette(alpha,p['alpha_threshold'])
    timings['silhouette_ms']=1000*(time.perf_counter()-t)
    guard(key+'_full_visibility');t=time.perf_counter()
    mass,feature_alpha=feature_mass(m,s,model)
    participation_full,_=feature_mass(m,s,model,edge.astype(np.float32))
    torch.cuda.synchronize();timings['full_mass_and_boundary_feature_gradient_ms']=1000*(time.perf_counter()-t)
    if np.abs(feature_alpha-full).max()>3e-6:raise AssertionError('alpha feature forward differs')
    if abs(float(mass.sum(dtype=np.float64))-float(full.sum(dtype=np.float64)))/max(float(full.sum()),1.)>2e-5:raise AssertionError('global backward mass differs')
    centers=project_centers(model,s)
    comparisons={};scores={};t=time.perf_counter()
    for delta in p['deltas']:
        l1,raw,part,bound=compare_sides(ids,weights,full,points-delta*normal,points+delta*normal,count,batch=p['sparse_batch_edges'])
        ratio=normalize_scores(raw,mass,p['min_visibility_mass'],p['epsilon'])
        comparisons[delta]=(l1,raw,part,bound);scores[delta]=ratio
    timings['CPU_sparse_comparison_all_deltas_ms']=1000*(time.perf_counter()-t)
    l1,raw,part,bound=comparisons[p['main_delta']];ratio=scores[p['main_delta']]
    eligible=(mass>=p['min_visibility_mass'])&(raw>=p['raw_absolute_floor'])
    budgets={};selected_by_method={};footprints={};causal={};subset_images={};contributions={};ids_export={}
    nprimary=min(int(np.ceil(count*p['primary_diagnostic_count_fraction'])),int(eligible.sum()))
    main_ids=top_ids(ratio,eligible,nprimary)
    heldout_ids=top_ids(scores[p['heldout_delta']],eligible,len(main_ids))
    stability=dict(delta1_delta2_jaccard=jaccard(top_ids(scores[1],eligible,len(main_ids)),main_ids),
        delta2_delta4_jaccard=jaccard(main_ids,heldout_ids),direction={})
    for degrees in p['direction_diagnostic_degrees']:
        theta=np.radians(degrees);nrot=np.column_stack([np.cos(theta)*normal[:,0]-np.sin(theta)*normal[:,1],np.sin(theta)*normal[:,0]+np.cos(theta)*normal[:,1]])
        t=time.perf_counter();_,rot_raw,_,_=compare_sides(ids,weights,full,points-2*nrot,points+2*nrot,count,batch=p['sparse_batch_edges'])
        rot_score=normalize_scores(rot_raw,mass,p['min_visibility_mass'],p['epsilon'])
        stability['direction'][str(degrees)]=dict(jaccard=jaccard(main_ids,top_ids(rot_score,eligible,len(main_ids))),CPU_ms=1000*(time.perf_counter()-t))
        np.save(tmp/('score_direction_'+str(degrees)+'.npy'),rot_score)
    ambiguity=float(bound.sum()/max(l1.sum(),1e-12))
    proposed=select_ids(ratio,raw,mass,cal['auto_ratio_floor'],p['raw_absolute_floor'],p['min_visibility_mass'])
    refusal=[]
    if not len(points):refusal.append('NO_EDGE')
    if not len(proposed):refusal.append('NO_ABOVE_INDEPENDENT_NULL_FLOOR')
    if ambiguity>p['auto_max_aggregate_ambiguity_over_observed_L1']:refusal.append('TOPK_L1_AMBIGUITY_TOO_LARGE')
    if stability['delta2_delta4_jaccard']<p['auto_min_delta2_delta4_Jaccard']:refusal.append('HELDOUT_DELTA_UNSTABLE')
    auto=proposed if not refusal else np.empty(0,np.int32)
    ids_export['automatic_candidate_ids']=proposed;ids_export['automatic_accepted_ids']=auto
    automatic=dict(state='REFUSED' if refusal else 'CANDIDATE_ONLY_HUMAN_PENDING',reasons=refusal,
        proposed_count=len(proposed),accepted_count=len(auto),ratio_floor=cal['auto_ratio_floor'],
        primary_display='predeclared 0.5% diagnostic budget; never relabeled automatic success')
    for fraction in p['diagnostic_count_fractions']:
        guard(key+'_budget_'+str(fraction));desired=min(int(np.ceil(count*fraction)),int(eligible.sum()))
        selected=dict(gaer_ratio=top_ids(ratio,eligible,desired),gaer_raw=top_ids(raw,eligible,desired),
            alphaT_participation=top_ids(participation_full,eligible,desired))
        # Baselines use the common evidence-eligible domain; no zero-score padding.
        common=min(map(len,selected.values()))
        selected={k:v[:common] for k,v in selected.items()}
        selected['visibility_matched_random']=matched_random(selected['gaer_ratio'],mass,p['random_seed']+int(camera['metadata_index']),p['random_mass_log_bin_width'])
        stats={};images=[]
        for method,chosen in selected.items():
            suffix=method+'_'+str(fraction);ids_export[suffix+'_ids']=chosen
            selectedrgb=render_subset(m,s,model,chosen)
            contribution=render_features(m,s,model,chosen)
            fs=footprint_stats(contribution,sdf,centers[chosen]);fs['count']=len(chosen)
            fs['summed_full_visibility']=float(mass[chosen].sum(dtype=np.float64))
            fs['mass_vs_feature_map_relative_error']=abs(fs['summed_full_visibility']-fs['full_T_selected_mass'])/max(fs['summed_full_visibility'],1e-12)
            stats[method]=fs;images.append((f'{method} n={len(chosen)} budget={fraction:.3%}',selectedrgb))
            save_rgb(tmp/(suffix+'_selected_only.jpg'),selectedrgb)
            if fraction==p['primary_diagnostic_count_fraction']:
                selected_by_method[method]=chosen;subset_images[method]=selectedrgb;contributions[method]=contribution
                np.save(tmp/(method+'_fullT_contribution.npy'),contribution)
                deleted,deleted_alpha=deletion(m,s,model,chosen)
                causal[method]=causal_metrics(rgb0,deleted,alpha,deleted_alpha,sdf,points,normal)
                causal[method]['selected_count']=len(chosen);causal[method]['summed_full_visibility']=fs['summed_full_visibility']
                np.save(tmp/(method+'_deleted_RGB.npy'),deleted);np.save(tmp/(method+'_deleted_alpha.npy'),deleted_alpha)
                save_rgb(ART/'figures'/(key+'_'+method+'_selected_only.jpg'),selectedrgb)
                save_rgb(tmp/(method+'_deleted.jpg'),deleted)
                save_rgb(tmp/(method+'_fullT_contribution.jpg'),1-contribution)
                diff=np.sqrt(((rgb0-deleted)**2).mean(0))
                sheet(ART/'figures'/(key+'_'+method+'_deletion.jpg'),[
                    ('full native SH3 original',rgb0),('actual opacity0 deletion; holes are losses',deleted),
                    ('RGB change, fixed scale 0.25',heat(diff,.25)),('alpha loss, fixed scale 1',heat(np.maximum(0,alpha-deleted_alpha),1))],tile=400)
        sheet(ART/'figures'/(key+'_budget_'+str(fraction)+'_selected_only.jpg'),images,cols=4,tile=400)
        budgets[str(fraction)]=stats
    if selected_by_method:
        footprints=budgets[str(p['primary_diagnostic_count_fraction'])]
    sensitivities=[]
    for K in p['sensitivity_K']:
        guard(key+'_sensitivity_K'+str(K));out,timings['K'+str(K)]=timed_forward(m,s,model,K)
        if not np.array_equal(out.rgb.cpu().numpy(),rgb0):raise AssertionError('K sensitivity RGB differs')
        kid=out.gaussian_ids.cpu().numpy();kw=out.gaussian_weights.cpu().numpy();kf=out.all_contribution_sum.cpu().numpy()
        if not(np.array_equal(kid[...,:8],ids) and np.array_equal(kw[...,:8],weights)):raise AssertionError('K prefix differs')
        t=time.perf_counter();kl,kr,_,kb=compare_sides(kid,kw,kf,points-2*normal,points+2*normal,count,batch=p['sparse_batch_edges'])
        ks=normalize_scores(kr,mass,p['min_visibility_mass'],p['epsilon']);ki=top_ids(ks,eligible,len(main_ids))
        timings['K'+str(K)]['CPU_sparse_comparison_ms']=1000*(time.perf_counter()-t)
        ids_export['K'+str(K)+'_ratio_ids']=ki
        np.save(tmp/('K'+str(K)+'_ratio_score.npy'),ks)
        render=render_subset(m,s,model,ki);save_rgb(ART/'figures'/(key+'_K'+str(K)+'_selected_only.jpg'),render)
        fc=render_features(m,s,model,ki)
        sensitivities.append(dict(K=K,selected_count=len(ki),RGB_bitwise_equal=True,K8_prefix_exact=True,
            global_mass_coverage=float(kw.sum(dtype=np.float64)/kf.sum(dtype=np.float64)),
            residual_bound_mean=float(kb.mean()),aggregate_ambiguity_over_L1=float(kb.sum()/max(kl.sum(),1e-12)),
            K8_jaccard=jaccard(main_ids,ki),footprint=footprint_stats(fc,sdf,centers[ki])))
        del out,kid,kw,kf;gc.collect()
    guard(key+'_baseline_final')
    with torch.no_grad(): last,_=m.GaussianRasterizer(s)(**model)
    if not np.array_equal(last.cpu().numpy(),rgb0):raise AssertionError('original RGB changed after stage calls')
    rgbcheck['post_all_calls_bitwise_equal']=True
    del last
    arraydict=dict(original_ids=np.arange(count,dtype=np.int32),raw_score=raw.astype(np.float32),score=ratio.astype(np.float32),
        full_visible_mass=mass,full_alphaT_edge_participation=participation_full,**ids_export)
    archive=ART/'downloads'/(key+'_scores_ids.npz');np.savez_compressed(archive,scene=np.array(name),camera=np.array(camera['key']),**arraydict)
    for label,a in dict(raw_score=raw,gaussian_scores=ratio,full_visible_mass=mass,topk_ids=ids,topk_weights=weights,
        alpha=alpha,full_accepted_alpha=full,edge=edge,signed_distance=sdf,baseline_RGB=rgb0).items():np.save(tmp/(label+'.npy'),a)
    for delta,(dl,dr,dp,db) in comparisons.items():
        np.savez_compressed(tmp/('endpoints_delta'+str(delta)+'.npz'),points=points,normal=normal,minus=points-delta*normal,
            plus=points+delta*normal,observed_L1=dl,unknown_residual_bound=db,L1_lower=np.maximum(0,dl-db),L1_upper=dl+db)
        np.save(tmp/('gaussian_scores_delta'+str(delta)+'.npy'),scores[delta])
    selected=selected_by_method['gaer_ratio'];selrgb=subset_images['gaer_ratio'];fc=contributions['gaer_ratio']
    attrmap=np.zeros_like(alpha);attrmap[edge]=l1
    unknownmap=np.zeros_like(alpha);unknownmap[edge]=bound
    candidate=np.repeat(edge[...,None],3,axis=-1).astype(float)
    overlay=endpoint_overlay(rgb0,points,normal,centers[selected])
    save_rgb(ART/'figures'/(key+'_full_RGB.jpg'),rgb0)
    sheet(ART/'figures'/(key+'_full_RGB_vs_selected_only.jpg'),[
        (key+' original full SH3 800x800',rgb0),(f'{key} only selected original kernels n={len(selected)}; 0.5% diagnostic',selrgb)],tile=800)
    sheet(ART/'figures'/(key+'_evidence.jpg'),[
        ('original native RGB',rgb0),('alpha silhouette candidate, E=1',candidate),
        ('edge-gated observed attribution L1; NOT detector',heat(attrmap,1)),('unknown Rminus+Rplus, fixed scale 1',heat(unknownmap,1)),
        ('selected mass under full model T; black diagnostic',1-fc),('selected-only native original color; changed T',selrgb),
        ('same-count full alphaT participation selected-only',subset_images['alphaT_participation']),
        ('normal endpoints green/blue; original projected centers purple',overlay)],cols=4,tile=400)
    crops(ART/'figures'/(key+'_crops.jpg'),[('original',rgb0),('endpoints + centers',overlay),
        ('fullT selected mass',1-fc),('selected-only',selrgb)],points)
    score_histogram(ART/'figures'/(key+'_score_hist.jpg'),ratio,mass,selected,key+' all original Gaussian ratio scores')
    coverage=weights.sum(2)/np.maximum(full,1e-30)
    result=dict(unit=key,scene=name,camera=camera,gaussian_count=count,resolution=[800,800],SH_degree=3,depth='NOT_AVAILABLE',
        config_sha256=confsha,RGB_checks=rgbcheck,edge_pixels=len(points),eligible_gaussians=int(eligible.sum()),automatic=automatic,
        main_selected_count=len(selected),budgets=budgets,causal=causal,K_sensitivity=sensitivities,stability=stability,
        visibility=dict(method='full native color[0] gradient with all-pixel ones, feature/bg0 pass, original SH3 RGB unchanged',
            fullmass_sum=float(mass.sum(dtype=np.float64)),accepted_alpha_sum=float(full.sum(dtype=np.float64)),
            feature_alpha_max_error=float(np.abs(feature_alpha-full).max()),weak_mass_rejected_count=int((mass<p['min_visibility_mass']).sum())),
        coverage=dict(global_mass_coverage=float(weights.sum(dtype=np.float64)/full.sum(dtype=np.float64)),
            positive_alpha_pixel_coverage=quantiles(coverage[full>0]),edge_pixel_coverage=quantiles(coverage[edge]),
            endpoint_observed_L1=quantiles(l1),endpoint_unknown_Rsum=quantiles(bound),
            aggregate_ambiguity_over_observed_L1=ambiguity,unknown_positive_bound_endpoint_count=int((bound>2e-6).sum()),
            interpretation='actual full L1 lies in max(0, observed-Rsum)..observed+Rsum; missing original IDs are unknown, not physical zero'),
        scores=dict(raw_positive=quantiles(raw[raw>0]),ratio_positive=quantiles(ratio[ratio>0]),
            ratio_nonzero_count=int((ratio>0).sum()),raw_nonzero_count=int((raw>0).sum())),
        diagnostic_archive=str(archive.relative_to(ROOT)),selected_ids_sha256=digest(selected.tolist()),
        timing=timings,end_to_end_seconds=time.perf_counter()-tstart,
        status='COMPLETE_DIAGNOSTIC; silhouette-only; automatic reliability assessed separately; human visual GO pending')
    result['random_control']=dict(count_matched=len(selected_by_method['visibility_matched_random'])==len(selected),
        full_visibility_relative_mass_error=abs(float(mass[selected_by_method['visibility_matched_random']].sum())-float(mass[selected].sum()))/max(float(mass[selected].sum()),1e-12),
        common_eligible_domain='raw>=0.01 and full mass>=0.25 for score baselines; random samples ALL full-mass-matched rows independently',
        overlap_with_ratio=jaccard(selected,selected_by_method['visibility_matched_random']))
    atomic_json(tmp/'MANIFEST.json',dict(config=config,config_sha256=confsha,archive=str(archive),status='COMPLETE'))
    os.replace(tmp,dst)
    resultpath=ART/'results'/(key+'.json');atomic_json(resultpath,result)
    files=list(dst.rglob('*'))+[archive,resultpath]+list((ART/'figures').glob(key+'_*'))
    atomic_json(seal,dict(status='COMPLETE',config_sha256=confsha,files={str(f.relative_to(ROOT)):sha(f) for f in files if f.is_file()}))
    print('COMPLETE',key,'selected',len(selected),'auto',automatic['state'],'seconds',round(result['end_to_end_seconds'],2),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--units',nargs='*');args=parser.parse_args()
    guard('run_start');torch.set_num_threads(2);freeze=make_freeze();cal=calibrate()
    modules={k:backend(k) for k in ('actual','patched')};results=[];failures=[]
    for name,record in freeze['scenes'].items():
        guard('load_'+name);model=scene_io.load_model(record)
        for camera in record['cameras']:
            key=name+'_'+camera['key']
            if args.units and key not in args.units:continue
            try:results.append(unit(name,record,camera,model,modules,freeze,cal))
            except Exception as ex:
                failure=dict(unit=key,error=str(ex),traceback=traceback.format_exc());failures.append(failure)
                atomic_json(ART/'failures'/(key+'_'+str(time.time_ns())+'.json'),failure);print('FAILED',key,ex,flush=True)
            gc.collect();torch.cuda.empty_cache()
        del model;gc.collect();torch.cuda.empty_cache()
    protected=check_protected(freeze);atomic_json(ART/'PROTECTED_AFTER.json',protected)
    atomic_json(ART/'results/RUN_SUMMARY.json',dict(completed=[r['unit'] for r in results],failures=failures,protected_unchanged=protected['passed']))
    if failures or not protected['passed']:raise SystemExit(1)

if __name__=='__main__':main()
