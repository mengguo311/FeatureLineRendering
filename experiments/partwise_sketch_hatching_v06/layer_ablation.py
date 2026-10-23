"""One ablation: fixed original-GS links and fixed paths, change direction layers."""
import runtime
import numpy as np
from scipy import ndimage
from render import _coverage
from geometry import project

def combine_coverage(coverage,strength,supersample=2):
    if set(coverage)!={0,1}: raise ValueError('this comparison needs the two saved layers')
    ink={}
    for k,mask in coverage.items():
        a=np.zeros(mask.shape,np.float32);a[mask]=strength;ink[k]=a
    h,w=ink[0].shape;s=supersample
    low=lambda x:x.reshape(h//s,s,w//s,s).mean((1,3))
    return dict(cross=low(np.maximum(ink[0],ink[1])),base=low(ink[0]),second=low(ink[1]))

def render_pair(mesh,paths,meta,camera):
    data=_coverage(mesh,{4:paths},meta['styles'],camera,2)
    pair=combine_coverage(data['coverage'][4],meta['styles']['4'].get('ink_strength',.8),2)
    return pair,{k:v for k,v in data.items() if k!='coverage'}

def match_scales(masses):
    if set(masses)!={'cross','base'} or min(masses.values())<=0: raise ValueError('both arms need visible BUILD ink')
    budget=.95*min(masses.values())
    return {k:budget/v for k,v in masses.items()},budget

def ink_shape(alpha,target):
    """Image-space topology diagnostics, not surface/path continuity ground truth."""
    out={}
    for name,threshold in [('nonzero',1/255),('visible',.05)]:
        mask=(alpha>threshold)&target
        labels,n=ndimage.label(mask,np.ones((3,3),bool))
        sizes=np.bincount(labels.ravel())[1:]
        out[name]=dict(pixels=int(mask.sum()),components=int(n),
            small_components_le4=int((sizes<=4).sum()),
            small_component_pixels=int(sizes[sizes<=4].sum()),
            target_fraction=float(mask.sum()/max(target.sum(),1)))
    return out

def projected_length(paths,camera,alpha,active_layers):
    """Sample fixed path centerlines every <=0.5px against rendered ink.

    Includes occluded samples in the denominator; other strokes may overlap a
    sample. This is a rendered-support length proxy, not per-stroke visibility GT.
    """
    total=visible=0.;samples=hits=0;stroke_hits={}
    for points,layer,stroke in zip(paths['points'],paths['layer_id'],paths['stroke_id']):
        if int(layer) not in active_layers: continue
        uv,z=project(points,camera)
        if (z<=.2).any(): continue
        length=float(np.linalg.norm(uv[1]-uv[0]));n=max(1,int(np.ceil(length/.5)))
        xy=np.rint(uv[0]+((np.arange(n)+.5)/n)[:,None]*(uv[1]-uv[0])).astype(int)
        inside=(xy[:,0]>=0)&(xy[:,1]>=0)&(xy[:,0]<alpha.shape[1])&(xy[:,1]<alpha.shape[0])
        good=np.zeros(n,bool);good[inside]=alpha[xy[inside,1],xy[inside,0]]>.05
        total+=length;visible+=length*good.mean();samples+=n;hits+=int(good.sum())
        stroke_hits[int(stroke)]=stroke_hits.get(int(stroke),False) or bool(good.any())
    return dict(projected_length_pixels=total,ink_supported_length_pixels=visible,
        supported_fraction=visible/max(total,1e-30),samples=samples,ink_supported_samples=hits,
        active_stroke_ids=len(stroke_hits),stroke_ids_with_rendered_support=sum(stroke_hits.values()),
        scope='Centerline samples against actual alpha>.05; overlap can credit another stroke; no independent visibility or attachment GT.')
