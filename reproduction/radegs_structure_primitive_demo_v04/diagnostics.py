"""Post-freeze measurement only; never used to fit or select parameters."""
from common import *
import csv

def main():
    rows=[];details=[]
    for d in sorted((T/'results').iterdir()):
        if not (d/'SEAL.json').exists():continue
        s=json.loads((d/'RESULTS.json').read_text());a=dict(np.load(d/'optimized_primitives.npz'));b=dict(np.load(d/'initial_primitives.npz'));g=dict(np.load(d/'optimized_gaussians.npz'));layout=dict(np.load(d/'sampling_layout.npz'))
        active=[]
        for kind,ix in zip(a['type'],a['node_index']):
            active.extend(ix[[0]] if kind=='point' else ix[[0,3]] if kind=='line' else ix)
        active=np.unique(active);shift=np.linalg.norm(a['points'][active]-b['points'][active],axis=1);bound=a['bounds'][active]
        counts=np.bincount(layout['primitive_id'],minlength=s['primitives']);v=g['view_votes'];scene=d.name.split('_')[0]
        old=np.load(O/'results_v2'/scene/'balanced_gaussians.npz')['means'].shape[0]
        info={'unit':d.name,'old_3view_balanced_gaussians':int(old),'segments':s['segments'],'primitives':s['primitives'],'gaussians':s['derived_gaussians'],'line':s['type_counts'].get('line',0),'bezier':s['type_counts'].get('bezier',0),'point_residual':s['type_counts'].get('point',0),'raw_marked_observations':s['all_observations'],'assigned_observations':s['assigned_observations'],'merged_segment_fraction':s['merged_segments']/s['segments'],'active_control_nodes':len(active),'moved_active_nodes':int((shift>1e-10).sum()),'active_nodes_at_bound':int((shift>=bound*(1-1e-6)).sum()),'maximum_shift_over_bound':float((shift/np.maximum(bound,1e-30)).max()),'primitives_median_sample_count':float(np.median(counts)),'kernels_single_view_fraction':float((v==1).mean()),'initial_objective':s['optimization_initial']['objective'],'final_objective':s['optimization_final']['objective'],'runtime_seconds':s['runtime_seconds'],'peak_RSS_MiB':s['peak_rss_KiB']/1024,'asset_reload_exact':s['reload_render_bitexact']}
        rows.append(info);details.append({'summary':info,'kind_counts':s['kind_counts'],'reason_counts':s['reason_counts'],'camera_metrics':s['metrics']})
    js(T/'NUMERICAL_DIAGNOSTICS.json',{'not_model_selection':True,'units':details})
    with (T/'COUNTS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
