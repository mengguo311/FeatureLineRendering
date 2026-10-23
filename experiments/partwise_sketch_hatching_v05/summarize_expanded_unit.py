"""Descriptive readback of saved source edits; never changes frozen gates."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from run_expanded_unit import load,ARMS
from run_path_unit import read_npz
from run_unit import panel


def summarize(unit):
    p=load(unit);summaries={};allrows=[]
    for scene,s in p['scenes'].items():
        root=unit/'results'/scene;valid=json.loads((unit/f'VALIDATION_{scene}.json').read_text())
        assert valid['actual_scaled_matching_valid']
        build=json.loads((root/'BUILD_AUDIT.json').read_text());sel=read_npz(root/'EDIT_SELECTION.npz')
        cand=read_npz(root/'CANDIDATES.npz');binding=read_npz(root/'SOURCE_BINDING.npz');fp=read_npz(root/'FOOTPRINT_BINDING.npz')
        old=np.flatnonzero(cand['previous_path']>0);new=np.flatnonzero(cand['specific']>0)
        overlap=np.intersect1d(old,new);newonly=np.setdiff1d(new,old);removed=np.setdiff1d(old,new)
        prior=read_npz(Path(p['prior_unit'])/'results'/scene/'SOURCE_BINDING.npz')
        transitions=dict(overlap=len(overlap),new_only=len(newonly),removed_old=len(removed),
            new_only_previously_M1_UNKNOWN=int(prior['unknown'][newonly].sum()))
        np.savez_compressed(root/'SELECTION_TRANSITIONS.npz',source_index=np.arange(s['source_count']),
            old_selected=cand['previous_path']>0,new_selected=cand['specific']>0,
            old_M1_unknown=prior['unknown'],new_M1_unknown=binding['unknown'])
        # Diagnose previously documented leakage IDs without changing selection.
        oldfail='orbit_301_12_'+('5.1' if scene=='chair' else '5.3')
        diag=json.loads((Path(p['prior_unit'])/'results'/scene/oldfail/'TRANSFER_DIAGNOSIS.json').read_text())
        diagnostic=[]
        for entry in diag['top_far_bound_IDs']:
            gid=entry['source_index'];diagnostic.append(dict(entry,new_strength=float(sel['specific'][gid]),
                new_M1_unknown=bool(binding['unknown'][gid]),new_footprint_reason=str(fp['reason'][gid]),
                expanded_BUILD_worst_far_fraction=float(fp['worst_view_far_fraction'][gid])))
        js(root/'PREVIOUS_LEAKING_IDS_READBACK.json',dict(scope='Post-evaluation explanation only; unit004 is exposed BUILD, not held-out recovery.',rows=diagnostic))
        rows=[];panels=[];counts={arm:dict(locality=0,coverage=0,joint=0) for arm in ARMS}
        for c in s['cameras']:
            folder=root/c['view'];row=json.loads((folder/'EVALUATION.json').read_text());frame=read_npz(folder/'baseline.npz')
            assert c['view'] in valid['checks'];edits={arm:read_npz(folder/f'tint_{arm}.npz')['rgb'] for arm in ARMS}
            reg=frame['proxy_regions']==4;foreground=frame['alpha']>=.5;mask=frame['path_mask']
            visual={}
            for arm in ARMS:
                d=np.abs(np.clip(edits[arm],0,1)-np.clip(frame['rgb'],0,1)).sum(2);changed=d>1/255
                visual[arm]=dict(authored_region4_pixels=int(reg.sum()),path_capsule_pixels=int(mask.sum()),
                    eroded_interior_pixels=row['arms'][arm]['target_interior']['pixels'],
                    source_foreground_pixels=int(foreground.sum()),changed_source_foreground_pixels=int((foreground&changed).sum()),
                    changed_source_foreground_fraction=float(changed[foreground].mean()) if foreground.any() else None,
                    changed_authored_region4_pixels=int((reg&changed).sum()),
                    changed_authored_region4_fraction=float(changed[reg].mean()) if reg.any() else None,
                    authored_region4_mean_clipped_RGB_L1=float(d[reg].mean()) if reg.any() else None,
                    changed_capsule_pixels=int((mask&changed).sum()))
                counts[arm]['locality']+=int(row['arms'][arm]['intent_locality_gate'])
                counts[arm]['coverage']+=int(row['coverage'][arm]['coverage_gate'])
                counts[arm]['joint']+=int(row['joint_transfer'][arm])
            # Actual before/after views plus a clearly identified amplified diagnostic.
            heat=np.clip(np.abs(edits['specific']-frame['rgb']).sum(2)/.3,0,1)
            heat=np.stack([np.ones_like(heat),1-heat,1-heat],-1)
            panel(folder/'expanded_vs_previous.png',[frame['rgb'],edits['previous_path'],edits['specific'],heat],
                ['Original GS / full SH3','Old BUILD source edit','Expanded BUILD source edit','Actual L1 / 0.3 diagnostic'],
                scene+' '+c['view']+' | Whole object; matched BUILD effect; frozen controls')
            js(folder/'VISIBILITY_READBACK.json',dict(utc=now(),display_threshold='clipped RGB L1 > 1/255; descriptive only, no new PASS gate',arms=visual))
            kd=read_npz(folder/'SELECTED_KERNEL_DIAGNOSTICS.npz');ids=kd['source_index'];mass=kd['full_pixel_mass']
            group_stats={}
            for name,which in [('retained_old_IDs',np.isin(ids,overlap)),('new_selected_IDs',np.isin(ids,newonly))]:
                total=float((mass[which,0]*kd['strength'][which]).sum());far=float((mass[which,3]*kd['strength'][which]).sum())
                group_stats[name]=dict(selected_IDs=int(which.sum()),visible_IDs=int((mass[which,0]>0).sum()),
                    weighted_total_responsibility=total,weighted_far_responsibility=far,
                    far_fraction=far/total if total else None,far_RGB_L1_upper_bound=float(kd['far_RGB_L1_upper_bound'][which].sum()))
            worst=np.argsort(-kd['far_RGB_L1_upper_bound'],kind='stable')[:10];worstrows=[]
            for j in worst:
                gid=int(ids[j]);worstrows.append(dict(source_index=gid,was_old_selected=bool(cand['previous_path'][gid]>0),
                    was_old_M1_unknown=bool(prior['unknown'][gid]),new_M1_unknown=bool(binding['unknown'][gid]),
                    expanded_BUILD_worst_far_fraction=float(fp['worst_view_far_fraction'][gid]),
                    evaluation_far_fraction=float(mass[j,3]/mass[j,0]) if mass[j,0]>0 else None,
                    evaluation_total_mass=float(mass[j,0]),projected_sigma_major_px=float(kd['projected_sigma_major'][j]),
                    far_RGB_L1_upper_bound=float(kd['far_RGB_L1_upper_bound'][j])))
            diagnosis=dict(post_evaluation_only=True,scope='Per-ID alpha*T and triangle color bound; not exact RGB damage allocation or physical ownership.',
                groups=group_stats,largest_far_bound_original_IDs=worstrows)
            js(folder/'EVAL_FAILURE_ID_DIAGNOSIS.json',diagnosis)
            rows.append(dict(view=c['view'],arms=row['arms'],coverage=row['coverage'],joint=row['joint_transfer'],
                M1_previous=row['M1_previous_projection'],M1_new=row['M1_projection'],visual=visual,path_support=row['path_support'],failure_ID_diagnosis=diagnosis))
            panels.append(folder/'comparison.png');allrows.append(dict(scene=scene,**rows[-1]))
        images=[Image.open(x).convert('RGB') for x in panels]
        sheet=Image.new('RGB',(images[0].width,sum(x.height for x in images)),'white');y=0
        for im in images:sheet.paste(im,(0,y));y+=im.height
        sheet.save(root/'ALL_EVALUATION_VIEWS.png')
        summaries[scene]=dict(source_count=s['source_count'],M1_transition=build['M1_transition'],
            selection_counts=build['footprint_counts'],selection_transition=transitions,
            scheduled_views=len(s['cameras']),evaluated_and_validated_views=len(rows),pass_counts=counts,
            locality_scorable_views=sum(r['arms']['specific']['target_interior']['pixels']>0 for r in rows),
            coverage_scorable_views=sum(r['coverage']['specific']['coverage_scorable'] for r in rows),
            previous_unknown_responsibility_range=[min(r['M1_previous']['source_unknown_mass_fraction'] for r in rows),max(r['M1_previous']['source_unknown_mass_fraction'] for r in rows)],
            new_unknown_responsibility_range=[min(r['M1_new']['source_unknown_mass_fraction'] for r in rows),max(r['M1_new']['source_unknown_mass_fraction'] for r in rows)],
            actual_scaled_budget=valid['actual_scaled_BUILD_RGB_L1'],budget_relative_errors=valid['budget_relative_errors'],
            prior_leaking_ID_readback=diagnostic,views=rows)
    total={arm:{k:sum(s['pass_counts'][arm][k] for s in summaries.values()) for k in ('locality','coverage','joint')} for arm in ARMS}
    js(unit/'SUMMARY.json',dict(utc=now(),scenes=summaries,pass_counts=total,
        scientific_verdict='UNCERTIFIED_CPU_MAPPING; finite authored-intent comparison only',
        scope='Expanded evidence has three times as many BUILD cameras. This does not isolate view diversity from evidence volume. No semantic, physical, native, or H1/H2/H3 superiority claim.'))
    print(json.dumps(dict(pass_counts=total,scenes={k:{x:v[x] for x in ('M1_transition','selection_counts','selection_transition')} for k,v in summaries.items()}),default=runtime.json_default),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);summarize(ap.parse_args().unit)
