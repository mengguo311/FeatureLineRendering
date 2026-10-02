"""Overlay dense object/image ink on matching frozen-GS arc frames.
Each video frame is generated from its own archived camera raster, never from a still.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from hybrid_dense_v1 import ROOT, image_edges, compose

def validate_scene(scene):
    if scene not in ('lego','chair','drums','ficus'):
        raise ValueError('unsupported scene')
    return scene


def overlay_ink(rgb, object_mask, image_mask):
    if rgb.ndim != 3 or rgb.shape[2] != 3 or object_mask.shape != rgb.shape[:2] or image_mask.shape != rgb.shape[:2]:
        raise ValueError('RGB and both layers must have identical pixel geometry')
    out=rgb.copy()
    out[image_mask]=[10,10,10]  # dark image-space edges
    out[object_mask]=[255,90,20]  # orange fixed-object-space ink
    return out


def arc_frame(scene, arc, frame):
    root=ROOT/scene/'evaluate'
    key=f'arc{arc}_{frame:03d}'
    with np.load(root/'native'/f'{key}.npz') as data:
        gs=np.uint8(np.round(np.clip(data['gs_rgb'],0,1)*255))
        alpha=data['alpha'].copy()
        depth=data['D.native_edge'].copy()
    with np.load(root/'arrays'/f'{key}_I.npz') as data:
        obj=data['ink'].copy()
    rgb,dep=image_edges(gs.astype('float32')/255.0,depth,alpha)
    layers=compose(obj,rgb,dep,alpha)
    over=overlay_ink(gs,layers['object'],layers['image'])
    return gs,over,{k:int(v.sum()) for k,v in layers.items()}


def run(scene,arc,output):
    validate_scene(scene)
    if arc not in (0,1):raise ValueError('supported arcs only')
    root=ROOT/scene/'evaluate'
    frames=sorted(int(p.stem.split('_')[1]) for p in (root/'native').glob(f'arc{arc}_*.npz'))
    if not frames or frames != list(range(len(frames))):raise RuntimeError('arc frame list not complete and contiguous')
    output.mkdir(parents=True,exist_ok=True)
    h=w=800;fps=12
    main_path=output/f'{scene}_arc{arc}_overlay.mp4'
    compare_path=output/f'{scene}_arc{arc}_comparison.mp4'
    temp_main=main_path.with_name(main_path.stem+'.partial.mp4')
    temp_compare=compare_path.with_name(compare_path.stem+'.partial.mp4')
    main=cv2.VideoWriter(str(temp_main),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
    compare=cv2.VideoWriter(str(temp_compare),cv2.VideoWriter_fourcc(*'mp4v'),fps,(2*w,h))
    if not main.isOpened() or not compare.isOpened():raise RuntimeError('mp4 encoder not available')
    stats=[]
    try:
        for i in frames:
            gs,over,counts=arc_frame(scene,arc,i)
            if gs.shape!=(h,w,3):raise ValueError('unexpected frame dimensions')
            side=np.concatenate((gs,over),axis=1)
            cv2.putText(side,'Frozen GS RGB',(15,34),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),3,cv2.LINE_AA)
            cv2.putText(side,'Frozen GS RGB',(15,34),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),1,cv2.LINE_AA)
            cv2.putText(side,'3D orange + image-space black',(w+15,34),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),3,cv2.LINE_AA)
            cv2.putText(side,'3D orange + image-space black',(w+15,34),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),1,cv2.LINE_AA)
            main.write(cv2.cvtColor(over,cv2.COLOR_RGB2BGR))
            compare.write(cv2.cvtColor(side,cv2.COLOR_RGB2BGR))
            if i in (0,len(frames)//2,len(frames)-1):
                cv2.imwrite(str(output/f'{scene}_arc{arc}_frame{i:03d}.png'),cv2.cvtColor(over,cv2.COLOR_RGB2BGR))
            stats.append(dict(frame=i,**counts))
    finally:
        main.release();compare.release()
    # Check both encodes in full before exposing final paths.
    for partial,target,size in ((temp_main,main_path,(w,h)),(temp_compare,compare_path,(2*w,h))):
        cap=cv2.VideoCapture(str(partial)); seen=0
        while True:
            ok,img=cap.read()
            if not ok:break
            if (img.shape[1],img.shape[0]) != size:raise RuntimeError('decoded video dimension mismatch')
            seen+=1
        cap.release()
        if seen != len(frames):raise RuntimeError(f'incomplete decode {partial}: {seen}/{len(frames)}')
        partial.replace(target)
    manifest=dict(scene=scene,arc=arc,frames=len(frames),fps=fps,source_native=str(root/'native'),source_object_ink=str(root/'arrays'),method='matching-camera frozen GS RGB + existing fixed-3D I ink + new RGB/depth/alpha image edges; no reprojection shift',frame_stats=stats,limitations='No temporal transport; same per-frame detector on each actual raster; earlier fixed curve I arm was NO_GO; no TEST or mesh.')
    (output/f'{scene}_arc{arc}_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(scene=scene,arc=arc,frames=len(frames),main=str(main_path),comparison=str(compare_path))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--arc',type=int,default=0);p.add_argument('--scenes',nargs='+',default=['lego','chair']);args=p.parse_args()
    for scene in args.scenes:run(scene,args.arc,args.output)
