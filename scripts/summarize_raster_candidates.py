#!/usr/bin/env python3
"""Join immutable numerical artifacts; visual decisions are separately attributed."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_raster_candidates import OUT,ARMS,git,sha,dump


def read(p):return json.loads(p.read_text())


def main():
    if git('branch','--show-current')!='raster-state-candidates':raise RuntimeError('wrong branch')
    m=read(OUT/'MANIFEST.json');p=OUT/'lego';s1=read(p/'step1.json');s2=read(p/'step2.json');s3=read(p/'step3.json');s4=read(p/'step4.json');r=read(p/'render.json')
    arms={}
    for a in ARMS:
        st=s3['arms'].get(a,{})
        arms[a]={k:v for k,v in s4['arms'][a].items() if k!='path_source_indices'}
        arms[a].update(observations=st.get('observations'),clusters=st.get('accepted',0),median_support_views=st.get('accepted_support_median'),
                       render_means={mode:r['means'][mode][a] for mode in r['means']})
    channel_stats={}
    for name in m['fields']['arm_channels']['D']:
        rows=[x for x in s2['views'] if x['mode']=='real' and x['channel']==name]
        reasons={}
        for x in rows:
            for k,n in x['reasons'].items():reasons[k]=reasons.get(k,0)+n
        channel_stats[name]=dict(samples=sum(x['input_samples'] for x in rows),accepted=sum(x['accepted'] for x in rows),reasons=reasons,
            median_of_accepted_view_reprojection_medians=float(np.median([x['accepted_reprojection_median'] for x in rows])),
            mean_silhouette_fraction=float(np.mean([v['channels'][name]['silhouette_fraction'] for v in s1['views']])))
    access={str(f.relative_to(OUT)):read(f) for f in OUT.glob('*/access_*.json')}
    secondary={k:read(OUT/'chair_transfer'/f'{k}.json') for k in ['smoke','step1','step2','step3']}
    inputs=[p/'step1.json',p/'step2.json',p/'step3.json',p/'step4.json',p/'render.json',p/'DECISION.json',
            p/'diagnostics/audit.json',p/'diagnostics/region_trace.json',OUT/'chair_transfer/step3.json']
    stages=['smoke','baseline','step1','step2','step3','step4_smoke','step4','render']
    result=dict(schema=1,generated_at_commit=git('rev-parse','HEAD'),base_commit=m['base_commit'],manifest_sha256=sha(OUT/'MANIFEST.json'),
        script_sha256=sha(__file__),decision=read(p/'DECISION.json'),scope=m['state']['type'],official_rgb=r['official_rgb'],
        primary='lego',train_views=m['train_indices'],test_sealed=m['test_sealed'],arms=arms,channel_anchors=channel_stats,
        primary_k4_k8_mean_mask_jaccard=float(np.mean([v['k4_k8_jaccard'] for v in s1['views']])),
        matched_null_comparisons=s3['null_comparison'],ink_calibration=r['calibration'],
        videos=r['videos'],primary_seconds={k:read(p/f'{k}.json')['seconds'] for k in stages},
        source_audit=read(p/'diagnostics/audit.json')['sources'],D_overlapping_source_survival=read(p/'diagnostics/audit.json')['D_overlapping_source_survival'],
        region_trace=read(p/'diagnostics/region_trace.json')['regions'],
        secondary=dict(scope='4 TRAIN views, Step1-3 plus initial linelets; no complete NPR claim',views=m['secondary_cheap_indices'],
            arms=secondary['step3']['arms'],matched=secondary['step3']['null_comparison'],
            k4_k8_mean_mask_jaccard=float(np.mean([v['k4_k8_jaccard'] for v in secondary['step1']['views']])),
            seconds={k:d['seconds'] for k,d in secondary.items()}),
        checks=dict(stage_failures={k:v['failure'] for k,v in access.items() if 'failure' in v},
            per_stage_rgb_reads={k:v['rgb_reads'] for k,v in access.items()},
            tests='33 passing unit tests; see TEST_RESULTS.txt',mesh_precision_recall_computed=False,
            original_GS_training_split_independently_verified=False),
        input_artifact_sha256={str(f.relative_to(OUT)):sha(f) for f in inputs})
    dump(OUT/'RESULTS.json',result)
    for a,d in arms.items():print(a,d['new_linelets'],d['new_in_chains'],d['final_chains'],d['render_means']['native']['visible_length_px'])


if __name__=='__main__':main()
