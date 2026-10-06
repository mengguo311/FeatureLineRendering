"""Plain resumable production: exact old spatial ink -> mandatory receivers -> 8-view counts."""
import argparse,csv,gc,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
from scipy.ndimage import distance_transform_edt
from runtime import *
from binding import backend,scene_io,boundary,ops,read_api
from freeze import make_freeze,check_protected,PROTOCOL
from assignment import assign,aggregate,rank_ids,REASONS
from media import save,sheet,heat,support_overlay,winner_images

def sealed(unit,config,fn):
    guard(unit);seal=ART/'seals'/(unit+'.json');result=ART/'results'/(unit+'.json');conf=digest(config)
    if seal.exists():
        rec=json.loads(seal.read_text())
        if rec['config_sha256']!=conf:raise RuntimeError('sealed config changed: '+unit)
        for p,h in rec['files'].items():
            if sha(ROOT/p)!=h:raise RuntimeError('sealed bytes changed: '+p)
        print('SEALED_SKIP',unit,flush=True);return json.loads(result.read_text())
    start=time.perf_counter();print('RUNNING',unit,flush=True)
    rec=fn();rec['unit']=unit;rec['end_to_end_seconds']=time.perf_counter()-start;atomic_json(result,rec)
    files=[result]+[ROOT/p for p in rec['files']]
    atomic_json(seal,dict(unit=unit,config_sha256=conf,files={str(p.relative_to(ROOT)):sha(p) for p in files},status='COMPLETE'))
    print('COMPLETE',unit,round(rec['end_to_end_seconds'],3),flush=True);return rec

def relative(p):return str(p.relative_to(ROOT))
def forward(module,settings,model,K=None):
    guard('forward_K'+str(K));torch.cuda.reset_peak_memory_stats()
    a,b=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
    t=time.perf_counter();a.record()
    with torch.no_grad():r=module.GaussianRasterizer(settings)(**model,**(dict(attribution=True,K=K) if K else {}))
    b.record();torch.cuda.synchronize()
    return r,dict(cuda_ms=a.elapsed_time(b),wall_ms=1000*(time.perf_counter()-t),peak_GPU_bytes=torch.cuda.max_memory_allocated(),
        scope='one actual native forward; no fabricated warmup/median; excludes CPU copies and assignment')

def region_masks(alpha,line):
    fg=alpha>.5;sdf=distance_transform_edt(fg)-distance_transform_edt(~fg)
    return dict(line=line,nonline=~line,interior_line=line&(sdf>4),outline_line=line&(np.abs(sdf)<=4),
        exterior_line=line&(sdf< -4),foreground=fg,interior=sdf>4,outline=np.abs(sdf)<=4),sdf

def fullT_metrics(contribution,alpha,line):
    masks,sdf=region_masks(alpha,line);total=float(contribution.sum(dtype=np.float64));fraction=contribution/np.maximum(alpha,1e-20)
    rec=dict(full_T_selected_mass=total,selected_mass_on_line_fraction=float(contribution[line].sum(dtype=np.float64)/max(total,1e-20)),
        leakage_non_line_mass_fraction=float(contribution[~line].sum(dtype=np.float64)/max(total,1e-20)))
    for key,mask in masks.items():
        mass=float(contribution[mask].sum(dtype=np.float64));full=float(alpha[mask].sum(dtype=np.float64))
        rec[key]=dict(pixels=int(mask.sum()),selected_mass=mass,full_mass=full,mass_recall=mass/max(full,1e-20),
            fraction_gt_01_pixels=int((mask&(fraction>.1)).sum()),fraction_gt_05_pixels=int((mask&(fraction>.5)).sum()),
            fraction_gt_01_rate=float((fraction[mask]>.1).mean()) if mask.any() else 0.,
            fraction_gt_05_rate=float((fraction[mask]>.5).mean()) if mask.any() else 0.)
    rec['interior_mass_fraction']=float(contribution[sdf>4].sum(dtype=np.float64)/max(total,1e-20))
    return rec

def counter_descriptors(a,ink,count):
    winner=a['winner_map'][ink>.2];valid=winner>=0;w=winner[valid];fallback=a['fallback_map'][ink>.2][valid]!=0
    return dict(fallback_counts=np.bincount(w,weights=fallback.astype(np.int64),minlength=count).astype(np.int64),
        center_weight_sum=np.bincount(w,weights=a['selected_center_weight'][valid],minlength=count),
        endpoint_D_sum=np.bincount(w,weights=a['selected_D'][valid],minlength=count),
        unknown_sum=np.bincount(w,weights=a['unknown_bound'][valid],minlength=count),
        weighted_ink=np.bincount(w,weights=ink[ink>.2][valid],minlength=count))

def view_unit(scene,record,v,model,modules,frozen):
    key=v['key'];unit=scene+'_vote_'+key;download=ART/'downloads'/scene/key;rawout=OUT/'units'/scene/key
    config=dict(view=v,protocol=PROTOCOL,method=frozen['source_method_files'],model_sha256=record['model_sha256'])
    def calculate():
        raw=np.load(v['raw']);rgb=raw['rgb'];fields=np.load(v['fields']);union=fields['union'];normal=fields['normal'];confidence=fields['confidence']
        ink=1-boundary.ink(union)[...,0];line=ink>.2
        s=scene_io.make_settings(modules['patched'],v['camera']);timings={}
        stock,timings['stock']=forward(modules['actual'],scene_io.make_settings(modules['actual'],v['camera']),model)
        baseline=stock[0].cpu().numpy().transpose(1,2,0);del stock
        if not np.array_equal(baseline,rgb):raise AssertionError('canonical cached fullSH3 RGB not bitwise aligned')
        on,timings['K8']=forward(modules['patched'],s,model,8)
        if not np.array_equal(on.rgb.cpu().numpy().transpose(1,2,0),rgb):raise AssertionError('K8 changed RGB')
        ids=on.gaussian_ids.cpu().numpy();weights=on.gaussian_weights.cpu().numpy();alpha=on.all_contribution_sum.cpu().numpy()
        alpha_error=float(np.abs(alpha-raw['alpha']).max())
        if alpha_error>3e-6:raise AssertionError('canonical alpha alignment failed')
        del on
        if key=='r_000':
            t=time.perf_counter();recomputed=boundary.analyze(rgb,frozen['foundation_config'])
            for name in ('union','normal','confidence'):
                if not np.array_equal(fields[name],recomputed[name]):raise AssertionError('same-detector cached field mismatch: '+name)
            timings['deterministic_same_detector_recompute_s']=time.perf_counter()-t
        start=time.perf_counter();a=assign(ids,weights,alpha,line,normal,confidence,record['count'])
        timings['CPU_assignment_s']=time.perf_counter()-start
        guard(unit+'_visibility');start=time.perf_counter();mass,feature_alpha=ops.feature_mass(modules['patched'],s,model)
        torch.cuda.synchronize();timings['full_visibility_gradient_s']=time.perf_counter()-start
        if np.abs(feature_alpha-alpha).max()>3e-6:raise AssertionError('fullT feature alpha failed')
        if abs(mass.sum(dtype=np.float64)-alpha.sum(dtype=np.float64))/max(alpha.sum(dtype=np.float64),1)>2e-5:raise AssertionError('full mass gradient mismatch')
        files=[]
        src=download/'source_fields.npz';npz(src,RGB=rgb,alpha=alpha,union=union,ink=ink,line_binary=line,
            normal_xy=normal,confidence=confidence,agreement=fields['agreement']);files.append(relative(src))
        dst=download/'assignment.npz';npz(dst,**{k:x for k,x in a.items() if isinstance(x,np.ndarray)},
            **counter_descriptors(a,ink,record['count']),original_N=np.array(record['count']));files.append(relative(dst))
        vis=download/'visible_mass.npz';npz(vis,original_fullT_visible_mass=mass);files.append(relative(vis))
        buf=rawout/'K8_buffer.npz';npz(buf,original_ids=ids,alphaT_weights=weights,full_accepted_alpha=alpha);files.append(relative(buf))
        sensitivities=[]
        if key in PROTOCOL['sensitivity_views']:
            for K in PROTOCOL['sensitivity_K']:
                guard(unit+'_K'+str(K));out,timings['K'+str(K)]=forward(modules['patched'],s,model,K)
                kid=out.gaussian_ids.cpu().numpy();kw=out.gaussian_weights.cpu().numpy()
                if not np.array_equal(out.rgb.cpu().numpy().transpose(1,2,0),rgb):raise AssertionError('sensitivity RGB mismatch')
                if not np.array_equal(kid[:,:,:8],ids) or not np.array_equal(kw[:,:,:8],weights):raise AssertionError('K8 prefix differs')
                start=time.perf_counter();ka=assign(kid,kw,alpha,line,normal,confidence,record['count'])
                timings['K'+str(K)]['CPU_assignment_s']=time.perf_counter()-start
                path=download/('sensitivity_K'+str(K)+'.npz');npz(path,winner_map=ka['winner_map'],fallback_map=ka['fallback_map'],counts=ka['counts'])
                files.append(relative(path));changed=(ka['winner_map'][line]!=a['winner_map'][line])
                sensitivities.append(dict(K=K,marked_pixels=int(line.sum()),changed_winners=int(changed.sum()),changed_fraction=float(changed.mean()),
                    changed_vote_IDs=int((ka['counts']!=a['counts']).sum()),fallback_pixels=int(np.isin(ka['fallback_map'][line],[1,2,3,4]).sum()),
                    K8_prefix_bitwise=True,RGB_bitwise=True))
                del out,kid,kw,ka;gc.collect()
        mdir=ART/'media'/scene/'receivers'/key
        standalone,overlay=winner_images(rgb,a['winner_map'],line)
        panels=[('native original full SH3',rgb),('same old RGB spatial union ink',boundary.ink(union)),
            ('ALL marked pixels ink > 0.2',1-line.astype(np.float32)),('receiver original-ID random colors',standalone),
            ('receiver pixels on native RGB',overlay),('fallback=orange; D=green; bg=red',fallback_colors(a['fallback_map']))]
        for name,img in [('RGB',rgb),('spatial_union_ink',boundary.ink(union)),('marked_binary',1-line.astype(np.float32)),
            ('winner_ID',standalone),('receiver_overlay',overlay)]:
            path=mdir/(name+'.png');save(path,img);files.append(relative(path))
        p=mdir/'evidence.jpg';sheet(p,panels,cols=3,tile=800,title=scene+' '+key+' | cached RGB spatial ink drives mandatory receivers');files.append(relative(p))
        roi=[240,260,560,580] if scene=='lego' else [240,330,560,650]
        crop_panels=[(label,np.asarray(image_to_array(img))[roi[1]:roi[3],roi[0]:roi[2]]) for label,img in panels[:5]]
        p=mdir/'interior_zoom.png';sheet(p,crop_panels,cols=5,tile=640,title='Frozen old ROI; nearest native content shown; no manual annotation');files.append(relative(p))
        masks,_=region_masks(alpha,line);assigned=a['winner_map']>=0
        reason_counts={REASONS[i]:int((a['fallback_map'][line]==i).sum()) for i in REASONS if i!=255}
        return dict(scene=scene,view=key,marked_pixels=int(line.sum()),weak_pixels=int(((ink>0)&~line).sum()),
            received_pixels=int(assigned.sum()),unassignable_pixels=a['unassignable'],received_ratio=float(assigned.sum()/max(line.sum(),1)),
            fallback_reasons=reason_counts,endpoint_only_best_pixels=int(a['endpoint_only_best'].sum()),
            unknown_positive_pixels=int((a['unknown_bound']>2e-6).sum()),unknown_bound_sum=float(a['unknown_bound'].sum(dtype=np.float64)),
            regions={name:dict(marked=int(mask.sum()),received=int((mask&assigned).sum())) for name,mask in masks.items() if name.endswith('line') and name!='nonline'},
            K_sensitivity=sensitivities,timing=timings,RGB_cached_stock_K8_bitwise=True,alpha_cached_max_abs=alpha_error,
            source_fields_sha256=sha(src),winner_map_sha256=array_sha(a['winner_map']),line_binary_sha256=array_sha(line),
            assignment_archive=relative(dst),source_archive=relative(src),visible_mass_archive=relative(vis),files=files)
    return sealed(unit,config,calculate)

def image_to_array(a):
    return np.repeat(a[...,None],3,2) if a.ndim==2 else a
def fallback_colors(f):
    rgb=np.ones(f.shape+(3,),np.float32);rgb[f==0]=[.05,.7,.3];rgb[np.isin(f,[1,2,3,4])]=[1,.45,.05];rgb[f==5]=[1,0,0];return rgb

def matched_random(selected,mass,seed):
    rng=np.random.default_rng(seed);bins=np.floor(np.log(np.maximum(mass,1e-12))/.1).astype(np.int32);pools={};chosen=[]
    for i in selected:
        b=bins[i]
        if b not in pools:pools[b]=rng.permutation(np.flatnonzero(bins==b)).tolist()
        if not pools[b]:raise RuntimeError('mass matched pool exhausted')
        chosen.append(pools[b].pop())
    return np.asarray(chosen,np.int32)

def jaccard(a,b):
    a=set(map(int,a));b=set(map(int,b));return len(a&b)/max(len(a|b),1)

def vote_scene(scene,record,views,frozen):
    config=dict(scene=scene,view_seals=[sha(ART/'seals'/(scene+'_vote_'+v['view']+'.json')) for v in views],protocol=PROTOCOL)
    def calculate():
        n=record['count'];data=[np.load(ROOT/v['assignment_archive']) for v in views];mass=sum(np.load(ROOT/v['visible_mass_archive'])['original_fullT_visible_mass'].astype(np.float64) for v in views)
        main=aggregate([(v['view'],a['counts'],v['marked_pixels']) for v,a in zip(views,data)],n)
        center=aggregate([(v['view'],a['center_counts'],v['marked_pixels']) for v,a in zip(views,data)],n)
        refused=aggregate([(v['view'],a['nofallback_counts'],v['marked_pixels']) for v,a in zip(views,data)],n)
        ranks=rank_ids(main['raw_frequency'],main['view_count']);cranks=rank_ids(center['raw_frequency'],center['view_count']);rranks=rank_ids(refused['raw_frequency'],refused['view_count'])
        sets={};random_check={}
        for k in (100,500,2000):sets['top'+str(k)]=ranks[:k]
        for k in (2,4,6):sets['views_ge'+str(k)]=np.flatnonzero(main['view_count']>=k).astype(np.int32)
        for k in (500,2000):
            sets['center_top'+str(k)]=cranks[:k];sets['nofallback_top'+str(k)]=rranks[:k]
            sets['random_top'+str(k)]=matched_random(sets['top'+str(k)],mass,1729+k)
            chosen=sets['top'+str(k)];random=sets['random_top'+str(k)]
            random_check[str(k)]=dict(count=len(random),same_count=len(chosen)==len(random),
                summed_source_visible_mass_relative_error=abs(float(mass[random].sum()-mass[chosen].sum()))/max(float(mass[chosen].sum()),1e-20),
                overlap_count=int(np.intersect1d(chosen,random).size),sampling='all original rows with same .1-wide log source-visible-mass bin, without replacement')
        descriptors={k:sum(a[k] for a in data) for k in ('fallback_counts','center_weight_sum','endpoint_D_sum','unknown_sum','weighted_ink')}
        exposure=sum((np.load(ROOT/v['visible_mass_archive'])['original_fullT_visible_mass']>0).astype(np.int16) for v in views)
        archive=ART/'downloads'/(scene+'_votes_all_original.npz')
        npz(archive,original_ids=np.arange(n,dtype=np.int32),view_keys=np.asarray([v['view'] for v in views]),
            **main,center_raw_frequency=center['raw_frequency'],center_view_count=center['view_count'],nofallback_raw_frequency=refused['raw_frequency'],
            total_visible_mass=mass,visibility_view_exposure=exposure,
            raw_per_visible_mass=main['raw_frequency']/np.maximum(mass,1e-20),view_count_per_exposure=main['view_count']/np.maximum(exposure,1),
            ranked_original_ids=ranks,**descriptors,**{k+'_ids':v for k,v in sets.items()})
        csvpath=ART/'downloads'/(scene+'_top100.csv');csvpath.parent.mkdir(parents=True,exist_ok=True)
        with csvpath.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['rank','original_ID','raw_pixel_frequency','distinct_views','per_view_normalized_frequency','fallback_fraction',
                'mean_center_alphaT','mean_endpoint_D','mean_unknown_bound','source_visible_mass','raw_per_visible_mass','view_exposure']+[v['view'] for v in views])
            for r,i in enumerate(ranks[:100],1):
                frequency=int(main['raw_frequency'][i]);den=max(frequency,1)
                writer.writerow([r,int(i),frequency,int(main['view_count'][i]),float(main['view_normalized'][i]),float(descriptors['fallback_counts'][i]/den),
                    float(descriptors['center_weight_sum'][i]/den),float(descriptors['endpoint_D_sum'][i]/den),float(descriptors['unknown_sum'][i]/den),
                    float(mass[i]),float(frequency/max(mass[i],1e-20)),int(exposure[i])]+main['per_view_counts'][:,i].tolist())
        stability=[]
        for index,v in enumerate(views):
            reduced=main['per_view_counts'].sum(0)-main['per_view_counts'][index]
            vc=(main['per_view_counts']>0).sum(0)-(main['per_view_counts'][index]>0)
            ranking=rank_ids(reduced,vc);stability.append(dict(dropped=v['view'],top500_jaccard=jaccard(ranks[:500],ranking[:500]),top2000_jaccard=jaccard(ranks[:2000],ranking[:2000])))
        sensitivity=[]
        sensitivity_keys=PROTOCOL['sensitivity_views'];ix=[j for j,v in enumerate(views) if v['view'] in sensitivity_keys]
        k8_counts=main['per_view_counts'][ix];k8rank=rank_ids(k8_counts.sum(0),(k8_counts>0).sum(0))
        for K in (16,32):
            counts=np.stack([np.load(ART/'downloads'/scene/views[j]['view']/('sensitivity_K'+str(K)+'.npz'))['counts'] for j in ix])
            kranks=rank_ids(counts.sum(0),(counts>0).sum(0))
            sensitivity.append(dict(K=K,views=sensitivity_keys,changed_aggregate_vote_IDs=int((counts.sum(0)!=k8_counts.sum(0)).sum()),
                top500_jaccard=jaccard(k8rank[:500],kranks[:500]),top2000_jaccard=jaccard(k8rank[:2000],kranks[:2000])))
        if main['raw_frequency'].sum()!=sum(v['received_pixels'] for v in views):raise AssertionError('raw frequency not one per receiver')
        return dict(scene=scene,original_N=n,source_views=8,marked_pixels=sum(v['marked_pixels'] for v in views),
            received_pixels=int(main['raw_frequency'].sum()),unassignable_pixels=sum(v['unassignable_pixels'] for v in views),
            eligible_positive_vote_IDs=len(ranks),sets={k:dict(count=len(v),IDs_sha256=array_sha(v)) for k,v in sets.items()},
            main_vs_center_top500_jaccard=jaccard(sets['top500'],sets['center_top500']),main_vs_center_top2000_jaccard=jaccard(sets['top2000'],sets['center_top2000']),
            random_check=random_check,drop_one_view_stability=stability,K_four_view_aggregate_sensitivity=sensitivity,
            vote_archive=relative(archive),top100_csv=relative(csvpath),files=[relative(archive),relative(csvpath)])
    return sealed(scene+'_aggregate',config,calculate)

def display_unit(scene,record,v,model,m,vote,frozen,evaluation=False):
    key=v['key'];kind='eval' if evaluation else 'display';unit=scene+'_'+kind+'_'+key
    config=dict(view=v,aggregate_seal=sha(ART/'seals'/(scene+'_aggregate.json')),method=frozen['source_method_files'],protocol=PROTOCOL)
    def calculate():
        s=scene_io.make_settings(m,v['camera']);files=[];timings={}
        if evaluation:
            out,timings['native_K1']=forward(m,s,model,1);rgb=out.rgb.cpu().numpy().transpose(1,2,0);alpha=out.all_contribution_sum.cpu().numpy();del out
            start=time.perf_counter();field=boundary.analyze(rgb,frozen['foundation_config']);ink=1-boundary.ink(field['union'])[...,0];line=ink>.2
            timings['same_old_spatial_analyze_s']=time.perf_counter()-start
            src=ART/'downloads'/scene/key/'source_fields.npz';npz(src,RGB=rgb,alpha=alpha,union=field['union'],ink=ink,line_binary=line,normal_xy=field['normal'],confidence=field['confidence']);files.append(relative(src))
            # Stock forward independent of attribution path on reserved views.
            stock,timings['stock_check']=forward(backend('actual'),scene_io.make_settings(backend('actual'),v['camera']),model)
            if not np.array_equal(stock[0].cpu().numpy().transpose(1,2,0),rgb):raise AssertionError('holdout native RGB alignment failed')
            del stock
        else:
            src=ART/'downloads'/scene/key/'source_fields.npz';z=np.load(src);rgb=z['RGB'];alpha=z['alpha'];ink=z['ink'];line=z['line_binary']
        votes=np.load(ROOT/vote['vote_archive']);mainfreq=votes['raw_frequency'];maxfreq=float(mainfreq.max())
        sets={k[:-4]:votes[k] for k in votes.files if k.endswith('_ids') and k not in ('ranked_original_ids','original_ids')}
        mdir=ART/'media'/scene/kind/key;metrics={};contributions={};selected_images={}
        for name,chosen in sets.items():
            guard(unit+'_'+name);start=time.perf_counter();contribution=ops.render_features(m,s,model,chosen)
            if np.any(contribution>alpha+3e-6):raise AssertionError('selected full T mass exceeds full model')
            metrics[name]=dict(count=len(chosen),**fullT_metrics(contribution,alpha,line))
            selected=ops.render_subset(m,s,model,chosen);timings[name+'_render_pair_s']=time.perf_counter()-start
            path=mdir/(name+'_selected_only.png');save(path,selected);files.append(relative(path));selected_images[name]=selected
            path=mdir/(name+'_fullT_mass.png');save(path,heat(contribution));files.append(relative(path))
            path=OUT/'display_maps'/scene/kind/key/(name+'_fullT.npz');npz(path,contribution=contribution);files.append(relative(path))
            contributions[name]=contribution
        colors=torch.zeros((record['count'],3),device='cuda');feature=np.log1p(mainfreq)/max(np.log1p(maxfreq),1e-20)
        colors[:]=torch.as_tensor(feature[:,None],device='cuda',dtype=torch.float32)
        st=s._replace(bg=torch.zeros(3,device='cuda'),sh_degree=0)
        with torch.no_grad():fr,_=m.GaussianRasterizer(st)(**ops.feature_model(model,colors))
        frequency_map=fr[0].cpu().numpy();del fr,colors
        for name,a in [('RGB',rgb),('spatial_union_ink',1-ink),('top500_fullT_overlay',support_overlay(rgb,contributions['top500'],6)),
            ('vote_frequency_heatmap',heat(frequency_map*8)),('vote_frequency_overlay',support_overlay(rgb,frequency_map,8))]:
            path=mdir/(name+'.png');save(path,a);files.append(relative(path))
        p=mdir/'main_evidence.jpg';sheet(p,[('native original fullSH3',rgb),('old spatial RGB ink',1-ink),
            ('fixed TOP500 original SH3 only|n='+str(len(sets['top500'])),selected_images['top500']),
            ('TOP500 selected mass full model T|gain=6 overlay; no original recoloring',support_overlay(rgb,contributions['top500'],6)),
            ('raw votes log feature full model T|fixed gain=8, not original RGB',heat(frequency_map*8)),
            ('mandatory center TOP500 original SH3|n='+str(len(sets['center_top500'])),selected_images['center_top500'])],cols=3,tile=800,
            title=scene+' '+key+' | SAME eight-view fixed sets | '+kind);files.append(relative(p))
        p=mdir/'baseline_selected_only.jpg';sheet(p,[(name+'|n='+str(len(sets[name])),selected_images[name]) for name in
            ('top500','center_top500','random_top500','nofallback_top500','top2000','center_top2000','random_top2000','nofallback_top2000')],cols=4,tile=800,
            title=scene+' '+key+' fixed sets from 8 source views; original SH3 subsets');files.append(relative(p))
        post,_=forward(m,s,model)
        if not np.array_equal(post[0].cpu().numpy().transpose(1,2,0),rgb):raise AssertionError('original model changed after visualization')
        del post
        return dict(scene=scene,view=key,kind=kind,marked_pixels=int(line.sum()),metrics=metrics,timing=timings,source_archive=relative(src),
            source_RGB_float32_sha256=array_sha(rgb),source_line_binary_sha256=array_sha(line),camera_sha256=v['camera_sha256'],
            RGB_stock_and_post_bitwise=True,selection_holdout=evaluation,formal_blind=False,files=files)
    return sealed(unit,config,calculate)

def check_original_model(scene,record,model):
    # A separately decoded official GaussianModel verifies row order, ALL 16
    # full SH3 coefficients, activations and rotations, without writing PLY.
    api=read_api('vote_stock_model_check',FOUNDATION/'experiments/image_space_edge_foundation_v1/src/native.py')
    stock=api.load_model(record['model'])
    fields=dict(means3D=stock.get_xyz,shs=stock.get_features,opacities=stock.get_opacity,scales=stock.get_scaling,rotations=stock.get_rotation)
    equal={k:torch.equal(model[k],v) for k,v in fields.items()}
    if not all(equal.values()):raise AssertionError('official fullSH3 PLY decoding mismatch')
    rec=dict(scene=scene,original_N=record['count'],SH_degree=3,SH_shape=list(model['shs'].shape),official_GaussianModel_bitwise=equal,model_sha256=sha(record['model']))
    atomic_json(ART/'tests'/(scene+'_MODEL_CHECK.json'),rec);del stock;gc.collect();return rec

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scene',choices=['lego','chair','both'],default='both');args=parser.parse_args()
    guard('freeze');frozen=make_freeze();start=time.perf_counter();results={};failures={};modules={k:backend(k) for k in ('actual','patched')}
    for scene in (['lego','chair'] if args.scene=='both' else [args.scene]):
        try:
            rec=frozen['scenes'][scene];guard(scene+'_load');model=scene_io.load_model(rec);modelcheck=check_original_model(scene,rec,model)
            views=[view_unit(scene,rec,v,model,modules,frozen) for v in rec['vote_views']]
            vote=vote_scene(scene,rec,views,frozen)
            display=[display_unit(scene,rec,v,model,modules['patched'],vote,frozen) for v in rec['vote_views'] if v['key'] in PROTOCOL['visualization_views']]
            evaluation=[display_unit(scene,rec,v,model,modules['patched'],vote,frozen,True) for v in rec['evaluation_views']]
            results[scene]=dict(vote=vote,views=views,display=display,evaluation=evaluation,modelcheck=modelcheck)
            atomic_json(ART/'results'/(scene+'_COMPLETE.json'),results[scene]);del model;gc.collect();torch.cuda.empty_cache()
        except Exception as e:
            failures[scene]=dict(error=str(e),traceback=traceback.format_exc());atomic_json(ART/'failures'/(scene+'_'+str(time.time_ns())+'.json'),failures[scene])
            print('SCENE_FAILED',scene,failures[scene]['traceback'],flush=True);gc.collect();torch.cuda.empty_cache()
    protected=check_protected(frozen);atomic_json(ART/'tests/PROTECTED_AFTER.json',protected)
    atomic_json(OUT/'RUNNER_COMPLETE.json',dict(actual_seconds=time.perf_counter()-start,scenes=list(results),failures=failures,protected_passed=protected['passed'],freeze_sha256=sha(ART/'PRODUCTION_FREEZE.json')))
    if failures or not protected['passed']:raise SystemExit(1)

if __name__=='__main__':main()
