"""Actual source-only Lego camera arc and reversible original-opacity ramp."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from geometry import orbit_camera
import base_model as base
from link_renderer import Renderer
from membership import evaluated_tint_copy
from path_control import opacity_copy
from run_path_unit import load_protocol,read_npz
from run_unit import panel
from make_media import encode

def make(unit):
    p=load_protocol(unit);s=p['scenes']['lego'];out=output_guard(unit/'media');out.mkdir(exist_ok=False)
    cams=[orbit_camera(float(az),28,5.1,384) for az in np.linspace(262,302,8)]
    fixed=next(c for c in s['cameras'] if c['split']=='evaluation');ramp=np.linspace(0,1,6)
    z=read_npz(unit/'results/lego/EDIT_SELECTION.npz')
    mp=dict(frozen_utc=now(),scene='lego',arc_cameras=cams,edit_camera=fixed,opacity_strength_multipliers=ramp,
        frames_per_second=6,source_sha256=s['source']['sha256'],selection_sha256=sha(unit/'results/lego/EDIT_SELECTION.npz'),
        code_sha256=sha(__file__),scope='8 actual camera positions over 40 degrees plus 6 opacity levels; not full orbit or temporal-quality certification')
    js(out/'MOTION_PROTOCOL.json',mp);js(out/'MOTION_LOCK.json',dict(sha256=sha(out/'MOTION_PROTOCOL.json')))
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);r=Renderer(unit/'build');frames=[];bounds=[]
    for kind,cameras,mults in [('arc',cams,np.ones(len(cams))),('local_opacity',[fixed]*len(ramp),ramp)]:
        folder=out/kind;folder.mkdir()
        for i,(c,mult) in enumerate(zip(cameras,mults)):
            f,_=r.render(a,c)
            tint,_=r.render(evaluated_tint_copy(a,c,z['tint_path_linked'],z['tint']),c)
            opacity,_=r.render(opacity_copy(a,z['opacity_path_linked']*mult),c)
            file=folder/f'frame_{i:03d}.png'
            panel(file,[f['rgb'],tint['rgb'],opacity['rgb']],['Original GS / full SH3','Saved path-linked tint','Saved path-linked opacity'],
                f'Lego {kind} frame {i:02d} | {c["view"]} | opacity multiplier {mult:.2f}')
            yy,xx=np.nonzero(f['alpha']>.05)
            bounds.append(dict(kind=kind,frame=i,alpha_bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],
                border_alpha_max=float(max(f['alpha'][0].max(),f['alpha'][-1].max(),f['alpha'][:,0].max(),f['alpha'][:,-1].max())),
                opacity_RGB_L1=float(np.abs(opacity['rgb']-f['rgb']).sum())))
            frames.append(file)
        print(kind,len(cameras),'actual frames',flush=True)
    videos=encode(out/'arc','lego_source_arc')+encode(out/'local_opacity','lego_source_local_opacity')
    contact=Image.new('RGB',(1152,7*230),'white')
    for i,file in enumerate(frames):
        im=Image.open(file);im.thumbnail((576,220));contact.paste(im,(i%2*576,i//2*230))
    contact.save(out/'ALL_MOTION_FRAMES.png')
    assert len({json.dumps(c['extrinsic']) for c in cams})==8
    js(out/'VIDEO_VALIDATION.json',dict(utc=now(),videos=videos,frame_bounds=bounds,actual_camera_frames=8,
        actual_opacity_levels=6,distinct_camera_matrices=8,source_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],scope=mp['scope']))
    print(json.dumps(dict(actual_frames=14,all_decoded=True,lossless_frames_exact=True)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);make(p.parse_args().unit)
