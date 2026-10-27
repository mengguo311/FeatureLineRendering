"""Read-only numerical payload summary; writes only a new handoff summary."""
import runtime
from runtime import js
import json
UNIT=runtime.ROOT/'units/unit_003'
def main():
    temporal=json.loads((UNIT/'TEMPORAL.json').read_text());out={}
    for sequence,s in temporal['sequences'].items():
        frames=s['frame_metrics'];metrics=[x['global_absolute_difference'] for x in frames]
        rangeof=lambda v:[min(v),max(v)]
        out[sequence]=dict(visible_fraction=s['status_counts']['visible']/(36*s['frames']),
            object_coverage_range=rangeof([f['object_ink_coverage'] for f in frames]),
            seat_coverage_range=rangeof([f['seat_ink_coverage'] for f in frames if f['seat_ink_coverage'] is not None]),
            global_far_other_raw_L1_range=rangeof([m['far_other']['raw_L1_sum'] for m in metrics]),
            global_far_background_raw_L1_range=rangeof([m['far_background']['raw_L1_sum'] for m in metrics]),
            global_far_fraction_range=rangeof([m['far_raw_fraction'] for m in metrics]))
    times=[];visible=[]
    for p in sorted((UNIT/'renders').glob('*/*/RENDER_RECEIPT.json')):
        r=json.loads(p.read_text());times.append(r['seconds']);visible.append(r['observations']['status_counts'].get('visible',0))
    times.sort();out['render_seconds']=dict(count=len(times),min=times[0],median=times[len(times)//2],max=times[-1])
    out['visible_anchor_range']=[min(visible),max(visible)]
    out['events']=[{k:v for k,v in e.items() if k!='anchor'} for e in temporal['events']]
    js(UNIT/'SAVED_SUMMARY.json',out);print(json.dumps(out,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
