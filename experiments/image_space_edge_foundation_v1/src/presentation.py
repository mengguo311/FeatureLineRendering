"""Full-object media. Fixed native ROIs; all raw responses remain available."""
import hashlib,json,os,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from runtime import ART,OUT,ROOT,NATIVE,sha,scoped,atomic_json,guard
from boundary import ink,overlay
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n):return ImageFont.truetype(FONT,n)
def array_image(a):return Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8))
def save_image(path,a):
    p=scoped(path);tmp=p.with_name(p.stem+'.tmp'+p.suffix);im=array_image(a)
    if p.suffix in ['.jpg','.jpeg']:im.save(tmp,quality=96,subsampling=0)
    else:im.save(tmp)
    os.replace(tmp,p);return str(p.relative_to(ROOT))
def panel_sheet(panels,path,columns=None,size=800,title='',native=True):
    columns=columns or len(panels);rows=(len(panels)+columns-1)//columns
    header=44;top=46 if title else 0
    canvas=Image.new('RGB',(columns*size,rows*(size+header)+top),'white');draw=ImageDraw.Draw(canvas)
    if title:draw.text((12,10),title,font=font(22),fill='black')
    for i,(label,a) in enumerate(panels):
        x=(i%columns)*size;y=(i//columns)*(size+header)+top
        draw.text((x+8,y+6),label,font=font(16 if size>=400 else 11),fill='black')
        im=a if isinstance(a,Image.Image) else array_image(a)
        if im.size!=(size,size):im=im.resize((size,size),Image.Resampling.LANCZOS)
        canvas.paste(im,(x,y+header))
    p=scoped(path);canvas.save(p,quality=96,subsampling=0) if p.suffix=='.jpg' else canvas.save(p)
    return str(p.relative_to(ROOT))
def map_rgb(a,cmap='inferno'):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import cm
    return cm.get_cmap(cmap)(np.clip(a,0,1))[...,:3].astype(np.float32)
def profile_plot(profiles,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    p=profiles;valid=np.flatnonzero(p['valid']);invalid=np.flatnonzero(~p['valid'])
    # Deterministic spaced candidates, not hand annotated success examples.
    def spaced(ids,n=3):return ids[np.linspace(0,len(ids)-1,min(n,len(ids)),dtype=int)] if len(ids) else []
    selected=list(spaced(valid))+list(spaced(invalid))
    fig,axes=plt.subplots(2,3,figsize=(12,6),squeeze=False)
    for ax in axes.flat:ax.set_visible(False)
    for ax,j in zip(axes.flat,selected):
        ax.set_visible(True);x=p['offsets'];s=p['samples'][j]
        a=1/(1+np.exp(np.clip(-(x-p['center'][j])*4.394449/p['width'][j],-60,60)))
        fit=p['minus'][j]+a[:,None]*p['signed_contrast'][j]
        for c,color in enumerate(['r','g','b']):ax.plot(x,s[:,c],color=color);ax.plot(x,fit[:,c],color=color,ls='--',alpha=.6)
        ax.set_title(f"{'fit' if p['valid'][j] else 'detail/unknown'} xy={p['xy'][j].astype(int)}\nw={p['width'][j]:.1f} residual={p['residual'][j]:.3f} code={p['rejection'][j]}",fontsize=8)
        ax.set_ylim(0,1);ax.set_xlabel('normal offset / native pixels',fontsize=8)
    fig.suptitle('Observed RGB + bounded two-side monotone fit; no physical-edge labels')
    fig.tight_layout();pout=scoped(path);fig.savefig(pout,dpi=140);plt.close(fig)
    return str(pout.relative_to(ROOT))
def ffmpeg():
    p=NATIVE/'deps/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
    if not p.is_file():
        import imageio_ffmpeg
        p=Path(imageio_ffmpeg.get_ffmpeg_exe())
    return str(p)
def encode_video(frame_dir,path,width,height,count=33):
    ff=ffmpeg();p=scoped(path)
    subprocess.run([ff,'-y','-v','error','-threads','2','-framerate','12','-i',str(frame_dir/'%03d.png'),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(p)],check=True)
    # Stream every frame to avoid retaining hundreds of MB of decoded panels.
    proc=subprocess.Popen([ff,'-v','error','-threads','2','-i',str(p),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    hashes=[];nbytes=width*height*3
    while True:
        data=bytearray()
        while len(data)<nbytes:
            chunk=proc.stdout.read(nbytes-len(data))
            if not chunk:break
            data.extend(chunk)
        if not data:break
        if len(data)!=nbytes:raise RuntimeError('partial decoded frame')
        hashes.append(hashlib.sha256(data).hexdigest())
    if proc.wait()!=0 or len(hashes)!=count:raise RuntimeError('video incomplete')
    if len(set(hashes))!=count:raise RuntimeError('duplicate decoded panels')
    # Header topology demonstrates moov precedes mdat (faststart).
    blob=p.read_bytes();moov=blob.find(b'moov');mdat=blob.find(b'mdat')
    return dict(path=str(p.relative_to(ROOT)),sha256=sha(p),frames=count,decoded_frames=len(hashes),distinct_decoded_frames=len(set(hashes)),
                decoded_sha256=hashes,width=width,height=height,codec='H264',pixel_format='yuv420p',fps=12,faststart=0<moov<mdat)
