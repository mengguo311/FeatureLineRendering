"""New native renders, contribution vs removed-primitive subset, fixed-gain diffs."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from runtime import ROOT,ART,OUT,atomic_json,sha

def save_png(path,im):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    arr=np.asarray(im)
    if arr.ndim==2:arr=np.repeat(arr[...,None],3,2)
    Image.fromarray(np.round(np.clip(arr,0,1)*255).astype(np.uint8)).save(path)

def panel_sheet(panels,path,columns=4,size=384):
    rows=(len(panels)+columns-1)//columns
    canvas=Image.new('RGB',(columns*size,rows*(size+44)),(245,245,245));draw=ImageDraw.Draw(canvas)
    for j,(label,im) in enumerate(panels):
        x=(j%columns)*size;y=(j//columns)*(size+44)
        arr=np.asarray(im)
        if arr.ndim==2:arr=np.repeat(arr[...,None],3,2)
        tile=Image.fromarray(np.round(np.clip(arr,0,1)*255).astype(np.uint8)).resize((size,size),Image.Resampling.BICUBIC)
        canvas.paste(tile,(x,y+44));draw.text((x+5,y+4),label,fill=(0,0,0))
    Path(path).parent.mkdir(parents=True,exist_ok=True);canvas.save(path)

def synthetic_sheet(images,path):panel_sheet(images,path,columns=4,size=192)

def evidence_overlay(rgb,maps,ref):
    im=np.asarray(rgb).copy()
    unknown=maps['unknown']>.05
    im[unknown]=im[unknown]*.7+np.array([.5,.4,.5])*.3
    pil=Image.fromarray(np.round(np.clip(im,0,1)*255).astype(np.uint8));d=ImageDraw.Draw(pil)
    for s in ref['samples']:
        x,y=s['center'];nx,ny=s['normal'];color=(0,180,240) if s['class_name']=='outline' else (255,70,0)
        d.line([(x-12*nx,y-12*ny),(x+12*nx,y+12*ny)],fill=color,width=2)
        d.ellipse((x-3,y-3,x+3,y+3),outline=color,width=2)
    for f in ref['flat']:d.rectangle(f['roi'],outline=(0,220,60),width=2)
    return np.asarray(pil)/255.

def plot_profiles(path,sample,gt,b0,p,q):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from evidence import profile_vector
    fig,axes=plt.subplots(1,3,figsize=(12,3))
    t=np.linspace(-12,12,97)
    for j in range(3):
        for label,rgb in [('reference',gt),('baseline',b0),('+ delta',p),('- delta',q)]:
            axes[j].plot(t,profile_vector(rgb,sample,True)[:,j],label=label)
        axes[j].set_xlabel('fixed normal offset (native px)');axes[j].set_title('linear RGB'[7:]+str(j))
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(path,dpi=140);plt.close(fig)

def scene_view(scene,view,m,camera,baseline,sets,plus,minus,gain,model_sha):
    import torch
    from adapter import contribution,subset,render,numpy_image
    with np.load(ROOT/view['maps_path']) as z:maps={k:z[k] for k in z.files}
    key=view['entry']['key'];target=view['reference'];basepath=ART/'media'/scene/key;basepath.mkdir(parents=True,exist_ok=True)
    panels=[('original TRAIN reference RGB',maps['rgb']),('new full-SH3 native baseline',baseline),
            ('cyan AA / orange color / green flat / purple unknown',evidence_overlay(maps['rgb'],maps,target)),
            ('fixed evaluation band 2px',maps['band2'])]
    meta=dict(scene=scene,camera=view['entry']['camera'],camera_hash=view['entry']['camera_hash'],model_sha256=model_sha,
              view=key,panel_sources=[],diff_visual_gain=gain,subset_semantics='unselected primitives removed: unoccluded diagnostic, not actual alpha*T',
              contribution_semantics='all original primitives remain in traversal; selected feature 1, others 0; full-model T preserved',
              original_color_semantics='original fullSH3 native direction/clamp, original opacity/scale/rotation; white background',
              class_provenance=target['metadata'],human_visual_GO='PENDING')
    save_png(basepath/'baseline_native.png',baseline);save_png(basepath/'reference.png',maps['rgb'])
    for name,ids in sets.items():
        ids=np.asarray(ids,dtype=np.int64)
        with torch.no_grad():
            mass=contribution(m,camera,ids).cpu().numpy()
            only=numpy_image(render(subset(m,ids),camera)) if len(ids) else np.ones_like(baseline)
        save_png(basepath/f'{name}_contribution.png',mass);save_png(basepath/f'{name}_subset_original_color.png',only)
        panels.extend([(f'{name} contribution; N={len(ids)}',mass),(f'{name} subset removed; N={len(ids)}',only)])
        ids_path=ART/'selection_ids'/scene/f'{name}.json'
        if not ids_path.exists():atomic_json(ids_path,dict(model_sha256=model_sha,original_rows=ids.tolist(),count=len(ids)))
        meta['panel_sources'].append(dict(name=name,selected_count=len(ids),selected_original_row_ids=str(ids_path.relative_to(ROOT)),ids_sha256=sha(ids_path)))
    dp=plus-baseline;dm=minus-baseline
    save_png(basepath/'plus_raw.png',plus);save_png(basepath/'minus_raw.png',minus)
    # Lossless float differences are retained, in addition to visual display encoding.
    np.savez_compressed(basepath/'native_diffs_float32.npz',plus=dp.astype(np.float32),minus=dm.astype(np.float32))
    panels.extend([(f'+ DC diff centered .5; gain={gain}',.5+gain*dp),(f'- DC diff centered .5; gain={gain}',.5+gain*dm)])
    s=next((s for s in target['samples'] if s['class_name']=='clear_color_transition'),target['samples'][0] if target['samples'] else None)
    if s:
        cx,cy=np.round(s['center']).astype(int);sl=(slice(max(cy-24,0),min(cy+25,baseline.shape[0])),slice(max(cx-24,0),min(cx+25,baseline.shape[1])))
        panels.extend([('ROI native baseline',baseline[sl]),('ROI accepted subset',only[sl]),
                       ('ROI + diff common gain',(.5+gain*dp)[sl]),('ROI - diff common gain',(.5+gain*dm)[sl])])
        plot_profiles(basepath/'normal_profiles.png',s,maps['rgb'],baseline,plus,minus)
        meta['zoom_sample_id']=s['id']
    panel_sheet(panels,basepath/'sheet.png',columns=4,size=384)
    atomic_json(basepath/'SOURCE.json',meta)
    return str((basepath/'sheet.png').relative_to(ROOT))
