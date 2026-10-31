"""Unit 2 engineering behavior; scientific kernels remain pinned and unchanged."""
from common import *
from pipeline import restore

def select_groups(groups):
    cross=[g for g in groups if g['old_parent_count']>1]
    by_count=sorted(cross,key=lambda g:(-g['kernels'],g['edge_id']))
    by_length=sorted(cross,key=lambda g:(-g['supported_length_p'],g['edge_id']))
    growth=[g for g in by_length if g['growth_gate']]
    selected={g['edge_id']:g for g in by_count[:3]+by_length[:3]+growth[:5]}
    for kind in ('line','polyline'):
        z=[g for g in growth if g['model']==kind]
        if z:selected[z[0]['edge_id']]=z[0]
    return list(selected.values())

def scene_contract(c,a,cams):
    assert len(a['means'])==c['kernel_count']
    assert [x['view'] for x in cams]==c['views']

def resume_state(e,s):restore(e,s)

def crop_family(paths,out_prefix):
    """Secondary display only: union of actual native RGB8 pixels; never rerender."""
    ims=[np.asarray(Image.open(p).convert('RGB')) for p in paths]
    assert len({im.shape for im in ims})==1
    mask=np.logical_or.reduce([np.any(im<254,axis=2) for im in ims]);yy,xx=np.nonzero(mask)
    if not len(xx):return dict(status='NO_VISIBLE_PIXELS',sources=[str(p) for p in paths])
    h,w=mask.shape;box=[max(0,int(xx.min())-16),max(0,int(yy.min())-16),min(w,int(xx.max())+17),min(h,int(yy.max())+17)];files=[]
    for p,im in zip(paths,ims):
        crop=Image.fromarray(im).crop(box);crop=crop.resize((crop.width*4,crop.height*4),Image.Resampling.NEAREST)
        dest=Path(str(out_prefix)+'_'+Path(p).stem+'.png');atomic(dest,lambda f,im=crop:im.save(f,format='PNG'));files.append(str(dest))
    return dict(status='SAVED',sources=[str(p) for p in paths],crop_box_xyxy=box,scale=4,resampling='NEAREST',files=files,primary_native_images_preserved=True)
