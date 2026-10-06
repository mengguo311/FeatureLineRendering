"""Native-sized individual images and reviewable sheets with literal output labels."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

def rgb_image(a):
    a=np.asarray(a)
    if a.ndim==3 and a.shape[0]==3: a=a.transpose(1,2,0)
    if a.ndim==2: a=np.repeat(a[...,None],3,axis=2)
    return Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5))

def save_rgb(p,a): rgb_image(a).save(p,quality=93,subsampling=0)

def heat(a,scale=None):
    scale=max(float(np.max(a)),1e-12) if scale is None else max(scale,1e-12)
    v=np.clip(a/scale,0,1)
    return np.stack((v,np.sqrt(v)*.6,(1-v)*.15),axis=-1)

def sheet(path,items,cols=2,tile=800):
    rows=(len(items)+cols-1)//cols
    canvas=Image.new('RGB',(cols*tile,rows*(tile+42)),(246,246,246));draw=ImageDraw.Draw(canvas)
    for j,(label,img) in enumerate(items):
        img=rgb_image(img) if not isinstance(img,Image.Image) else img
        img=img.resize((tile,tile),Image.Resampling.LANCZOS)
        x=(j%cols)*tile;y=(j//cols)*(tile+42)
        canvas.paste(img,(x,y+42));draw.text((x+12,y+12),label,fill=(0,0,0))
    canvas.save(path,quality=90,subsampling=0)

def endpoint_overlay(original,p,n,centers,delta=2):
    img=rgb_image(original);d=ImageDraw.Draw(img)
    # Fixed regular subsampling, independent of scores.
    for q,nn in zip(p[::max(1,len(p)//100)],n[::max(1,len(p)//100)]):
        a=q-delta*nn;b=q+delta*nn
        d.line((a[1],a[0],b[1],b[0]),fill=(255,40,30),width=1)
        d.ellipse((a[1]-1,a[0]-1,a[1]+1,a[0]+1),fill=(40,240,20))
        d.ellipse((b[1]-1,b[0]-1,b[1]+1,b[0]+1),fill=(0,100,255))
    for y,x in centers:
        if 0<=x<img.width and 0<=y<img.height: d.ellipse((x-1,y-1,x+1,y+1),fill=(210,0,220))
    return img

def crops(path,items,p):
    if len(p)==0:return
    positions=p[np.linspace(0,len(p)-1,3,dtype=int)]
    out=[]
    for j,(y,x) in enumerate(positions):
        x=int(np.clip(x,64,736));y=int(np.clip(y,64,736))
        for label,img in items:
            im=rgb_image(img) if not isinstance(img,Image.Image) else img
            out.append((f'crop{j}: {label} x={x} y={y}',im.crop((x-64,y-64,x+64,y+64))))
    sheet(path,out,cols=len(items),tile=256)

def score_histogram(path,score,mass,selected,title):
    # PIL logarithmic histogram is sufficient for a small static artifact.
    img=Image.new('RGB',(800,350),'white');d=ImageDraw.Draw(img)
    vals=score[score>0]; bins=np.linspace(-6,2,65)
    hist,_=np.histogram(np.log10(np.maximum(vals,1e-12)),bins)
    picked,_=np.histogram(np.log10(np.maximum(score[selected],1e-12)),bins)
    maxh=max(1,hist.max());sx=700/len(hist)
    for j,(a,b) in enumerate(zip(hist,picked)):
        x=50+j*sx;d.rectangle((x,290-240*a/maxh,x+sx-1,290),fill=(170,180,200))
        d.rectangle((x,290-240*b/maxh,x+sx-1,290),fill=(220,30,30))
    d.text((30,12),title,fill='black')
    d.text((30,310),f'log10 ratio score -6 to +2; red selected n={len(selected)}; positive n={len(vals)}',fill='black')
    img.save(path,quality=90)
