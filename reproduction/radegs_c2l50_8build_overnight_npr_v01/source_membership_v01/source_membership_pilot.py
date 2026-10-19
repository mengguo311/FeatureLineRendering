"""Read-only-source, calibrated CPU-EWA source-index membership pilot."""
import os, sys
sys.dont_write_bytecode = True
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json, hashlib, shutil, time
import numpy as np
from PIL import Image, ImageDraw
from source_membership import contributions, sample_pixels, assign

BASE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
R04=BASE/'c2l50_8build_overnight_npr_v01/rounds/r04'
OUT=BASE/'c2l50_8build_source_membership_v01'
JOINT_CODE=Path('/home/u00134/3dgs_line/gaer_c2l50_8build_joint_gs_v01/reproduction/radegs_c2l50_8build_joint_gs_v01')
sys.path.insert(0,str(JOINT_CODE))
from format import read_ply,activate
from renderer import project_cov, colors, render


def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False))


def label_image(rgb,labels,unknown):
    palette=np.array([[.55,.55,.55],[.05,.75,.95],[.98,.35,.14],[.40,.80,.20]])
    result=rgb.copy();mask=(labels>0)&~unknown
    result[mask]=.35*rgb[mask]+.65*palette[labels[mask]]
    result[unknown]=.55*rgb[unknown]+.45*palette[0]
    return result


def main():
    config_path=Path(__file__).with_name('source_membership_config.json')
    cfg=json.loads(config_path.read_text());s=cfg['scene']
    assert not OUT.exists(), 'Refuse to overwrite a pilot (preserve sealed results)'
    assert shutil.disk_usage('/').free>=2**30 and shutil.disk_usage(BASE).free>=10*2**30
    assert len(os.sched_getaffinity(0))<=2 and os.environ['CUDA_VISIBLE_DEVICES']==''
    reg=json.loads((BASE/'c2l50_multiview05_v01/REGISTRY.json').read_text())['scenes'][s]
    source_path=Path(reg['model']); assert digest(source_path)==reg['model_sha256']
    joint=BASE/'c2l50_8build_joint_gs_v01/scenes'/s/'model/merged_native.ply'
    original=read_ply(source_path)
    n=len(original); rng=json.loads((joint.parent/'RANGES.json').read_text())
    assert rng['source']['start']==0 and rng['source']['stop']==n
    jp=read_ply(joint);assert len(jp)>=n
    for key in original.dtype.names:
        assert np.array_equal(original[key],jp[key][:n]),('source prefix field differs',key)
    a=activate(original)
    views=cfg['fit_views']+cfg['reserved_views']; cams={v:next(c for c in reg['cameras'] if c['view']==v) for v in views}
    audit=dict(config_sha256=digest(config_path),source_sha256=digest(source_path),joint_sha256=digest(joint),source_count=n,source_prefix_equal=True,cpu_affinity=sorted(os.sched_getaffinity(0)),views={})
    outputs={};score=np.zeros((n,3));baseline=np.zeros((n,3));shuffled=np.zeros((n,3));exposure=np.zeros(n);vcount=np.zeros(n,dtype=np.uint8)
    stage=Path(str(OUT)+'.partial');assert not stage.exists();stage.mkdir(parents=True)
    write_json(stage/'INPUT_AUDIT.json',audit)
    for vi,v in enumerate(views):
        start=time.monotonic();c=cams[v];d=np.load(R04/'B'/s/'coupled'/('fit' if v in cfg['fit_views'] else v)/(v+'.npz'),allow_pickle=False)
        labels=d['labels']; unknown=d['unknown'];prob=d['probability']; raw=np.load(BASE/'c2l50_multiview05_v01/scenes'/s/'inputs'/(v+'.npz'),allow_pickle=False)
        native_rgb=raw['rgb'];native_alpha=raw['alpha'].squeeze()
        ref=render(a,c,background=(1,1,1),floor=.12**2)
        mae=float(np.mean(np.abs(ref['rgb']-native_rgb)));am=float(np.mean(np.abs(ref['alpha']-native_alpha)))
        gate=cfg['calibration_gate'];assert mae<=gate['full_rgb_mae_max'] and am<=gate['full_alpha_mae_max'],('renderer-calibration',v,mae,am)
        uv,z,cov=project_cov(a['means'],a['covariance'],c,.12**2)
        valid=(z>.2)&np.isfinite(z)&np.isfinite(uv).all(axis=1)&np.isfinite(cov).all(axis=(1,2))
        ids0=np.flatnonzero(valid);v_uv,v_z,v_cov,v_op=uv[valid],z[valid],cov[valid],a['opacity'][valid]
        samples=sample_pixels(labels,unknown,cfg['fit_samples_per_view'] if v in cfg['fit_views'] else cfg['reserved_samples_per_view'],cfg['sampler_seed']+vi)
        q_values=np.array([prob[y,x] for x,y,_ in samples]); shuffle=np.random.default_rng(cfg['sampler_seed']+100+vi).permutation(len(samples)); visited=np.zeros(n,dtype=bool)
        all_ids=[];all_weights=[];all_xy=[];mass_errors=[];pred=[];conf=[]
        for si,(x,y,sample_w) in enumerate(samples):
            local,w=contributions(v_uv,v_z,v_cov,v_op,x,y)
            ids=ids0[local]
            mass_errors.append(abs(w.sum()-float(ref['alpha'][y,x])))
            q=np.asarray(q_values[si],dtype=float)
            if q.min() < -1e-5 or abs(q.sum()-1)>2e-4: raise ValueError(('invalid r04 q',v,x,y,q))
            q=np.clip(q,0,None);q/=q.sum()
            if v in cfg['fit_views']:
                val=w*sample_w
                np.add.at(exposure,ids,val)
                for j in range(3):
                    np.add.at(score[:,j],ids,val*q[j])
                    np.add.at(shuffled[:,j],ids,val*q_values[shuffle[si],j])
                if len(w):
                    baseline[ids[np.argmax(w)],:]+=sample_w*q
                visited[ids[w>=cfg['pixel_w_min_for_view_presence']]]=True
            else:
                all_ids.append(ids.astype(np.int32));all_weights.append(w.astype(np.float32));all_xy.append((x,y))
        if v in cfg['fit_views']:vcount+=visited.astype(np.uint8)
        maxerr=max(mass_errors);assert maxerr<=gate['sample_mass_max_error'],('mass calibration',v,maxerr)
        audit['views'][v]=dict(rgb_mae=mae,alpha_mae=am,sample_mass_max_error=maxerr,samples=len(samples),valid_gaussians=int(valid.sum()),seconds=round(time.monotonic()-start,2))
        print(v,audit['views'][v],flush=True)
        if v in cfg['reserved_views']:
            offsets=np.r_[0,np.cumsum([len(x) for x in all_ids])]
            np.savez_compressed(stage/(v+'_reserved_samples.npz'),ids=np.concatenate(all_ids),weights=np.concatenate(all_weights),offsets=offsets,xy=np.array(all_xy),labels=labels[np.array(all_xy)[:,1],np.array(all_xy)[:,0]])
        outputs[v]=(native_rgb,labels,unknown,c)
        write_json(stage/'INPUT_AUDIT.json',audit)
    result,reason=assign(score,exposure,cfg['min_exposure'],cfg['min_label_fraction'])
    result[vcount<cfg['min_distinct_fit_views']]=0;reason[vcount<cfg['min_distinct_fit_views']]='single_view'
    control,creason=assign(baseline,baseline.sum(1),cfg['min_exposure'],cfg['min_label_fraction']);control[vcount<2]=0
    null,_=assign(shuffled,shuffled.sum(1),cfg['min_exposure'],cfg['min_label_fraction']);null[vcount<2]=0
    np.savez_compressed(stage/'SOURCE_MEMBERSHIP.npz',source_index=np.arange(n,dtype=np.int32),membership_score=score,exposure=exposure,distinct_fit_views=vcount,part_id=result,reason=reason,baseline_part_id=control,shuffled_part_id=null)
    summary=dict(status='DIAGNOSTIC_ONLY_NOT_CERTIFIED',original_source_count=n,part_counts={str(i):int(np.sum(result==i)) for i in range(4)},baseline_counts={str(i):int(np.sum(control==i)) for i in range(4)},null_counts={str(i):int(np.sum(null==i)) for i in range(4)},reasons={k:int(np.sum(reason==k)) for k in np.unique(reason)},reserved={})
    pal=np.array([[.55,.55,.55],[.05,.75,.95],[.98,.35,.14],[.40,.80,.20]])
    for v in views:
        native_rgb,labels,unknown,c=outputs[v];orig=render(a,c,background=(1,1,1),floor=.12**2)['rgb']
        original_colors=colors(a,c);part_colors=original_colors.copy();part_colors[result>0]=pal[result[result>0]]
        tint_asset=dict(means=a['means'],covariance=a['covariance'],opacity=a['opacity'],colors=part_colors)
        tint=render(tint_asset,c,background=(1,1,1),floor=.12**2)['rgb']
        edit_asset=dict(means=a['means'],covariance=a['covariance'],opacity=a['opacity'].copy(),colors=original_colors)
        edit_asset['opacity'][result==1]=0
        edit=render(edit_asset,c,background=(1,1,1),floor=.12**2)['rgb']
        panels=[orig,label_image(orig,labels,unknown),tint,edit]
        tiles=[Image.fromarray(np.uint8(np.clip(x,0,1)*255)) for x in panels]
        image=Image.new('RGB',(4*c['width'],c['height']+34),'white')
        for k,im in enumerate(tiles):image.paste(im,(k*c['width'],34))
        draw=ImageDraw.Draw(image)
        for k,title in enumerate(('Source RGB','r04 2D parts','Source-ID tinted','Remove source part 1')):draw.text((k*c['width']+8,10),v+' '+title,fill='black')
        image.save(stage/(v+'_FOUR_PANELS.jpg'),quality=90)
        if v in cfg['reserved_views']:
            data=np.load(stage/(v+'_reserved_samples.npz'));xy=data['xy'];target=data['labels'];ids=data['ids'];ww=data['weights'];off=data['offsets'];pred=[];valid_pred=[]
            for i in range(len(xy)):
                local=ids[off[i]:off[i+1]];w=ww[off[i]:off[i+1]];votes=np.bincount(result[local],weights=w,minlength=4);pred.append(int(np.argmax(votes[1:])+1) if len(w) and votes[1:].max()>votes[0] else 0)
            pred=np.array(pred);m=(pred>0)
            summary['reserved'][v]=dict(sample_pixels=len(xy),predicted_nonunknown=int(m.sum()),agreement_with_r04_2D_on_predicted=float(np.mean(pred[m]==target[m])) if m.any() else None,edited_rgb_mae=float(np.mean(np.abs(edit-orig))),note='Agreement is to weak r04 pseudo-labels, not physical part accuracy')
    write_json(stage/'SUMMARY.json',summary)
    write_json(stage/'OUTPUT_SHA256.json',{p.name:digest(p) for p in stage.iterdir() if p.is_file() and p.name!='OUTPUT_SHA256.json'})
    stage.rename(OUT)
    print('OUTPUT',OUT,'SUMMARY',summary,flush=True)

if __name__=='__main__':main()
