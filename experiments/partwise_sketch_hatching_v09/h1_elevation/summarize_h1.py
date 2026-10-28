"""Descriptive readout of frozen metrics; no selection or rerendering."""
import runtime
from runtime import ROOT as UNIT,js
import json
import numpy as np
from linked_asset import npz

def main():
    rows=json.loads((UNIT/'CAMERAS.json').read_text());metrics=json.loads((UNIT/'SUMMARY_METRICS.json').read_text())
    temp=json.loads((UNIT/'TEMPORAL.json').read_text());frames={r['key']:r for r in metrics};arc=[r for r in rows if 'index' in r]
    numbers=dict(temporal=temp['summary'],frames={},pair_results={},scope='Descriptive one-object summaries; repeated observations, unequal method coverage, no significance or pure-anchor claim')
    for row in rows:
        key=row['key'];r=frames[key];gen=json.loads((UNIT/'renders'/key/'GENERATION.json').read_text())
        numbers['frames'][key]=dict(camera=[row['azimuth'],row['elevation']],B0_paths=gen['paths'],B0_stops=gen['stops'],
            necessary_pixels=r['metrics']['natural']['B0']['regions']['necessary_interior']['pixels'],
            necessary_coverage={a:r['metrics']['natural'][a]['regions']['necessary_interior']['coverage_fraction'] for a in ('B0','B1')},
            rgb_effect={m:{a:r['metrics'][m][a]['target_rgb_effect'] for a in ('B0','B1')} for m in ('natural','matched')})
    for mode in ('natural','matched'):
        records=[]
        for pair in temp['pairs']:
            m=pair['metrics'][mode]
            records.append(dict(source=pair['source'],destination=pair['destination'],visibility=pair['visibility'],
                pixel_L1={a:m[a]['L1_per_common_pixel'] for a in ('B0','B1')},union_L1={a:m[a]['L1_per_union_ink'] for a in ('B0','B1')},
                center_distance={a:m[a]['centerlines']['centerline_to_actual_ink_mean_px'] for a in ('B0','B1')},
                missing_fraction={a:m[a]['centerlines']['common_visible_without_destination_ink_length_px']/m[a]['centerlines']['common_visible_with_source_ink_length_px'] if m[a]['centerlines']['common_visible_with_source_ink_length_px'] else None for a in ('B0','B1')}))
        numbers['pair_results'][mode]=records
    numbers['common_pixel_observations']=sum(p['visibility']['common_visible_pixels'] for p in temp['pairs'])
    numbers['source_target_pixel_observations']=sum(p['visibility']['source_target_pixels'] for p in temp['pairs'])
    numbers['common_fraction']=numbers['common_pixel_observations']/numbers['source_target_pixel_observations']
    numbers['natural_B1_not_lower_pixel_L1']=[f"{p['source']}->{p['destination']}" for p in numbers['pair_results']['natural'] if p['pixel_L1']['B1']>=p['pixel_L1']['B0']]
    numbers['natural_B1_not_lower_union_L1']=[f"{p['source']}->{p['destination']}" for p in numbers['pair_results']['natural'] if p['union_L1']['B1']>=p['union_L1']['B0']]
    numbers['arc_ranges']={a:dict(necessary_coverage=[min(numbers['frames'][r['key']]['necessary_coverage'][a] for r in arc),max(numbers['frames'][r['key']]['necessary_coverage'][a] for r in arc)],
        natural_rgb_effect=[min(numbers['frames'][r['key']]['rgb_effect']['natural'][a] for r in arc),max(numbers['frames'][r['key']]['rgb_effect']['natural'][a] for r in arc)]) for a in ('B0','B1')}
    numbers['far_absolute_ranges']={k:[min(r['metrics'][m][a]['regions'][k]['absolute_source_L1'] for r in metrics for m in ('natural','matched') for a in ('B0','B1')),
        max(r['metrics'][m][a]['regions'][k]['absolute_source_L1'] for r in metrics for m in ('natural','matched') for a in ('B0','B1'))] for k in ('far_other','far_background')}
    d=UNIT/'renders/006';c=npz(d/'COMMON.npz');pixel={}
    for arm in ('B0','B1'):
        f=npz(d/'natural'/arm/'FRAME.npz');pixel[arm]=dict(own_ink=float(f['own_ink'][185,157]),hybrid=f['hybrid'][185,157],absolute_source_L1=float(np.abs(f['hybrid'][185,157]-c['source'][185,157]).sum()))
    numbers['far_pixel_006']=dict(x=157,y=185,native_region=int(c['regions'][185,157]),source=c['source'][185,157],arms=pixel)
    js(UNIT/'REPORT_NUMBERS.json',numbers)
    short={k:v for k,v in numbers.items() if k not in ('pair_results','frames')}
    short['keyframes']={k:numbers['frames'][k] for k in ('BUILD','000','003','006','009','012')}
    print(json.dumps(short,default=runtime.json_default),flush=True)

if __name__=='__main__':main()
