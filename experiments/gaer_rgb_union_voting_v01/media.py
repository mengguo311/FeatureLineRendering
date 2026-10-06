"""Native original subset views and explicitly separate diagnostic overlays."""
import os
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from runtime import scoped
def image(a):
    if a.ndim==3 and a.shape[0]==3:a=a.transpose(1,2,0)
    if a.ndim==2:a=np.repeat(a[...,None],3,2)
    return Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8))
def save(p,a):
    p=scoped(p);tmp=p.with_name(p.stem+'.tmp'+p.suffix);im=a if isinstance(a,Image.Image) else image(a)
    if p.suffix in ('.jpg','.jpeg'):im.save(tmp,quality=96,subsampling=0)
    else:im.save(tmp)
    os.replace(tmp,p)
def sheet(p,panels,cols=4,tile=400,title=''):
    rows=(len(panels)+cols-1)//cols;header=52;top=56
    im=Image.new('RGB',(cols*tile,rows*(tile+header)+top),'white');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',max(12,tile//27))
    d.text((10,10),title,font=font,fill='black')
    for j,(label,a) in enumerate(panels):
        x=(j%cols)*tile;y=(j//cols)*(tile+header)+top
        # Keep labels on two lines without hiding exact view/count information.
        parts=label.split('|');d.text((x+7,y+5),'\n'.join(parts[:2]),font=font,fill='black')
        a=a if isinstance(a,Image.Image) else image(a)
        if a.size!=(tile,tile):a=a.resize((tile,tile),Image.Resampling.LANCZOS)
        im.paste(a,(x,y+header))
    save(p,im)
def heat(a,scale=1.):
    x=np.clip(np.asarray(a)/scale,0,1)
    # white -> orange -> red -> purple. Diagnostic feature only.
    return np.stack([1-.4*x*x,1-.9*x,1-.75*x],-1)
def support_overlay(rgb,mass,gain=6.):
    a=np.clip(mass*gain,0,.9)[...,None]
    return np.clip(rgb,0,1)*(1-a)+np.array([.95,.08,.55])*a
def id_colors(ids):
    ids=np.asarray(ids,np.int64);v=np.maximum(ids,0)+1
    colors=np.stack([((v*1103515245+12345)%65536)/65535.,((v*214013+2531011)%65536)/65535.,((v*1664525+1013904223)%65536)/65535.],-1)
    return .15+.75*colors
def winner_images(rgb,winner,line):
    colors=id_colors(winner);valid=line&(winner>=0)
    standalone=np.ones_like(rgb);standalone[valid]=colors[valid];standalone[line&~valid]=[1,0,0]
    overlay=rgb.copy();overlay[valid]=.2*rgb[valid]+.8*colors[valid];overlay[line&~valid]=[1,0,0]
    return standalone,overlay
