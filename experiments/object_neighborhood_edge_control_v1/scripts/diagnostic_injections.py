"""Independent single-cause fixtures on copies; never count as natural GS gains."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,ART,atomic_json,resource_guard,sha

def run():
    guard=resource_guard()
    import torch
    import numpy as np
    from renderer_adapter import load_checkpoint,make_camera,rgb,contribution
    from edge_profiles import linear_to_srgb
    from PIL import Image,ImageDraw
    initial=OUT/'models/panels_high/chkpnt7000.pth';original_sha=sha(initial)
    directory=OUT/'controls/panels_high';identity=json.loads((directory/'identity.json').read_text())
    labels=np.array(identity['label']);support=np.load(directory/'fixed_labels.npz');mass=support['band_mass']
    idx=int(np.argmax(np.where(labels==1,mass,-1)))
    frame=json.loads((EXP/'data/manifests/cameras.json').read_text())['splits']['val'][2]
    camera=make_camera(frame);m=load_checkpoint(initial)
    with torch.no_grad():before=rgb(m,camera).cpu().permute(1,2,0).numpy()
    base_diag=contribution(m,camera,labels)
    cases={};canvas=Image.new('RGB',(1280,570),(245,245,245));draw=ImageDraw.Draw(canvas)
    names=['original','scale_x2','label_flip','opacity_x0.2','coverage_delete']
    for k,name in enumerate(names):
        copy=load_checkpoint(initial);ell=labels.copy()
        with torch.no_grad():
            if name=='scale_x2':copy._scaling[idx]+=np.log(2)
            elif name=='label_flip':ell[idx]=2
            elif name=='opacity_x0.2':copy._opacity[idx]=torch.logit(copy.get_opacity[idx]*.2)
            elif name=='coverage_delete':copy._opacity[idx]=torch.logit(torch.tensor([1e-7],device='cuda'))
            image=rgb(copy,camera).cpu().permute(1,2,0).numpy()
        diag=contribution(copy,camera,ell)
        d=(image-before)**2
        cases[name]={'injected_fixture':True,'natural_performance':False,'modified_uid':identity['uid'][idx],
                     'rgb_mse_vs_original':float(d.mean()),
                     'alpha_mean_abs_change':float((diag['alpha']-base_diag['alpha']).abs().mean()),
                     'object_contribution_mean_abs_change':float((diag['objects']-base_diag['objects']).abs().mean()),
                     'only_cause':name}
        display=Image.fromarray(np.round(linear_to_srgb(image)*255).astype(np.uint8)).resize((256,256))
        canvas.paste(display,(k*256,30));draw.text((k*256+6,8),name,fill=(0,0,0))
        heat=np.clip(d.mean(-1)**.5*20,0,1);h=np.stack([heat,np.zeros_like(heat),np.zeros_like(heat)],-1)
        canvas.paste(Image.fromarray(np.round(h*255).astype(np.uint8)).resize((256,256)),(k*256,300))
    p=ART/'figures/diagnostic_single_cause_fixtures.png';canvas.save(p)
    assert sha(initial)==original_sha
    atomic_json(EXP/'results/tables/diagnostic_fixtures.json',{'scope':'injected diagnosis fixtures only, no natural error recovery claim',
        'camera':frame['id'],'original_checkpoint_sha256':original_sha,'original_unchanged':True,
        'cases':cases,'figure_sha256':sha(p),'guard':guard})

if __name__=='__main__':run()
