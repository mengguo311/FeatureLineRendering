#!/usr/bin/env python3
"""Post-hoc inspection ONLY. Reads completed outputs, never feeds selection.

Shows every selected bridge at its maximum visible-length frame, plus all 120
frames for the single preregistered selected target b71. These zoom diagnostics
are explicitly not the unselected full-video main result.
"""
import json
from pathlib import Path
import subprocess
import sys
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from src.common import Camera,project
from run_vrss import label


def train_targets():
    """Post-selection display of preregistered loci; no scoring or selection."""
    import torch
    from src import common,render,stroke_relations as drawing
    from run_vrss import scaled
    from run_gap_recovery import load_paths,checked_selection
    base=ROOT/'out/gap_recovery';p=base/'lego_dev'
    output=p/'preregistered_target_check.png'
    if output.exists():raise FileExistsError(output)
    m=json.loads((base/'MANIFEST.json').read_text());selection=checked_selection(m,'lego')
    g=common.load_gaussians('lego');keep=render.defloat_mask(g['mu'],g['opacity']);cams,_=common.load_cameras('lego')
    paths=load_paths(base/'audit/lego/candidates.npz');curves=load_paths(base/'audit/lego/hypotheses.npz')
    selected=[np.asarray(row['points']) for row in selection['variants']['object_image']['paths']]
    tiles=[];torch.set_num_threads(4)
    for v in [1,27,79]:
        cam=scaled(cams[v],400);gb=render.render_gbuffer(g,keep,cam)
        original=drawing.draw_paths(drawing.project_paths(drawing.densify(paths),cam,gb['depth']),np.ones(len(paths),bool),(400,400))
        added=drawing.draw_paths(drawing.project_paths(selected,cam,gb['depth']),np.ones(len(selected),bool),(400,400))
        full=np.minimum(original,added)
        rgb=cv2.imread(str(base/f'audit/lego/original_train_{v:03d}.png'))[26:,:400]
        for bid in [71,152,153]:
            uv,_=project(curves[bid],cam);x,y=np.clip(np.round(uv.mean(0)).astype(int),[22,22],[377,377])
            tiles.append(np.hstack([label(cv2.resize(im[y-22:y+23,x-22:x+23],(180,180),interpolation=cv2.INTER_NEAREST),f'{n} b{bid} TRAIN{v}') for n,im in zip(['RGB','original','frozen full'],[rgb,original,full])]))
    cv2.imwrite(str(output),np.vstack(tiles))


def read_video(path):
    cap=cv2.VideoCapture(str(path));frames=[]
    while True:
        ok,im=cap.read()
        if not ok:break
        frames.append(im)
    cap.release()
    if len(frames)!=120:raise RuntimeError('incomplete video')
    return frames


def main():
    branch=subprocess.check_output(['git','-C',str(ROOT),'branch','--show-current'],text=True).strip()
    if branch!='gap-recovery':raise RuntimeError('wrong branch')
    if sys.argv[1:]==['--train-targets']:
        train_targets();return
    p=ROOT/'out/gap_recovery/lego_dev'
    if (p/'inspection_index.json').exists():raise FileExistsError('inspection already generated')
    m=json.loads((p/'render_metrics.json').read_text());s=json.loads((p/'frozen_bridges.json').read_text())
    c=json.loads((p/'dev_cameras.json').read_text());cams=[Camera(c['K'],w,400,400) for w in c['w2c']]
    frames=read_video(p/'rgb_original_recovered.mp4');ablation=read_video(p/'ablation_original_object_full.mp4')
    debug=read_video(p/'bridge_debug_all.mp4')
    points={v['bridge_id']:np.asarray(v['points']) for variant in s['variants'].values() for v in variant['paths']}
    full=set(s['variants']['object_image']['selected_ids']);objs=set(s['variants']['object_only']['selected_ids'])
    tiles=[];index=[]
    for bid,pts in sorted(points.items()):
        lens=np.asarray([r['bridges_visible_length_px'][str(bid)] for r in m['per_frame']]);j=int(lens.argmax())
        uv,_=project(pts,cams[j]);x,y=np.clip(np.round(uv.mean(0)).astype(int),[16,16],[383,383])
        rgb=frames[j][26:,:400];orig=frames[j][26:,400:800];ob=ablation[j][26:,400:800];fu=frames[j][26:,800:]
        di=debug[j][26:,800:] if bid in full else debug[j][26:,400:800]
        columns=[]
        for name,im in zip(['RGB','original','object','full','DIAGNOSTIC'],[rgb,orig,ob,fu,di]):
            crop=im[y-16:y+17,x-16:x+17]
            columns.append(label(cv2.resize(crop,(165,165),interpolation=cv2.INTER_NEAREST),f'{name} b{bid} f{j}'))
        tiles.append(np.hstack(columns));index.append(dict(bridge_id=bid,frame=j,max_visible_length_px=float(lens.max()),
            visible_frames_gt1px=int((lens>1).sum()),object_only=bid in objs,object_image=bid in full))
    for page,start in enumerate(range(0,len(tiles),6)):
        cv2.imwrite(str(p/f'all_bridge_crops_{page:02d}.png'),np.vstack(tiles[start:start+6]))
    target=71;pts=points[target];tiles=[]
    for j,cam in enumerate(cams):
        uv,_=project(pts,cam);x,y=np.clip(np.round(uv.mean(0)).astype(int),[14,14],[385,385])
        images=[frames[j][26:,:400],frames[j][26:,400:800],frames[j][26:,800:]]
        tiles.append(np.hstack([label(cv2.resize(im[y-14:y+15,x-14:x+15],(87,87),interpolation=cv2.INTER_NEAREST),f'{n} f{j}') for n,im in zip(['RGB','orig','full'],images)]))
    for page,start in enumerate(range(0,120,40)):
        cv2.imwrite(str(p/f'b71_all_frames_{page:02d}.png'),np.vstack([np.hstack(tiles[i:i+4]) for i in range(start,start+40,4)]))
    (p/'inspection_index.json').write_text(json.dumps(dict(purpose='post-hoc complete bridge inspection, never method evidence',all_selected_bridges=index,target_71_all_120_frames=True),indent=2)+'\n')
    print(json.dumps(index,indent=2))

if __name__=='__main__':main()
