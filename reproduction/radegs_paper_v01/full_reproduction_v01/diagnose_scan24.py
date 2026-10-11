"""CPU-only audit of sealed raw exports; never modifies model/data/thresholds."""
import csv
import datetime
import json
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

WORK=Path(__file__).resolve().parents[3]
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=HDD/'full_reproduction_v01/scan24_diagnosis'
ART=WORK/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01'
MODEL=HDD/'models/scan24_paper_text_half_30k'
DATA=HDD/'data/prepared/scan24'
sys.path.insert(0,str(WORK/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal


def quantiles(x):
    x=np.asarray(x);v=x[np.isfinite(x)]
    return dict(zip(['min','p01','p10','p50','p90','p99','max'],map(float,np.quantile(v,[0,.01,.1,.5,.9,.99,1])))) if v.size else None


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    state=HDD/'gradient_fix_v01/pilot/state'
    config=json.loads((state/'runner_config.json').read_text())
    verified={s:verify_seal(state/(s+'.seal.json'),s,config['inputs']) for s in ['smoke','train','export']}
    assert all(verified.values()),verified
    meta=json.loads((MODEL/'depth_normal/cameras_and_conventions.json').read_text())
    assert len(meta)==49 and len(list((MODEL/'depth_normal').glob('*.npz')))==49
    rows=[];frames={};reps=['0000','0012','0024','0036','0048']
    for cam in meta:
        name=cam['view'];file=MODEL/'depth_normal'/(name+'.npz')
        with np.load(file) as z:values={k:z[k] for k in z.files}
        dep=values['median_camera_z'][0];alpha=values['alpha'][0]
        W,H=cam['width'],cam['height'];assert dep.shape==(H,W)==(581,777)
        im=Image.open(DATA/'images'/(name+'.png'))
        # Exact C24 PILtoTorch mask resize (PIL default resampling), CPU array.
        mask=np.asarray(im.split()[3].resize((W,H)),dtype=np.float32)/255
        gt=np.stack([np.asarray(c.resize((W,H)),dtype=np.float32)/255 for c in im.split()[:3]],axis=-1)
        foreground=mask>=.5;opaque=alpha>=.5;positive=np.isfinite(dep)&(dep>0)
        valid=positive&(dep<8)&foreground&opaque
        masked=np.where(foreground&opaque,dep,0).astype(np.float32)
        e=np.asarray(cam['extrinsic'],dtype=np.float64);r=e[:3,:3];center=-r.T@e[:3,3]
        row={'view':name,'pixels':int(dep.size),'npz_sha256':sha256(file),
             'finite_by_channel':{k:int(np.isfinite(v).sum()) for k,v in values.items()},
             'nonfinite_by_channel':{k:int((~np.isfinite(v)).sum()) for k,v in values.items()},
             'depth_positive':int(positive.sum()),'depth_quantiles':quantiles(dep),
             'alpha_quantiles':quantiles(alpha),'alpha_gtmask_quantiles':quantiles(alpha[foreground]),
             'alpha_ge_05':int(opaque.sum()),'GT_mask_ge_05':int(foreground.sum()),
             'alpha_GT_intersection':int((foreground&opaque).sum()),
             'masked_finite_positive_lt8':int(valid.sum()),'masked_valid_quantiles':quantiles(dep[valid]),
             'GT_coverage_at_original_threshold':float(valid.sum()/foreground.sum()),
             'masked_negative':int((masked<0).sum()),'masked_ge8':int((masked>=8).sum()),
             'stride_valid_counts':{str(s):int(valid[:H//s*s:s,:W//s*s:s].sum()) for s in [1,2,4,8,16]},
             'rgb_quantiles':quantiles(values['rgb']),'rgb_outside_0_1_fraction':float(((values['rgb']<0)|(values['rgb']>1)).mean()),
             'rotation_det':float(np.linalg.det(r)),'rotation_orthogonality_max_error':float(abs(r@r.T-np.eye(3)).max()),
             'camera_center_scene':center.tolist(),'extrinsic_kind':'world-to-camera, direct C24 camera_utils R.T/T; no inversion before Open3D',
             'fx':cam['fx'],'fy':cam['fy']}
        rows.append(row)
        if name in reps:frames[name]=(gt,values,valid,foreground)
        print(json.dumps({'view':name,'valid':row['masked_finite_positive_lt8'],'coverage':row['GT_coverage_at_original_threshold'],'stride8':row['stride_valid_counts']['8'],'alpha_median':row['alpha_quantiles']['p50']}),flush=True)
    # No metrics here are held-out test/official DTU evaluation metrics.
    with (MODEL/'iteration_loss.jsonl').open() as f:losses=[json.loads(s) for s in f]
    assert len(losses)==30000 and {r['iteration'] for r in losses}==set(range(1,30001))
    windows=[]
    for lo,hi in [(1,100),(14001,15000),(15001,15100),(15101,16000),(19001,20000),(24001,25000),(29001,30000)]:
        x=[r for r in losses if lo<=r['iteration']<=hi]
        windows.append({'iterations':[lo,hi],'mean':{k:float(np.mean([r[k] for r in x])) for k in ['photo','distortion','normal','total','points']},'last':x[-1]})
    # Fixed, prespecified camera indices covering the sequence; no quality selection.
    fig,axes=plt.subplots(5,7,figsize=(21,16),constrained_layout=True)
    labels=['Dataset RGB (training view)','Rendered RGB (clipped display)','Alpha [0,1]','Median camera-z [1.5,4.5]','Original TSDF valid pixels','Blended normal (raw alphaT)','Depth-derived normal']
    for j,name in enumerate(reps):
        gt,v,valid,foreground=frames[name];dep=v['median_camera_z'][0]
        panels=[gt,np.clip(v['rgb'].transpose(1,2,0),0,1),v['alpha'][0],dep,valid,
                np.clip(.5+.5*v['blended_normal_camera'].transpose(1,2,0),0,1),
                np.clip(.5+.5*v['median_depth_normal_camera'].transpose(1,2,0),0,1)]
        for k,panel in enumerate(panels):
            ax=axes[j,k]
            if k==2:ax.imshow(panel,cmap='viridis',vmin=0,vmax=1)
            elif k==3:ax.imshow(np.where(dep>0,dep,np.nan),cmap='turbo',vmin=1.5,vmax=4.5)
            elif k==4:ax.imshow(panel,cmap='gray',vmin=0,vmax=1)
            else:ax.imshow(panel)
            ax.set_xticks([]);ax.set_yticks([])
            if j==0:ax.set_title(labels[k],fontsize=10)
            if k==0:ax.set_ylabel('View '+name,fontsize=12)
    fig.suptitle('scan24 paper-text 30k: fixed representative views; alpha>=0.5 AND dataset mask>=0.5; depth in scene units\nRaw arrays unchanged. RGB clipped only for display. No mesh/evaluation success claimed.',fontsize=14)
    figure=OUT/'scan24_rgb_alpha_depth_normal.png';fig.savefig(figure,dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(13,10),constrained_layout=True)
    it=np.array([r['iteration'] for r in losses]);smooth=lambda k:np.convolve([r[k] for r in losses],np.ones(100)/100,mode='valid')
    for k in ['photo','distortion','normal']:axes[0].plot(it[99:],smooth(k),label=k)
    axes[0].set_yscale('log');axes[0].set_ylabel('100-step mean (raw loss)');axes[0].legend()
    axes[1].plot(it,[r['points'] for r in losses]);axes[1].set_ylabel('Gaussian count')
    for ax in axes[:2]:ax.axvline(15001,color='red',linestyle='--');ax.set_xlabel('Iteration')
    axes[2].bar([r['view'] for r in rows],[r['GT_coverage_at_original_threshold']*100 for r in rows]);axes[2].tick_params(axis='x',rotation=90);axes[2].set_ylabel('Valid TSDF / GT mask (%)');axes[2].set_xlabel('Every exported view, original thresholds')
    fig.savefig(OUT/'scan24_training_and_coverage.png',dpi=140);plt.close(fig)
    result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified_stages':verified,'views':rows,'training_windows':windows,
            'summary':{'views':len(rows),'empty_full_resolution_valid_views':[r['view'] for r in rows if r['masked_finite_positive_lt8']==0],
                       'empty_stride8_valid_views':[r['view'] for r in rows if r['stride_valid_counts']['8']==0],
                       'total_original_threshold_valid_pixels':sum(r['masked_finite_positive_lt8'] for r in rows),
                       'overall_GT_coverage_at_original_threshold':sum(r['masked_finite_positive_lt8'] for r in rows)/sum(r['GT_mask_ge_05'] for r in rows)},
            'protocol_unchanged':{'depth_scale':1.0,'depth_max':8.0,'voxel_size':.002,'alpha_threshold':.5,'mask_threshold':.5},
            'visuals':[str(figure),str(OUT/'scan24_training_and_coverage.png')],
            'metrics_scope':'diagnostic training-view coverage/loss, not held-out NVS or DTU ground-truth geometric metrics'}
    atomic_json(OUT/'diagnosis.json',result)
    with (OUT/'views.csv').open('w') as f:
        keys=['view','pixels','depth_positive','alpha_ge_05','GT_mask_ge_05','alpha_GT_intersection','masked_finite_positive_lt8','GT_coverage_at_original_threshold','masked_negative','masked_ge8']
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows({k:r[k] for k in keys} for r in rows)
    master=json.loads((ART/'MASTER_STATUS.json').read_text());master.update(verified_stages=['smoke','train','export'],last_event='Verified seals; completed 49-view CPU audit and real array visualizations',next_action='reproduce Open3D DepthTouch failure on cached masked depth; distinguish empty/sparse inputs from API behavior',utc=result['utc']);master['experiment_counts'].update(verified_train=1,verified_export=1);atomic_json(ART/'MASTER_STATUS.json',master)
    print(json.dumps(result['summary'],indent=2),flush=True)


if __name__=='__main__':main()
