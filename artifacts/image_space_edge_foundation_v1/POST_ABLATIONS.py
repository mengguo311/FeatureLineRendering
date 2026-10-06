"""Expose existing RGB coherent component without profiles, from frozen fields.

This post-production diagnostic never re-tunes/re-renders any spatial method.
The saved detail layer is exactly the opponent tensor/ridge/tangent component
without profile acceptance/strength augmentation. It is an existing-component
control and prevents attributing its appearance to the new profile machinery.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,sha,atomic_json,guard
from campaign import metrics
from boundary import ink,overlay
from presentation import save_image,panel_sheet

def run():
    records=[];dev=[]
    for scene in ['lego','chair']:
        panels=[]
        for role,keys in [('dev',['r_007','r_033','r_059','r_086']),('fixed',['r_000','r_008','r_018','r_030'])]:
            for key in keys:
                guard(scene+'/no_profile_diagnostic/'+key)
                f=np.load(OUT/('dev_fields' if role=='dev' else 'fixed_fields')/scene/key/'fields.npz')
                a,b=metrics(f['detail']),metrics(f['union'])
                row=dict(scene=scene,role=role,key=key,no_profile=a,union=b,increased_pixels=int((f['union']>f['detail']+1e-6).sum()),
                         pixel_MAE=float(abs(f['union']-f['detail']).mean()),exact_field_source='frozen detail, gain1; original spatial orientation/confidence/ridges unchanged')
                (dev if role=='dev' else records).append(row)
                if role=='fixed':
                    z=np.load(OUT/'raw'/scene/role/key/'native.npz');p=ART/'media'/scene/'fixed'/key
                    save_image(p/'RGB_coherent_no_profiles_ink.png',ink(f['detail']))
                    save_image(p/'RGB_coherent_no_profiles_overlay.png',overlay(z['rgb'],f['detail']))
                    panels.extend([(key+' existing RGB coherent / no profiles',ink(f['detail'])),(key+' proposed RGB profile union',ink(f['union']))])
        panel_sheet(panels,ART/'media'/scene/'fourview_profile_ablation.png',columns=2,size=800,title='Frozen RGB coherent existing component vs profile union; every fixed view')
    a=sum(r['no_profile']['ink_area'] for r in dev);b=sum(r['union']['ink_area'] for r in dev)
    al=sum(r['no_profile']['ridge_length'] for r in dev);bl=sum(r['union']['ridge_length'] for r in dev)
    atomic_json(ART/'PROFILE_ABLATION.json',dict(source_sha256=sha(__file__),records=records,DEV=dev,
          DEV_area_ratio=a/b,DEV_length_ratio=al/bl,gain=1.,postproduction_diagnostic=True,
          scope='exposes frozen existing-component layer; no parameter selection after fixed view inspection; no novelty or superiority claim'))
if __name__=='__main__':run()
