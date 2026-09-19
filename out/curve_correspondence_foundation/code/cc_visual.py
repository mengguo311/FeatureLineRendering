"""Actual curve projections and review media, never illustrative substitutes."""
import hashlib,pathlib,shutil
import cv2
import numpy as np
import imageio_ffmpeg
from cc import project_jacobian
from cc_io import write_json

def color_for(identity):
    b=hashlib.sha256(str(identity).encode()).digest();return tuple(int(40+x%170) for x in b[:3])

def rgb8(image):
    return np.ascontiguousarray(np.round(np.clip(image,0,1)*255).astype('u1'))

def write_png(path,image):
    path=pathlib.Path(path);a=np.asarray(image)
    if a.dtype!=np.uint8:a=np.round(np.clip(a,0,1)*255).astype('u1')
    ok,data=cv2.imencode('.png',a[:,:,::-1]);assert ok
    with path.open('xb') as f:f.write(data.tobytes())

def draw_polyline(image,points,color=(0,0,0),width=1):
    p=np.asarray(points,float)
    if len(p)<2:return
    valid=np.isfinite(p).all(1)&np.all(abs(p)<1e5,axis=1)
    indices=np.flatnonzero(valid)
    canvas=np.ascontiguousarray(image)
    for run in np.split(indices,np.flatnonzero(np.diff(indices)>1)+1):
        if len(run)>=2:cv2.polylines(canvas,[(p[run]*16).round().astype('i4')],False,color,width,cv2.LINE_AA,shift=4)
    if canvas is not image:image[:]=canvas

def curve_image(records,camera,size=400,color=False,background=None):
    image=np.full((size,size,3),255,'u1') if background is None else np.round(np.clip(background,0,1)*255).astype('u1').copy()
    for r in records:
        uv,_,_=project_jacobian(np.asarray(r['xyz']),camera['K'],camera['w2c']);draw_polyline(image,uv,color_for(r['id']) if color else (0,0,0))
    return image

def ink(image):return float(np.sum(1-np.asarray(image,float).mean(axis=2)/255))

def ink_prefix(records,cameras,budget,size=400):
    ordered=sorted(records,key=lambda r:hashlib.sha256(r['id'].encode()).hexdigest());selected=[];best=[];best_error=abs(budget);best_ink=0.
    canvases=[np.full((size,size,3),255,'u1') for _ in cameras]
    for r in ordered:
        selected.append(r)
        for canvas,c in zip(canvases,cameras):
            uv,_,_=project_jacobian(np.asarray(r['xyz']),c['K'],c['w2c']);draw_polyline(canvas,uv)
        value=float(np.mean([ink(c) for c in canvases]));error=abs(value-budget)
        if error<best_error:best=list(selected);best_error=error;best_ink=value
        if value>=budget:break
    return dict(ids=[r['id'] for r in best],ink=best_ink,budget=budget,relative_error=best_error/budget if budget else None,comparable=bool(budget and best_error/budget<=.05))

def contact_sheet(images,labels,columns=4):
    if not images:return np.full((64,400,3),255,'u1')
    h,w=images[0].shape[:2];rows=int(np.ceil(len(images)/columns));sheet=np.full((rows*(h+28),columns*w,3),255,'u1')
    for i,(im,label) in enumerate(zip(images,labels)):
        y=(i//columns)*(h+28);x=(i%columns)*w;sheet[y+28:y+28+h,x:x+w]=im
        cv2.putText(sheet,str(label)[:70],(x+5,y+19),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,0,0),1,cv2.LINE_AA)
    return sheet

def write_video(path,frames,fps):
    path=pathlib.Path(path)
    if path.exists():raise FileExistsError(path)
    iterator=iter(frames);first=next(iterator);h,w=first.shape[:2]
    writer=imageio_ffmpeg.write_frames(str(path),(w,h),fps=fps,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=7,macro_block_size=1,ffmpeg_log_level='error')
    writer.send(None);writer.send(np.ascontiguousarray(first))
    try:
        for frame in iterator:writer.send(np.ascontiguousarray(frame))
    finally:writer.close()

def blind_package(items,directory,seed):
    directory=pathlib.Path(directory);directory.mkdir(parents=True,exist_ok=False);rng=np.random.default_rng(seed);order=rng.permutation(len(items));key=[]
    for i,j in enumerate(order):
        identity,path=items[j];target=directory/f'{i+1:04d}.png';target.write_bytes(pathlib.Path(path).read_bytes());key.append(dict(file=target.name,identity=identity,source=str(path),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    (directory/'README.md').write_text('# Blinded review package\n\nImages are randomized; the identity key is stored outside this directory.\nReview shape coherence, internal structure, cross-part errors and clutter.\nEmpty images are actual empty outputs. No independent reviews have occurred.\n')
    return key
