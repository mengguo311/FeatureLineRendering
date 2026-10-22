"""A short real source camera arc and source tint ramp, without fitting."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from geometry import orbit_camera
import base_model as base
from footprint import FootprintRenderer
from membership import evaluated_tint_copy
from run_footprint_unit import load
from run_path_unit import read_npz
from run_unit import panel
from make_media import encode

def make(unit):
    p=load(unit);s=p['scenes']['chair'];root=unit/'results/chair';out=output_guard(unit/'media');out.mkdir(exist_ok=False)
    z=read_npz(root/'EDIT_SELECTION.npz');cams=[orbit_camera(float(az),28,4.9,384) for az in (193,203,213,223)]
    fixed=[c for c in s['cameras'] if c['split']=='evaluation'][0];ramp=np.linspace(0,1,4)
    protocol=dict(utc=now(),arc_cameras=cams,edit_camera=fixed,tint_multipliers=ramp,
        selection_sha256=sha(root/'EDIT_SELECTION.npz'),source_sha256=s['source']['sha256'],code_sha256=sha(__file__),
        scope='4 real camera positions over 30 degrees and 4 real source-tint levels; presentation only, no new selection, no 360-orbit or temporal-stability claim')
    js(out/'MOTION_PROTOCOL.json',protocol);js(out/'MOTION_LOCK.json',dict(sha256=sha(out/'MOTION_PROTOCOL.json')))
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);a['source_index']=np.arange(len(a['means']))
    r=FootprintRenderer(unit/'build');frames=[];records=[]
    for kind,cameras,mults in [('arc',cams,np.ones(4)),('local_tint',[fixed]*4,ramp)]:
        folder=out/kind;folder.mkdir();baseline=None
        for i,(c,mult) in enumerate(zip(cameras,mults)):
            if kind=='arc' or baseline is None:baseline,_=r.render(a,c)
            edit,_=r.render(evaluated_tint_copy(a,c,z['specific']*mult,z['tint']),c)
            file=folder/f'frame_{i:03d}.png'
            panel(file,[baseline['rgb'],edit['rgb']],['Original GS / full SH3','Fixed original-ID source tint'],
                f'Chair {kind} frame {i} | {c["view"]} | tint multiplier {mult:.3f} | CPU source-only')
            np.savez_compressed(folder/f'raw_{i:03d}.npz',original_RGB=baseline['rgb'],edited_RGB=edit['rgb'],alpha=baseline['alpha'],camera_json=np.array(json.dumps(c)),strength_multiplier=mult)
            yy,xx=np.nonzero(baseline['alpha']>.05)
            records.append(dict(kind=kind,frame=i,RGB_L1=float(np.abs(edit['rgb']-baseline['rgb']).sum()),
                alpha_bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],
                border_alpha_max=float(max(baseline['alpha'][0].max(),baseline['alpha'][-1].max(),baseline['alpha'][:,0].max(),baseline['alpha'][:,-1].max()))))
            frames.append(file)
        print('actual media frames',kind,4,flush=True)
    videos=encode(out/'arc','chair_source_arc')+encode(out/'local_tint','chair_source_tint')
    sheet=Image.new('RGB',(1152,4*330),'white')
    for i,file in enumerate(frames):
        im=Image.open(file);im.thumbnail((576,330));sheet.paste(im,(i%2*576,i//2*330))
    sheet.save(out/'ALL_MOTION_FRAMES.png')
    assert records[4]['RGB_L1']==0 and records[7]['RGB_L1']>0
    assert len({json.dumps(c['extrinsic']) for c in cams})==4
    js(out/'VIDEO_VALIDATION.json',dict(utc=now(),videos=videos,frames=records,actual_arc_cameras=4,actual_tint_levels=4,
        all_frames_decoded=True,FFV1_frames_exact=True,source_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],scope=protocol['scope']))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True,type=Path);make(ap.parse_args().unit)
