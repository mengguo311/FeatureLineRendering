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
from source_membership import contributions, sample_pixels, resolve_membership, shuffled_within_strata, winner_vote, replay_rgb, conflicting_views

BASE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
R04=BASE/'c2l50_8build_overnight_npr_v01/rounds/r04'
OUT=BASE/'c2l50_8build_source_membership_v01/ficus_cpu_ewa_source_index_pilot_v01'
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
    audit=dict(config_sha256=digest(config_path),source_sha256=digest(source_path),joint_sha256=digest(joint),source_count=n,source_prefix_equal=True,cpu_affinity=sorted(os.sched_getaffinity(0)),source_floor_variance=cfg['source_floor_variance'],registry_sha256=digest(BASE/'c2l50_multiview05_v01/REGISTRY.json'),joint_cpp_sha256=digest(JOINT_CODE/'ewa.cpp'),joint_renderer_sha256=digest(JOINT_CODE/'renderer.py'),joint_library_sha256=digest(BASE/'c2l50_8build_joint_gs_v01/build/libjoint.so'),code_sha256={p.name:digest(p) for p in Path(__file__).parent.glob('*.py')},views={})
    outputs={};score=np.zeros((n,3));baseline=np.zeros((n,3));shuffled=np.zeros((n,3));exposure=np.zeros(n);vcount=np.zeros(n,dtype=np.uint8);baseline_views=np.zeros(n,dtype=np.uint8)
    stage=Path(str(OUT)+'.partial');assert not stage.exists();stage.mkdir(parents=True)
    write_json(stage/'INPUT_AUDIT.json',audit)
    for vi,v in enumerate(views):
        start=time.monotonic();c=cams[v];label_path=R04/'B'/s/'coupled'/('fit' if v in cfg['fit_views'] else v)/(v+'.npz');input_path=BASE/'c2l50_multiview05_v01/scenes'/s/'inputs'/(v+'.npz')
        d=np.load(label_path,allow_pickle=False)
        labels=d['labels']; unknown=d['unknown'];prob=d['probability']; raw=np.load(input_path,allow_pickle=False)
        native_rgb=raw['rgb'];native_alpha=raw['alpha'].squeeze();floor=cfg['source_floor_variance']
        ref=render(a,c,background=(1,1,1),floor=floor)
        mae=float(np.mean(np.abs(ref['rgb']-native_rgb)));am=float(np.mean(np.abs(ref['alpha']-native_alpha)))
        subject=(labels>0)&(~unknown)
        smae=float(np.mean(np.abs(ref['rgb'][subject]-native_rgb[subject])));sam=float(np.mean(np.abs(ref['alpha'][subject]-native_alpha[subject])))
        gate=cfg['calibration_gate'];assert mae<=gate['full_rgb_mae_max'] and am<=gate['full_alpha_mae_max'] and smae<=gate['subject_rgb_mae_max'] and sam<=gate['subject_alpha_mae_max'],('renderer-calibration',v,mae,am,smae,sam)
        uv,z,cov=project_cov(a['means'],a['covariance'],c,floor)
        valid=(z>.2)&np.isfinite(z)&np.isfinite(uv).all(axis=1)&np.isfinite(cov).all(axis=(1,2))
        ids0=np.flatnonzero(valid);v_uv,v_z,v_cov,v_op=uv[valid],z[valid],cov[valid],a['opacity'][valid]
        samples=sample_pixels(labels,unknown,cfg['fit_samples_per_view'] if v in cfg['fit_views'] else cfg['reserved_samples_per_view'],cfg['sampler_seed']+vi)
        q_values=np.array([prob[y,x] for x,y,_ in samples]); sample_labels=np.array([labels[y,x] for x,y,_ in samples]); q_shuffled=shuffled_within_strata(q_values,sample_labels,cfg['sampler_seed']+100+vi)
        visited=np.zeros(n,dtype=bool);winner_seen=np.zeros(n,dtype=bool);vscore=np.zeros((n,3));vexp=np.zeros(n)
        all_ids=[];all_weights=[];all_xy=[];mass_errors=[];rgb_errors=[];source_colors=colors(a,c)
        for si,(x,y,sample_w) in enumerate(samples):
            local,w=contributions(v_uv,v_z,v_cov,v_op,x,y)
            ids=ids0[local]
            mass_errors.append(abs(w.sum()-float(ref['alpha'][y,x])))
            rgb_errors.append(float(np.max(np.abs(replay_rgb(ids,w,source_colors,np.ones(3))-ref['rgb'][y,x]))))
            q=np.asarray(q_values[si],dtype=float)
            if q.min() < -1e-5 or abs(q.sum()-1)>2e-4: raise ValueError(('invalid r04 q',v,x,y,q))
            q=np.clip(q,0,None);q/=q.sum()
            if v in cfg['fit_views']:
                val=w*sample_w
                np.add.at(exposure,ids,val);np.add.at(vexp,ids,val)
                for j in range(3):
                    np.add.at(score[:,j],ids,val*q[j]);np.add.at(vscore[:,j],ids,val*q[j])
                    np.add.at(shuffled[:,j],ids,val*q_shuffled[si,j])
                if len(w):
                    winner,mass=winner_vote(ids,w,sample_w)
                    baseline[winner,:]+=mass*q
                    if w[np.argmax(w)]>=cfg['pixel_w_min_for_view_presence']: winner_seen[winner]=True
                visited[ids[w>=cfg['pixel_w_min_for_view_presence']]]=True
            else:
                all_ids.append(ids.astype(np.int32));all_weights.append(w.astype(np.float32));all_xy.append((x,y))
        if v in cfg['fit_views']:
            vcount+=visited.astype(np.uint8);baseline_views+=winner_seen.astype(np.uint8)
            np.savez_compressed(stage/(v+'_build_samples.npz'),xy=np.array([(x,y) for x,y,_ in samples],dtype=np.int32),sampling_weight=np.array([w for x,y,w in samples]),label=sample_labels,score=vscore,exposure=vexp,visited=visited,winner_seen=winner_seen)
        maxerr=max(mass_errors);rgb_err=max(rgb_errors)
        assert maxerr<=gate['sample_mass_max_error'] and rgb_err<=gate['sample_rgb_max_error'],('sample calibration',v,maxerr,rgb_err)
        audit['views'][v]=dict(rgb_mae=mae,alpha_mae=am,subject_rgb_mae=smae,subject_alpha_mae=sam,sample_mass_max_error=maxerr,sample_rgb_max_error=rgb_err,label_sha256=digest(label_path),input_sha256=digest(input_path),samples=len(samples),valid_gaussians=int(valid.sum()),seconds=round(time.monotonic()-start,2))
        print(v,audit['views'][v],flush=True)
        if v in cfg['reserved_views']:
            offsets=np.r_[0,np.cumsum([len(x) for x in all_ids])]
            np.savez_compressed(stage/(v+'_reserved_samples.npz'),ids=np.concatenate(all_ids),weights=np.concatenate(all_weights),offsets=offsets,xy=np.array(all_xy),labels=labels[np.array(all_xy)[:,1],np.array(all_xy)[:,0]])
        outputs[v]=(native_rgb,labels,unknown,c)
        write_json(stage/'INPUT_AUDIT.json',audit)
    params=dict(min_exposure=cfg['min_exposure'],min_fraction=cfg['min_label_fraction'],min_views=cfg['min_distinct_fit_views'])
    result,reason=resolve_membership(score,exposure,vcount,**params)
    build_scores=[np.load(stage/(v+'_build_samples.npz'))['score'] for v in cfg['fit_views']]
    conflict=conflicting_views(build_scores[0],build_scores[1],cfg['view_conflict_min_mass'],cfg['view_conflict_min_fraction'])
    result[conflict]=0;reason[conflict]='view_conflict'
    control,creason=resolve_membership(baseline,baseline.sum(1),baseline_views,**params)
    null,nreason=resolve_membership(shuffled,shuffled.sum(1),vcount,**params)
    np.savez_compressed(stage/'SOURCE_MEMBERSHIP.npz',source_index=np.arange(n,dtype=np.int32),membership_score=score,exposure=exposure,distinct_fit_views=vcount,part_id=result,reason=reason,baseline_part_id=control,baseline_distinct_fit_views=baseline_views,shuffled_part_id=null)
    summary=dict(status='DIAGNOSTIC_ONLY_NOT_CERTIFIED',original_source_count=n,part_counts={str(i):int(np.sum(result==i)) for i in range(4)},baseline_counts={str(i):int(np.sum(control==i)) for i in range(4)},null_counts={str(i):int(np.sum(null==i)) for i in range(4)},reasons={k:int(np.sum(reason==k)) for k in np.unique(reason)},eligible_definition='ONLY sampled pixels with known r04 pseudo-label; unknown footprint not tested',reserved={})
    pal=np.array([[.55,.55,.55],[.05,.75,.95],[.98,.35,.14],[.40,.80,.20]])
    for v in views:
        native_rgb,labels,unknown,c=outputs[v];floor=cfg['source_floor_variance'];orig=render(a,c,background=(1,1,1),floor=floor)['rgb']
        original_colors=colors(a,c);panels=[orig,label_image(orig,labels,unknown)]
        edits={}; edit_stats={}
        for arm,part in (('alphaT',result),('winner',control),('shuffled',null)):
            part_colors=original_colors.copy();part_colors[part>0]=pal[part[part>0]]
            tint_asset=dict(means=a['means'],covariance=a['covariance'],opacity=a['opacity'],colors=part_colors)
            tint=render(tint_asset,c,background=(1,1,1),floor=floor)['rgb'];panels.append(tint)
            edit_asset=dict(means=a['means'],covariance=a['covariance'],opacity=a['opacity'].copy(),colors=original_colors)
            edit_asset['opacity'][part==1]=0
            edit=render(edit_asset,c,background=(1,1,1),floor=floor)['rgb'];edits[arm]=edit;panels.append(edit)
            delta=np.mean(np.abs(edit-orig),axis=2);target=(labels==1)&~unknown;other=(labels>=2)&~unknown
            edit_stats[arm]=dict(changed_target_mean=float(delta[target].mean()),changed_other_mean=float(delta[other].mean()),changed_whole_mean=float(delta.mean()),note='Compared to r04 weak pixel labels, not semantic accuracy')
        # Orig, r04, then per-arm tinted and independently edited source-only renders.
        titles=('Source RGB','r04 2D parts','alphaT source-ID','alphaT remove 1','Winner source-ID','Winner remove 1','Shuffle source-ID','Shuffle remove 1')
        tiles=[Image.fromarray(np.uint8(np.clip(x,0,1)*255)) for x in panels]
        image=Image.new('RGB',(len(tiles)*c['width'],c['height']+34),'white')
        for k,im in enumerate(tiles):image.paste(im,(k*c['width'],34))
        draw=ImageDraw.Draw(image)
        for k,title in enumerate(titles):draw.text((k*c['width']+8,10),v+' '+title,fill='black')
        image.save(stage/(v+'_EIGHT_PANELS.jpg'),quality=90)
        summary.setdefault('edit',{})[v]=edit_stats
        if v in cfg['reserved_views']:
            data=np.load(stage/(v+'_reserved_samples.npz'));xy=data['xy'];target=data['labels'];ids=data['ids'];ww=data['weights'];off=data['offsets'];arm_metrics={}
            for arm,part in (('alphaT',result),('winner',control),('shuffled',null)):
                pred=[]
                for i in range(len(xy)):
                    local=ids[off[i]:off[i+1]];w=ww[off[i]:off[i+1]];votes=np.bincount(part[local],weights=w,minlength=4)
                    pred.append(int(np.argmax(votes[1:])+1) if len(w) and votes[1:].max()>votes[0] else 0)
                pred=np.asarray(pred);m=pred>0
                arm_metrics[arm]=dict(predicted_nonunknown=int(m.sum()),conditional_pseudolabel_agreement=float(np.mean(pred[m]==target[m])) if m.any() else None)
            summary['reserved'][v]=dict(sample_pixels=len(xy),arms=arm_metrics,note='Stratified sample/conditional r04 pseudo-label agreement, not full-scene or true physical accuracy')
    write_json(stage/'SUMMARY.json',summary)
    write_json(stage/'OUTPUT_SHA256.json',{p.name:digest(p) for p in stage.iterdir() if p.is_file() and p.name!='OUTPUT_SHA256.json'})
    stage.rename(OUT)
    print('OUTPUT',OUT,'SUMMARY',summary,flush=True)

if __name__=='__main__':main()
