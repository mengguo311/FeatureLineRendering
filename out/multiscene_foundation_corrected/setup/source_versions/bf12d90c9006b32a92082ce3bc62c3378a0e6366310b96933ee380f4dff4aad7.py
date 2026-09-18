"""Deterministic raw axial-glyph diagnostics; no curve or stroke organization."""
import hashlib
from pathlib import Path
import subprocess
import cv2
import numpy as np
from .foundation import project_jacobian


def spatial_order(rows,delta):
    def key(r):
        cell=np.floor(np.array(r['point'])/(delta*.5)).astype('i8')
        return (hashlib.sha256((':'.join(map(str,cell))).encode()).hexdigest(),str(r['query']))
    return sorted(rows,key=key)


def glyph_image(rows,camera,delta,layers=None,background=None):
    mask=np.zeros((400,400),'u1');stats=dict(glyphs=len(rows),in_frame=0,visible_segments=0,total_segments=4*len(rows),uncertain_segments=0)
    if rows:
        points=np.array([r['point'] for r in rows]);axes=np.array([r['axis'] for r in rows])
        # Canonical sign makes AA rasterization invariant to axial representation.
        indices=np.argmax(abs(axes),axis=1);sign=np.sign(axes[np.arange(len(axes)),indices]);axes*=sign[:,None]
        samples=(points[:,None]+delta*np.linspace(-1,1,5)[None,:,None]*axes[:,None]).reshape(-1,3)
        uv,z,_=project_jacobian(samples,camera['K'],camera['w2c']);inside=(z>0)&np.isfinite(uv).all(1)&(uv>=0).all(1)&(uv<=399).all(1)
        front=np.ones(len(samples)) if layers is None else layers.query(uv,z,delta)[0]
        valid=inside&(front>=.8);stats['uncertain_segments']=int(np.sum(inside&(front>.1)&(front<.8)))
        uv=np.nan_to_num(uv).reshape(-1,5,2);valid=valid.reshape(-1,5);inside=inside.reshape(-1,5)
        stats['in_frame']=int(inside.any(1).sum())
        for i in range(len(rows)):
            for j in range(4):
                if valid[i,j] and valid[i,j+1]:
                    a,b=np.round(uv[i,j:j+2]*256).astype(int)
                    cv2.line(mask,tuple(a),tuple(b),255,1,cv2.LINE_AA,shift=8);stats['visible_segments']+=1
    stats['ink_area']=float(mask.sum(dtype=float)/255)
    bg=np.ones((400,400,3),float) if background is None else np.asarray(background,float)
    return bg*(1-mask[:,:,None]/255.),stats


def ink_prefix(rows,cameras,delta,budget,cfg,layers=None):
    ordered=spatial_order(rows,delta)
    def ink(n):return float(np.mean([glyph_image(ordered[:n],c,delta,None if layers is None else layers[c['index']])[1]['ink_area'] for c in cameras]))
    if budget<=0:return [],dict(comparable=False,reason='zero PCA ink budget',relative_error=None,count=0)
    lo,hi=0,min(1,len(ordered))
    while hi<len(ordered) and ink(hi)<budget:
        lo=hi;hi=min(len(ordered),max(hi+1,hi*2))
    while lo<hi:
        mid=(lo+hi)//2
        if ink(mid)<budget:lo=mid+1
        else:hi=mid
    candidates=sorted(set([max(0,lo-1),lo]));values=[ink(n) for n in candidates]
    index=min(range(len(candidates)),key=lambda i:abs(values[i]-budget));n=candidates[index];actual=values[index]
    error=abs(actual-budget)/budget
    return ordered[:n],dict(count=n,budget=budget,ink_area=actual,relative_error=error,comparable=error<=cfg['visuals']['ink_tolerance'])


def orbit_cameras(target,radius,reference,cfg):
    cameras=[];target=np.asarray(target,float)
    for i in range(cfg['visuals']['video_frames']):
        phi=2*np.pi*i/cfg['visuals']['video_frames']+np.deg2rad(cfg['visuals']['phase_degrees'])
        elevation=np.deg2rad(cfg['visuals']['elevation_base']+cfg['visuals']['elevation_amplitude']*np.sin(2*phi))
        center=target+radius*np.array([np.cos(elevation)*np.cos(phi),np.cos(elevation)*np.sin(phi),np.sin(elevation)])
        forward=(target-center)/radius;right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);down=np.cross(forward,right)
        R=np.stack([right,down,forward]);w=np.eye(4);w[:3,:3]=R;w[:3,3]=-R@center
        cameras.append(dict(reference,w2c=w.tolist(),index=i))
    return cameras


def write_png(path,rgb):
    path=Path(path);data=np.round(np.clip(rgb,0,1)*255).astype('u1')[:,:,::-1]
    ok,encoded=cv2.imencode('.png',data,[cv2.IMWRITE_PNG_COMPRESSION,6])
    if not ok:raise RuntimeError('PNG encoder failed')
    with path.open('xb') as f:f.write(encoded.tobytes())


def write_video(path,frames,cfg):
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    ffmpeg='/home/u00134/bin/miniconda3/envs/ts_diffusion/bin/ffmpeg'
    command=[ffmpeg,'-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','400x400','-r',str(cfg['visuals']['fps']),'-i','-','-an','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','18',str(path)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE);count=0
    try:
        for frame in frames:
            if frame.shape!=(400,400,3):raise ValueError('video frame dimensions changed')
            process.stdin.write(np.round(np.clip(frame,0,1)*255).astype('u1').tobytes());count+=1
        process.stdin.close();error=process.stderr.read();process.stderr.close();code=process.wait()
        if code:raise RuntimeError(error.decode())
        if count!=cfg['visuals']['video_frames']:raise ValueError('wrong frame count')
    finally:
        if process.poll() is None:process.kill();process.wait()
