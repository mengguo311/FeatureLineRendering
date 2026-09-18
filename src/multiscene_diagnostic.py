"""Post-hoc resolution diagnosis, explicitly incapable of assigning eligibility."""
import hashlib
from pathlib import Path
import cv2
import numpy as np
from .foundation import freeze_json,native_render,qualification_metrics,save_sheet
from .multiscene_qualification import save_grid


def resolution_diagnostic(asset,cameras,output,base_size=400,source_size=800):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'full_resolution').mkdir();rows=[];panels=[]
    def metrics(a,b,roi):
        values=qualification_metrics(a,b,roi)
        return {key:value for key,value in values.items() if key not in ['passed','thresholds']}
    for camera in cameras:
        p=Path(camera['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=camera['sha256']:raise ValueError('photo hash changed')
        rgba=cv2.imread(str(p),cv2.IMREAD_UNCHANGED)[:,:,[2,1,0,3]].astype(float)/255
        if rgba.shape[:2]!=(source_size,source_size):raise ValueError('unexpected source resolution')
        K=np.array(camera['K']);K[:2]*=source_size/base_size
        K[0,2]=K[1,2]=(source_size-1)/2
        i,split=camera['index'],camera['split'];roi=rgba[:,:,3]>=.5
        small_roi=cv2.resize(rgba[:,:,3],(base_size,base_size),interpolation=cv2.INTER_AREA)>=.5
        for bg in [0,1]:
            rgb=native_render(asset,K,camera['w2c'],source_size,source_size,bg)['stock_rgb']
            gt=rgba[:,:,:3]*rgba[:,:,3:]+bg*(1-rgba[:,:,3:])
            small=cv2.resize(rgb,(base_size,base_size),interpolation=cv2.INTER_AREA)
            gt_small=cv2.resize(gt,(base_size,base_size),interpolation=cv2.INTER_AREA)
            rows.append(dict(view=i,split=split,background=bg,native_metrics=metrics(gt,rgb,roi),
                             downsampled_metrics=metrics(gt_small,small,small_roi)))
            name=f'{split}_{i:03d}_{bg}'
            save_sheet(output/f'full_resolution/{name}_native.png',[(f'stock {source_size}px',rgb)])
            comparison=[(f'{split} {i} bg{bg} GT',gt_small),(f'{source_size} to {base_size}',small),('absolute error x5',abs(small-gt_small)*5)]
            save_sheet(output/f'full_resolution/{name}_comparison.png',comparison)
            if i in [1,27,53,79] or len(cameras)==1:
                panels.extend([(title,cv2.resize(im,(200,200),interpolation=cv2.INTER_AREA)) for title,im in comparison])
    if panels:save_grid(output/'comparison.png',panels,3)
    result=dict(purpose='post-hoc resolution diagnosis; no qualification or foundation inference',
        native_size=source_size,comparison_size=base_size,principal_point=(source_size-1)/2,rows=rows)
    freeze_json(output/'diagnostic.json',result)
    return result
