"""Frozen quality/dose gates with native800 calibration and area400 measurements."""
import hashlib
from pathlib import Path
import time
import cv2
import numpy as np
from .foundation import freeze_json,native_render,replay_native,calibration_metrics,qualification_metrics,save_sheet
from .corrected_sampling import area_downsample,stock_reference
from .corrected_layers import AreaLayers
from .multiscene import controlled_asset,perturbation_specs,seed_eligibility,controlled_eligibility
from .multiscene_qualification import save_grid


def calibrated_view(asset,camera,selected=None,outside=None):
    n=len(asset['mu']);selected=np.zeros(n,bool) if selected is None else selected
    outside=np.zeros(n,bool) if outside is None else outside
    K=np.asarray(camera['native_K']);w=np.asarray(camera['w2c'])
    white=native_render(asset,K,w,800,800,1);black=native_render(asset,K,w,800,800,0)
    replay=replay_native(white,800,800,selected,outside,1)
    calibration=calibration_metrics(white,black['stock_rgb'],replay)
    for bg,state in [(1,white),(0,black)]:
        stock=stock_reference(asset,w,camera['FoVx'],camera['FoVy'],bg)
        error=float(np.abs(stock-state['stock_rgb']).max())
        calibration[f'stock_top_level_{bg}_max_abs']=error
        calibration['passed'] &= bool(np.isfinite(error) and error<=1/255)
    rgb={1:area_downsample(white['stock_rgb']),0:area_downsample(black['stock_rgb'])}
    maps={k:area_downsample(replay[k]) for k in ['alpha','selected','outside']}
    maps['alpha_native']=area_downsample(1-white['final_T'])
    calibration['resolution']=800
    return white,rgb,maps,calibration


def reference(camera):
    p=Path(camera['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=camera['sha256']:raise ValueError('photograph hash changed')
    rgba=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
    if rgba is None or rgba.shape!=(800,800,4):raise ValueError('expected frozen 800 RGBA')
    rgba=rgba[:,:,[2,1,0,3]].astype('f8')/255
    return ({bg:area_downsample(rgba[:,:,:3]*rgba[:,:,3:]+bg*(1-rgba[:,:,3:])) for bg in [0,1]},area_downsample(rgba[:,:,3]))


def _new_output(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'native').mkdir();(output/'full_resolution').mkdir();return output


def measure_quality(asset,cameras,cfg,output):
    output=_new_output(output);rows=[];calibration=[];panels=[];start=time.monotonic()
    for camera in cameras:
        i,split=camera['index'],camera['split'];gt,alpha=reference(camera);roi=alpha>=cfg['native']['alpha_roi']
        state,rgb,maps,cal=calibrated_view(asset,camera);calibration.append(dict(view=i,split=split,**cal))
        cache=dict(roi=roi,alpha=alpha,**{f'rgb_{bg}':rgb[bg] for bg in [0,1]},**{f'gt_{bg}':gt[bg] for bg in [0,1]})
        np.savez_compressed(output/f'native/{split}_{i:03d}.npz',**cache)
        if split=='train':np.savez_compressed(output/f'native/state_{i:03d}.npz',**state)
        for bg in [0,1]:
            rows.append(dict(split=split,view=i,background=bg,**qualification_metrics(gt[bg],rgb[bg],roi)))
            current=[(f'{split} {i} bg{bg} reference',gt[bg]),('native800 area400',rgb[bg]),('absolute error x5',abs(rgb[bg]-gt[bg])*5)]
            save_sheet(output/f'full_resolution/{split}_{i:03d}_{bg}.png',current)
            if i in cfg['visuals']['fixed_train']:panels.extend((t,cv2.resize(im,(200,200),interpolation=cv2.INTER_AREA)) for t,im in current)
        print('quality',split,i,cal['passed'],flush=True)
    save_grid(output/'quality.png',panels,3)
    eligibility=seed_eligibility(rows,cfg);eligibility['calibration_pass']=all(r['passed'] for r in calibration)
    eligibility['passed'] &= eligibility['calibration_pass']
    report=dict(rows=rows,calibration=calibration,eligibility=eligibility,sampling='native800_area400',elapsed_seconds=time.monotonic()-start)
    freeze_json(output/'quality.json',report);return report


def qualify_parent(asset,cameras,cfg,output,frozen_parent=None):
    output=_new_output(output);specs=perturbation_specs(cfg)
    _,parents,selected,_=controlled_asset(asset,specs[0],cfg)
    low,high=np.quantile(asset['mu'].astype(float),cfg['probe']['box_quantiles'],axis=0)
    margin=cfg['probe']['box_margin_diagonal']*np.linalg.norm(high-low);low-=margin;high+=margin
    outside=np.any((asset['mu']<low)|(asset['mu']>high),axis=1)
    frozen=dict(original_count=len(asset['mu']),selected_count=int(selected.sum()),parent_mask_sha256=hashlib.sha256(selected.tobytes()).hexdigest(),parameter_hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in asset.items()},box=[low.tolist(),high.tolist()],specifications=specs)
    if frozen_parent is not None and frozen!=frozen_parent:raise ValueError('archived parent/specification hash mismatch')
    freeze_json(output/'parent_frozen.json',frozen)
    np.savez_compressed(output/'native/parents.npz',parents=parents,selected=selected)
    baseline={};calibration=[];coverage=[];samples=[];start=time.monotonic()
    for camera in cameras:
        i=camera['index'];state,rgb,maps,cal=calibrated_view(asset,camera,selected,outside)
        calibration.append(dict(view=i,**cal));roi=maps['alpha_native']>=cfg['native']['alpha_roi']
        mass=float(maps['alpha'][roi].sum());total=float(maps['alpha'].sum())
        cov=float(maps['selected'][roi].sum()/mass) if mass else 0
        outside_mass=float(maps['outside'].sum()/total) if total else 1
        layers=AreaLayers(state);quantiles=layers.quantiles()
        K=np.asarray(camera['K']);samples.extend((quantiles[:,:,1][roi]/np.sqrt(K[0,0]*K[1,1])).tolist())
        np.savez_compressed(output/f'native/parent_{i:03d}.npz',**state)
        np.savez_compressed(output/f'native/measurement_{i:03d}.npz',rgb_0=rgb[0],rgb_1=rgb[1],roi=roi,depth_quantiles=quantiles,**maps)
        coverage.append(dict(view=i,selected=cov,outside=outside_mass,mass=mass,roi_pixels=int(roi.sum())))
        baseline[i]=dict(rgb=rgb,roi=roi,mass=mass,selected=cov)
        print('parent',i,cal['passed'],flush=True)
        del layers
    variants=[]
    for spec in specs:
        child,_,_,minor=controlled_asset(asset,spec,cfg);rows=[];cover=[];cal=[];panels=[]
        np.savez_compressed(output/f"native/{spec['name']}_parameters.npz",**child)
        for camera in cameras:
            i=camera['index'];base=baseline[i]
            state,rgb,maps,c=calibrated_view(child,camera,minor);cal.append(dict(view=i,**c))
            cover.append(dict(view=i,selected=base['selected'],minor=float(maps['selected'][base['roi']].sum()/base['mass']) if base['mass'] else 0))
            np.savez_compressed(output/f"native/{spec['name']}_{i:03d}.npz",**state)
            for bg in [0,1]:
                original=base['rgb'][bg]
                rows.append(dict(view=i,background=bg,**qualification_metrics(original,rgb[bg],base['roi'])))
                current=[(f'{i} bg{bg} parent',original),(spec['name'],rgb[bg]),('absolute error x10',abs(rgb[bg]-original)*10)]
                save_sheet(output/f"full_resolution/{spec['name']}_{i:03d}_{bg}.png",current)
                if i in cfg['visuals']['fixed_train']:panels.extend((t,cv2.resize(im,(200,200),interpolation=cv2.INTER_AREA)) for t,im in current)
        save_grid(output/f"{spec['name']}.png",panels,3)
        eligibility=controlled_eligibility(rows,cover,cfg);eligibility['calibration_pass']=all(r['passed'] for r in cal)
        eligibility['passed'] &= eligibility['calibration_pass']
        variants.append(dict(**spec,rows=rows,coverage=cover,calibration=cal,eligibility=eligibility))
        print('dose',spec['name'],eligibility,flush=True)
        if time.monotonic()-start>cfg['budget']['prerequisite_seconds_per_scene']:raise TimeoutError('preregistered prerequisite budget exceeded')
    delta=float(np.median(samples)) if samples else None
    valid=bool(all(r['passed'] for r in calibration) and delta is not None and np.isfinite(delta) and delta>0 and all(r['outside']<=cfg['native']['outside_mass_max'] for r in coverage))
    report=dict(calibration=calibration,coverage=coverage,delta=delta,delta_foreground_rays=len(samples),box=[low.tolist(),high.tolist()],variants=variants,valid_parent_geometry=valid,sampling='native800_area400',elapsed_seconds=time.monotonic()-start)
    freeze_json(output/'qualification.json',report);return report
