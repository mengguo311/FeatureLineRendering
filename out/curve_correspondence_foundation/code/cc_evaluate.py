"""Read-only frozen-output evaluation, diagnostics and actual review media."""
import argparse,collections,datetime,hashlib,itertools,pathlib,sys,time
import numpy as np
import cv2
import cc,cc_visual as vis
from cc_io import read_json,write_json,sha,seal,verify_seal,scene_inputs
from cc_report import arm_gates
from cc_runner import O,R,P,confine,primary_arm_names
from src.corrected_qualification import reference
from src.corrected_visuals import orbit_cameras

def identity_certificate(records,edges,m):
    if not records:return False
    lookup={frozenset([e['a'],e['b']]):e for e in edges if e['selected']}
    for r in records:
        if len(set(r['views']))<3 or not r['identity_frozen_before_fit'] or r['cycle_p90'] is None or r['cycle_p90']>m['cycle_arc_p90_max']:return False
        count=0
        for a,b in itertools.combinations(r['nodes'],2):
            e=lookup.get(frozenset([a,b]))
            if e is None:continue
            count+=1
            for side in ['a','b']:
                margin=e.get('margin_'+side);ratio=e.get('ratio_'+side)
                if (margin is not None and margin<m['margin_min']) or ratio is None or ratio>m['ratio_max']:return False
        if count<3:return False
    return True

def failure_buckets(curves,candidates,rejected,annotation):
    categories={'view_dependent_silhouette':'smooth_silhouette','shadows':'shadow_highlight','highlights':'shadow_highlight','repeated_texture':'repeated_texture','junctions':'junctions','multilayer_cross_part':'multilayer'}
    buckets={}
    for name,old in categories.items():
        regions=[r for r in annotation.get('challenges',[]) if r['category']==old];ids=set()
        for k,c in curves.items():
            xy=np.mean(c['points'],axis=0)
            for r in regions:
                a,b,x,y=r['box']
                if c['view']==r['view'] and a<=xy[0]<=x and b<=xy[1]<=y:ids.add(k)
        rows=[e for e in candidates if e['a'] in ids or e['b'] in ids]
        buckets[name]=dict(curves=len(ids),curve_ids=sorted(ids),candidate_associations=len(rows),selected_associations=sum(bool(e.get('selected')) for e in rows),reasons=dict(collections.Counter(x for e in rows for x in e['reasons'])),regions=regions,status='COARSE_REGION_PROXY' if regions else 'NO_CERTIFIED_REGION')
    return dict(buckets=buckets,semantic_truth=False,independent=False,shadow_highlight_separation='unknown; overlapping inherited challenge boxes',fit_rejections=dict(collections.Counter(x for r in rejected for x in r['reasons'])))

def comparison_sets(arms,F_cameras,cfg):
    nonempty=[len(r) for r in arms.values() if r];count=min([cfg['visuals']['track_cardinality'],*nonempty]) if nonempty else 0
    ordered={n:sorted(r,key=lambda x:hashlib.sha256(x['id'].encode()).hexdigest()) for n,r in arms.items()}
    native_ink={n:float(np.mean([vis.ink(vis.curve_image(r,c)) for c in F_cameras])) for n,r in arms.items()}
    positive=[v for v in native_ink.values() if v>0];budget=min(positive)*cfg['visuals']['ink_fraction'] if positive else 0.
    selected={n:vis.ink_prefix(r,F_cameras,budget) for n,r in arms.items()};ink={n:[r for r in rows if r['id'] in selected[n]['ids']] for n,rows in arms.items()}
    return dict(native=arms,cardinality={n:r[:count] for n,r in ordered.items()},ink=ink),dict(cardinality=count,native_ink=native_ink,ink_budget=budget,ink=selected,empty_arms=[n for n,r in arms.items() if not r])

def view_evaluation(records,cameras,fields,delta,cfg,output,name):
    result=cc.predict(records,cameras,fields,delta,cfg['gates']);write_json(output/f'{name}_samples.json.gz',result.pop('samples'));return result

def evaluate_numbers(scene,cfg,output,photos,fields):
    base=O/'scenes'/scene;info=cfg['scenes'][scene];delta=info['eligibility']['delta'];g=cfg['gates']
    cameras={split:scene_inputs(cfg,scene,split)['cameras'] for split in ['F','C','DEV']}
    arms={name:read_json(base/f'F/{name}.json.gz') for name in primary_arm_names(cfg)}
    Cfits={name:read_json(base/f'C/{name}.json.gz')['accepted'] for name in ['image_only','gs']}
    repeats={asset:read_json(base/f'repeats/{asset}/gs.json.gz') for asset in info['assets'] if asset!='seed_1729'}
    curves=read_json(base/'F/curves.json.gz');candidates=read_json(base/'F/candidates.json.gz');prediction={}
    for name,record in arms.items():
        prediction[name]={split:view_evaluation(record['accepted'],cameras[split],fields[split],delta,cfg,output,f'{name}_{split}') for split in ['F','C','DEV']}
    repeat_metrics={};metrics={};gates={};base_yield={}
    for name in ['image_only','gs']:
        rows=arms[name]['accepted'];yp=cc.yield_metrics(rows,cameras['F'],delta,g);base_yield[name]=yp;rep={}
        rep['C_independent']=cc.match_geometry(rows,Cfits[name],delta,g)
        for i in cfg['splits']['F']:
            key=f'loo_{i:03d}'+('_gs' if name=='gs' else '');rep[key]=cc.match_geometry(rows,arms[key]['accepted'],delta,g)
        if name=='gs':
            for a,v in repeats.items():rep[a]=cc.match_geometry(rows,v['accepted'],delta,g)
        else:rep['posterior_invariance_by_construction']=dict(passed=True,measured=False,explanation='image-only generator has no posterior input; not evidence for GS benefit')
        repeat_metrics[name]=rep
        controls={s:{n:prediction[n+('_gs' if name=='gs' else '')][s] for n in ['shifted','random_graph','pairwise','no_order']} for s in ['C','DEV']}
        summary=dict(yield_pass=yp['passed'],fit_pass=yp['fit_passed'],C_pass=prediction[name]['C']['passed'],DEV_pass=prediction[name]['DEV']['passed'],C_coverage=prediction[name]['C']['track_coverage'],DEV_coverage=prediction[name]['DEV']['track_coverage'],repeat_pass=all(v['passed'] for v in rep.values()),certificate=identity_certificate(rows,candidates,cfg['matching']),C_null=cc.null_gate(prediction[name]['C'],controls['C'],g),DEV_null=cc.null_gate(prediction[name]['DEV'],controls['DEV'],g))
        metrics[name]=summary;gates[name]=arm_gates(summary,g)
    benefit={'seed_1729':cc.gs_benefit(prediction['image_only']['DEV'],prediction['gs']['DEV'],g)};posterior_predictions={}
    for a,r in repeats.items():
        posterior_predictions[a]=view_evaluation(r['accepted'],cameras['DEV'],fields['DEV'],delta,cfg,output,'repeat_'+a+'_DEV');benefit[a]=cc.gs_benefit(prediction['image_only']['DEV'],posterior_predictions[a],g)
    stable_benefit=all(x['passed'] for x in benefit.values());verdict=cc.decision(True,all(gates['image_only'].values()),all(gates['gs'].values()),stable_benefit)
    extraction=read_json(base/'F/extraction_summary.json');cand_summary=read_json(base/'F/candidate_summary.json')
    result=dict(scene=scene,verdict=verdict,qualifier='BOTH' if info['eligibility']['route_a'] and info['eligibility']['route_b'] else 'CONTROLLED_ONLY' if info['eligibility']['route_b'] else 'SEED_ONLY',segments=sum(x['curves'] for x in extraction),candidates=cand_summary['proposed'],pairs=cand_summary['selected'],identities=arms['image_only']['identity_hypotheses'],image_tracks=len(arms['image_only']['accepted']),gs_tracks=len(arms['gs']['accepted']),arms=len(arms)+len(Cfits)+len(repeats),gates=gates,G0_execution_pending_final_audit=True,G5_gs_benefit=stable_benefit,gate_inputs=metrics,yield_metrics=base_yield,predictions=prediction,repeatability=repeat_metrics,gs_benefit=benefit,posterior_predictions=posterior_predictions,arm_counts={k:len(v['accepted']) for k,v in arms.items()},C_counts={k:len(v) for k,v in Cfits.items()},repeat_counts={k:len(v['accepted']) for k,v in repeats.items()},candidate_summary=cand_summary,extraction_summary=extraction,manual=dict(independent_review_count=0,status='PENDING_INDEPENDENT_REVIEW'))
    write_json(output/'metrics.json',result);return result,arms,curves,candidates,repeats

def extraction_and_candidates(output,scene,cfg,photos,curves,candidates,arms,annotation):
    panels=[];labels=[];base=O/'scenes'/scene
    for split in ['F','C']:
        for view in cfg['splits'][split]:
            ex=read_json(base/f'{split}/extraction_{view:03d}.json.gz');im=np.round(photos[view]*255).astype('u1')
            for r in ex['rejected']:vis.draw_polyline(im,r['pixels'],(180,180,180))
            for c in ex['curves']:vis.draw_polyline(im,c['pixels'],vis.color_for(c['id']))
            for x,y in ex['graph']['junctions']:cv2.circle(im,(x,y),2,(255,0,0),1)
            vis.write_png(output/f'extraction_{split}_{view:03d}.png',im);panels.append(cv2.resize(im,(200,200)));labels.append(f'{split} {view}: {len(ex["curves"])} segments')
    vis.write_png(output/'extraction_contact.png',vis.contact_sheet(panels,labels,4))
    groups=collections.defaultdict(list)
    for e in candidates:
        if e['selected']:groups['selected_pairs'].append(e)
        for reason in e['reasons']:groups[reason].append(e)
    for bucket,rows in groups.items():
        panels=[];labels=[]
        chosen=sorted(rows,key=lambda x:hashlib.sha256((x['a']+'|'+x['b']).encode()).hexdigest())[:12]
        for index,e in enumerate(chosen):
            a=curves[e['a']];b=curves[e['b']];left=np.round(photos[a['view']]*255).astype('u1');right=np.round(photos[b['view']]*255).astype('u1')
            vis.draw_polyline(left,a['pixels'],(255,0,0),2);vis.draw_polyline(right,b['pixels'],(255,0,0),2)
            # Show competing identities in the destination view, not only the chosen pair.
            for alt in candidates:
                if alt['a']==e['a'] and alt['b']!=e['b'] and curves[alt['b']]['view']==b['view'] and alt.get('score') is not None:
                    vis.draw_polyline(right,curves[alt['b']]['pixels'],(0,100,255))
            im=np.concatenate([left,right],axis=1)
            for sa,tb in zip(e['sa'][::3],e['tb'][::3]):
                p=cc.interpolate(a['points'],sa);q=cc.interpolate(b['points'],tb)+[400,0]
                cv2.line(im,tuple(np.round(p).astype(int)),tuple(np.round(q).astype(int)),(70,160,60),1,cv2.LINE_AA)
            vis.write_png(output/f'candidate_{bucket}_{index:02d}.png',im);panels.append(cv2.resize(im,(400,200)));labels.append(f'{bucket}; views {a["view"]}/{b["view"]}; score {e.get("score")}')
        vis.write_png(output/f'candidate_{bucket}_contact.png',vis.contact_sheet(panels,labels,2))
    rejection=arms['image_only']['rejected'];tracks=arms['image_only']['identity_tracks'];entries=[('accepted_identity',t) for t in tracks]+[(r.get('stage','reject')+':'+','.join(r['reasons']),r) for r in rejection]
    panels=[];labels=[]
    for index,(label,t) in enumerate(entries):
        nodes=t['nodes'];thumbs=[]
        for node in nodes:
            c=curves[node];im=np.round(photos[c['view']]*255).astype('u1');vis.draw_polyline(im,c['pixels'],vis.color_for('|'.join(nodes)),2);thumbs.append(cv2.resize(im,(200,200)))
        sheet=vis.contact_sheet(thumbs,[f'view {curves[n]["view"]}' for n in nodes],min(4,len(nodes)))
        vis.write_png(output/f'track_identity_{index:03d}.png',sheet)
        panels.append(cv2.resize(sheet,(400,200)));labels.append(label)
    if not panels:panels=[np.full((200,400,3),255,'u1')];labels=['No image identity hypotheses; see pair rejections']
    vis.write_png(output/'identity_rejection_contact.png',vis.contact_sheet(panels,labels,3))
    buckets=failure_buckets(curves,candidates,rejection,annotation)
    buckets['buckets']['junctions'].update(status='DETECTOR_TOPOLOGY',junction_count=sum(len(read_json(base/f'F/extraction_{v:03d}.json.gz')['graph']['junctions']) for v in cfg['splits']['F']))
    write_json(output/'failure_buckets.json',buckets)
    region_panels=[];region_labels=[]
    for name,bucket in buckets['buckets'].items():
        for reg in bucket['regions']:
            v=reg['view'];c=cfg['scenes'][scene]['cameras'][f'train_{v:03d}'];a,b,x,y=reg['box']
            im=vis.curve_image(arms['image_only']['accepted'],c,color=True,background=photos[v]);crop=im[b:y,a:x]
            region_panels.append(cv2.resize(crop,(200,200)));region_labels.append(name+' '+str(v)+' (proxy)')
    vis.write_png(output/'failure_regions.png',vis.contact_sheet(region_panels,region_labels,4))

def generate_visuals(scene,cfg,output,photos,arms,curves,candidates,repeats,result):
    visual=output/'visual';visual.mkdir();info=cfg['scenes'][scene];delta=info['eligibility']['delta'];Fcam=scene_inputs(cfg,scene,'F')['cameras']
    names=['image_only','gs','shifted','shifted_gs','random_graph','random_graph_gs','pairwise','pairwise_gs','no_order','no_order_gs']
    display={n:arms[n]['accepted'] for n in names}
    pca=read_json(P/f'local/{scene}/F/pca.json')['accepted'];display['pca_reference']=[dict(id=str(r['query']),xyz=np.array(r['point'])[None]+np.array([-1,1])[:,None]*delta*np.array(r['axis'])[None]) for r in pca]
    sets,comparison=comparison_sets(display,list(Fcam.values()),cfg);write_json(visual/'comparison_selection.json',comparison)
    review=[];ink_actual={}
    for mode,selected in sets.items():
        fixed=[];labels=[]
        for name,records in selected.items():
            ink_actual[mode+'_'+name]={}
            panels=[];panel_labels=[]
            for split in ['F','C','DEV']:
                for v,c in scene_inputs(cfg,scene,split)['cameras'].items():
                    im=vis.curve_image(records,c);path=visual/f'{mode}_{name}_{split}_{v:03d}.png';vis.write_png(path,im)
                    ink_actual[mode+'_'+name][f'{split}_{v}']=vis.ink(im)
                    panels.append(cv2.resize(im,(200,200)));panel_labels.append(f'{split} {v}; n={len(records)}')
                    if split=='DEV':review.append((f'{mode}/{name}/{split}/{v}',path))
                    if mode=='native' and name in ['image_only','gs']:
                        vis.write_png(visual/f'overlay_{name}_{split}_{v:03d}.png',vis.curve_image(records,c,color=True,background=photos[v]))
            vis.write_png(visual/f'{mode}_{name}_contact.png',vis.contact_sheet(panels,panel_labels,4))
            for v in cfg['visuals']['fixed_dev']:
                c=info['cameras'][f'train_{v:03d}'];fixed.append(cv2.resize(vis.curve_image(records,c),(200,200)));labels.append(f'{name} DEV {v}; n={len(records)}')
        vis.write_png(visual/f'{mode}_all_arms_contact.png',vis.contact_sheet(fixed,labels,4))
    write_json(visual/'actual_ink.json',ink_actual)
    # Remaining reached LOO and posterior arms get actual fixed-F projections.
    for name,r in {**{n:arms[n] for n in arms if n.startswith('loo_')},**{'repeat_'+k:v for k,v in repeats.items()}}.items():
        panels=[cv2.resize(vis.curve_image(r['accepted'],Fcam[v],color=True,background=photos[v]),(200,200)) for v in cfg['visuals']['fixed_train']]
        vis.write_png(visual/f'{name}_fixed_F.png',vis.contact_sheet(panels,[f'{name} {v}' for v in cfg['visuals']['fixed_train']],2))
    annotation=read_json(P/f'annotations/{scene}_internal.json');extraction_and_candidates(visual,scene,cfg,photos,curves,candidates,arms,annotation)
    video=[]
    if any(display[n] for n in names):
        target=np.mean(info['eligibility']['box'],axis=0);radius=float(np.median([np.linalg.norm(cc.camera_center(c)-target) for c in Fcam.values()]));orbit=orbit_cameras(target,radius,next(iter(Fcam.values())),cfg);write_json(visual/'orbit_cameras.json',orbit)
        for name in names:
            if not display[name]:continue
            frames=[vis.curve_image(display[name],c) for c in orbit];vis.write_video(visual/f'{name}_orbit.mp4',frames,cfg['visuals']['fps']);vis.write_png(visual/f'{name}_orbit_contact.png',vis.contact_sheet([cv2.resize(f,(100,100)) for f in frames],[str(i) for i in range(120)],12));video.append(dict(arm=name,frames=120,fps=24,visibility='unclipped fixed-geometry diagnostic',path=f'{name}_orbit.mp4'))
        # Fixed cardinality across all arms, including PCA, in one review video.
        frames=[]
        for c in orbit:frames.append(vis.contact_sheet([cv2.resize(vis.curve_image(r,c),(200,200)) for r in sets['cardinality'].values()],[n for n in sets['cardinality']],4))
        vis.write_video(visual/'cardinality_comparison.mp4',frames,cfg['visuals']['fps']);video.append(dict(arm='cardinality_comparison',frames=120,fps=24,visibility='unclipped fixed-geometry diagnostic',path='cardinality_comparison.mp4'))
    write_json(visual/'video_status.json',dict(trigger=any(display[n] for n in names),videos=video,no_view_dependent_geometry=True,limitation='White-background diagnostic projections; no new orbit GS visibility renders or independent RGB truth.'))
    key=vis.blind_package(review,visual/'blinded_review',cfg['visuals']['review_seed']);write_json(visual/'review_identity_key.json',key)
    return dict(pngs=len(list(visual.rglob('*.png'))),videos=video,blinded_images=len(key),independent_reviews=0,comparison=comparison)

def run(scene):
    cfg=read_json(O/'config.json');assert sha(O/'config.json')==(O/'config.json.sha256').read_text().strip();base=O/'scenes'/scene;info=cfg['scenes'][scene]
    for directory in [base/'F',base/'C',*[base/'repeats'/a for a in info['assets'] if a!='seed_1729']]:
        if not verify_seal(directory,read_json(directory/'frozen.json')):raise ValueError('frozen output changed')
    output=O/'evaluation'/scene;output.mkdir(parents=True,exist_ok=False)
    photos_in=[c['path'] for split in ['F','C','DEV'] for c in scene_inputs(cfg,scene,split)['cameras'].values()]
    scientific=[*photos_in,P/f'annotations/{scene}_internal.json',P/f'local/{scene}/F/pca.json',P/f'evaluation/{scene}/visual/DEV_render_equivalence.json',*[p for p in base.rglob('*') if p.is_file()]]
    sources=[*list((O/'code').glob('*.py')),*list((R/'src').glob('*.py'))];readonly=[*scientific,*sources]
    policy=dict(scene=scene,task='evaluation',readonly=[str(pathlib.Path(p).resolve()) for p in readonly]+[str(pathlib.Path(sys.prefix).resolve()),'/usr','/lib','/lib64','/etc','/proc','/sys'],writable=[str(output),'/dev'],photo_inputs=photos_in,input_hashes={str(p):sha(p) for p in scientific},source_hashes={str(p):sha(p) for p in sources},config_sha256=sha(O/'config.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(output/'allowlist.json',policy);confine(readonly,output);start=time.monotonic();photos={};fields={}
    for split in ['F','C','DEV']:
        fields[split]={}
        for v,c in scene_inputs(cfg,scene,split)['cameras'].items():
            rgb,alpha=reference(c);photos[v]=rgb[1];fields[split][v]=cc.edge_field(rgb[1],cfg)
    result,arms,curves,candidates,repeats=evaluate_numbers(scene,cfg,output,photos,fields);print(scene,'MACHINE',result['verdict'],result['gates'],flush=True)
    write_json(output/'inherited_DEV_posterior_qualification.json',read_json(P/f'evaluation/{scene}/visual/DEV_render_equivalence.json'))
    media=generate_visuals(scene,cfg,output,photos,arms,curves,candidates,repeats,result);write_json(output/'media.json',media)
    write_json(output/'complete.json',dict(scene=scene,elapsed_seconds=time.monotonic()-start,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict=result['verdict']));write_json(output/'frozen.json',seal(output));print('EVALUATION SEALED',scene,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scene',required=True);run(p.parse_args().scene)
