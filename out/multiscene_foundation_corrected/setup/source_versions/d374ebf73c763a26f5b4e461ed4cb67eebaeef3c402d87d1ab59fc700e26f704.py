"""Stock-renderer measurements for the two separately registered routes."""
import hashlib
from pathlib import Path
import time
import cv2
import numpy as np
from .foundation import (freeze_json, native_render, replay_native, calibration_metrics,
                         qualification_metrics, save_sheet)
from .multiscene import perturbation_specs, controlled_asset, controlled_eligibility, seed_eligibility


def save_grid(path,panels,columns=3):
    if not panels:
        raise ValueError('no reached image panels')
    height,width=panels[0][1].shape[:2]
    rows=(len(panels)+columns-1)//columns
    sheet=np.full((rows*(height+28),columns*width,3),255,np.uint8)
    for i,(title,rgb) in enumerate(panels):
        y,x=(i//columns)*(height+28),(i%columns)*width
        sheet[y+28:y+28+height,x:x+width]=np.round(np.clip(rgb,0,1)*255).astype('u1')[:,:,::-1]
        cv2.putText(sheet,title,(x+4,y+19),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,0,0),1,cv2.LINE_AA)
    ok,data=cv2.imencode('.png',sheet,[cv2.IMWRITE_PNG_COMPRESSION,6])
    if not ok: raise RuntimeError('PNG encoder failed')
    with Path(path).open('xb') as stream:stream.write(data.tobytes())


def measure_quality(asset,cameras,cfg,output,size=400):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'native').mkdir();(output/'full_resolution').mkdir()
    rows=[];calibration=[];panels=[]
    for camera in cameras:
        i,split=camera['index'],camera['split'];p=Path(camera['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=camera['sha256']:
            raise ValueError('frozen photograph hash mismatch')
        rgba=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)
        if rgba is None or rgba.shape[2]!=4:
            raise ValueError('expected RGBA synthetic photograph')
        rgba=rgba[:,:,[2,1,0,3]].astype(float)/255
        alpha=cv2.resize(rgba[:,:,3],(size,size),interpolation=cv2.INTER_AREA)
        roi=alpha>=.5;K=np.array(camera['K']);w2c=np.array(camera['w2c'])
        rendered={bg:native_render(asset,K,w2c,size,size,bg) for bg in [0,1]}
        if split=='train':
            replay=replay_native(rendered[1],size,size,np.zeros(len(asset['mu']),bool),
                                 np.zeros(len(asset['mu']),bool),1)
            calibration.append(dict(view=i,**calibration_metrics(rendered[1],rendered[0]['stock_rgb'],replay)))
        cache=dict(roi=roi)
        for bg in [0,1]:
            gt=rgba[:,:,:3]*rgba[:,:,3:]+bg*(1-rgba[:,:,3:])
            gt=cv2.resize(gt,(size,size),interpolation=cv2.INTER_AREA)
            rgb=rendered[bg]['stock_rgb'];metrics=qualification_metrics(gt,rgb,roi)
            rows.append(dict(split=split,view=i,background=bg,**metrics))
            cache[f'rgb_{bg}']=rgb;cache[f'gt_{bg}']=gt
            current=[(f'{split} {i} bg{bg} GT',gt),('stock render',rgb),('abs error x5',np.abs(rgb-gt)*5)]
            save_sheet(output/f'full_resolution/{split}_{i:03d}_{bg}.png',current)
            if i in cfg['visuals']['fixed_train'] or len(cameras)==2:
                panels.extend([(label,cv2.resize(img,(200,200),interpolation=cv2.INTER_AREA)) for label,img in current])
        np.savez_compressed(output/f'native/{split}_{i:03d}.npz',**cache)
    if panels:save_grid(output/'quality.png',panels,3)
    eligibility=seed_eligibility(rows,cfg)
    eligibility['calibration_pass']=all(r['passed'] for r in calibration)
    eligibility['passed']=eligibility['passed'] and eligibility['calibration_pass']
    report=dict(rows=rows,calibration=calibration,eligibility=eligibility)
    freeze_json(output/'quality.json',report)
    return report


def qualify_parent(asset, cameras, cfg, output, size=400):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    # The first exclusive artifact freezes selection and geometry before any render.
    specs=perturbation_specs(cfg)
    _,parents,selected,_=controlled_asset(asset,specs[0],cfg)
    low,high=np.quantile(asset['mu'].astype(float),cfg['probe']['box_quantiles'],axis=0)
    margin=cfg['probe']['box_margin_diagonal']*np.linalg.norm(high-low);low-=margin;high+=margin
    outside=np.any((asset['mu']<low)|(asset['mu']>high),axis=1)
    freeze_json(output/'parent_frozen.json',dict(original_count=len(asset['mu']),
        selected_count=int(selected.sum()),parent_mask_sha256=hashlib.sha256(selected.tobytes()).hexdigest(),
        parameter_hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in asset.items()},
        box=[low.tolist(),high.tolist()],specifications=specs))
    (output/'native').mkdir();(output/'full_resolution').mkdir()
    np.savez_compressed(output/'native/parents.npz',parents=parents,selected=selected)
    baseline={};calibration=[];coverage=[];samples=[];start=time.monotonic()
    for camera in cameras:
        i=camera['index'];K=np.array(camera['K']);w2c=np.array(camera['w2c'])
        white=native_render(asset,K,w2c,size,size,1);black=native_render(asset,K,w2c,size,size,0)
        replay=replay_native(white,size,size,selected,outside,1)
        cal=dict(view=i,**calibration_metrics(white,black['stock_rgb'],replay));calibration.append(cal)
        roi=white['final_T']<=1-cfg['native']['alpha_roi'];mass=float(replay['alpha'][roi].sum(dtype=float))
        cov=float(replay['selected'][roi].sum(dtype=float)/mass) if mass else 0.
        total=float(replay['alpha'].sum(dtype=float))
        outside_mass=float(replay['outside'].sum(dtype=float)/total) if total else 1.
        coverage.append(dict(view=i,selected=cov,outside=outside_mass,mass=mass,roi_pixels=int(roi.sum())))
        samples.extend((replay['depth_quantiles'][:,:,1][roi]/np.sqrt(K[0,0]*K[1,1])).tolist())
        np.savez_compressed(output/f'native/parent_{i:03d}.npz',**white,stock_black=black['stock_rgb'],
                            roi=roi,depth_quantiles=replay['depth_quantiles'])
        baseline[i]=dict(white=white['stock_rgb'],black=black['stock_rgb'],roi=roi,mass=mass,selected=cov)
    variants=[]
    if all(r['passed'] for r in calibration):
        for spec in specs:
            child,_,_,minor=controlled_asset(asset,spec,cfg)
            np.savez_compressed(output/f"native/{spec['name']}_parameters.npz",**child)
            rows=[];cover=[];cal=[];small_panels=[]
            for camera in cameras:
                i=camera['index'];base=baseline[i];K=np.array(camera['K']);w2c=np.array(camera['w2c'])
                white=native_render(child,K,w2c,size,size,1);black=native_render(child,K,w2c,size,size,0)
                replay=replay_native(white,size,size,minor,np.zeros(len(minor),bool),1)
                cal.append(dict(view=i,**calibration_metrics(white,black['stock_rgb'],replay)))
                mass=float(replay['selected'][base['roi']].sum(dtype=float))
                cover.append(dict(view=i,selected=base['selected'],minor=mass/base['mass'] if base['mass'] else 0.))
                np.savez_compressed(output/f"native/{spec['name']}_{i:03d}.npz",**white,
                    stock_black=black['stock_rgb'],depth_quantiles=replay['depth_quantiles'])
                for bg,key,state in [(1,'white',white),(0,'black',black)]:
                    rgb=state['stock_rgb'];original=base[key]
                    rows.append(dict(view=i,background=bg,**qualification_metrics(original,rgb,base['roi'])))
                    panels=[(f'{i} {key} parent',original),(spec['name'],rgb),('absolute error x10',np.abs(rgb-original)*10)]
                    save_sheet(output/f"full_resolution/{spec['name']}_{i:03d}_{key}.png",panels)
                    if i in cfg['visuals']['fixed_train'] or len(cameras)==1:
                        small_panels.extend([(label,cv2.resize(img,(200,200),interpolation=cv2.INTER_AREA)) for label,img in panels])
            # save_sheet supports rows; all frozen fixed views and both backgrounds.
            if small_panels:
                save_grid(output/f"{spec['name']}.png",small_panels,columns=3)
            eligibility=controlled_eligibility(rows,cover,cfg)
            eligibility['calibration_pass']=all(r['passed'] for r in cal)
            eligibility['passed']=eligibility['passed'] and eligibility['calibration_pass']
            variants.append(dict(**spec,rows=rows,coverage=cover,calibration=cal,eligibility=eligibility))
            if time.monotonic()-start>cfg['budget']['prerequisite_seconds_per_scene']:
                raise TimeoutError('preregistered prerequisite budget exceeded')
    delta=float(np.median(samples)) if samples else None
    valid=bool(all(r['passed'] for r in calibration) and delta is not None and np.isfinite(delta)
               and delta>0 and all(r['outside']<=cfg['native']['outside_mass_max'] for r in coverage))
    report=dict(calibration=calibration,coverage=coverage,delta=delta,box=[low.tolist(),high.tolist()],
                variants=variants,valid_parent_geometry=valid,elapsed_seconds=time.monotonic()-start)
    freeze_json(output/'qualification.json',report)
    return report
