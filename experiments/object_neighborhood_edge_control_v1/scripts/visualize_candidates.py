"""Actual training-camera support and fixed-UID candidate diagrams."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,ART,EXP,atomic_json,resource_guard,sha

def run(scene):
    guard=resource_guard()
    import numpy as np
    import torch
    from PIL import Image,ImageDraw
    from renderer_adapter import load_checkpoint,make_camera,rgb,contribution
    from edge_profiles import linear_to_srgb
    from metrics import visible_band
    from data_access import config,frames,training_view
    cfg=config();d=OUT/'controls'/scene;identity=json.loads((d/'identity.json').read_text());sel=json.loads((d/'selection.json').read_text())
    m=load_checkpoint(OUT/'models'/scene/'chkpnt7000.pth');f=frames('train')[12];camera=make_camera(f)
    with torch.no_grad():image=rgb(m,camera).cpu().permute(1,2,0).numpy()
    labels=np.asarray(identity['label']);ids=np.asarray(identity['uid']);mu=m.get_xyz.detach().cpu().numpy()
    hp=np.c_[mu,np.ones(len(mu))]@camera.full_proj_transform.cpu().numpy()
    ndc=hp[:,:2]/hp[:,3:4];pixel=(ndc+1)*256-.5
    canvas=Image.new('RGB',(1536,550),(245,245,245));draw=ImageDraw.Draw(canvas)
    mass=np.load(d/'fixed_labels.npz')['band_mass'];info={}
    for i,key in enumerate(('C0','C1','B6')):
        pic=Image.fromarray(np.round(linear_to_srgb(image)*255).astype(np.uint8));painter=ImageDraw.Draw(pic)
        selected=np.isin(ids,sel['selections'][key]['uids'])
        for x,y in pixel[selected]:
            if np.isfinite([x,y]).all() and 0<=x<512 and 0<=y<512:
                painter.ellipse((x-1.5,y-1.5,x+1.5,y+1.5),fill=(255,220,0))
        canvas.paste(pic,(i*512,30));draw.text((i*512+12,8),f'{key}: {selected.sum()} stable UIDs, training camera',fill=(0,0,0))
        info[key]={'selected':int(selected.sum()),'mass_fraction':float(mass[selected].sum()/max(mass.sum(),1e-8))}
    p=ART/'figures'/f'{scene}_candidates.png';p.parent.mkdir(exist_ok=True);canvas.resize((1152,412)).save(p)
    atomic_json(EXP/f'results/manifests/{scene}_candidate_figure.json',{'scene':scene,'training_camera':f['id'],
        'selection_sha256':sha(d/'selection.json'),'identity_sha256':sha(d/'identity.json'),
        'figure_sha256':sha(p),'marker_note':'projected centres of actual selected fixed UIDs; not footprints or physical contact proof',
        'mass':info,'guard':guard})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('scene');run(p.parse_args().scene)
