"""Foreground-owned view contour layer on unchanged proxy hatch coverage.

Silhouette band/strength/depth threshold inherit render.py. Unlike its old
absolute rolled-depth edge, each depth jump belongs only to its nearer pixel.
This remains a reconstructed-proxy heuristic, not confirmed structural lines.
"""
import runtime
import numpy as np
from scipy import ndimage
from geometry import ray_surface
from render import _coverage
from hatching import validate_style


def contour_masks(depth,regions,supersample=2,region=4,threshold=.035):
    depth=np.asarray(depth);regions=np.asarray(regions)
    if depth.ndim!=2 or regions.shape!=depth.shape:raise ValueError('same2D depth and labels required')
    if supersample!=2 or threshold!=.035:raise ValueError('unit007 contour settings are frozen')
    hit=np.isfinite(depth)
    silhouette=hit & ~ndimage.binary_erosion(hit,iterations=supersample)
    occlusion=np.zeros(depth.shape,bool)
    for axis in (0,1):
        left=[slice(None),slice(None)];right=left.copy()
        left[axis]=slice(None,-1);right[axis]=slice(1,None)
        left,right=tuple(left),tuple(right)
        a,b=depth[left],depth[right];both=np.isfinite(a)&np.isfinite(b)
        delta=np.zeros_like(a);np.subtract(a,b,out=delta,where=both)
        jump=both&(np.abs(delta)>threshold)
        occlusion[left] |= jump&(a<b)
        occlusion[right] |= jump&(b<a)
    target=regions==region
    return dict(silhouette=silhouette&target,occlusion=occlusion&target)


def render_contours(mesh,paths,meta,camera):
    scale=2;style=meta['styles']['4'];validate_style(style)
    # Reuse the unchanged accepted capsule/depth code, not a new hatch backend.
    data=_coverage(mesh,{4:paths},meta['styles'],camera,scale)
    depth,face_image,regions,_=ray_surface(mesh,camera,scale)
    np.testing.assert_array_equal(regions[1::2,1::2],data['regions'])
    layers=[]
    for mask in data['coverage'][4].values():
        ink=np.zeros(mask.shape,np.float32);ink[mask]=style.get('ink_strength',.80);layers.append(ink)
    hatch=np.maximum.reduce(layers)
    masks=contour_masks(depth,regions)
    contour=(masks['silhouette']|masks['occlusion']).astype(np.float32)*.85
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    pair=dict(hatch=low(hatch),outlined=low(np.maximum(hatch,contour)))
    raster=dict(depth_hi=depth,face_hi=face_image,regions_hi=regions,hatch_hi=hatch,contour_hi=contour,
        silhouette_hi=masks['silhouette'],occlusion_hi=masks['occlusion'])
    hi=dict(regions=data['regions'],proxy=data['proxy'],contour_ink=low(contour),
        silhouette_ink=low(masks['silhouette'].astype(np.float32)*.85),
        occlusion_ink=low(masks['occlusion'].astype(np.float32)*.85),raster=raster,
        diagnostics=dict(silhouette_subpixels=int(masks['silhouette'].sum()),
            occlusion_subpixels=int(masks['occlusion'].sum()),union_subpixels=int((contour>0).sum()),
            contour_over_old_hatch_subpixels=int(((contour>0)&(hatch>0)).sum()),
            scope='Proxy first-hit owner only; depth threshold may include noisy holes or steep surface gradients.'))
    return pair,hi
