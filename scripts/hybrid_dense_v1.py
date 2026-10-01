"""Automatic dense two-space ink pilot on archived F-only frozen-GS outputs.

Object layer: previously fitted fixed 3D curves (I arm), not a new fit.
Image layer: per-view RGB/depth/alpha edges; not a fixed asset.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path('/home/u00134/3dgs_line/tier1/out/direct_curve_global_fit_probe/run')
F = (1, 14, 27, 41, 53, 67, 79, 93)


def compose(object_ink, rgb_edges, depth_edges, alpha):
    """Keep generous foreground 2D evidence; attribute overlaps to 3D ink."""
    if not (object_ink.shape == rgb_edges.shape == depth_edges.shape == alpha.shape):
        raise ValueError('all layers must share native pixel dimensions')
    foreground = alpha >= 0.08
    # A small expansion preserves the actual silhouette instead of cutting it.
    foreground = cv2.dilate(foreground.astype('uint8'), np.ones((3,3),'uint8')) > 0
    obj = object_ink >= 0.30
    image = ((rgb_edges > 0) | (depth_edges > 0)) & foreground
    image &= ~(cv2.dilate(obj.astype('uint8'), np.ones((3,3),'uint8')) > 0)
    return dict(object=obj, image=image, hybrid=obj | image)


def image_edges(gs_rgb, depth_edge, alpha):
    rgb = np.uint8(np.round(np.clip(gs_rgb,0,1) * 255))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Two scales: retain detailed RGB contours and longer smooth boundaries.
    fine = cv2.Canny(cv2.GaussianBlur(gray,(3,3),0.65), 18, 48, L2gradient=True)
    coarse = cv2.Canny(cv2.GaussianBlur(gray,(5,5),1.4), 25, 65, L2gradient=True)
    silhouette = cv2.Canny(np.uint8(np.round(np.clip(alpha,0,1)*255)), 25, 65)
    return ((fine>0)|(coarse>0)).astype('uint8'), ((depth_edge>0)|(silhouette>0)).astype('uint8')


def white_ink(mask):
    return np.repeat(np.where(mask[:,:,None],0,255).astype('uint8'),3,axis=2)


def panel(image,title):
    h,w=image.shape[:2]
    result=Image.new('RGB',(w,h+34),'white')
    result.paste(Image.fromarray(image),(0,34))
    ImageDraw.Draw(result).text((12,10),title,fill='black')
    return result


def render(scene, index, output):
    if scene not in ('lego','chair') or index not in F:
        raise ValueError('only preregistered TRAIN-F lego/chair inputs are permitted')
    source = ROOT/scene
    with np.load(source/'fit'/'native'/f'{index}.npz') as data:
        gs_rgb=data['gs_rgb'].copy(); alpha=data['alpha'].copy()
        depth_edge=data['D.native_edge'].copy()
    with np.load(source/'evaluate'/'arrays'/f'F_{index}_I.npz') as data:
        obj=data['ink'].copy()
    rgb,depth=image_edges(gs_rgb,depth_edge,alpha)
    layers=compose(obj,rgb,depth,alpha)
    output.mkdir(parents=True,exist_ok=True)
    gs=np.uint8(np.round(np.clip(gs_rgb,0,1)*255))
    panels=[panel(gs,'Frozen vanilla GS RGB'),panel(white_ink(layers['object']),'Fixed 3D curve projections (prior I arm)'),panel(white_ink(layers['image']),'View-dependent RGB + depth + alpha'),panel(white_ink(layers['hybrid']),'Dense automatic composite')]
    sheet=Image.new('RGB',(gs.shape[1]*4,gs.shape[0]+34),'white')
    for i,p in enumerate(panels):sheet.paste(p,(i*gs.shape[1],0))
    sheet.save(output/f'{scene}_F{index}_layers.jpg',quality=92,subsampling=0)
    Image.fromarray(white_ink(layers['hybrid'])).save(output/f'{scene}_F{index}_hybrid.png')
    counts={k:int(v.sum()) for k,v in layers.items()}
    counts.update(scene=scene,view=index,resolution=list(alpha.shape),input_role='TRAIN-F; original GS checkpoint trained on TRAIN',object_source=str(source/'evaluate'/'arrays'/f'F_{index}_I.npz'),image_source=str(source/'fit'/'native'/f'{index}.npz'),thresholds={'rgb_fine':[18,48],'rgb_coarse':[25,65],'silhouette':[25,65],'foreground_alpha':0.08,'object_ink':0.30})
    (output/f'{scene}_F{index}.json').write_text(json.dumps(counts,indent=2)+'\n')
    return counts

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    for scene in ('lego','chair'):
        for index in (1,41):print(json.dumps(render(scene,index,args.output)),flush=True)
