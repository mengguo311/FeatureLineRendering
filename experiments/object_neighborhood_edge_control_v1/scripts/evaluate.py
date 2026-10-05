"""Read-only evaluator. TEST and path require an immutable pre-evaluation seal."""
import argparse
import json
import time
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,ART,atomic_json,sha,resource_guard,code_identity

def evaluate(scene,method,group='val',save_figures=True):
    guard=resource_guard()
    import numpy as np
    import torch
    from renderer_adapter import load_checkpoint,make_camera,rgb,contribution
    from metrics import evaluate_frame,visible_band
    from edge_profiles import linear_to_srgb
    from PIL import Image,ImageDraw
    cfg=json.loads((EXP/'configs/pilot.json').read_text())
    directory=OUT/'controls'/scene;checkpoint=directory/f'{method}.pth'
    if group in ('test','path'):
        freeze=json.loads((EXP/'results/manifests/test_freeze.json').read_text())
        key=scene+'/'+method
        if key not in freeze['checkpoints'] or freeze['checkpoints'][key]!=sha(checkpoint):
            raise RuntimeError('TEST checkpoint does not match pre-evaluation freeze')
        if freeze['data_sha256']!=sha(EXP/'data/manifests/data_freeze.json'):
            raise RuntimeError('data freeze changed')
        for file,digest in freeze['evaluator_source_sha256'].items():
            if sha(Path(file))!=digest:raise RuntimeError('evaluator changed after freeze: '+file)
    identity_file=directory/(f'{method}_identity.json' if method.startswith('B4') else 'identity.json')
    identity=json.loads(identity_file.read_text());labels=np.asarray(identity['label'])
    m=load_checkpoint(checkpoint)
    initial=OUT/'models'/scene/f'chkpnt{cfg["training"]["iterations"]}.pth';original=load_checkpoint(initial)
    fs=json.loads((EXP/'data/manifests/cameras.json').read_text())['splits'][group]
    # Synchronized stock timing, identical hardware/resolution/warmup.
    cam=make_camera(fs[0],cfg['resolution'],cfg['camera_angle_x'])
    with torch.no_grad():
        for _ in range(10):rgb(m,cam)
        torch.cuda.synchronize();start=time.monotonic()
        for _ in range(30):rgb(m,cam)
        torch.cuda.synchronize();frame_ms=(time.monotonic()-start)/30*1000
    rows=[];frames_manifest=[];pathdir=OUT/'renders'/scene/method/group;pathdir.mkdir(parents=True,exist_ok=True)
    for i,frame in enumerate(fs):
        cam=make_camera(frame,cfg['resolution'],cfg['camera_angle_x'])
        with np.load(OUT/'data'/scene/group/frame['id']/'A_target.npz') as target:
            reference=target['rgb'];ids=target['instance'];depthgt=target['depth_ray_parameter']
        with torch.no_grad():
            im=rgb(m,cam).cpu().permute(1,2,0).numpy()
            before=rgb(original,cam).cpu().permute(1,2,0).numpy()
        diag=contribution(m,cam,labels)
        objects=diag['objects'].cpu().permute(1,2,0).numpy();alpha=diag['alpha'].cpu().numpy()
        depth=diag['depth_center_proxy'].cpu().numpy()
        metrics,profile,refprofile=evaluate_frame(im,reference,ids,objects,alpha,depth,depthgt,before)
        rows.append({'scene':scene,'method':method,'split':group,'view':frame['id'],'seed':cfg['seed'],
                     'metrics':metrics,'profile':profile,'reference_profile':refprofile})
        if save_figures:
            def display(x):return Image.fromarray(np.round(linear_to_srgb(x)*255).astype(np.uint8))
            parts=[display(reference),display(before),display(im)]
            montage=Image.new('RGB',(1536,550),(245,245,245));draw=ImageDraw.Draw(montage)
            for j,(name,part) in enumerate(zip(('GT A','B0 natural trained',method+' pilot seed1729'),parts)):
                montage.paste(part,(j*512,30));draw.text((j*512+12,8),name,fill=(0,0,0))
            png=pathdir/f'{i:04d}.png';montage.save(png)
            frames_manifest.append({'index':i,'camera_id':frame['id'],'camera_sha256':sha(OUT/'data'/scene/group/frame['id']/'A_target.npz'),
                                    'theta_deg':frame['theta_deg'],'png_sha256':sha(png)})
            if i==0:
                curated=ART/'figures';curated.mkdir(exist_ok=True)
                montage.resize((1152,412)).save(curated/f'{scene}_{method}_{group}.png')
                band,_=visible_band(ids)
                ys,xs=np.nonzero(band)
                if len(xs):
                    center=int(np.median(xs));crop=(max(0,center-32),180,min(512,center+32),330)
                    zoom=Image.new('RGB',(768,650),(245,245,245));d=ImageDraw.Draw(zoom)
                    for j,(name,part) in enumerate(zip(('GT A','B0',method),parts)):
                        zoom.paste(part.crop(crop).resize((256,600)),(j*256,30));d.text((j*256+8,8),name,fill=(0,0,0))
                    zoom.save(curated/f'{scene}_{method}_{group}_edge_zoom.png')
                overlay=display(im);arr=np.array(overlay);arr[band]=arr[band]//2+np.array([100,50,0],np.uint8)
                Image.fromarray(arr).save(curated/f'{scene}_{method}_{group}_band.png')
                display(np.clip(objects,0,1)).save(curated/f'{scene}_{method}_{group}_objects.png')
    keys=rows[0]['metrics'];means={}
    for k in keys:
        vals=[r['metrics'][k] for r in rows if isinstance(r['metrics'][k],(int,float)) and not isinstance(r['metrics'][k],bool)]
        means[k]=float(np.mean(vals)) if vals else None
    result={'scene':scene,'method':method,'split':group,'seed':cfg['seed'],'frame_count':len(rows),
        'gaussian_count':len(labels),'render_frame_ms':frame_ms,'warmup':10,'timing_repetitions':30,
        'mean_metrics':means,'rows':rows,'checkpoint_sha256':sha(checkpoint),
        'identity_sha256':sha(identity_file),'input_data_freeze_sha256':sha(EXP/'data/manifests/data_freeze.json'),
        'source':code_identity(),'guard':guard,'scope':'single-seed pilot; no formal/method superiority claim'}
    atomic_json(EXP/f'results/tables/{scene}_{method}_{group}.json',result)
    atomic_json(EXP/f'results/manifests/{scene}_{method}_{group}_frames.json',frames_manifest)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('method');p.add_argument('--split',default='val',choices=['val','test','path'])
    p.add_argument('--no-figures',action='store_true');a=p.parse_args();evaluate(a.scene,a.method,a.split,not a.no_figures)
