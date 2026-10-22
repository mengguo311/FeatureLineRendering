"""Actual changing-camera source-GS arc and fixed-camera kernel tint ramp."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,subprocess
import numpy as np
from PIL import Image,ImageDraw
from geometry import orbit_camera
import base_model as base
from link_renderer import Renderer
from membership import load_binding,evaluated_tint_copy
from run_unit import panel

FFMPEG=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_p0p1_v01/.runtime_p0/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')

def encode(folder,name):
    files=sorted(folder.glob('frame_*.png'));im=Image.open(files[0]);w,h=im.size
    result=[]
    for ext,codec,pix in [('mkv','ffv1','bgr0'),('mp4','libx264','yuv420p')]:
        dest=folder.parent/(name+'.'+ext)
        cmd=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-filter_threads','1','-framerate','6','-i',str(folder/'frame_%03d.png'),
             '-c:v',codec,'-pix_fmt',pix,'-threads','1','-y',str(dest)]
        enc=subprocess.run(cmd,capture_output=True,text=True,timeout=90);enc.check_returncode()
        dec=[str(FFMPEG),'-nostdin','-v','error','-threads','1','-i',str(dest),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
        decoded=subprocess.run(dec,capture_output=True,timeout=90);decoded.check_returncode()
        frames=np.frombuffer(decoded.stdout,np.uint8).reshape(-1,h,w,3);assert len(frames)==len(files)
        errors=[]
        for f,path in zip(frames,files):
            ref=np.asarray(Image.open(path).convert('RGB'));err=float(np.abs(f.astype(float)-ref).mean());errors.append(err)
            if ext=='mkv':np.testing.assert_array_equal(f,ref)
        result.append(dict(file=str(dest),sha256=sha(dest),encoded_frames=len(files),decoded_frames=len(frames),
            lossless_exact=ext=='mkv',frame_MAE_8bit=errors,encode_command=cmd,decode_command=dec,encode_returncode=enc.returncode,decode_returncode=decoded.returncode))
    return result

def make(unit):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text());out=unit/'media';out.mkdir(exist_ok=False)
    cams=[orbit_camera(float(az),28,4.9,384) for az in np.linspace(43,133,12)]
    ramp=np.linspace(0,1,6)
    # Motion is presentation replay, frozen before drawing; no membership changes.
    mp=dict(frozen_utc=now(),source_sha256=p['source']['sha256'],binding_sha256=sha(unit/'results/SOURCE_BINDING.npz'),
        selection_sha256=sha(unit/'results/EDIT_SELECTION.npz'),code_sha256=sha(__file__),arc_cameras=cams,
        edit_camera=cams[0],edit_strength_multipliers=ramp,frames_per_second=6,
        scope='12 actual camera positions over a 90-degree arc, not a 360 orbit; 6 actually rerendered tint levels, not UI recording or temporal certification')
    js(out/'MOTION_PROTOCOL.json',mp);js(out/'MOTION_LOCK.json',dict(sha256=sha(out/'MOTION_PROTOCOL.json')))
    a=base.load_source(p['source']['original_ply'],p['source']['sha256']);load_binding(unit/'results/SOURCE_BINDING.npz',p['source']['sha256'],len(a['means']))
    with np.load(unit/'results/EDIT_SELECTION.npz') as z:strength=z['linked'];tint=z['tint']
    r=Renderer(unit/'build');frames=[];bounds=[]
    for name,cameras,mults in [('arc',cams,np.ones(12)),('local_edit',[cams[0]]*6,ramp)]:
        folder=out/name;folder.mkdir();baseframe=None
        for i,(c,mult) in enumerate(zip(cameras,mults)):
            if name=='arc' or baseframe is None:baseframe,_=r.render(a,c)
            edit,_=r.render(evaluated_tint_copy(a,c,strength*mult,tint),c)
            file=folder/f'frame_{i:03d}.png'
            panel(file,[baseframe['rgb'],edit['rgb']],['Original GS / full SH3','Linked ORIGINAL Gaussian tint'],
                f'{name} frame {i:02d} | {c["view"]} | tint multiplier {mult:.2f} | CPU source-only')
            yy,xx=np.nonzero(baseframe['alpha']>.05)
            bounds.append(dict(kind=name,frame=i,alpha_gt_005_bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],
                border_alpha_max=float(max(baseframe['alpha'][0].max(),baseframe['alpha'][-1].max(),baseframe['alpha'][:,0].max(),baseframe['alpha'][:,-1].max()))))
            frames.append((name,i,file))
        print('rendered',name,len(cameras),flush=True)
    videos=encode(out/'arc','source_arc')+encode(out/'local_edit','source_local_edit')
    thumbs=[]
    for name,i,file in frames:
        im=Image.open(file);im.thumbnail((576,330));thumbs.append(im.copy())
    sheet=Image.new('RGB',(576*3,330*6),'white')
    for i,im in enumerate(thumbs):sheet.paste(im,(i%3*576,i//3*330))
    sheet.save(out/'ALL_MOTION_FRAMES.png')
    assert len({json.dumps(c['extrinsic']) for c in cams})==12
    js(out/'VIDEO_VALIDATION.json',dict(utc=now(),videos=videos,frame_bounds=bounds,distinct_arc_cameras=12,
        same_saved_source_ID_strengths=True,PLY_unchanged=sha(p['source']['original_ply'])==p['source']['sha256'],
        scope=mp['scope']))
    print(json.dumps(dict(arc_frames=12,edit_frames=6,all_decoded=True,all_lossless_exact=True)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);make(p.parse_args().unit)
